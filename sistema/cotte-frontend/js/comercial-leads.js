// COTTE — Comercial Leads
// Tabela, ordenação, detalhe, CRUD, WhatsApp/Email, lembrete inline
// Requer: comercial-core.js

// ═══════════════════════════════════════════════════════════════════════════════
// LEADS TABLE
// ═══════════════════════════════════════════════════════════════════════════════
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
    var propostas = await api.get('/comercial/propostas-publicas/leads/' + leadId + '/propostas');
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
  var search = document.getElementById('leads-search')?.value || '';
  var status = document.getElementById('leads-filter-status')?.value || '';
  var score = document.getElementById('leads-filter-score')?.value || '';
  var filtroArquivados = document.getElementById('leads-filter-arquivados')?.value || 'ativos';
  var url = '/comercial/leads?page=' + leadsPage + '&per_page=25&order_by=' + leadsOrderBy + '&order_dir=' + leadsOrderDir;
  if (search) url += '&search=' + encodeURIComponent(search);
  if (status) url += '&status=' + status;
  if (score) url += '&lead_score=' + score;
  if (typeof leadsFilterOrigemId === 'number' && leadsFilterOrigemId > 0) {
    url += '&origem_lead_id=' + leadsFilterOrigemId;
  }
  if (filtroArquivados === 'arquivados') url += '&ativo=false';
  else if (filtroArquivados === 'ativos') url += '&ativo=true';
  if (leadsFilterFollowUpHoje) url += '&follow_up_hoje=true';
  if (leadsFilterEmpresaTrial) url += '&empresa_trial=true';

  try {
    var res = await api.get(url);
    var items = res.items || [];
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
// LEAD DETAIL
// ═══════════════════════════════════════════════════════════════════════════════
async function abrirDetalhe(id) {
  leadAtualId = id;
  document.getElementById('modal-detail').classList.add('open');
  document.getElementById('detail-content').innerHTML = '<div class="loading" style="padding:60px"><div class="spinner"></div></div>';
  try {
    var l = await api.get('/comercial/leads/' + id);
    var scoreAtual = l.lead_score || 'frio';
    var statusAtual = l.status_pipeline || 'novo';
    var statusLabel = STATUS_LABELS[statusAtual] || statusAtual;
    var ini = (l.nome_empresa || l.nome_responsavel || '?').slice(0, 2).toUpperCase();
    var avatarCls = scoreAtual === 'quente' ? 'red' : scoreAtual === 'morno' ? 'amber' : '';

    var stagesForSelect = pipelineStages.length
      ? pipelineStages.filter(function(s) { return s.ativo; })
      : Object.keys(STATUS_LABELS).map(function(slug) { return {slug:slug, label:STATUS_LABELS[slug], cor:STATUS_COLORS[slug]||'#94a3b8'}; });

    var statusPills = stagesForSelect.map(function(s) {
      var isActive = l.status_pipeline === s.slug;
      var bg = isActive ? (s.cor || '#94a3b8') : 'transparent';
      return '<button class="lead-status-quick-btn' + (isActive ? ' active' : '') + '" data-lead-id="' + l.id + '" data-status="' + s.slug + '"' +
        (isActive ? ' style="background:' + bg + ';color:#fff"' : '') + '>' + esc(s.label) + '</button>';
    }).join('');

    var scorePicks = ['quente','morno','frio'].map(function(s) {
      var isActive = scoreAtual === s;
      return '<button class="score-pick' + (isActive ? ' active ' + s : '') + '" data-lead-id="' + l.id + '" data-score="' + s + '">' + s + '</button>';
    }).join('');

    var fmt = function(v) {
      var value = (v ?? '').toString().trim();
      return value ? esc(value) : '<span class="lead-field-value empty">Não informado</span>';
    };

    var diasNoSistema = Math.floor((Date.now() - new Date(l.criado_em)) / (1000*60*60*24));
    var diasStr = diasNoSistema === 0 ? 'Hoje' : diasNoSistema === 1 ? '1 dia' : diasNoSistema + ' dias';

    var html = '';

    // HEADER
    html += '<div style="display:flex;align-items:center;gap:14px;padding:20px 24px;border-bottom:1px solid var(--border);background:var(--surface);position:sticky;top:0;z-index:5">' +
      '<div class="lead-panel-avatar ' + avatarCls + '" style="width:48px;height:48px;border-radius:13px;font-size:16px">' + ini + '</div>' +
      '<div style="flex:1;min-width:0">' +
        '<div style="font-family:\'Outfit\',sans-serif;font-size:19px;font-weight:700;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(l.nome_empresa) + '</div>' +
        '<div style="font-size:13px;color:var(--muted);display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:2px">' +
          '<span>' + esc(l.nome_responsavel) + '</span>' +
          '<span style="color:var(--border)">\u00B7</span>' +
          '<span class="lead-badge status-' + statusAtual + '">' + esc(statusLabel) + '</span>' +
          (l.lead_score ? '<span class="score ' + l.lead_score + '">' + esc(l.lead_score) + '</span>' : '') +
          '<span style="color:var(--border)">\u00B7</span>' +
          '<span style="font-size:11px;color:var(--muted2)">' + diasStr + ' no pipeline</span>' +
        '</div>' +
      '</div>' +
      '<div style="display:flex;gap:6px;flex-shrink:0">' +
        (l.whatsapp ? '<button class="btn btn-sm btn-ghost btn-detail-wa" data-id="' + l.id + '" style="padding:7px 10px" title="WhatsApp">\uD83D\uDCF1</button>' : '') +
        (l.email ? '<button class="btn btn-sm btn-ghost btn-detail-em" data-id="' + l.id + '" style="padding:7px 10px" title="E-mail">\uD83D\uDCE7</button>' : '') +
        '<button class="btn btn-sm btn-ghost btn-detail-lemb" data-id="' + l.id + '" style="padding:7px 10px" title="Lembrete">\u23F0</button>' +
        '<button class="btn btn-sm btn-ghost btn-detail-edit" data-id="' + l.id + '" style="padding:7px 10px" title="Editar">\u270F\uFE0F</button>' +
        '<button class="modal-close" id="btn-close-detail" style="margin-left:4px" aria-label="Fechar">&times;</button>' +
      '</div>' +
    '</div>';

    // BODY
    html += '<div class="lead-detail-scroll" style="padding:20px 24px;display:flex;flex-direction:column;gap:16px">';

    // QUICK ACTIONS
    html += '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
      '<div style="flex:1;min-width:200px"><div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:var(--muted);margin-bottom:6px">Status do Pipeline</div><div class="lead-status-quick" style="flex-wrap:wrap">' + statusPills + '</div></div>' +
      '<div><div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:var(--muted);margin-bottom:6px">Score</div><div class="score-picker">' + scorePicks + '</div></div>' +
    '</div>';

    // TWO COLUMN LAYOUT
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px" class="lead-detail-grid">';

    // LEFT COLUMN
    html += '<div style="display:flex;flex-direction:column;gap:14px">';
    html += '<div class="lead-panel-section">' +
      '<div class="lead-panel-section-title">\uD83D\uDC64 Contato</div>' +
      '<div class="lead-field"><span class="lead-field-label">Responsável</span><span class="lead-field-value">' + fmt(l.nome_responsavel) + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">Empresa</span><span class="lead-field-value">' + fmt(l.nome_empresa) + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">WhatsApp</span><span class="lead-field-value">' + (l.whatsapp ? esc(l.whatsapp) + ' <button class=\"lead-field-action btn-detail-wa\" data-id=\"' + l.id + '\" title=\"Enviar WhatsApp\">\uD83D\uDCF1</button>' : '<span class="lead-field-value empty">\u2014</span>') + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">E-mail</span><span class="lead-field-value">' + (l.email ? esc(l.email) + ' <button class=\"lead-field-action btn-detail-em\" data-id=\"' + l.id + '\" title=\"Enviar E-mail\">\uD83D\uDCE7</button>' : '<span class="lead-field-value empty">\u2014</span>') + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">Cidade</span><span class="lead-field-value">' + fmt(l.cidade) + '</span></div>' +
    '</div>';

    html += '<div class="lead-panel-section">' +
      '<div class="lead-panel-section-title">\uD83D\uDCBC Negócio</div>' +
      '<div class="lead-field"><span class="lead-field-label">Segmento</span><span class="lead-field-value">' + fmt(l.segmento_nome) + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">Origem</span><span class="lead-field-value">' + fmt(l.origem_nome) + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">Plano Interesse</span><span class="lead-field-value">' + (l.interesse_plano ? esc(l.interesse_plano.toUpperCase()) : '<span class="lead-field-value empty">\u2014</span>') + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">Valor Proposto</span><span class="lead-field-value">' + (l.valor_proposto ? '<strong style="color:var(--green)">R$ ' + fmtMoeda(l.valor_proposto) + '</strong> <button class="lead-field-action btn-detail-gerar-orcamento" data-id="' + l.id + '" data-valor="' + (l.valor_proposto || 0) + '" data-desc="' + esc(l.nome_empresa || l.nome_responsavel) + '" title="Gerar orçamento">\uD83D\uDCC4</button>' : '<span class="lead-field-value empty">\u2014</span>') + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">Próx. Contato</span><span class="lead-field-value">' + (l.proximo_contato_em ? fmtDataHora(l.proximo_contato_em) : '<span class="lead-field-value empty">\u2014</span>') + '</span></div>' +
      '<div class="lead-field"><span class="lead-field-label">Criado em</span><span class="lead-field-value">' + fmtData(l.criado_em) + ' (' + diasStr + ')</span></div>' +
    '</div>';
    html += '</div>';

    // RIGHT COLUMN
    html += '<div style="display:flex;flex-direction:column;gap:14px">';

    if (l.empresa) {
      var emp = l.empresa;
      var empStatusMap = {'trial':{label:'Trial',color:'#8b5cf6'},'pagante':{label:'Ativo',color:'#10b981'},'bloqueado':{label:'Bloqueado',color:'#ef4444'},'expirado':{label:'Expirado',color:'#f59e0b'}};
      var empSt = empStatusMap[emp.status] || {label: emp.status, color:'var(--muted)'};
      var usuariosHtml = emp.usuarios && emp.usuarios.length
        ? emp.usuarios.map(function(u) {
            return '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">' +
              '<span style="width:6px;height:6px;border-radius:50%;background:' + (u.online ? '#10b981' : 'var(--border)') + ';flex-shrink:0;' + (u.online ? 'box-shadow:0 0 0 2px rgba(16,185,129,0.25)' : '') + '"></span>' +
              '<div style="flex:1;min-width:0"><div style="font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(u.nome) + '</div><div style="font-size:10px;color:var(--muted)">' + (u.ultima_atividade_em ? fmtDataHora(u.ultima_atividade_em) : 'Nunca acessou') + '</div></div>' +
            '</div>';
          }).join('')
        : '<div style="font-size:12px;color:var(--muted);padding:4px 0">Nenhum usuário</div>';

      html += '<div class="lead-panel-section" style="border-left:3px solid ' + empSt.color + '">' +
        '<div class="lead-panel-section-title">\uD83C\uDFE2 Empresa no Sistema <span class="pill" style="background:' + empSt.color + '20;color:' + empSt.color + ';font-size:10px;margin-left:auto">' + empSt.label + '</span></div>' +
        '<div class="lead-stats-row" style="margin-bottom:12px">' +
          '<div class="lead-stat-box"><div class="lead-stat-value" style="color:var(--accent)">' + (emp.total_orcamentos || 0) + '</div><div class="lead-stat-label">Orçamentos</div></div>' +
          '<div class="lead-stat-box"><div class="lead-stat-value" style="color:#10b981">' + (emp.orcamentos_aprovados || 0) + '</div><div class="lead-stat-label">Aprovados</div></div>' +
          '<div class="lead-stat-box"><div class="lead-stat-value" style="color:#f59e0b">' + (emp.orcamentos_pendentes || 0) + '</div><div class="lead-stat-label">Pendentes</div></div>' +
        '</div>' +
        '<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:var(--muted);margin-bottom:6px">Usuários (' + (emp.usuarios ? emp.usuarios.length : 0) + ')</div>' +
        usuariosHtml +
        '<div style="display:flex;gap:6px;margin-top:10px">' +
          '<button class="btn btn-sm btn-primary btn-reenviar-senha" data-id="' + l.id + '" style="font-size:11px;padding:5px 10px">\uD83D\uDD10 Reenviar Senha</button>' +
        '</div>' +
      '</div>';
    } else {
      html += '<div class="lead-panel-section" style="background:var(--accent-dim);border-color:rgba(6,182,212,0.2)">' +
        '<div style="text-align:center;padding:12px 0">' +
          '<div style="font-size:28px;margin-bottom:8px">\uD83D\uDE80</div>' +
          '<div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px">Converter Lead em Cliente</div>' +
          '<div style="font-size:12px;color:var(--muted);margin-bottom:14px;line-height:1.4">Crie uma conta no sistema para este lead e envie as credenciais automaticamente.</div>' +
          '<button class="btn btn-primary btn-criar-empresa" data-id="' + l.id + '" style="width:100%;justify-content:center">\u2795 Criar Empresa e Enviar Credenciais</button>' +
        '</div>' +
      '</div>';
    }

    // Propostas Públicas
    html += '<div class="lead-panel-section">' +
      '<div class="lead-panel-section-title">\ud83d\udcc4 Propostas Públicas</div>' +
      '<div id="lead-propostas-container">' +
        '<div class="loading" style="padding:20px"><div class="spinner" style="width:20px;height:20px"></div></div>' +
      '</div>' +
      '<div style="margin-top:12px">' +
        '<button class="btn btn-sm btn-primary" id="btn-enviar-proposta-lead" data-lead-id="' + l.id + '">+ Enviar Proposta</button>' +
      '</div>' +
    '</div>';

    // Lembretes
    if (l.lembretes && l.lembretes.length) {
      html += '<div class="lead-panel-section"><div class="lead-panel-section-title">\u23F0 Lembretes (' + l.lembretes.length + ')</div>';
      html += l.lembretes.slice(0, 3).map(function(r) {
        var atrasado = (r.status || '').toLowerCase() === 'atrasado';
        var concluido = (r.status || '').toLowerCase().startsWith('conclu');
        return '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);' + (concluido ? 'opacity:.5' : '') + '">' +
          '<span style="width:6px;height:6px;border-radius:50%;background:' + (atrasado ? '#ef4444' : concluido ? '#10b981' : 'var(--accent)') + ';flex-shrink:0"></span>' +
          '<div style="flex:1;min-width:0"><div style="font-size:12px;font-weight:600">' + esc(r.titulo) + '</div><div style="font-size:10px;color:var(--muted)">' + fmtDataHora(r.data_hora) + '</div></div>' +
          (!concluido ? '<button class="lead-field-action btn-concluir-lembrete" data-id="' + r.id + '" title="Concluir">\u2713</button>' : '') +
        '</div>';
      }).join('');
      if (l.lembretes.length > 3) html += '<div style="font-size:11px;color:var(--muted);margin-top:4px">+' + (l.lembretes.length - 3) + ' mais</div>';
      html += '</div>';
    }

    // Notes
    html += '<div class="lead-panel-section">' +
      '<div class="lead-panel-section-title">\uD83D\uDCDD Adicionar Nota</div>' +
      '<div class="lead-note-composer">' +
        '<textarea id="obs-input" placeholder="Escreva uma observação sobre este lead..." rows="2"></textarea>' +
        '<button class="btn btn-sm btn-primary btn-add-obs" data-id="' + l.id + '" style="flex-shrink:0;padding:6px 12px">Enviar</button>' +
      '</div>' +
    '</div>';

    if (l.observacoes) {
      html += '<div class="lead-panel-section"><div class="lead-panel-section-title">\uD83D\uDCCB Observações</div><div style="font-size:13px;color:var(--text);line-height:1.6;white-space:pre-wrap">' + esc(l.observacoes) + '</div></div>';
    }

    html += '</div>'; // end right column
    html += '</div>'; // end grid

    // TIMELINE
    if (l.interacoes && l.interacoes.length) {
      html += '<div class="lead-panel-section"><div class="lead-panel-section-title">\uD83D\uDCCB Timeline de Interações (' + l.interacoes.length + ')</div><div class="lead-timeline">';
      html += l.interacoes.slice(0, 15).map(function(i) {
        var tipo = (i.tipo || '').toLowerCase();
        var emoji = '\uD83D\uDCDD';
        if (tipo.includes('whatsapp')) emoji = '\uD83D\uDCF1';
        else if (tipo.includes('email')) emoji = '\uD83D\uDCE7';
        else if (tipo.includes('status')) emoji = '\uD83D\uDD04';
        else if (tipo.includes('lembrete')) emoji = '\u23F0';
        var sistema = tipo.includes('sistema') || tipo.includes('status') || tipo.includes('cadastro') || tipo.includes('origem');
        return '<div class="lead-tl-item"><div class="lead-tl-dot">' + emoji + '</div><div class="lead-tl-content"><div class="lead-tl-text">' + esc(i.conteudo || '') + '</div><div class="lead-tl-meta"><span class="lead-tl-tag ' + (sistema ? 'system' : 'user') + '">' + (sistema ? 'Sistema' : 'Comentário') + '</span></div></div><div class="lead-tl-time">' + fmtDataHora(i.criado_em) + '</div></div>';
      }).join('');
      if (l.interacoes.length > 15) html += '<div style="font-size:11px;color:var(--muted);padding:8px 0 0 46px">+' + (l.interacoes.length - 15) + ' interações mais antigas</div>';
      html += '</div></div>';
    }

    // DANGER ZONE
    html += '<div class="danger-zone" style="margin-top:4px">' +
      '<div class="danger-zone-title">\u26A0\uFE0F Zona de Perigo</div>' +
      '<div class="danger-zone-actions">' +
        '<button class="btn btn-sm btn-ghost btn-arquivar" data-id="' + l.id + '">' + (l.ativo ? '\uD83D\uDCE6 Arquivar Lead' : '\u267B\uFE0F Reativar Lead') + '</button>' +
        '<button class="btn btn-sm btn-danger btn-excluir-lead" data-id="' + l.id + '">\uD83D\uDDD1 Excluir permanentemente</button>' +
      '</div>' +
    '</div>';

    html += '</div>'; // end scroll body
    document.getElementById('detail-content').innerHTML = html;

    // === Event listeners do detail panel ===
    var detailContent = document.getElementById('detail-content');

    detailContent.querySelector('#btn-close-detail').addEventListener('click', function() { fecharModal('modal-detail'); });

    detailContent.querySelectorAll('.btn-detail-wa').forEach(function(btn) {
      btn.addEventListener('click', function() { abrirModalWhatsApp(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-detail-em').forEach(function(btn) {
      btn.addEventListener('click', function() { abrirModalEmail(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-detail-lemb').forEach(function(btn) {
      btn.addEventListener('click', function() { abrirModalLembrete(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-detail-edit').forEach(function(btn) {
      btn.addEventListener('click', function() { editarLead(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-detail-gerar-orcamento').forEach(function(btn) {
      btn.addEventListener('click', function() { irParaGerarOrcamento(parseInt(this.dataset.id), parseFloat(this.dataset.valor), this.dataset.desc); });
    });

    detailContent.querySelectorAll('.lead-status-quick-btn').forEach(function(btn) {
      btn.addEventListener('click', function() { alterarStatusLead(parseInt(this.dataset.leadId), this.dataset.status); });
    });
    detailContent.querySelectorAll('.score-pick').forEach(function(btn) {
      btn.addEventListener('click', function() { alterarScore(parseInt(this.dataset.leadId), this.dataset.score); });
    });

    detailContent.querySelectorAll('.btn-reenviar-senha').forEach(function(btn) {
      btn.addEventListener('click', function() { reenviarSenhaLead(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-criar-empresa').forEach(function(btn) {
      btn.addEventListener('click', function() { criarEmpresaFromLead(parseInt(this.dataset.id)); });
    });

    detailContent.querySelector('#btn-enviar-proposta-lead')?.addEventListener('click', function() {
      abrirModalEnviarProposta(parseInt(this.dataset.leadId));
    });

    carregarPropostasDoLead(l.id);

    detailContent.querySelectorAll('.lead-status-quick-btn').forEach(function(btn) {
      btn.addEventListener('click', function() { concluirLembrete(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-add-obs').forEach(function(btn) {
      btn.addEventListener('click', function() { adicionarObservacao(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-arquivar').forEach(function(btn) {
      btn.addEventListener('click', function() { arquivarLead(parseInt(this.dataset.id)); });
    });
    detailContent.querySelectorAll('.btn-excluir-lead').forEach(function(btn) {
      btn.addEventListener('click', function() { excluirLead(parseInt(this.dataset.id)); });
    });

  } catch(e) {
    document.getElementById('detail-content').innerHTML = '<div style="padding:40px;text-align:center">' +
      '<div style="font-size:40px;margin-bottom:12px">\uD83D\uDE15</div>' +
      '<div style="font-size:15px;font-weight:600;color:var(--text);margin-bottom:4px">Erro ao carregar detalhes</div>' +
      '<div style="font-size:13px;color:var(--muted)">' + esc(e.message || 'Tente novamente') + '</div>' +
    '</div>';
  }
}

async function alterarStatusLead(id, novoStatus) {
  try {
    await api.patch('/comercial/leads/' + id + '/status', { status: novoStatus });
    showToast('Status atualizado!', 'success');
    carregarPipeline();
    carregarLeadsTabela();
    abrirDetalhe(id);
  } catch(e) { showToast('Erro ao atualizar status', 'error'); abrirDetalhe(id); }
}

async function alterarScore(id, score) {
  try {
    await api.patch('/comercial/leads/' + id, { lead_score: score });
    showToast('Score atualizado!', 'success');
    carregarPipeline();
    carregarLeadsTabela();
    abrirDetalhe(id);
  } catch(e) { showToast('Erro ao atualizar score', 'error'); }
}

async function criarEmpresaFromLead(leadId) {
  if (!confirm('Criar empresa e enviar credenciais de acesso para este lead?')) return;
  try {
    var res = await api.post('/comercial/leads/' + leadId + '/criar-empresa');
    showToast(res.mensagem || 'Empresa criada com sucesso!', 'success');
    abrirDetalhe(leadId);
    carregarPipeline();
  } catch(e) { showToast(e.message || 'Erro ao criar empresa', 'error'); }
}

async function reenviarSenhaLead(leadId) {
  if (!confirm('Gerar nova senha e enviar para o lead?')) return;
  try {
    var res = await api.post('/comercial/leads/' + leadId + '/reenviar-senha');
    showToast(res.mensagem || 'Nova senha enviada!', 'success');
    abrirDetalhe(leadId);
  } catch(e) { showToast(e.message || 'Erro ao reenviar senha', 'error'); }
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
    var res = await api.get('/comercial/leads?search=' + encodeURIComponent(q) + '&per_page=10&ativo=true');
    var items = res.items || [];
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
    await api.post('/comercial/leads/' + leadId + '/observacao', { conteudo: conteudo });
    showToast('Observação adicionada!', 'success');
    abrirDetalhe(leadId);
  } catch(e) { showToast('Erro ao adicionar observação', 'error'); }
}

async function arquivarLead(id) {
  try {
    var res = await api.patch('/comercial/leads/' + id + '/arquivar');
    showToast(res.ativo ? 'Lead reativado!' : 'Lead arquivado!', 'success');
    fecharModal('modal-detail');
    carregarPipeline();
    carregarLeadsTabela();
  } catch(e) { showToast('Erro ao salvar lead', 'error'); }
}

async function excluirLead(id) {
  if (!confirm('Excluir este lead permanentemente? Esta ação não pode ser desfeita.')) return;
  try {
    await api.delete('/comercial/leads/' + id);
    showToast('Lead excluído!', 'success');
    fecharModal('modal-detail');
    carregarPipeline();
    carregarLeadsTabela();
  } catch(e) { showToast('Erro ao excluir lead', 'error'); }
}

async function concluirLembrete(id) {
  try {
    await api.post('/comercial/lembretes/' + id + '/concluir');
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
    var propostas = await api.get('/comercial/propostas-publicas?ativo=true');
    select.innerHTML = '<option value="">Não vincular agora</option>' + propostas.map(function(p) {
      return '<option value="' + p.id + '">' + esc(p.nome) + '</option>';
    }).join('');
  } catch (e) {
    select.innerHTML = '<option value="">Não vincular agora</option>';
  }
}

async function vincularPropostaAoLead(leadId, propostaPublicaId, validadeDias, dadosLead) {
  await api.post('/comercial/propostas-publicas/leads/' + leadId + '/propostas', {
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
  document.getElementById('modal-lead-title').textContent = 'Novo Lead';
  document.getElementById('form-lead').reset();
  document.getElementById('lead-id').value = '';
  document.getElementById('lead-proposta-validade').value = '7';
  populateLeadSelects();
  carregarOpcoesPropostaLead();
  limparResumoPropostaVinculadaLead();
  document.getElementById('modal-lead').classList.add('open');
}

async function editarLead(id) {
  leadAtualId = id;
  populateLeadSelects();
  await carregarOpcoesPropostaLead();
  try {
    var l = await api.get('/comercial/leads/' + id);
    document.getElementById('modal-lead-title').textContent = 'Editar Lead';
    document.getElementById('lead-id').value = l.id;
    document.getElementById('lead-nome-responsavel').value = l.nome_responsavel || '';
    document.getElementById('lead-nome-empresa').value = l.nome_empresa || '';
    document.getElementById('lead-whatsapp').value = l.whatsapp || '';
    document.getElementById('lead-email').value = l.email || '';
    document.getElementById('lead-cidade').value = l.cidade || '';
    document.getElementById('lead-segmento-id').value = l.segmento_id || '';
    document.getElementById('lead-origem-id').value = l.origem_lead_id || '';
    document.getElementById('lead-plano').value = l.interesse_plano || '';
    document.getElementById('lead-valor').value = l.valor_proposto || '';
    document.getElementById('lead-observacoes').value = l.observacoes || '';
    if (l.proximo_contato_em) document.getElementById('lead-proximo-contato').value = new Date(l.proximo_contato_em).toISOString().slice(0, 16);
    document.getElementById('lead-empresa-id').value = l.empresa_id || '';
    document.getElementById('lead-proposta-publica-id').value = '';
    document.getElementById('lead-proposta-validade').value = '7';
    await carregarResumoPropostaVinculadaLead(id);
    fecharModal('modal-detail');
    document.getElementById('modal-lead').classList.add('open');
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
    segmento_id: parseInt(document.getElementById('lead-segmento-id').value) || null,
    origem_lead_id: parseInt(document.getElementById('lead-origem-id').value) || null,
    interesse_plano: document.getElementById('lead-plano').value || null,
    valor_proposto: parseFloat(document.getElementById('lead-valor').value) || null,
    observacoes: document.getElementById('lead-observacoes').value || null,
    proximo_contato_em: document.getElementById('lead-proximo-contato').value || null,
    empresa_id: parseInt(document.getElementById('lead-empresa-id').value) || null,
  };

  var propostaPublicaId = parseInt(document.getElementById('lead-proposta-publica-id').value) || null;
  var validadeProposta = parseInt(document.getElementById('lead-proposta-validade').value) || 7;

  var btn = document.getElementById('btn-salvar-lead');
  await withBtnLoading(btn, async function() {
    try {
      var leadIdVinculo = leadAtualId;
      if (leadAtualId) {
        await api.patch('/comercial/leads/' + leadAtualId, data);
      } else {
        var leadCriado = await api.post('/comercial/leads', data);
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
    const propostas = await api.get(`/comercial/propostas-publicas/leads/${leadId}/propostas`);
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
    const propostas = await api.get('/comercial/propostas-publicas?ativo=true');
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
    const proposta = await api.get(`/comercial/propostas-publicas/${propostaId}`);
    
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
    
    await api.post(`/comercial/propostas-publicas/leads/${window.enviarPropostaLeadId}/propostas`, {
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
    const analytics = await api.get(`/comercial/propostas-publicas/enviadas/${propostaEnviadaId}/analytics`);
    
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
      const proposta = await api.get(`/comercial/propostas-publicas/${propostaId}`);
      
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
});

// Exportar funções
window.abrirAnalyticsProposta = abrirAnalyticsProposta;
