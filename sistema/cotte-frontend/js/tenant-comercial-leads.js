// COTTE — Comercial Leads
// Tabela, ordenação, detalhe, CRUD, WhatsApp/Email, lembrete inline
// Requer: comercial-core.js

// ═══════════════════════════════════════════════════════════════════════════════
// LEADS TABLE
// ═══════════════════════════════════════════════════════════════════════════════
// ── Detecção de duplicata ──────────────────────────────────────────
var _dupTimer = null;
var _dupIgnorada = false;  // true quando usuário clica "Ignorar"
var _dupLeadId = null;     // id do lead duplicado encontrado

function _normalizarTelefone(v) {
  return (v || '').replace(/\D/g, '');
}

function _inicialsDup(nome) {
  var parts = (nome || '').trim().split(' ');
  return (parts[0][0] || '') + (parts[1] ? parts[1][0] : '');
}

function _mostrarCardDuplicata(lead) {
  var card = document.getElementById('lead-duplicata-card');
  if (!card) return;
  var initials = _inicialsDup(lead.nome_responsavel).toUpperCase();
  var status = lead.status_pipeline || '';
  card.innerHTML =
    '<div class="dup-label">⚠️ Lead já existe</div>' +
    '<div class="dup-info">' +
      '<div class="dup-avatar">' + initials + '</div>' +
      '<div>' +
        '<div class="dup-nome">' + (lead.nome_responsavel || '') + '</div>' +
        '<div class="dup-meta">' + (lead.nome_empresa || '') +
          ' · <span class="dup-status">● ' + status + '</span></div>' +
      '</div>' +
    '</div>' +
    '<div class="dup-actions">' +
      '<button class="btn-dup-atualizar" onclick="_usarLeadExistente(' + lead.id + ', this)">Atualizar este lead</button>' +
      '<button class="btn-dup-ignorar" onclick="_ignorarDuplicata()">Ignorar</button>' +
    '</div>';
  card.style.display = 'block';
}

function _ocultarCardDuplicata() {
  var card = document.getElementById('lead-duplicata-card');
  if (card) { card.style.display = 'none'; card.innerHTML = ''; }
}

async function _usarLeadExistente(leadId, btn) {
  btn.disabled = true;
  btn.textContent = 'Carregando...';
  try {
    var l = await api.get('/tenant/comercial/leads/' + leadId);
    leadAtualId = leadId;
    document.getElementById('modal-lead-title').textContent = 'Editando: ' + (l.nome_responsavel || 'Lead');
    document.getElementById('lead-id').value = l.id;
    document.getElementById('lead-nome-responsavel').value = l.nome_responsavel || '';
    document.getElementById('lead-nome-empresa').value = l.nome_empresa || '';
    document.getElementById('lead-whatsapp').value = l.whatsapp || '';
    document.getElementById('lead-email').value = l.email || '';
    document.getElementById('lead-cidade').value = l.cidade || '';
    document.getElementById('lead-segmento-id').value = l.segmento_id || '';
    document.getElementById('lead-origem-id').value = l.origem_lead_id || '';
    document.getElementById('lead-valor').value = l.valor_proposto || l.valor_estimado || '';
    document.getElementById('lead-observacoes').value = l.observacoes || '';
    if (l.proximo_contato_em)
      document.getElementById('lead-proximo-contato').value = new Date(l.proximo_contato_em).toISOString().slice(0, 16);
    // Endereço
    document.getElementById('lead-cep').value = l.cep || '';
    document.getElementById('lead-logradouro').value = l.logradouro || '';
    document.getElementById('lead-numero').value = l.numero || '';
    document.getElementById('lead-complemento').value = l.complemento || '';
    document.getElementById('lead-bairro').value = l.bairro || '';
    document.getElementById('lead-uf').value = l.uf || '';
    if (l.cep || l.logradouro) document.getElementById('accordion-endereco').open = true;
    _ocultarCardDuplicata();
    _dupLeadId = leadId;
    showToast('Formulário carregado com dados do lead existente', 'info');
  } catch(e) {
    showToast('Erro ao carregar lead', 'error');
    btn.disabled = false;
    btn.textContent = 'Atualizar este lead';
  }
}

function _ignorarDuplicata() {
  _dupIgnorada = true;
  _ocultarCardDuplicata();
}

async function _checkDuplicataLead(whatsapp, email) {
  var wa = _normalizarTelefone(whatsapp);
  var em = (email || '').trim();
  if (!wa && !em) { _ocultarCardDuplicata(); return; }
  if (_dupIgnorada) return;

  var params = new URLSearchParams();
  if (wa) params.set('whatsapp', wa);
  if (em) params.set('email', em);

  try {
    var lead = await api.get('/tenant/comercial/leads/check-duplicata?' + params.toString());
    if (lead && lead.id && (!leadAtualId || lead.id !== leadAtualId)) {
      _mostrarCardDuplicata(lead);
    } else {
      _ocultarCardDuplicata();
    }
  } catch(e) {
    _ocultarCardDuplicata();
  }
}

// ── CEP / Endereço ─────────────────────────────────────────────────
function formatarCep(input) {
  var v = input.value.replace(/\D/g, '').slice(0, 8);
  input.value = v.length > 5 ? v.slice(0,5) + '-' + v.slice(5) : v;
}

