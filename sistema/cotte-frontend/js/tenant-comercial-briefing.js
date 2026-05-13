/* tenant-comercial-briefing.js — Briefing Diário IA */
(function () {
  'use strict';

  var CACHE_KEY = function () { return 'briefing_cache_' + new Date().toISOString().slice(0, 10); };
  var ESTADO_KEY = function () { return 'briefing_estado_' + new Date().toISOString().slice(0, 10); };

  var PRIORIDADE_CONFIG = {
    urgente:     { label: '🔥 URGENTE',      cor: '#ef4444', fundo: '#fef2f2', borda: '#fca5a5' },
    hoje:        { label: '📅 HOJE',          cor: '#d97706', fundo: '#fffbeb', borda: '#fed7aa' },
    esta_semana: { label: '📆 ESTA SEMANA',  cor: '#6366f1', fundo: '#f5f3ff', borda: '#c4b5fd' },
  };

  var ACAO_LABEL = {
    mensagem_whatsapp: '💬 WhatsApp',
    mensagem_email:    '📧 Email',
    mover_etapa:       '🔄 Pipeline',
    nenhuma:           '',
  };

  var ETAPA_LABELS = {
    novo:               'Novo',
    contato_iniciado:   'Contato',
    proposta_enviada:   'Proposta',
    negociacao:         'Negociação',
    fechado_ganho:      'Ganho',
    fechado_perdido:    'Perdido',
  };

  var _dados = null;
  var _estado = {};
  var _templates = null;

  function _carregarEstado() {
    try { _estado = JSON.parse(localStorage.getItem(ESTADO_KEY())) || {}; }
    catch (e) { _estado = {}; }
  }

  function _salvarEstado() {
    localStorage.setItem(ESTADO_KEY(), JSON.stringify(_estado));
  }

  function _carregarCache() {
    try {
      var raw = localStorage.getItem(CACHE_KEY());
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function _salvarCache(dados) {
    localStorage.setItem(CACHE_KEY(), JSON.stringify(dados));
  }

  async function _carregarTemplates(tipo, canal) {
    if (_templates) return _templates;
    try {
      var params = '?tipo=' + tipo + '&canal=' + canal;
      var res = await window.ApiService.get('/tenant/comercial/templates' + params);
      _templates = res || [];
      return _templates;
    } catch (e) {
      console.error('[BriefingIA] Erro ao carregar templates:', e);
      return [];
    }
  }

  async function _fetchBriefing(forcar) {
    if (!forcar) {
      var cache = _carregarCache();
      if (cache) return cache;
    }
    var res = await window.ApiService.get('/tenant/comercial/leads/briefing');
    if (res && res.success && res.data) {
      _salvarCache(res.data);
      return res.data;
    }
    throw new Error('Resposta inválida do servidor');
  }

  function _esc(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _scoreLabel(score) {
    var m = { quente: '🔴 Quente', morno: '🟡 Morno', frio: '🔵 Frio' };
    return m[score] || score;
  }

  function _etapaLabel(etapa) {
    if (!etapa) return '';
    if (window.STATUS_LABELS && window.STATUS_LABELS[etapa]) return window.STATUS_LABELS[etapa];
    return ETAPA_LABELS[etapa] || etapa.replace(/_/g, ' ');
  }

  function _renderProgressBar(concluidos, total) {
    if (total === 0) return '';
    var pct = Math.round((concluidos / total) * 100);
    return '<div class="briefing-progress-bar"><div class="briefing-progress-fill" style="width:' + pct + '%"></div></div>' +
           '<p class="briefing-progress-label">' + concluidos + ' de ' + total + ' ações concluídas hoje</p>';
  }

  function _contar() {
    if (!_dados || !_dados.items) return { concluidos: 0, total: 0 };
    var total = _dados.items.filter(function (i) { return _estado[i.lead_id] !== 'pulado'; }).length;
    var concluidos = _dados.items.filter(function (i) { return _estado[i.lead_id] === 'concluido'; }).length;
    return { concluidos: concluidos, total: total };
  }

  function _renderCard(item) {
    var cfg = PRIORIDADE_CONFIG[item.prioridade] || PRIORIDADE_CONFIG.hoje;
    var acaoLabel = ACAO_LABEL[item.tipo_acao] || '';
    var concluido = _estado[item.lead_id] === 'concluido';

    var esmaecidoAttr = concluido ? ' style="opacity:0.55;pointer-events:none"' : '';
    var concluidoBadge = concluido
      ? '<div style="color:#10b981;font-size:0.8rem;margin-top:6px">✅ Concluído</div>' : '';

    var valorStr = item.valor_proposto > 0
      ? ' · R$ ' + Number(item.valor_proposto).toLocaleString('pt-BR', { minimumFractionDigits: 0 }) + '/mês'
      : '';

    var rascunhoHtml;
    if (item.tipo_acao === 'mover_etapa') {
      rascunhoHtml = '<div class="briefing-motivo" style="background:' + cfg.fundo + ';border:1px solid ' + cfg.borda + '">' +
        '<strong>IA sugere:</strong> ' + _esc(item.motivo) + '</div>';
    } else if (item.rascunho) {
      rascunhoHtml = '<div class="briefing-rascunho" id="rascunho-' + item.lead_id + '">' + _esc(item.rascunho) + '</div>';
    } else {
      rascunhoHtml = '<div class="briefing-rascunho briefing-sem-rascunho">' +
        (item.motivo ? _esc(item.motivo) : 'Sem rascunho disponível.') + '</div>';
    }

    var botoesHtml = '';
    if (!concluido) {
      if (item.tipo_acao === 'mover_etapa') {
        botoesHtml =
          '<button class="briefing-btn-enviar" onclick="BriefingIA.confirmarEtapa(' + item.lead_id + ',\'' + _esc(item.etapa_sugerida || '') + '\')">✓ Mover etapa</button>' +
          '<button class="briefing-btn-ver" onclick="BriefingIA.verLead(' + item.lead_id + ')">Ver lead</button>' +
          '<button class="briefing-btn-pular" onclick="BriefingIA.pular(' + item.lead_id + ')">✗ Pular</button>';
      } else {
        var canalFiltro = item.tipo_acao === 'mensagem_email' ? 'email' : 'whatsapp';
        botoesHtml =
          '<button class="briefing-btn-campanha" onclick="BriefingIA.campanhaRapida(' + item.lead_id + ',\'' + item.tipo_acao + '\')">🚀 Campanha</button>' +
          '<button class="briefing-btn-enviar" onclick="BriefingIA.enviar(' + item.lead_id + ',\'' + item.tipo_acao + '\')">✓ Enviar agora</button>' +
          '<button class="briefing-btn-template" onclick="BriefingIA.selecionarTemplate(' + item.lead_id + ',\'' + canalFiltro + '\')">📋 Template</button>' +
          '<button class="briefing-btn-editar" onclick="BriefingIA.editar(' + item.lead_id + ')">✎ Editar</button>' +
          '<button class="briefing-btn-pular" onclick="BriefingIA.pular(' + item.lead_id + ')">✗ Pular</button>';
      }
    }

    return '<div class="briefing-card" id="briefing-card-' + item.lead_id + '" data-lead-id="' + item.lead_id + '"' +
      ' style="border-left:4px solid ' + cfg.borda + '"' + esmaecidoAttr + '>' +
      '<div class="briefing-card-header">' +
        '<div>' +
          '<span class="briefing-badge" style="background:' + cfg.fundo + ';color:' + cfg.cor + '">' + cfg.label + '</span>' +
          (item.dias_sem_contato ? '<span style="font-size:0.72rem;color:#94a3b8;margin-left:6px">' + item.dias_sem_contato + ' dias sem contato</span>' : '') +
          '<h4 class="briefing-lead-nome">' + _esc(item.empresa || item.nome) + '</h4>' +
          '<span class="briefing-lead-info">' + _esc(item.nome) + ' · ' + _scoreLabel(item.score) + ' · ' + _etapaLabel(item.etapa) + valorStr + '</span>' +
        '</div>' +
        '<span class="briefing-acao-label">' + acaoLabel + '</span>' +
      '</div>' +
      rascunhoHtml +
      '<div class="briefing-actions">' + botoesHtml + '</div>' +
      concluidoBadge +
    '</div>';
  }

  function _atualizarBadge() {
    var badge = document.getElementById('badge-briefing');
    if (!badge || !_dados || !_dados.items) return;
    var pendentes = _dados.items.filter(function (i) {
      return _estado[i.lead_id] !== 'concluido' && _estado[i.lead_id] !== 'pulado';
    }).length;
    badge.textContent = pendentes;
    badge.style.display = pendentes > 0 ? 'inline-block' : 'none';
  }

  function _renderBriefing() {
    var el = document.getElementById('briefing-container');
    if (!el || !_dados) return;

    var items = _dados.items || [];
    var visiveis = items.filter(function (i) { return _estado[i.lead_id] !== 'pulado'; });
    var counts = _contar();

    var geradoEm = '';
    if (_dados.gerado_em) {
      try {
        geradoEm = ' · gerado às ' + new Date(_dados.gerado_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      } catch (e) {}
    }
    var dataHoje = new Date().toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short' });

    var html = '<div class="briefing-header">' +
      '<div>' +
        '<div style="display:flex;align-items:center;gap:8px">' +
          '<h3 class="briefing-title">Briefing de hoje — ' + dataHoje + '</h3>' +
          '<button class="briefing-btn-info" onclick="BriefingIA.toggleRegras()" title="Ver regras de priorização">ℹ️</button>' +
        '</div>' +
        '<p class="briefing-subtitle">IA analisou ' + (_dados.total_leads || 0) + ' leads · ' +
          (_dados.total_acoes || 0) + ' precisam de ação' + geradoEm + '</p>' +
      '</div>' +
      '<button class="briefing-btn-atualizar" onclick="BriefingIA.atualizar()">🔄 Atualizar</button>' +
    '</div>' +
    '<div id="briefing-regras" class="briefing-regras-box" style="display:none">' +
      '<h4>Como a IA prioriza seus contatos:</h4>' +
      '<ul>' +
        '<li>🔥 <strong>Urgente</strong>: Propostas paradas há +5 dias, leads quentes sem contato há 3 dias ou agendamentos vencidos.</li>' +
        '<li>📅 <strong>Hoje</strong>: Agendamentos para hoje ou leads mornos sem contato há 7 dias.</li>' +
        '<li>📆 <strong>Esta Semana</strong>: Outros leads que precisam de acompanhamento em breve.</li>' +
        '<li>✅ <strong>Em dia</strong>: Contatos recentes ou leads frios sem pendências.</li>' +
      '</ul>' +
      '<p style="margin-top:8px;font-size:0.75rem;color:#64748b">A IA também considera se o cliente respondeu recentemente para sugerir mudanças de etapa.</p>' +
    '</div>' +
    _renderProgressBar(counts.concluidos, counts.total);

    if (visiveis.length === 0) {
      html += '<div class="briefing-vazio">✅ Tudo em dia! Nenhum lead precisa de atenção hoje.</div>';
    } else {
      html += visiveis.map(_renderCard).join('');
    }

    var pulados = items.filter(function (i) { return _estado[i.lead_id] === 'pulado'; });
    if (pulados.length > 0) {
      html += '<p class="briefing-pulados-label">Pulados hoje: ' + pulados.length + '</p>';
    }

    el.innerHTML = html;
    _atualizarBadge();
  }

  async function _carregarEExibir(forcar) {
    var el = document.getElementById('briefing-container');
    if (!el) return;
    el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
      _dados = await _fetchBriefing(forcar);
      _renderBriefing();
    } catch (e) {
      el.innerHTML = '<div class="briefing-erro">Não foi possível carregar o briefing. Tente novamente.<br>' +
        '<button class="briefing-btn-atualizar" style="margin-top:12px" onclick="BriefingIA.atualizar()">🔄 Tentar novamente</button></div>';
      console.error('[BriefingIA]', e);
    }
  }

  // ── CSS inline ───────────────────────────────────────────────────────────────
  function _injectStyles() {
    if (document.getElementById('briefing-styles')) return;
    var style = document.createElement('style');
    style.id = 'briefing-styles';
    style.textContent = [
      '.briefing-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;gap:12px;flex-wrap:wrap}',
      '.briefing-title{margin:0;font-size:1rem;font-weight:600;color:#1e293b}',
      '.briefing-subtitle{margin:4px 0 0;font-size:0.78rem;color:#64748b}',
      '.briefing-btn-atualizar{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:6px 12px;font-size:0.78rem;cursor:pointer;color:#374151;white-space:nowrap;flex-shrink:0}',
      '.briefing-btn-atualizar:hover{background:#e2e8f0}',
      '.briefing-progress-bar{background:#e2e8f0;border-radius:4px;height:6px;margin-bottom:6px}',
      '.briefing-progress-fill{background:#10b981;height:100%;border-radius:4px;transition:width .3s}',
      '.briefing-progress-label{font-size:0.75rem;color:#64748b;margin:0 0 20px}',
      '.briefing-card{border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:12px;background:#fff;transition:opacity .2s}',
      '.briefing-card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;gap:8px}',
      '.briefing-card-header>div{min-width:0}',
      '.briefing-badge{font-size:0.7rem;font-weight:600;padding:2px 8px;border-radius:10px;display:inline-block}',
      '.briefing-lead-nome{margin:6px 0 2px;font-size:0.9rem;font-weight:600;color:#1e293b}',
      '.briefing-lead-info{font-size:0.75rem;color:#64748b;display:block;overflow-wrap:anywhere}',
      '.briefing-acao-label{font-size:0.75rem;color:#94a3b8;flex-shrink:0;margin-top:2px}',
      '.briefing-rascunho{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:10px;font-size:0.82rem;color:#374151;font-style:italic;margin-bottom:10px;white-space:pre-wrap;word-break:break-word}',
      '.briefing-sem-rascunho{font-style:normal;color:#94a3b8}',
      '.briefing-motivo{border-radius:6px;padding:10px;font-size:0.82rem;color:#374151;margin-bottom:10px}',
      '.briefing-actions{display:flex;gap:8px;flex-wrap:wrap}',
      '.briefing-btn-campanha{background:linear-gradient(135deg, #f59e0b, #ef4444);color:#fff;border:none;border-radius:6px;padding:7px 12px;font-size:0.8rem;font-weight:600;cursor:pointer}',
      '.briefing-btn-campanha:hover{opacity:0.9}',
      '.briefing-btn-enviar{background:#10b981;color:#fff;border:none;border-radius:6px;padding:7px 16px;font-size:0.8rem;font-weight:600;cursor:pointer}',
      '.briefing-btn-enviar:hover{background:#059669}',
      '.briefing-btn-enviar:disabled{background:#94a3b8;cursor:not-allowed}',
      '.briefing-btn-editar,.briefing-btn-ver{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:7px 12px;font-size:0.8rem;cursor:pointer;color:#374151}',
      '.briefing-btn-editar:hover,.briefing-btn-ver:hover{background:#e2e8f0}',
      '.briefing-btn-pular{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:7px 12px;font-size:0.8rem;cursor:pointer;color:#94a3b8}',
      '.briefing-btn-pular:hover{background:#fef2f2;color:#ef4444;border-color:#fca5a5}',
      '.briefing-vazio{text-align:center;padding:40px 20px;color:#10b981;font-size:1rem;font-weight:500;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0}',
      '.briefing-erro{text-align:center;padding:32px 20px;color:#ef4444;font-size:0.9rem;background:#fef2f2;border-radius:8px;border:1px solid #fca5a5}',
      '.briefing-pulados-label{font-size:0.75rem;color:#94a3b8;text-align:center;margin-top:8px}',
      '.briefing-textarea-edicao{width:100%;min-height:80px;border:1px solid #6366f1;border-radius:6px;padding:10px;font-size:0.82rem;font-family:inherit;resize:vertical;box-sizing:border-box;margin-bottom:10px}',
      '.briefing-btn-template{background:#6366f1;color:#fff;border:none;border-radius:6px;padding:7px 12px;font-size:0.8rem;font-weight:500;cursor:pointer}',
      '.briefing-btn-template:hover{background:#4f46e5}',
      '.briefing-btn-info{background:transparent;border:none;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:0.85rem;color:#64748b;transition:background .2s}',
      '.briefing-btn-info:hover{background:#f1f5f9;color:#1e293b}',
      '.briefing-regras-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-bottom:20px;animation:slideDown 0.3s ease-out}',
      '.briefing-regras-box h4{margin:0 0 10px;font-size:0.85rem;font-weight:600;color:#1e293b}',
      '.briefing-regras-box ul{margin:0;padding-left:18px;font-size:0.8rem;color:#334155;line-height:1.6}',
      '.briefing-regras-box li{margin-bottom:6px}',
      '@keyframes slideDown{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}',
      '.briefing-template-dropdown{position:absolute;top:100%;left:0;z-index:100;background:#fff;border:1px solid #e2e8f0;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);min-width:250px;max-height:300px;overflow-y:auto;margin-top:4px}',
      '.briefing-template-list{padding:8px 0}',
      '.briefing-template-item{padding:10px 14px;cursor:pointer;border-bottom:1px solid #f1f5f9}',
      '.briefing-template-item:last-child{border-bottom:none}',
      '.briefing-template-item:hover{background:#f8fafc}',
      '.briefing-template-item strong{display:block;font-size:13px;color:#1e293b}',
      '@media(max-width:560px){.briefing-header{display:grid;grid-template-columns:1fr}.briefing-btn-atualizar{width:100%;justify-content:center}.briefing-card{padding:12px}.briefing-card-header{flex-direction:column;align-items:stretch}.briefing-acao-label{margin-top:0}.briefing-actions{display:grid;grid-template-columns:1fr;gap:8px}.briefing-actions>button{flex:1 1 140px;width:100%}.briefing-template-dropdown{position:static;min-width:0;width:100%;box-shadow:none}}',
    ].join('');
    document.head.appendChild(style);
  }

  // ── API pública ──────────────────────────────────────────────────────────────
  window.BriefingIA = {
    init: function () {
      _injectStyles();
      _carregarEstado();

      var tab = document.getElementById('tab-hoje');
      if (!tab) return;

      var btn = document.getElementById('tab-hoje-btn');
      if (btn) {
        btn.addEventListener('click', function () {
          if (!_dados) _carregarEExibir(false);
        });
      }

      // Aba ativa por padrão: carrega imediatamente
      if (tab.classList.contains('active')) {
        _carregarEExibir(false);
      }
    },

    atualizar: function () {
      _dados = null;
      _carregarEExibir(true);
    },

    toggleRegras: function () {
      var el = document.getElementById('briefing-regras');
      if (!el) return;
      var isHidden = el.style.display === 'none';
      el.style.display = isHidden ? 'block' : 'none';
      var btn = document.querySelector('.briefing-btn-info');
      if (btn) btn.style.background = isHidden ? '#e2e8f0' : 'transparent';
    },

    enviar: async function (leadId, tipoAcao) {
      var card = document.getElementById('briefing-card-' + leadId);
      var rascunhoEl = card && card.querySelector('#rascunho-' + leadId);
      if (!rascunhoEl) { alert('Rascunho não encontrado.'); return; }

      var mensagem = rascunhoEl.tagName === 'TEXTAREA' ? rascunhoEl.value.trim() : rascunhoEl.textContent.trim();
      if (!mensagem) { alert('A mensagem está vazia.'); return; }

      var btnEnviar = card ? card.querySelector('.briefing-btn-enviar') : null;
      if (btnEnviar) { btnEnviar.disabled = true; btnEnviar.textContent = 'Enviando…'; }

      try {
        var endpoint = tipoAcao === 'mensagem_email'
          ? '/tenant/comercial/leads/' + leadId + '/email'
          : '/tenant/comercial/leads/' + leadId + '/whatsapp';
        var payload = tipoAcao === 'mensagem_email'
          ? { assunto: 'Follow-up Comercial', mensagem: mensagem }
          : { mensagem: mensagem };
        await window.ApiService.post(endpoint, payload);
        _estado[leadId] = 'concluido';
        _salvarEstado();
        _renderBriefing();
      } catch (e) {
        if (btnEnviar) { btnEnviar.disabled = false; btnEnviar.textContent = '✓ Enviar agora'; }
        alert('Erro ao enviar mensagem. Tente novamente.');
        console.error('[BriefingIA.enviar]', e);
      }
    },

    editar: function (leadId) {
      var card = document.getElementById('briefing-card-' + leadId);
      var rascunhoEl = card && card.querySelector('#rascunho-' + leadId);
      if (!rascunhoEl) return;

      var texto = rascunhoEl.textContent;
      var textarea = document.createElement('textarea');
      textarea.className = 'briefing-textarea-edicao';
      textarea.id = 'rascunho-' + leadId;
      textarea.value = texto;
      rascunhoEl.replaceWith(textarea);
      textarea.focus();

      var btnEditar = card ? card.querySelector('.briefing-btn-editar') : null;
      if (btnEditar) {
        btnEditar.textContent = '💾 Salvar';
        btnEditar.onclick = function () {
          var novoTexto = textarea.value.trim();
          var novoPara = document.createElement('div');
          novoPara.className = 'briefing-rascunho';
          novoPara.id = 'rascunho-' + leadId;
          novoPara.textContent = novoTexto;
          textarea.replaceWith(novoPara);
          btnEditar.textContent = '✎ Editar';
          btnEditar.onclick = function () { BriefingIA.editar(leadId); };
        };
      }
    },

    pular: function (leadId) {
      _estado[leadId] = 'pulado';
      _salvarEstado();
      _renderBriefing();
    },

    confirmarEtapa: async function (leadId, etapaSugerida) {
      if (!etapaSugerida) { alert('Nenhuma etapa sugerida disponível.'); return; }
      var card = document.getElementById('briefing-card-' + leadId);
      var btn = card ? card.querySelector('.briefing-btn-enviar') : null;
      if (btn) { btn.disabled = true; btn.textContent = 'Movendo…'; }
      try {
        await window.ApiService.put('/tenant/comercial/leads/' + leadId, { status_pipeline: etapaSugerida });
        _estado[leadId] = 'concluido';
        _salvarEstado();
        _renderBriefing();
      } catch (e) {
        if (btn) { btn.disabled = false; btn.textContent = '✓ Mover etapa'; }
        alert('Erro ao mover etapa. Tente novamente.');
        console.error('[BriefingIA.confirmarEtapa]', e);
      }
    },

    verLead: function (leadId) {
      var tabBtn = document.getElementById('tab-leads-btn');
      if (tabBtn) tabBtn.click();
      // Tenta abrir detalhe após switch de aba
      if (typeof window.abrirDetalhe === 'function') {
        setTimeout(function () { window.abrirDetalhe(leadId); }, 300);
      }
    },

    selecionarTemplate: async function(leadId, canal) {
      var card = document.getElementById('briefing-card-' + leadId);
      if (!card) return;

      var templates = await _carregarTemplates('followup', canal);
      if (!templates.length) {
        alert('Nenhum template de follow-up cadastrado para ' + canal + '. Cadastre na aba Templates.');
        return;
      }

      var dropdownId = 'template-dropdown-' + leadId;
      var existing = document.getElementById(dropdownId);
      if (existing) { existing.remove(); return; }

      var dropdown = document.createElement('div');
      dropdown.id = dropdownId;
      dropdown.className = 'briefing-template-dropdown';
      dropdown.innerHTML = '<div class="briefing-template-list">' +
        templates.map(function(t) {
          return '<div class="briefing-template-item" onclick="BriefingIA.usarTemplate(' + leadId + ',' + t.id + ',\'' + canal + '\')">' +
            '<strong>' + _esc(t.nome) + '</strong>' +
            '<span style="display:block;font-size:11px;color:#64748b">' + _esc((t.conteudo || '').slice(0,60)) + '...</span>' +
          '</div>';
        }).join('') +
        '<div class="briefing-template-item" style="color:#94a3b8;text-align:center" onclick="this.parentElement.parentElement.remove()">Cancelar</div>' +
      '</div>';

      var actionsEl = card.querySelector('.briefing-actions');
      if (actionsEl) {
        actionsEl.style.position = 'relative';
        actionsEl.appendChild(dropdown);
      }
    },

    usarTemplate: async function(leadId, templateId, canal) {
      var card = document.getElementById('briefing-card-' + leadId);
      if (!card) return;

      var dropdown = document.getElementById('template-dropdown-' + leadId);
      if (dropdown) dropdown.remove();

      try {
        var preview = await window.ApiService.post('/tenant/comercial/templates/' + templateId + '/preview?lead_id=' + leadId, {});
        
        var rascunhoEl = card.querySelector('#rascunho-' + leadId);
        if (rascunhoEl) {
          if (rascunhoEl.tagName === 'TEXTAREA') {
            rascunhoEl.value = preview.conteudo || '';
          } else {
            rascunhoEl.textContent = preview.conteudo || '';
          }
        }
      } catch (e) {
        alert('Erro ao carregar template. Tente novamente.');
        console.error('[BriefingIA.usarTemplate]', e);
      }
    },

    campanhaRapida: async function(leadId, tipoAcao) {
      var canal = tipoAcao === 'mensagem_email' ? 'email' : 'whatsapp';
      _templates = null; // Invalida cache para garantir canal certo
      var templates = await _carregarTemplates('followup', canal);
      if (!templates.length) {
        alert('Nenhum template de follow-up cadastrado para ' + canal + '. Cadastre na aba Templates.');
        return;
      }
      
      var card = document.getElementById('briefing-card-' + leadId);
      var nomeLead = '';
      if (card) {
        var elNome = card.querySelector('.briefing-lead-nome');
        if (elNome) nomeLead = elNome.textContent;
      }
      
      if (typeof window.abrirModalCampanhaRapida === 'function') {
        window.abrirModalCampanhaRapida(leadId, templates[0].id, canal, nomeLead);
      } else {
        console.error('[BriefingIA] abrirModalCampanhaRapida não encontrado no escopo global.');
      }
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { window.BriefingIA.init(); });
  } else {
    window.BriefingIA.init();
  }
})();
