// COTTE — Comercial Dashboard
// Dashboard, métricas, listas de ação
// Requer: comercial-core.js

// ═══════════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarDashboard() {
  try {
    var results = await Promise.all([
      api.get('/comercial/dashboard'),
      api.get('/comercial/leads/follow-ups-hoje'),
      api.get('/comercial/leads/recentes?limit=5'),
    ]);
    renderMetrics(results[0]);
    renderActionList('followups-list', results[1], 'badge-followups');
    renderRecentList('recent-leads', results[2]);
    carregarNovosClientes();
  } catch(e) { showToast('Erro ao carregar dashboard', 'error'); }
}

async function carregarNovosClientes() {
  var el = document.getElementById('novos-clientes-list');
  var badge = document.getElementById('badge-novos-clientes');
  try {
    var origens = await api.get('/comercial/origens?ativo=true');
    origensCache = origens || origensCache;
    var origemLp = origensCache.find(function(o) { return o.nome.toLowerCase() === 'landing page'; });
    if (!origemLp) {
      el.innerHTML = '<div class="empty"><p>Nenhum cadastro via Landing Page ainda.</p></div>';
      badge.textContent = '0';
      return;
    }
    var data = await api.get('/comercial/leads?status=novo&origem_lead_id=' + origemLp.id + '&per_page=10');
    var items = data.items || [];
    badge.textContent = data.total || 0;
    if (!items.length) {
      el.innerHTML = '<div class="empty"><p>Nenhum novo cliente aguardando contato.</p></div>';
      return;
    }
    el.innerHTML = items.map(function(l) {
      return '<div class="action-item trial" data-lead-id="' + l.id + '">' +
        '<span class="ai-dot" style="background:#8b5cf6"></span>' +
        '<div class="ai-info">' +
          '<h4>' + esc(l.nome_empresa) + '</h4>' +
          '<p>' + esc(l.nome_responsavel) + ' \u00B7 ' + esc(l.whatsapp || l.email || '') + ' \u00B7 Trial</p>' +
        '</div>' +
        '<div class="ai-actions">' +
          '<button class="btn btn-sm btn-primary btn-wa-novo" data-id="' + l.id + '" style="padding:4px 10px;font-size:11px">WhatsApp</button>' +
        '</div>' +
      '</div>';
    }).join('');

    el.querySelectorAll('.action-item').forEach(function(item) {
      item.addEventListener('click', function() { abrirDetalhe(parseInt(this.dataset.leadId)); });
    });
    el.querySelectorAll('.btn-wa-novo').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        abrirModalWhatsApp(parseInt(this.dataset.id));
      });
    });
  } catch(e) {
    el.innerHTML = '<div class="empty"><p>Erro ao carregar.</p></div>';
  }
}