async function buscarCepLead() {
  var cepInput = document.getElementById('lead-cep');
  var btn = document.getElementById('btn-buscar-cep');
  var cep = (cepInput.value || '').replace(/\D/g, '');
  if (cep.length !== 8) { showToast('CEP deve ter 8 dígitos', 'error'); return; }
  var origText = btn.textContent;
  btn.textContent = '⏳';
  btn.disabled = true;
  try {
    var r = await fetch('https://viacep.com.br/ws/' + cep + '/json/');
    var d = await r.json();
    if (d.erro) { showToast('CEP não encontrado', 'error'); return; }
    var set = function(id, val) { var el = document.getElementById(id); if (el && val) el.value = val; };
    set('lead-logradouro', d.logradouro);
    set('lead-bairro', d.bairro);
    set('lead-cidade', d.localidade);
    set('lead-uf', d.uf);
    document.getElementById('accordion-endereco').open = true;
    showToast('Endereço preenchido!', 'success');
  } catch(_) {
    showToast('Erro ao buscar CEP', 'error');
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

function debounceLeads() {
  leadsFilterOrigemId = null;
  leadsFilterFollowUpHoje = false;
  leadsFilterEmpresaTrial = false;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(function() { carregarLeadsTabela(); }, 300);
}

/** Banner na aba Leads quando algum filtro especial do dashboard está ativo. */
function atualizarBannerFollowUpLeads() {
  var b = document.getElementById('leads-followup-banner');
  if (!b) return;
  if (leadsFilterEmpresaTrial) {
    b.style.display = 'block';
    b.innerHTML =
      '<div class="leads-followup-banner-inner">' +
      '<span>Exibindo apenas leads vinculados a <strong>empresas em trial ativo</strong>.</span>' +
      '<button type="button" class="btn btn-sm btn-secondary" id="btn-limpar-filtro-trial">Limpar filtro</button>' +
      '</div>';
    var btn = document.getElementById('btn-limpar-filtro-trial');
    if (btn) {
      btn.addEventListener('click', function() {
        leadsFilterEmpresaTrial = false;
        leadsPage = 1;
        carregarLeadsTabela();
      });
    }
  } else if (leadsFilterFollowUpHoje) {
    b.style.display = 'block';
    b.innerHTML =
      '<div class="leads-followup-banner-inner">' +
      '<span>Lista filtrada pelo campo <strong>Pr\u00F3ximo contato</strong> do lead (vencido ou para agora). Na aba <strong>Lembretes</strong> ficam compromissos com t\u00EDtulo e hor\u00E1rio na agenda.</span>' +
      '<button type="button" class="btn btn-sm btn-secondary" id="btn-limpar-filtro-followup">Limpar filtro</button>' +
      '</div>';
    var btn2 = document.getElementById('btn-limpar-filtro-followup');
    if (btn2) {
      btn2.addEventListener('click', function() {
        leadsFilterFollowUpHoje = false;
        leadsPage = 1;
        carregarLeadsTabela();
      });
    }
  } else {
    b.style.display = 'none';
    b.innerHTML = '';
  }
}

function sortLeads(col) {
  if (leadsOrderBy === col) leadsOrderDir = leadsOrderDir === 'asc' ? 'desc' : 'asc';
  else { leadsOrderBy = col; leadsOrderDir = 'asc'; }
  carregarLeadsTabela();
}

function atualizarHeaderOrdenacao() {
  document.querySelectorAll('#leads-table thead th[data-col]').forEach(function(th) {
    var col = th.dataset.col;
    var existing = th.querySelector('.sort-arrow');
    if (existing) existing.remove();
    if (col === leadsOrderBy) {
      var arrow = document.createElement('span');
      arrow.className = 'sort-arrow';
      arrow.textContent = leadsOrderDir === 'asc' ? ' \u25B2' : ' \u25BC';
      arrow.style.cssText = 'font-size:10px;color:var(--accent)';
      th.appendChild(arrow);
    }
  });
}

function limparResumoPropostaVinculadaLead() {
  var info = document.getElementById('lead-proposta-vinculada-info');
  if (!info) return;
  info.style.display = 'none';
  info.innerHTML = '';
}

async function carregarResumoPropostaVinculadaLead(leadId) {
  var info = document.getElementById('lead-proposta-vinculada-info');
  if (!info || !leadId) return;

  try {
    var propostas = await api.get('/tenant/comercial/propostas-publicas/leads/' + leadId + '/propostas');
    if (!propostas || propostas.length === 0) {
      limparResumoPropostaVinculadaLead();
      return;
    }

    var ultima = propostas[0];
    var statusLabel = {
      enviada: 'Enviada',
      visualizada: 'Visualizada',
      aceita: 'Aceita',
      expirada: 'Expirada',
      rascunho: 'Rascunho'
    }[ultima.status] || ultima.status;

    info.innerHTML = '<strong>Última proposta vinculada:</strong> ' + esc((ultima.proposta_template && ultima.proposta_template.nome) || 'Proposta') +
      ' • Status: ' + esc(statusLabel) +
      ' • Enviada em ' + esc(fmtData(ultima.criado_em));
    info.style.display = 'block';
  } catch (e) {
    limparResumoPropostaVinculadaLead();
  }
}

async function carregarLeadsTabela() {
  if (window._isCarregandoLeads) return;
  window._isCarregandoLeads = true;
  setTimeout(() => window._isCarregandoLeads = false, 200);
  var search = document.getElementById('leads-search')?.value || '';
  var status = document.getElementById('leads-filter-status')?.value || '';
  var score = document.getElementById('leads-filter-score')?.value || '';
  var filtroArquivados = document.getElementById('leads-filter-arquivados')?.value || 'ativos';
  var url = '/tenant/comercial/leads?page=' + leadsPage + '&per_page=25&order_by=' + leadsOrderBy + '&order_dir=' + leadsOrderDir;
  if (search) url += '&search=' + encodeURIComponent(search);
  if (status) url += '&status=' + status;
  if (score) url += '&lead_score=' + score;
  if (typeof leadsFilterOrigemId === 'number' && leadsFilterOrigemId > 0) {
    url += '&origem_lead_id=' + leadsFilterOrigemId;
  }
  if (filtroArquivados === 'arquivados') url += '&ativo=false';
  else if (filtroArquivados === 'ativos') url += '&ativo=true';
  if (leadsFilterFollowUpHoje) url += '&follow_up_hoje=true';
  

  try {
    var res = await api.get(url);
    var items = res.items || [];
    items.forEach(function(l) { window.leadsCache[l.id] = Object.assign(window.leadsCache[l.id] || {}, l); });
    atualizarBannerFollowUpLeads();
    var tbody = document.getElementById('leads-tbody');
    var mobileContainer = document.getElementById('leads-mobile-cards');
    var emptyHtml = '<tr><td colspan="9"><div class="state-empty" style="padding:40px"><div class="state-empty-icon">\uD83D\uDCEB</div><div class="state-empty-title">Nenhum lead encontrado</div><div class="state-empty-desc">Tente ajustar os filtros ou adicione um novo lead</div></div></td></tr>';
    var emptyMobile = '<div class="state-empty" style="padding:40px"><div class="state-empty-icon">\uD83D\uDCEB</div><div class="state-empty-title">Nenhum lead encontrado</div></div>';

    if (!items.length) {
      tbody.innerHTML = emptyHtml;
      mobileContainer.innerHTML = emptyMobile;
    } else {
      tbody.innerHTML = items.map(function(l) {
        return '<tr data-lead-id="' + l.id + '">' +
          '<td><div class="lt-company">' + esc(l.nome_empresa) + '</div><div class="lt-person">' + esc(l.nome_responsavel) + '</div></td>' +
          '<td>' + esc(l.nome_responsavel) + '</td>' +
          '<td class="lt-contact">' + esc(l.whatsapp || l.email || '\u2014') + '</td>' +
          '<td>' + (l.segmento_nome ? '<span class="kc-badge">' + esc(l.segmento_nome) + '</span>' : '\u2014') + '</td>' +
          '<td>' + (l.origem_nome ? '<span class="kc-badge">' + esc(l.origem_nome) + '</span>' : '\u2014') + '</td>' +
          '<td><span class="lead-badge status-' + l.status_pipeline + '">' + esc(STATUS_LABELS[l.status_pipeline] || l.status_pipeline) + '</span></td>' +
          '<td>' + (l.lead_score ? '<span class="score ' + l.lead_score + '">' + esc(l.lead_score) + '</span>' : '\u2014') + '</td>' +
          '<td style="white-space:nowrap">' + fmtData(l.criado_em) + '</td>' +
          '<td class="leads-actions-cell" data-id="' + l.id + '" data-wa="' + (l.whatsapp ? '1' : '') + '" data-em="' + (l.email ? '1' : '') + '" style="white-space:nowrap"></td>' +
        '</tr>';
      }).join('');
      atualizarHeaderOrdenacao();

      // Click nas linhas da tabela
      tbody.querySelectorAll('tr[data-lead-id]').forEach(function(row) {
        row.addEventListener('click', function() { abrirDetalhe(parseInt(this.dataset.leadId)); });
      });

      // Botões de ação nas células
      tbody.querySelectorAll('.leads-actions-cell').forEach(function(cell) {
        cell.addEventListener('click', function(e) { e.stopPropagation(); });
        var id = parseInt(cell.dataset.id);
        if (cell.dataset.wa) {
          var btnWa = document.createElement('button');
          btnWa.className = 'btn btn-sm btn-ghost';
          btnWa.style.cssText = 'padding:4px 7px';
          btnWa.textContent = '\uD83D\uDCF1';
          btnWa.title = 'WhatsApp';
          btnWa.addEventListener('click', function() { abrirModalWhatsApp(id); });
          cell.appendChild(btnWa);
        }
        if (cell.dataset.em) {
          var btnEm = document.createElement('button');
          btnEm.className = 'btn btn-sm btn-ghost';
          btnEm.style.cssText = 'padding:4px 7px';
          btnEm.textContent = '\uD83D\uDCE7';
          btnEm.title = 'E-mail';
          btnEm.addEventListener('click', function() { abrirModalEmail(id); });
          cell.appendChild(btnEm);
        }
        var btnLemb = document.createElement('button');
        btnLemb.className = 'btn btn-sm btn-ghost';
        btnLemb.style.cssText = 'padding:4px 7px';
        btnLemb.textContent = '\u23F0';
        btnLemb.title = 'Lembrete';
        btnLemb.addEventListener('click', function() { abrirModalLembrete(id); });
        cell.appendChild(btnLemb);
      });

      // Mobile cards
      mobileContainer.innerHTML = items.map(function(l) {
        var ini = (l.nome_empresa || l.nome_responsavel || '?').slice(0, 2).toUpperCase();
        var scoreClass = l.lead_score || '';
        var statusClass = 'status-' + l.status_pipeline;
        return '<div class="leads-mobile-card" data-lead-id="' + l.id + '">' +
          '<div class="lmc-header">' +
            '<div class="lmc-avatar">' + ini + '</div>' +
            '<div class="lmc-info"><div class="lmc-name">' + esc(l.nome_empresa) + '</div><div class="lmc-company">' + esc(l.nome_responsavel) + '</div></div>' +
            (l.lead_score ? '<span class="score ' + scoreClass + '">' + esc(l.lead_score) + '</span>' : '') +
          '</div>' +
          '<div class="lmc-meta">' +
            '<span class="lead-badge ' + statusClass + '">' + esc(STATUS_LABELS[l.status_pipeline] || l.status_pipeline) + '</span>' +
            (l.segmento_nome ? '<span class="kc-badge">' + esc(l.segmento_nome) + '</span>' : '') +
            (l.origem_nome ? '<span class="kc-badge">' + esc(l.origem_nome) + '</span>' : '') +
          '</div>' +
          '<div style="font-size:11px;color:var(--muted)">' + fmtData(l.criado_em) + '</div>' +
          '<div class="lmc-actions" data-id="' + l.id + '" data-wa="' + (l.whatsapp ? '1' : '') + '" data-em="' + (l.email ? '1' : '') + '"></div>' +
        '</div>';
      }).join('');

      mobileContainer.querySelectorAll('.leads-mobile-card[data-lead-id]').forEach(function(card) {
        card.addEventListener('click', function() { abrirDetalhe(parseInt(this.dataset.leadId)); });
      });
      mobileContainer.querySelectorAll('.lmc-actions').forEach(function(actions) {
        actions.addEventListener('click', function(e) { e.stopPropagation(); });
        var id = parseInt(actions.dataset.id);
        if (actions.dataset.wa) {
          var btn = document.createElement('button');
          btn.className = 'btn btn-sm btn-ghost';
          btn.textContent = '\uD83D\uDCF1 WhatsApp';
          btn.addEventListener('click', function() { abrirModalWhatsApp(id); });
          actions.appendChild(btn);
        }
        if (actions.dataset.em) {
          var btn2 = document.createElement('button');
          btn2.className = 'btn btn-sm btn-ghost';
          btn2.textContent = '\uD83D\uDCE7 E-mail';
          btn2.addEventListener('click', function() { abrirModalEmail(id); });
          actions.appendChild(btn2);
        }
        var btn3 = document.createElement('button');
        btn3.className = 'btn btn-sm btn-ghost';
        btn3.textContent = '\u23F0 Lembrete';
        btn3.addEventListener('click', function() { abrirModalLembrete(id); });
        actions.appendChild(btn3);
      });
    }
    var pg = document.getElementById('leads-pagination');
    var total = res.total || 0;
    var page = res.page || 1;
    var pages = res.pages || 1;
    pg.innerHTML = '<span>' + total + ' lead' + (total!==1?'s':'') + ' \u00B7 Página ' + page + ' de ' + pages + '</span>' +
      '<div style="display:flex;gap:6px">' +
        '<button ' + (page <= 1 ? 'disabled' : '') + ' id="pg-prev">\u2190 Anterior</button>' +
        '<button ' + (page >= pages ? 'disabled' : '') + ' id="pg-next">Próxima \u2192</button>' +
      '</div>';
    var prevBtn = document.getElementById('pg-prev');
    var nextBtn = document.getElementById('pg-next');
    if (prevBtn) prevBtn.addEventListener('click', function() { leadsPage = page - 1; carregarLeadsTabela(); });
    if (nextBtn) nextBtn.addEventListener('click', function() { leadsPage = page + 1; carregarLeadsTabela(); });
  } catch(e) {
    atualizarBannerFollowUpLeads();
    showToast('Erro ao carregar leads', 'error');
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
window.leadsCache = window.leadsCache || {};

// LEAD DETAIL
// ═══════════════════════════════════════════════════════════════════════════════

function computeNextStep(l) {
  var now = Date.now();
  var diasNoPipeline = Math.floor((now - new Date(l.criado_em)) / (864e5));
  var status = l.status_pipeline || 'novo';

  if (l.proximo_contato_em && new Date(l.proximo_contato_em) < now) {
    return { icon: '⏰', title: 'Ação pendente', text: 'Lembrete atrasado — entre em contato com ' + (l.nome_responsavel || 'o lead'), cta: 'Agendar lembrete', action: 'lemb' };
  }
  if (status === 'novo' && diasNoPipeline > 3) {
    return { icon: '👋', title: 'Primeiro contato', text: 'Este lead está aguardando há ' + diasNoPipeline + ' dias. Faça o primeiro contato.', cta: 'Enviar WhatsApp', action: 'wa' };
  }
  if (status === 'contato_iniciado' && diasNoPipeline > 5) {
    return { icon: '📄', title: 'Envie uma proposta', text: 'Contato iniciado há ' + diasNoPipeline + ' dias. Hora de apresentar uma proposta.', cta: 'Enviar proposta', action: 'proposta' };
  }
  if (status === 'proposta_enviada' && diasNoPipeline > 7) {
    return { icon: '🔄', title: 'Follow-up necessário', text: 'A proposta foi enviada há vários dias sem retorno. Faça um follow-up.', cta: 'Enviar WhatsApp', action: 'wa' };
  }
  if (status === 'negociacao' && !l.proximo_contato_em) {
    return { icon: '🤝', title: 'Agende o próximo passo', text: 'Negociação em andamento — agende o próximo contato para manter o momentum.', cta: 'Agendar lembrete', action: 'lemb' };
  }
  return null;
}

function switchDetailTab(tabName) {
  var dc = document.getElementById('detail-content');
  if (!dc) return;
  dc.querySelectorAll('.lead-tab-btn').forEach(function(btn) {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
    btn.setAttribute('aria-selected', btn.dataset.tab === tabName ? 'true' : 'false');
  });
  dc.querySelectorAll('.lead-tab-panel').forEach(function(panel) {
    panel.classList.toggle('active', panel.dataset.panel === tabName);
    panel.hidden = panel.dataset.panel !== tabName;
  });
}

function setupSheetDrag(sheetEl, overlayEl) {
  if (!window.matchMedia('(max-width: 768px)').matches) return;
  var startY = 0, currentY = 0, startTime = 0, dragging = false;

  function onStart(e) {
    var touch = e.touches ? e.touches[0] : e;
    startY = touch.clientY;
    startTime = Date.now();
    dragging = true;
    sheetEl.style.transition = 'none';
  }
  function onMove(e) {
    if (!dragging) return;
    var touch = e.touches ? e.touches[0] : e;
    currentY = touch.clientY - startY;
    if (currentY < 0) { currentY = 0; return; }
    sheetEl.style.transform = 'translateY(' + currentY + 'px)';
    overlayEl.style.backgroundColor = 'rgba(0,0,0,' + Math.max(0, 0.45 - currentY / 600) + ')';
    e.preventDefault();
  }
  function onEnd() {
    if (!dragging) return;
    dragging = false;
    var elapsed = Date.now() - startTime;
    var velocity = currentY / Math.max(elapsed, 1);
    sheetEl.style.transition = '';
    overlayEl.style.backgroundColor = '';
    if (currentY > 100 || velocity > 0.5) {
      fecharModal('modal-detail');
    } else {
      sheetEl.style.transform = '';
    }
    currentY = 0;
  }

  var grabber = sheetEl.querySelector('.lead-sheet-grabber');
  if (grabber) {
    grabber.addEventListener('touchstart', onStart, { passive: true });
    grabber.addEventListener('touchmove', onMove, { passive: false });
    grabber.addEventListener('touchend', onEnd);
  }
  var hero = sheetEl.querySelector('.lead-hero');
  if (hero) {
    hero.addEventListener('touchstart', onStart, { passive: true });
    hero.addEventListener('touchmove', onMove, { passive: false });
    hero.addEventListener('touchend', onEnd);
  }
}

function renderLeadDetail(l) {
  var scoreAtual = l.lead_score || 'frio';
  var statusAtual = l.status_pipeline || 'novo';
  var words = ((l.nome_empresa || l.nome_responsavel || '?').trim()).split(' ');
  var ini = (words[0] ? words[0][0] : '').toUpperCase() + (words[1] ? words[1][0] : '').toUpperCase();
  if (!ini.trim()) ini = '?';

  var diasNoSistema = Math.floor((Date.now() - new Date(l.criado_em)) / (864e5));
  var diasStr = diasNoSistema === 0 ? 'Hoje' : diasNoSistema === 1 ? '1 dia' : diasNoSistema + ' dias';

  var fmt = function(v) {
    var value = (v == null ? '' : String(v)).trim();
    return value ? esc(value) : '<span class="lead-field-value empty">—</span>';
  };

  // ── Pipeline stages ──
  var stages = pipelineStages.length
    ? pipelineStages.filter(function(s) { return s.ativo; })
    : Object.keys(STATUS_LABELS).map(function(slug) { return { slug: slug, label: STATUS_LABELS[slug], cor: STATUS_COLORS[slug] || '#94a3b8' }; });

  // ── Stepper HTML ──
  var stepperHtml = '';
  var activeIdx = stages.findIndex ? stages.findIndex(function(s) { return s.slug === statusAtual; }) : -1;
  if (activeIdx === -1) {
    for (var si = 0; si < stages.length; si++) { if (stages[si].slug === statusAtual) { activeIdx = si; break; } }
  }
  stages.forEach(function(s, idx) {
    var isDone = idx < activeIdx;
    var isActive = idx === activeIdx;
    var nodeCls = 'lds-node' + (isActive ? ' active' : isDone ? ' done' : '');
    stepperHtml += '<button class="' + nodeCls + '" role="tab" aria-selected="' + isActive + '" data-lead-id="' + l.id + '" data-status="' + s.slug + '" title="Mover para ' + esc(s.label) + '">' +
      '<div class="lds-dot"></div>' +
      '<span class="lds-label">' + esc(s.label) + '</span>' +
    '</button>';
    if (idx < stages.length - 1) {
      stepperHtml += '<div class="lds-line' + (isDone ? ' done' : '') + '" aria-hidden="true"></div>';
    }
  });

  // ── Score picker ──
  var scorePicks = ['quente', 'morno', 'frio'].map(function(s) {
    var isActive = scoreAtual === s;
    return '<button class="score-pick' + (isActive ? ' active ' + s : '') + '" data-lead-id="' + l.id + '" data-score="' + s + '">' + s + '</button>';
  }).join('');

  // ── Next step card ──
  var nextStep = computeNextStep(l);
  var nextStepHtml = nextStep
    ? '<div class="lead-next-step" role="note">' +
        '<span class="lns-icon">' + nextStep.icon + '</span>' +
        '<div class="lns-body">' +
          '<div class="lns-title">' + esc(nextStep.title) + '</div>' +
          '<div class="lns-text">' + esc(nextStep.text) + '</div>' +
        '</div>' +
        '<button class="lns-cta" data-next-action="' + nextStep.action + '" data-id="' + l.id + '">' + esc(nextStep.cta) + '</button>' +
      '</div>'
    : '';

  // ── Tab: Resumo ──
  var contatoHtml =
    '<div class="lead-card">' +
    '<div class="lead-card-title">👤 Contato</div>' +
    '<div class="lead-field"><span class="lead-field-label">Responsável</span><span class="lead-field-value">' + fmt(l.nome_responsavel) + '</span></div>' +
    '<div class="lead-field"><span class="lead-field-label">WhatsApp</span><span class="lead-field-value">' +
      (l.whatsapp ? esc(l.whatsapp) + ' <button class="lead-field-action btn-detail-wa" data-id="' + l.id + '" aria-label="Enviar WhatsApp">📱</button>' : '<span class="lead-field-value empty">—</span>') +
    '</span></div>' +
    '<div class="lead-field"><span class="lead-field-label">E-mail</span><span class="lead-field-value">' +
      (l.email ? esc(l.email) + ' <button class="lead-field-action btn-detail-em" data-id="' + l.id + '" aria-label="Enviar e-mail">📧</button>' : '<span class="lead-field-value empty">—</span>') +
    '</span></div>' +
    '<div class="lead-field"><span class="lead-field-label">Cidade</span><span class="lead-field-value">' + fmt(l.cidade) + '</span></div>' +
    '</div>';

  var negocioHtml =
    '<div class="lead-card">' +
    '<div class="lead-card-title">💼 Negócio</div>' +
    '<div class="lead-field"><span class="lead-field-label">Segmento</span><span class="lead-field-value">' + fmt(l.segmento_nome) + '</span></div>' +
    '<div class="lead-field"><span class="lead-field-label">Origem</span><span class="lead-field-value">' + fmt(l.origem_nome) + '</span></div>' +
    '<div class="lead-field"><span class="lead-field-label">Valor Proposto</span><span class="lead-field-value">' +
      (l.valor_proposto
        ? '<strong style="color:var(--green)">R$ ' + fmtMoeda(l.valor_proposto) + '</strong> <button class="lead-field-action btn-detail-gerar-orcamento" data-id="' + l.id + '" data-valor="' + (l.valor_proposto || 0) + '" data-desc="' + esc(l.nome_empresa || l.nome_responsavel) + '" title="Gerar orçamento">📄</button>'
        : '<span class="lead-field-value empty">—</span>') +
    '</span></div>' +
    '<div class="lead-field"><span class="lead-field-label">Próx. Contato</span><span class="lead-field-value">' + (l.proximo_contato_em ? fmtDataHora(l.proximo_contato_em) : '<span class="lead-field-value empty">—</span>') + '</span></div>' +
    '<div class="lead-field"><span class="lead-field-label">Criado em</span><span class="lead-field-value">' + fmtData(l.criado_em) + ' <span style="color:var(--muted);font-size:11px">(' + diasStr + ')</span></span></div>' +
    '</div>';

  var lembretesHtml = '';
  if (l.lembretes && l.lembretes.length) {
    lembretesHtml = '<div class="lead-card"><div class="lead-card-title">⏰ Lembretes (' + l.lembretes.length + ')</div>';
    lembretesHtml += l.lembretes.slice(0, 5).map(function(r) {
      var atrasado = (r.status || '').toLowerCase() === 'atrasado';
      var concluido = (r.status || '').toLowerCase().startsWith('conclu');
      var dotCls = 'lri-dot' + (atrasado ? ' atrasado' : concluido ? ' concluido' : '');
      return '<div class="lead-reminder-item" style="' + (concluido ? 'opacity:.5' : '') + '">' +
        '<span class="' + dotCls + '"></span>' +
        '<div class="lri-body"><div class="lri-title">' + esc(r.titulo) + '</div><div class="lri-date">' + fmtDataHora(r.data_hora) + '</div></div>' +
        (!concluido ? '<button class="lri-check btn-concluir-lembrete" data-id="' + r.id + '" title="Concluir">✓</button>' : '') +
      '</div>';
    }).join('');
    if (l.lembretes.length > 5) lembretesHtml += '<div style="font-size:11px;color:var(--muted);padding:6px 0 0">+' + (l.lembretes.length - 5) + ' mais</div>';
    lembretesHtml += '</div>';
  }

  var obsHtml = l.observacoes
    ? '<div class="lead-card"><div class="lead-card-title">📋 Observações</div><div style="font-size:13px;color:var(--text);line-height:1.6;white-space:pre-wrap">' + esc(l.observacoes) + '</div></div>'
    : '';

  var tabResumoHtml =
    '<div class="lead-tab-panel active" data-panel="resumo" role="tabpanel" aria-labelledby="tab-resumo">' +
      '<div class="lead-info-grid">' + contatoHtml + negocioHtml + '</div>' +
      lembretesHtml +
      obsHtml +
    '</div>';

  // ── Tab: Atividade (timeline com bolhas de chat para WhatsApp) ──
  var interacoes = (l.interacoes || []).slice().sort(function(a, b) {
    return new Date(a.criado_em) - new Date(b.criado_em);
  });
  var timelHtml = '';
  if (interacoes.length) {
    timelHtml += '<div class="lead-chat-timeline">';
    timelHtml += interacoes.slice(-30).map(function(i) {
      var tipo = (i.tipo || '').toLowerCase();
      var direcao = (i.direcao || 'enviado').toLowerCase();
      var isRecebido = direcao === 'recebido';
      // Mensagens WhatsApp: bolhas de chat
      if (tipo.includes('whatsapp')) {
        var tagLabel = isRecebido ? 'Lead' : 'Enviado';
        return '<div class="lead-tl-bubble ' + (isRecebido ? 'tl-bubble-in' : 'tl-bubble-out') + '">' +
          '<div class="tl-bubble-body">' +
            '<div class="tl-bubble-text">' + esc(i.conteudo || '') + '</div>' +
            '<div class="tl-bubble-meta">' +
              '<span class="lead-tl-tag ' + (isRecebido ? 'received' : 'sent') + '">' + tagLabel + '</span>' +
              '<span class="tl-bubble-time">' + fmtDataHora(i.criado_em) + '</span>' +
            '</div>' +
          '</div>' +
        '</div>';
      }
      // Outros tipos: estilo linear
      var emoji = '📝', tagLbl = 'Nota';
      if (tipo.includes('email')) { emoji = '📧'; tagLbl = 'E-mail'; }
      else if (tipo.includes('status')) { emoji = '🔄'; tagLbl = 'Status'; }
      else if (tipo.includes('lembrete')) { emoji = '⏰'; tagLbl = 'Lembrete'; }
      var isSistema = tipo.includes('sistema') || tipo.includes('status') || tipo.includes('cadastro') || tipo.includes('origem');
      return '<div class="lead-tl-item">' +
        '<div class="lead-tl-dot">' + emoji + '</div>' +
        '<div>' +
          '<div class="lead-tl-text">' + esc(i.conteudo || '') + '</div>' +
          '<div class="lead-tl-meta">' +
            '<span class="lead-tl-tag ' + (isSistema ? 'system' : 'user') + '">' + tagLbl + '</span>' +
            ' <span class="lead-tl-time">' + fmtDataHora(i.criado_em) + '</span>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');
    timelHtml += '</div>';
    if (l.interacoes && l.interacoes.length > 30) {
      timelHtml += '<div style="font-size:11px;color:var(--muted);padding:8px 0">▲ Mostrando as últimas 30 de ' + l.interacoes.length + ' interações</div>';
    }
  } else {
    timelHtml = '<div class="lead-propostas-empty">Nenhuma atividade registrada ainda.</div>';
  }


  var tabAtividadeHtml =
    '<div class="lead-tab-panel" data-panel="atividade" role="tabpanel" aria-labelledby="tab-atividade" hidden>' +
      timelHtml +
    '</div>';

  // ── Tab: Propostas ──
  var tabPropostasHtml =
    '<div class="lead-tab-panel" data-panel="propostas" role="tabpanel" aria-labelledby="tab-propostas" hidden>' +
      '<div id="lead-propostas-container"><div class="loading" style="padding:20px"><div class="spinner" style="width:20px;height:20px"></div></div></div>' +
      '<div style="margin-top:12px"><button class="btn btn-sm btn-primary" id="btn-enviar-proposta-lead" data-lead-id="' + l.id + '">+ Enviar Proposta</button></div>' +
    '</div>';

  // ── Accordion Danger ──
  var dangerHtml =
    '<details class="lead-danger-accordion">' +
      '<summary>⚠️ Zona de perigo</summary>' +
      '<div class="lead-danger-content">' +
        '<button class="btn btn-sm btn-ghost btn-arquivar" data-id="' + l.id + '">' + (l.ativo ? '📦 Arquivar Lead' : '♻️ Reativar Lead') + '</button>' +
        '<button class="btn btn-sm btn-danger btn-excluir-lead" data-id="' + l.id + '">🗑 Excluir permanentemente</button>' +
      '</div>' +
    '</details>';

  // ── Monta HTML completo ──
  var nAtiv = (l.interacoes || []).length;
  var html =
    '<div class="lead-hero">' +
      '<div class="lead-hero-stripe" aria-hidden="true"></div>' +
      '<div class="lead-hero-bg" aria-hidden="true"></div>' +
      '<div class="lead-hero-row1">' +
        '<div class="lead-avatar">' + ini + '</div>' +
        '<div class="lead-hero-info">' +
          '<div class="lead-hero-company" id="ld-title">' + esc(l.nome_empresa || l.nome_responsavel || 'Lead') + '</div>' +
          '<div class="lead-hero-row2">' +
            (l.nome_responsavel ? '<span>' + esc(l.nome_responsavel) + '</span><span class="lead-hero-sep">·</span>' : '') +
            '<span class="score ' + scoreAtual + '">' + scoreAtual + '</span>' +
            '<span class="lead-hero-sep">·</span>' +
            '<span>' + diasStr + ' no pipeline</span>' +
          '</div>' +
        '</div>' +
        '<button class="lead-sheet-close" id="btn-close-detail" aria-label="Fechar detalhes">&times;</button>' +
      '</div>' +
    '</div>' +

    nextStepHtml +

    '<div class="lead-status-stepper" role="tablist" aria-label="Status do pipeline">' +
      stepperHtml +
    '</div>' +

    '<div class="lead-action-rail">' +
      (l.whatsapp ? '<button class="lar-btn btn-detail-wa" data-id="' + l.id + '" aria-label="Enviar WhatsApp"><span class="lar-icon">📱</span>WhatsApp</button>' : '') +
      (l.email    ? '<button class="lar-btn btn-detail-em" data-id="' + l.id + '" aria-label="Enviar e-mail"><span class="lar-icon">📧</span>E-mail</button>' : '') +
      '<button class="lar-btn btn-detail-lemb" data-id="' + l.id + '" aria-label="Lembrete"><span class="lar-icon">⏰</span>Lembrete</button>' +
      '<button class="lar-btn btn-detail-edit" data-id="' + l.id + '" aria-label="Editar"><span class="lar-icon">✏️</span>Editar</button>' +
      '<div class="lar-divider" aria-hidden="true"></div>' +
      '<div class="score-picker">' + scorePicks + '</div>' +
    '</div>' +

    '<nav class="lead-tabs" role="tablist" aria-label="Seções do lead">' +
      '<button class="lead-tab-btn active" id="tab-resumo" role="tab" aria-selected="true" data-tab="resumo">Resumo</button>' +
      '<button class="lead-tab-btn" id="tab-atividade" role="tab" aria-selected="false" data-tab="atividade">Atividade' +
        (nAtiv > 0 ? ' <span class="lead-tab-count">' + nAtiv + '</span>' : '') +
      '</button>' +
      '<button class="lead-tab-btn" id="tab-propostas" role="tab" aria-selected="false" data-tab="propostas">Propostas</button>' +
    '</nav>' +

    '<div class="lead-tab-body">' +
      tabResumoHtml +
      tabAtividadeHtml +
      tabPropostasHtml +
      dangerHtml +
    '</div>' +

    '<div class="lead-composer">' +
      '<div class="lead-composer-field">' +
        '<textarea id="obs-input" placeholder="Adicionar nota ou comentário..." rows="1"></textarea>' +
        '<button class="lc-icon-btn lc-attach" title="Anexar arquivo" aria-label="Anexar arquivo">📎</button>' +
      '</div>' +
      '<button class="lc-send btn-add-obs" data-id="' + l.id + '" title="Enviar nota" aria-label="Enviar nota">&#10148;</button>' +
    '</div>';

  // ── Injeta no DOM ──
  var dc = document.getElementById('detail-content');
  dc.innerHTML = html;

  // Atualiza temperatura no lead-sheet para colorir faixa/avatar
  var sheetEl = document.getElementById('lead-sheet-inner');
  if (sheetEl) sheetEl.setAttribute('data-temperatura', scoreAtual);

  // ── Event listeners ──
  dc.querySelector('#btn-close-detail').addEventListener('click', function() { fecharModal('modal-detail'); });

  dc.querySelectorAll('.btn-detail-wa').forEach(function(btn) {
    btn.addEventListener('click', function() { abrirModalWhatsApp(parseInt(this.dataset.id)); });
  });
  dc.querySelectorAll('.btn-detail-em').forEach(function(btn) {
    btn.addEventListener('click', function() { abrirModalEmail(parseInt(this.dataset.id)); });
  });
  dc.querySelectorAll('.btn-detail-lemb').forEach(function(btn) {
    btn.addEventListener('click', function() { abrirModalLembrete(parseInt(this.dataset.id)); });
  });
  dc.querySelectorAll('.btn-detail-edit').forEach(function(btn) {
    btn.addEventListener('click', function() { editarLead(parseInt(this.dataset.id)); });
  });
  dc.querySelectorAll('.btn-detail-gerar-orcamento').forEach(function(btn) {
    btn.addEventListener('click', function() { irParaGerarOrcamento(parseInt(this.dataset.id), parseFloat(this.dataset.valor), this.dataset.desc); });
  });

  dc.querySelectorAll('.lds-node').forEach(function(btn) {
    btn.addEventListener('click', function() { alterarStatusLead(parseInt(this.dataset.leadId), this.dataset.status); });
  });

  dc.querySelectorAll('.score-pick').forEach(function(btn) {
    btn.addEventListener('click', function() { alterarScore(parseInt(this.dataset.leadId), this.dataset.score); });
  });

  dc.querySelectorAll('.lead-tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { switchDetailTab(this.dataset.tab); });
  });

  var nsCta = dc.querySelector('.lns-cta');
  if (nsCta && nextStep) {
    nsCta.addEventListener('click', function() {
      var action = this.dataset.nextAction;
      var id = parseInt(this.dataset.id);
      if (action === 'wa')        abrirModalWhatsApp(id);
      else if (action === 'lemb') abrirModalLembrete(id);
      else if (action === 'proposta') {
        switchDetailTab('propostas');
        setTimeout(function() { var b = document.getElementById('btn-enviar-proposta-lead'); if (b) b.click(); }, 200);
      }
    });
  }

  var btnProp = dc.querySelector('#btn-enviar-proposta-lead');
  if (btnProp) btnProp.addEventListener('click', function() { abrirModalEnviarProposta(parseInt(this.dataset.leadId)); });

  carregarPropostasDoLead(l.id);

  dc.querySelectorAll('.btn-concluir-lembrete').forEach(function(btn) {
    btn.addEventListener('click', function() { concluirLembrete(parseInt(this.dataset.id)); });
  });

  dc.querySelectorAll('.btn-add-obs').forEach(function(btn) {
    btn.addEventListener('click', function() { adicionarObservacao(parseInt(this.dataset.id)); });
  });

  dc.querySelectorAll('.btn-arquivar').forEach(function(btn) {
    btn.addEventListener('click', function() { arquivarLead(parseInt(this.dataset.id)); });
  });
  dc.querySelectorAll('.btn-excluir-lead').forEach(function(btn) {
    btn.addEventListener('click', function() { excluirLead(parseInt(this.dataset.id)); });
  });

  function onEsc(e) {
    if (e.key === 'Escape') { fecharModal('modal-detail'); document.removeEventListener('keydown', onEsc); }
  }
  document.addEventListener('keydown', onEsc);

  if (sheetEl) setupSheetDrag(sheetEl, document.getElementById('modal-detail'));

  var titleEl = dc.querySelector('#ld-title');
  if (titleEl) setTimeout(function() { titleEl.setAttribute('tabindex', '-1'); titleEl.focus(); }, 50);
}
async function abrirDetalhe(id) {
  leadAtualId = id;
  document.getElementById('modal-detail').classList.add('open');
  
  if (window.leadsCache[id]) {
    renderLeadDetail(window.leadsCache[id]);
  } else {
    document.getElementById('detail-content').innerHTML = '<div class="loading" style="padding:60px"><div class="spinner"></div></div>';
  }
  
  try {
    var l = await api.get('/tenant/comercial/leads/' + id);
    window.leadsCache[id] = Object.assign(window.leadsCache[id] || {}, l);
    renderLeadDetail(l);
  } catch(e) {
    if (!window.leadsCache[id]) {
      
    document.getElementById('detail-content').innerHTML = '<div style="padding:40px;text-align:center">' +
      '<div style="font-size:40px;margin-bottom:12px">\uD83D\uDE15</div>' +
      '<div style="font-size:15px;font-weight:600;color:var(--text);margin-bottom:4px">Erro ao carregar detalhes</div>' +
      '<div style="font-size:13px;color:var(--muted)">' + esc(e.message || 'Tente novamente') + '</div>' +
    '</div>';
  
    }
  }
}

async function alterarStatusLead(id, novoStatus) {
  try {
    await api.patch('/tenant/comercial/leads/' + id + '/status', { status: novoStatus });
    showToast('Status atualizado!', 'success');
    carregarPipeline();
    carregarLeadsTabela();
    abrirDetalhe(id);
  } catch(e) { showToast('Erro ao atualizar status', 'error'); abrirDetalhe(id); }
}

async function alterarScore(id, score) {
  try {
    await api.patch('/tenant/comercial/leads/' + id, { lead_score: score });
    showToast('Score atualizado!', 'success');
    carregarPipeline();
    carregarLeadsTabela();
    abrirDetalhe(id);
  } catch(e) { showToast('Erro ao atualizar score', 'error'); }
}

async function criarEmpresaFromLead(leadId) {
  showToast('Operação indisponível no comercial da empresa.', 'error');
}


async function reenviarSenhaLead(leadId) {
  showToast('Operação indisponível no comercial da empresa.', 'error');
}


function toggleFechados() {
  kanbanShowClosed = !kanbanShowClosed;
  var btn = document.getElementById('btn-toggle-fechados');
  if (btn) btn.textContent = kanbanShowClosed ? '\uD83D\uDE48 Ocultar fechados' : '\uD83D\uDC41 Mostrar fechados';
  carregarPipeline();
}

async function buscarLeadLembrete() {
  var q = document.getElementById('lemb-lead-search')?.value?.trim();
  var dd = document.getElementById('lemb-lead-dropdown');
  if (!q || q.length < 2) { dd.style.display = 'none'; return; }
  try {
    var res = await api.get('/tenant/comercial/leads?search=' + encodeURIComponent(q) + '&per_page=10&ativo=true');
    var items = res.items || [];
    items.forEach(function(l) { window.leadsCache[l.id] = Object.assign(window.leadsCache[l.id] || {}, l); });
    if (!items.length) { dd.style.display = 'none'; return; }
    dd.innerHTML = items.map(function(l) {
      return '<div class="lead-ac-item" data-id="' + l.id + '" data-label="' + esc(l.nome_empresa) + ' \u2014 ' + esc(l.nome_responsavel) + '">' + esc(l.nome_empresa) + ' \u2014 ' + esc(l.nome_responsavel) + '</div>';
    }).join('');
    dd.style.display = 'block';
    dd.querySelectorAll('.lead-ac-item').forEach(function(item) {
      item.addEventListener('click', function() {
        selecionarLeadLembrete(parseInt(this.dataset.id), this.dataset.label);
      });
    });
  } catch(e) { dd.style.display = 'none'; }
}

function selecionarLeadLembrete(id, label) {
  document.getElementById('lemb-lead-id').value = id;
  document.getElementById('lemb-lead-search').value = label;
  document.getElementById('lemb-lead-dropdown').style.display = 'none';
}

async function adicionarObservacao(leadId) {
  var input = document.getElementById('obs-input');
  var conteudo = input?.value?.trim();
  if (!conteudo) return;
  try {
    await api.post('/tenant/comercial/leads/' + leadId + '/observacao', { conteudo: conteudo });
    showToast('Observação adicionada!', 'success');
    abrirDetalhe(leadId);
  } catch(e) { showToast('Erro ao adicionar observação', 'error'); }
}

async function arquivarLead(id) {
  try {
    var res = await api.patch('/tenant/comercial/leads/' + id + '/arquivar');
    showToast(res.ativo ? 'Lead reativado!' : 'Lead arquivado!', 'success');
    fecharModal('modal-detail');
    carregarPipeline();
    carregarLeadsTabela();
  } catch(e) { showToast('Erro ao salvar lead', 'error'); }
}

async function excluirLead(id) {
  if (!confirm('Excluir este lead permanentemente? Esta ação não pode ser desfeita.')) return;
  try {
    await api.delete('/tenant/comercial/leads/' + id);
    showToast('Lead excluído!', 'success');
    fecharModal('modal-detail');
    carregarPipeline();
    carregarLeadsTabela();
  } catch(e) { showToast('Erro ao excluir lead', 'error'); }
}

async function concluirLembrete(id) {
  try {
    await api.post('/tenant/comercial/lembretes/' + id + '/concluir');
    showToast('Lembrete concluído!', 'success');
    if (leadAtualId) abrirDetalhe(leadAtualId);
  } catch(e) { showToast('Erro', 'error'); }
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEAD CRUD
// ═══════════════════════════════════════════════════════════════════════════════
function populateLeadSelects() {
  var segSel = document.getElementById('lead-segmento-id');
  var oriSel = document.getElementById('lead-origem-id');
  segSel.innerHTML = '<option value="">Selecione...</option>' + segmentosCache.map(function(s) { return '<option value="' + s.id + '">' + esc(s.nome) + '</option>'; }).join('');
  oriSel.innerHTML = '<option value="">Selecione...</option>' + origensCache.map(function(o) { return '<option value="' + o.id + '">' + esc(o.nome) + '</option>'; }).join('');
}

async function carregarOpcoesPropostaLead() {
  var select = document.getElementById('lead-proposta-publica-id');
  if (!select) return;

  try {
    var propostas = await api.get('/tenant/comercial/propostas-publicas?ativo=true');
    select.innerHTML = '<option value="">Não vincular agora</option>' + propostas.map(function(p) {
      return '<option value="' + p.id + '">' + esc(p.nome) + '</option>';
    }).join('');
  } catch (e) {
    select.innerHTML = '<option value="">Não vincular agora</option>';
  }
}

async function vincularPropostaAoLead(leadId, propostaPublicaId, validadeDias, dadosLead) {
  await api.post('/tenant/comercial/propostas-publicas/leads/' + leadId + '/propostas', {
    proposta_publica_id: propostaPublicaId,
    dados_personalizados: {
      empresa: dadosLead.nome_empresa || '',
      responsavel: dadosLead.nome_responsavel || '',
      email: dadosLead.email || '',
      whatsapp: dadosLead.whatsapp || '',
      cidade: dadosLead.cidade || ''
    },
    validade_dias: validadeDias
  });
}

function abrirModalLead() {
  leadAtualId = null;
  _dupIgnorada = false;
  _dupLeadId = null;
  _ocultarCardDuplicata();
  document.getElementById('modal-lead-title').textContent = 'Novo Lead';
  document.getElementById('form-lead').reset();
  document.getElementById('lead-id').value = '';
  document.getElementById('lead-proposta-validade').value = '7';
  populateLeadSelects();
  carregarOpcoesPropostaLead();
  limparResumoPropostaVinculadaLead();
  document.getElementById('modal-lead').classList.add('open');
}

async function preencherFormLead(l) {

    
    document.getElementById('modal-lead-title').textContent = 'Editar Lead';
    document.getElementById('lead-id').value = l.id;
    document.getElementById('lead-nome-responsavel').value = l.nome_responsavel || '';
    document.getElementById('lead-nome-empresa').value = l.nome_empresa || '';
    document.getElementById('lead-whatsapp').value = l.whatsapp || '';
    document.getElementById('lead-email').value = l.email || '';
    document.getElementById('lead-cidade').value = l.cidade || '';
    document.getElementById('lead-segmento-id').value = l.segmento_id || '';
    document.getElementById('lead-origem-id').value = l.origem_lead_id || '';
    document.getElementById('lead-valor').value = l.valor_proposto || '';
    document.getElementById('lead-observacoes').value = l.observacoes || '';
    if (l.proximo_contato_em) document.getElementById('lead-proximo-contato').value = new Date(l.proximo_contato_em).toISOString().slice(0, 16);
    // Endereço
    document.getElementById('lead-cep').value = l.cep || '';
    document.getElementById('lead-logradouro').value = l.logradouro || '';
    document.getElementById('lead-numero').value = l.numero || '';
    document.getElementById('lead-complemento').value = l.complemento || '';
    document.getElementById('lead-bairro').value = l.bairro || '';
    document.getElementById('lead-uf').value = l.uf || '';
    if (l.cep || l.logradouro) document.getElementById('accordion-endereco').open = true;
    document.getElementById('lead-proposta-publica-id').value = '';
    document.getElementById('lead-proposta-validade').value = '7';
    await carregarResumoPropostaVinculadaLead(l.id);
    
}

async function editarLead(id) {
  leadAtualId = id;
  populateLeadSelects();
  await carregarOpcoesPropostaLead();
  if (window.leadsCache[id]) {
    await preencherFormLead(window.leadsCache[id]);
    fecharModal('modal-detail');
    document.getElementById('modal-lead').classList.add('open');
  }
  try {
    var l = await api.get('/tenant/comercial/leads/' + id);
    window.leadsCache[id] = Object.assign(window.leadsCache[id] || {}, l);
    await preencherFormLead(l);
    if (!document.getElementById('modal-lead').classList.contains('open')) {
      fecharModal('modal-detail');
      document.getElementById('modal-lead').classList.add('open');
    }
  } catch(e) { showToast('Erro ao carregar lead', 'error'); }
}

async function salvarLead() {
  var nr = document.getElementById('lead-nome-responsavel').value;
  var ne = document.getElementById('lead-nome-empresa').value;
  var wa = document.getElementById('lead-whatsapp').value;
  var em = document.getElementById('lead-email').value;
  if (!nr || !ne) { showToast('Preencha responsável e empresa', 'error'); return; }
  if (!wa && !em) { showToast('Informe WhatsApp ou e-mail', 'error'); return; }

  var data = {
    nome_responsavel: nr, nome_empresa: ne,
    whatsapp: wa || null, email: em || null,
    cidade: document.getElementById('lead-cidade').value || null,
    cep: document.getElementById('lead-cep').value || null,
    logradouro: document.getElementById('lead-logradouro').value || null,
    numero: document.getElementById('lead-numero').value || null,
    complemento: document.getElementById('lead-complemento').value || null,
    bairro: document.getElementById('lead-bairro').value || null,
    uf: document.getElementById('lead-uf').value || null,
    segmento_id: parseInt(document.getElementById('lead-segmento-id').value) || null,
    origem_lead_id: parseInt(document.getElementById('lead-origem-id').value) || null,
    valor_proposto: parseFloat(document.getElementById('lead-valor').value) || null,
    observacoes: document.getElementById('lead-observacoes').value || null,
    proximo_contato_em: document.getElementById('lead-proximo-contato').value || null,
  };

  var propostaPublicaId = parseInt(document.getElementById('lead-proposta-publica-id').value) || null;
  var validadeProposta = parseInt(document.getElementById('lead-proposta-validade').value) || 7;

  var btn = document.getElementById('btn-salvar-lead');
  await withBtnLoading(btn, async function() {
    try {
      var leadIdVinculo = leadAtualId;
      if (leadAtualId) {
        await api.patch('/tenant/comercial/leads/' + leadAtualId, data);
      } else {
        var leadCriado = await api.post('/tenant/comercial/leads', data);
        leadIdVinculo = leadCriado.id;
      }

      if (propostaPublicaId && leadIdVinculo) {
        await vincularPropostaAoLead(leadIdVinculo, propostaPublicaId, validadeProposta, data);
        showToast(leadAtualId ? 'Lead atualizado e proposta vinculada!' : 'Lead criado e proposta vinculada!', 'success');
      } else {
        showToast(leadAtualId ? 'Lead atualizado!' : 'Lead criado!', 'success');
      }

      fecharModal('modal-lead');
      carregarPipeline(); carregarDashboard(); carregarLeadsTabela();
    } catch(e) { showToast(e.message || 'Erro ao salvar lead', 'error'); }
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// PROPOSTAS PÚBLICAS
// ═══════════════════════════════════════════════════════════════════════════════

async function carregarPropostasDoLead(leadId) {
  try {
    const propostas = await api.get(`/tenant/comercial/propostas-publicas/leads/${leadId}/propostas`);
    const container = document.getElementById('lead-propostas-container');
    
    if (!container) return;
    
    if (propostas.length === 0) {
      container.innerHTML = '<p style="font-size:13px;color:var(--muted);text-align:center;padding:16px">Nenhuma proposta enviada</p>';
      return;
    }
    
    container.innerHTML = propostas.map(p => {
      const statusLabel = {
        'enviada': 'Enviada',
        'visualizada': 'Visualizada',
        'aceita': 'Aceita ✓',
        'expirada': 'Expirada'
      }[p.status] || p.status;
      
      return `
        <div class="proposta-card">
          <div class="proposta-card-header">
            <span class="proposta-card-title">${p.proposta_template?.nome || 'Proposta'}</span>
            <span class="proposta-card-status ${p.status}">${statusLabel}</span>
          </div>
          <div class="proposta-card-meta">
            <span>Enviada em ${fmtData(p.criado_em)}</span>
            <span>•</span>
            <span>Vence em ${fmtData(p.expira_em)}</span>
          </div>
          <div class="proposta-card-actions">
            <button class="btn btn-sm btn-ghost" onclick="window.open('/p/${p.slug}', '_blank')" title="Visualizar">
              👁️ Ver
            </button>
            <button class="btn btn-sm btn-ghost" onclick="abrirAnalyticsProposta(${p.id})" title="Analytics">
              📊 Analytics
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (error) {
    console.error('Erro ao carregar propostas do lead:', error);
    const container = document.getElementById('lead-propostas-container');
    if (container) {
      container.innerHTML = '<p style="font-size:13px;color:var(--error);text-align:center;padding:16px">Erro ao carregar propostas</p>';
    }
  }
}

async function abrirModalEnviarProposta(leadId) {
  try {
    // Carregar propostas públicas disponíveis
    const propostas = await api.get('/tenant/comercial/propostas-publicas?ativo=true');
    const select = document.getElementById('ep-proposta-select');
    
    if (!select) return;
    
    select.innerHTML = '<option value="">Selecione...</option>' +
      propostas.map(p => `<option value="${p.id}">${p.nome}</option>`).join('');
    
    // Limpar variáveis
    document.getElementById('ep-variaveis-container').innerHTML = '';
    document.getElementById('ep-validade').value = '7';
    
    // Guardar ID do lead
    window.enviarPropostaLeadId = leadId;
    
    document.getElementById('modal-enviar-proposta').classList.add('open');
  } catch (error) {
    console.error('Erro ao abrir modal de envio:', error);
    showToast('Erro ao carregar propostas', 'error');
  }
}

async function confirmarEnvioProposta() {
  try {
    const propostaId = document.getElementById('ep-proposta-select').value;
    if (!propostaId) {
      showToast('Selecione uma proposta', 'error');
      return;
    }
    
    // Obter proposta para carregar variáveis
    const proposta = await api.get(`/tenant/comercial/propostas-publicas/${propostaId}`);
    
    // Coletar valores das variáveis
    const dadosPersonalizados = {};
    let variaveisPendentes = 0;
    
    for (const variavel of proposta.variaveis) {
      const input = document.getElementById(`ep-var-${variavel.nome}`);
      if (input) {
        const valor = input.value.trim();
        if (variavel.obrigatorio && !valor) {
          variaveisPendentes++;
          input.style.borderColor = 'var(--error)';
        } else {
          dadosPersonalizados[variavel.nome] = valor;
          input.style.borderColor = '';
        }
      }
    }
    
    if (variaveisPendentes > 0) {
      showToast('Preencha os campos obrigatórios', 'error');
      return;
    }
    
    const validade = parseInt(document.getElementById('ep-validade').value);
    
    await api.post(`/tenant/comercial/propostas-publicas/leads/${window.enviarPropostaLeadId}/propostas`, {
      proposta_publica_id: parseInt(propostaId),
      dados_personalizados: dadosPersonalizados,
      validade_dias: validade
    });
    
    showToast('Proposta enviada com sucesso!', 'success');
    document.getElementById('modal-enviar-proposta').classList.remove('open');
    
    // Recarregar propostas do lead
    carregarPropostasDoLead(window.enviarPropostaLeadId);
  } catch (error) {
    console.error('Erro ao enviar proposta:', error);
    showToast(error.message || 'Erro ao enviar proposta', 'error');
  }
}

async function abrirAnalyticsProposta(propostaEnviadaId) {
  try {
    const analytics = await api.get(`/tenant/comercial/propostas-publicas/enviadas/${propostaEnviadaId}/analytics`);
    
    const container = document.getElementById('analytics-content');
    if (!container) return;
    
    const tempoMedio = analytics.tempo_medio_segundos ? 
      Math.floor(analytics.tempo_medio_segundos / 60) + 'min ' + 
      (analytics.tempo_medio_segundos % 60) + 's' : '—';
    
    container.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:24px">
        <div style="text-align:center;padding:16px;background:var(--surface);border-radius:8px">
          <div style="font-size:24px;font-weight:700;color:var(--accent)">${analytics.total_visualizacoes}</div>
          <div style="font-size:12px;color:var(--muted)">Visualizações</div>
        </div>
        <div style="text-align:center;padding:16px;background:var(--surface);border-radius:8px">
          <div style="font-size:24px;font-weight:700;color:var(--text)">${tempoMedio}</div>
          <div style="font-size:12px;color:var(--muted)">Tempo Médio</div>
        </div>
        <div style="text-align:center;padding:16px;background:var(--surface);border-radius:8px">
          <div style="font-size:24px;font-weight:700;color:var(--text)">${analytics.secao_mais_vista || '—'}</div>
          <div style="font-size:12px;color:var(--muted)">Seção Mais Vista</div>
        </div>
      </div>
      
      <h4 style="margin:0 0 12px 0">Histórico de Visualizações</h4>
      <div style="max-height:300px;overflow-y:auto">
        ${analytics.visualizacoes.length === 0 
          ? '<p style="text-align:center;color:var(--muted);padding:20px">Nenhuma visualização registrada</p>'
          : analytics.visualizacoes.map(v => `
            <div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border)">
              <div style="flex:1">
                <div style="font-size:12px">${v.ip || 'IP não registrado'}</div>
                <div style="font-size:11px;color:var(--muted)">${fmtDataHora(v.criado_em)}</div>
              </div>
              <div style="text-align:right">
                <div style="font-size:12px">${v.secao_mais_vista || '—'}</div>
                <div style="font-size:11px;color:var(--muted)">${v.tempo_segundos}s</div>
              </div>
            </div>
          `).join('')
        }
      </div>
    `;
    
    document.getElementById('modal-analytics-proposta').classList.add('open');
  } catch (error) {
    console.error('Erro ao carregar analytics:', error);
    showToast('Erro ao carregar analytics', 'error');
  }
}

// Event listeners para modais de proposta
document.addEventListener('DOMContentLoaded', () => {
  // Mudança de proposta no modal de envio
  document.getElementById('ep-proposta-select')?.addEventListener('change', async (e) => {
    const propostaId = e.target.value;
    const container = document.getElementById('ep-variaveis-container');
    
    if (!propostaId) {
      container.innerHTML = '';
      return;
    }
    
    try {
      const proposta = await api.get(`/tenant/comercial/propostas-publicas/${propostaId}`);
      
      if (proposta.variaveis.length === 0) {
        container.innerHTML = '<p style="font-size:13px;color:var(--muted);padding:8px">Nenhuma variável configurada</p>';
        return;
      }
      
      container.innerHTML = proposta.variaveis.map(variavel => `
        <div class="fg">
          <label class="fl">${variavel.label} ${variavel.obrigatorio ? '*' : ''}</label>
          <input type="${variavel.tipo === 'numero' ? 'number' : 'text'}" 
                 class="fi" 
                 id="ep-var-${variavel.nome}" 
                 placeholder="${variavel.obrigatorio ? 'Obrigatório' : 'Opcional'}"
                 ${variavel.obrigatorio ? 'required' : ''}>
        </div>
      `).join('');
    } catch (error) {
      console.error('Erro ao carregar variáveis:', error);
    }
  });
  
  // Botão confirmar envio
  document.getElementById('btn-confirmar-envio-proposta')?.addEventListener('click', confirmarEnvioProposta);

  // Detecção de duplicata em tempo real
  var _waInput = document.getElementById('lead-whatsapp');
  var _emInput = document.getElementById('lead-email');

  function _onContatoInput() {
    clearTimeout(_dupTimer);
    if (_dupIgnorada) return;
    _dupTimer = setTimeout(function() {
      _checkDuplicataLead(
        document.getElementById('lead-whatsapp').value,
        document.getElementById('lead-email').value
      );
    }, 500);
  }

  if (_waInput) _waInput.addEventListener('input', _onContatoInput);
  if (_emInput) _emInput.addEventListener('input', _onContatoInput);

  // Busca automática de CEP ao digitar 8 dígitos
  var _cepInput = document.getElementById('lead-cep');
  if (_cepInput) _cepInput.addEventListener('input', function() {
    var digits = this.value.replace(/\D/g, '');
    if (digits.length === 8) buscarCepLead();
  });
});

// Exportar funções
window.abrirAnalyticsProposta = abrirAnalyticsProposta;