function renderMetrics(m) {
  var totalPipeline = (m.novos||0) + (m.propostas_enviadas||0) + (m.negociacoes||0);
  var totalFechados = (m.fechados_ganho||0) + (m.fechados_perdido||0);
  var taxaConversao = totalPipeline > 0 ? Math.round(((m.fechados_ganho||0) / (totalPipeline + totalFechados)) * 100) : 0;

  var grid = document.getElementById('metrics-grid');
  grid.innerHTML =
    '<div class="dash-kpi-row">' +
      '<div class="dash-kpi-card" data-tab="leads" role="button" tabindex="0" aria-label="Ver follow-ups">' +
        '<div class="dk-icon red">\uD83D\uDCCC</div>' +
        '<div class="dk-value" style="color:' + (m.follow_ups_hoje > 0 ? '#dc2626' : 'var(--text)') + '">' + (m.follow_ups_hoje || 0) + '</div>' +
        '<div class="dk-label">Follow-ups hoje</div><div class="dk-sub">Leads para contatar agora</div>' +
        '<span class="dk-badge ' + (m.follow_ups_hoje > 0 ? 'urgente' : 'ok') + '">' + (m.follow_ups_hoje > 0 ? 'Atenção' : 'OK') + '</span>' +
      '</div>' +
      '<div class="dash-kpi-card" data-tab="leads" role="button" tabindex="0" aria-label="Ver leads sem contato">' +
        '<div class="dk-icon amber">\u26A0\uFE0F</div>' +
        '<div class="dk-value" style="color:' + (m.leads_sem_contato > 0 ? '#d97706' : 'var(--text)') + '">' + (m.leads_sem_contato || 0) + '</div>' +
        '<div class="dk-label">Sem contato</div><div class="dk-sub">Aguardando 1\u00AA abordagem</div>' +
        '<span class="dk-badge ' + (m.leads_sem_contato > 0 ? 'urgente' : 'ok') + '">' + (m.leads_sem_contato > 0 ? 'Atenção' : 'OK') + '</span>' +
      '</div>' +
      '<div class="dash-kpi-card dash-kpi-empresas-trial" role="button" tabindex="0" aria-label="Ver leads de empresas em trial">' +
        '<div class="dk-icon violet">\uD83C\uDFE2</div>' +
        '<div class="dk-value" style="color:' + ((m.empresas_em_trial || 0) > 0 ? '#7c3aed' : 'var(--text)') + '">' + (m.empresas_em_trial || 0) + '</div>' +
        '<div class="dk-label">Empresas em trial</div><div class="dk-sub">Contas ativas no per\u00EDodo trial</div>' +
        '<span class="dk-badge ' + ((m.empresas_em_trial || 0) > 0 ? 'urgente' : 'ok') + '">' + ((m.empresas_em_trial || 0) > 0 ? 'Ativo' : 'OK') + '</span>' +
      '</div>' +
      '<div class="dash-kpi-card" data-tab="lembretes" role="button" tabindex="0" aria-label="Ver lembretes">' +
        '<div class="dk-icon purple">\u23F0</div>' +
        '<div class="dk-value">' + (m.lembretes_pendentes || 0) + '</div>' +
        '<div class="dk-label">Lembretes pendentes</div><div class="dk-sub">Agendados e em aberto</div>' +
        '<span class="dk-badge ' + (m.lembretes_pendentes > 0 ? 'urgente' : 'ok') + '">' + (m.lembretes_pendentes > 0 ? 'Pendente' : 'OK') + '</span>' +
      '</div>' +
    '</div>' +
    '<div class="dash-pipeline-row">' +
      '<div class="dash-pipe-card" data-status="novo" role="button" tabindex="0" aria-label="Ver leads novos" style="border-top:3px solid #94a3b8"><div class="dpc-num" style="color:#94a3b8">' + (m.novos || 0) + '</div><div class="dpc-lbl">Novos</div><div class="dpc-link">ver leads \u2192</div></div>' +
      '<div class="dash-pipe-card" data-status="proposta_enviada" role="button" tabindex="0" aria-label="Ver propostas" style="border-top:3px solid #f59e0b"><div class="dpc-num" style="color:#f59e0b">' + (m.propostas_enviadas || 0) + '</div><div class="dpc-lbl">Propostas</div><div class="dpc-link">ver leads \u2192</div></div>' +
      '<div class="dash-pipe-card" data-status="negociacao" role="button" tabindex="0" aria-label="Ver negociações" style="border-top:3px solid #06b6d4"><div class="dpc-num" style="color:#06b6d4">' + (m.negociacoes || 0) + '</div><div class="dpc-lbl">Negociação</div><div class="dpc-link">ver leads \u2192</div></div>' +
      '<div class="dash-pipe-card" data-status="fechado_ganho" role="button" tabindex="0" aria-label="Ver ganhos" style="border-top:3px solid #10b981"><div class="dpc-num" style="color:#10b981">' + (m.fechados_ganho || 0) + '</div><div class="dpc-lbl">Ganhos</div><div class="dpc-link">ver leads \u2192</div></div>' +
      '<div class="dash-pipe-card" data-status="fechado_perdido" role="button" tabindex="0" aria-label="Ver perdidos" style="border-top:3px solid #ef4444"><div class="dpc-num" style="color:#ef4444">' + (m.fechados_perdido || 0) + '</div><div class="dpc-lbl">Perdidos</div><div class="dpc-link">ver leads \u2192</div></div>' +
    '</div>' +
    '<div class="dash-value-row">' +
      '<div><div class="dvr-label">Pipeline ativo</div><div class="dvr-value">' + totalPipeline + ' lead' + (totalPipeline !== 1 ? 's' : '') + '</div></div>' +
      '<div class="dvr-breakdown">' +
        '<div class="dvr-item"><span class="dvr-dot" style="background:#94a3b8"></span> ' + (m.novos||0) + ' novos</div>' +
        '<div class="dvr-item"><span class="dvr-dot" style="background:#f59e0b"></span> ' + (m.propostas_enviadas||0) + ' propostas</div>' +
        '<div class="dvr-item"><span class="dvr-dot" style="background:#06b6d4"></span> ' + (m.negociacoes||0) + ' negociações</div>' +
        '<div class="dvr-item"><span class="dvr-dot" style="background:#10b981"></span> ' + taxaConversao + '% conversão</div>' +
      '</div>' +
    '</div>';

  // Event listeners para KPI cards
  grid.querySelectorAll('.dash-kpi-card[data-tab]').forEach(function(card) {
    var handler = function() { switchTab(card.dataset.tab); };
    card.addEventListener('click', handler);
    card.addEventListener('keydown', function(e) { if (e.key === 'Enter') handler(); });
  });

  // Event listeners para pipeline cards
  grid.querySelectorAll('.dash-pipe-card[data-status]').forEach(function(card) {
    var handler = function() { irParaLeadsComFiltro(card.dataset.status); };
    card.addEventListener('click', handler);
    card.addEventListener('keydown', function(e) { if (e.key === 'Enter') handler(); });
  });
}

function irParaLeadsComFiltro(status) {
  var el = document.getElementById('leads-filter-status');
  if (el) el.value = status;
  switchTab('leads');
}

function renderActionList(elId, leads, badgeId) {
  var el = document.getElementById(elId);
  if (badgeId) {
    var badgeEl = document.getElementById(badgeId);
    if (badgeEl) badgeEl.textContent = leads.length;
  }
  if (!el) return;
  if (!leads.length) {
    el.innerHTML = '<div class="state-empty" style="padding:24px"><div class="state-empty-icon">\u2705</div><div class="state-empty-desc">Nenhum item pendente</div></div>';
    return;
  }
  el.innerHTML = leads.map(function(l) {
    return '<div class="action-item" data-lead-id="' + l.id + '">' +
      '<span class="ai-dot"></span>' +
      '<div class="ai-info"><h4>' + esc(l.nome_empresa) + '</h4><p>' + esc(l.nome_responsavel) + ' \u00B7 ' + esc(l.whatsapp||l.email||'\u2014') + '</p></div>' +
      '<div class="ai-actions">' +
        (l.whatsapp ? '<button class="btn btn-sm btn-ghost btn-wa-action" data-id="' + l.id + '" style="padding:4px 8px">\uD83D\uDCF1</button>' : '') +
        (l.email ? '<button class="btn btn-sm btn-ghost btn-em-action" data-id="' + l.id + '" style="padding:4px 8px">\uD83D\uDCE7</button>' : '') +
      '</div>' +
    '</div>';
  }).join('');

  el.querySelectorAll('.action-item').forEach(function(item) {
    item.addEventListener('click', function() { abrirDetalhe(parseInt(this.dataset.leadId)); });
  });
  el.querySelectorAll('.btn-wa-action').forEach(function(btn) {
    btn.addEventListener('click', function(e) { e.stopPropagation(); abrirModalWhatsApp(parseInt(this.dataset.id)); });
  });
  el.querySelectorAll('.btn-em-action').forEach(function(btn) {
    btn.addEventListener('click', function(e) { e.stopPropagation(); abrirModalEmail(parseInt(this.dataset.id)); });
  });
}

function renderRecentList(elId, leads) {
  var el = document.getElementById(elId);
  if (!leads.length) {
    el.innerHTML = '<div class="state-empty" style="padding:24px"><div class="state-empty-icon">\uD83D\uDCEB</div><div class="state-empty-desc">Nenhum lead recente</div></div>';
    return;
  }
  el.innerHTML = leads.map(function(l) {
    return '<div class="action-item" data-lead-id="' + l.id + '">' +
      '<span class="ai-dot" style="background:#94a3b8"></span>' +
      '<div class="ai-info"><h4>' + esc(l.nome_empresa) + '</h4><p>' + esc(l.nome_responsavel) + ' \u00B7 ' + fmtData(l.criado_em) + '</p></div>' +
    '</div>';
  }).join('');

  el.querySelectorAll('.action-item').forEach(function(item) {
    item.addEventListener('click', function() { abrirDetalhe(parseInt(this.dataset.leadId)); });
  });
}
