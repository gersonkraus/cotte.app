// COTTE — Comercial Pipeline
// Kanban, drag-and-drop
// Requer: comercial-core.js, comercial-leads.js

// ═══════════════════════════════════════════════════════════════════════════════
// PIPELINE
// ═══════════════════════════════════════════════════════════════════════════════
function irParaGerarOrcamento(id, valor, desc) {
  window.location.href = 'orcamentos.html?lead_id=' + id + '&valor=' + valor + '&desc=' + encodeURIComponent(desc);
}

async function carregarPipeline() {
  try {
    var res = await api.get('/tenant/comercial/leads?per_page=200');
    var leads = res.items || res;
    renderKanban(leads);
  } catch(e) { showToast('Erro ao carregar pipeline', 'error'); }
}

function renderKanban(leads) {
  var allStages = pipelineStages.length
    ? pipelineStages.filter(function(s) { return s.ativo; })
    : [
        {slug:'novo',label:'Novo',cor:'#94a3b8',emoji:'\uD83C\uDD95',fechado:false},
        {slug:'contato_iniciado',label:'Contato',cor:'#3b82f6',emoji:'\uD83D\uDCDE',fechado:false},
        {slug:'proposta_enviada',label:'Proposta',cor:'#f59e0b',emoji:'\uD83D\uDCC4',fechado:false},
        {slug:'negociacao',label:'Negociação',cor:'#06b6d4',emoji:'\uD83E\uDD1D',fechado:false},
        {slug:'fechado_ganho',label:'Ganho',cor:'#10b981',emoji:'\u2705',fechado:true},
        {slug:'fechado_perdido',label:'Perdido',cor:'#ef4444',emoji:'\u274C',fechado:true},
      ];
  var stages = kanbanShowClosed ? allStages : allStages.filter(function(s) { return !s.fechado; });
  var board = document.getElementById('kanban-board');
  var groups = {};
  allStages.forEach(function(s) { groups[s.slug] = []; });
  leads.forEach(function(l) {
    if (groups[l.status_pipeline] !== undefined) groups[l.status_pipeline].push(l);
    else groups[l.status_pipeline] = [l];
  });

  board.innerHTML = stages.map(function(s) {
    var slug = s.slug;
    var stageColor = s.cor || STATUS_COLORS[slug] || '#94a3b8';
    var colLeads = groups[slug] || [];
    var totalValor = colLeads.reduce(function(sum, l) { return sum + (l.valor_proposto || 0); }, 0);
    var valorStr = totalValor > 0 ? '<span class="k-valor-total">R$ ' + fmtMoeda(totalValor) + '</span>' : '';
    var cardsHtml = colLeads.length
      ? colLeads.map(function(l) { return kanbanCard(l); }).join('')
      : '<div class="k-empty">Nenhum lead nesta etapa</div>';
    return '<div class="k-col" data-s="' + slug + '" role="region" aria-label="' + esc(s.label) + '">' +
      '<div class="k-head" style="border-top-color:' + stageColor + '">' +
        '<div class="k-head-left k-head-left--row"><span class="k-title-emoji" aria-hidden="true">' + esc(s.emoji || '') + '</span><div class="k-title">' + esc(s.label) + '</div>' +
          (valorStr ? '<div class="k-sub">' + valorStr + '</div>' : '') +
        '</div>' +
        '<span class="k-count">' + colLeads.length + '</span>' +
      '</div>' +
      '<div class="k-cards" id="col-' + slug + '">' +
        cardsHtml +
      '</div>' +
    '</div>';
  }).join('');

  board.querySelectorAll('.k-card').forEach(function(card) {
    card.addEventListener('dragstart', function(e) {
      card.classList.add('dragging');
      e.dataTransfer.setData('text/plain', card.dataset.id);
    });
    card.addEventListener('dragend', function() {
      card.classList.remove('dragging');
      board.querySelectorAll('.k-cards').forEach(function(c) { c.classList.remove('drag-over'); });
    });
  });

  board.querySelectorAll('.k-cards').forEach(function(col) {
    col.addEventListener('dragover', function(e) { e.preventDefault(); });
    col.addEventListener('dragenter', function() { this.classList.add('drag-over'); });
    col.addEventListener('dragleave', function() { this.classList.remove('drag-over'); });
    var slug = col.id.replace('col-', '');
    col.addEventListener('drop', function(e) { 
      this.classList.remove('drag-over');
      dropCard(e, slug); 
    });
  });
}

function kanbanCard(l) {
  var scoreClass = l.lead_score ? 'score-' + l.lead_score : '';
  var diasNoSistema = Math.floor((Date.now() - new Date(l.criado_em)) / (1000*60*60*24));
  var diasStr = diasNoSistema === 0 ? 'hoje' : diasNoSistema === 1 ? '1d' : diasNoSistema + 'd';
  var diasCls = diasNoSistema >= 14 ? 'danger' : diasNoSistema >= 7 ? 'warn' : '';
  var proxVencido = l.proximo_contato_em && new Date(l.proximo_contato_em) < new Date();

  return '<div class="k-card' + (proxVencido ? ' k-card--vencido' : '') + '" draggable="true" data-id="' + l.id + '" title="' + (proxVencido ? '\u26A0\uFE0F Próximo contato vencido' : '') + '">' +
    '<div class="k-card-header">' +
      '<div class="kc-company" style="flex:1;min-width:0">' + esc(l.nome_empresa) + '</div>' +
      '<span class="kc-days ' + diasCls + '">' + diasStr + '</span>' +
    '</div>' +
    '<div class="kc-person">' + esc(l.nome_responsavel) + '</div>' +
    '<div class="kc-meta">' +
      (l.nova_resposta_whatsapp ? '<span class="lead-wa-nova-badge lead-wa-nova-badge--compact" aria-label="Nova resposta no WhatsApp">WhatsApp</span>' : '') +
      (l.lead_score ? '<span class="kc-badge ' + scoreClass + '">' + esc(l.lead_score) + '</span>' : '') +
      (l.segmento_nome ? '<span class="kc-badge">' + esc(l.segmento_nome) + '</span>' : '') +
      (l.interesse_plano ? '<span class="kc-badge">' + esc(l.interesse_plano.toUpperCase()) + '</span>' : '') +
      (proxVencido ? '<span class="kc-badge kc-badge--vencido">\u26A0\uFE0F vencido</span>' : '') +
    '</div>' +
    (l.valor_proposto ? '<div class="kc-value">\uD83D\uDCB0 R$ ' + fmtMoeda(l.valor_proposto) + '</div>' : '') +
    '<div class="kc-actions">' +
      '<button class="kc-btn btn-kc-fast-followup" data-id="' + l.id + '" title="Segure para Follow-up amanhã 9h" aria-label="Agendar follow-up rápido" style="user-select:none;-webkit-touch-callout:none;touch-action:manipulation;">' +
        '<svg class="kc-fast-followup-icon" width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
          '<path d="M13 2 4 14h7l-1 8 10-13h-7l1-7Z" fill="currentColor"></path>' +
        '</svg>' +
      '</button>' +
      '<button class="kc-btn btn-kc-detail" data-id="' + l.id + '" title="Ver detalhes">\uD83D\uDC41</button>' +
      '<button class="kc-btn btn-kc-edit" data-id="' + l.id + '" title="Editar">\u270F\uFE0F</button>' +
      (l.whatsapp ? '<button class="kc-btn btn-kc-wa" data-id="' + l.id + '" title="WhatsApp">\uD83D\uDCF1</button>' : '') +
      (l.email ? '<button class="kc-btn btn-kc-em" data-id="' + l.id + '" title="E-mail">\uD83D\uDCE7</button>' : '') +
    '</div>' +
  '</div>';
}

// Delegação de eventos para botões do kanban
document.addEventListener('click', function(e) {
  var btn = e.target.closest('.btn-kc-detail');
  if (btn) { e.stopPropagation(); abrirDetalhe(parseInt(btn.dataset.id)); return; }
  btn = e.target.closest('.btn-kc-edit');
  if (btn) { e.stopPropagation(); editarLead(parseInt(btn.dataset.id)); return; }
  btn = e.target.closest('.btn-kc-wa');
  if (btn) { e.stopPropagation(); abrirModalWhatsApp(parseInt(btn.dataset.id)); return; }
  btn = e.target.closest('.btn-kc-em');
  if (btn) { e.stopPropagation(); abrirModalEmail(parseInt(btn.dataset.id)); return; }
});

// 1-Click Fast Follow-up (Long Press)
var lpTimer = null;
var lpTarget = null;
var lpFired = false;

function cancelLongPress() {
  if (lpTimer) { clearTimeout(lpTimer); lpTimer = null; }
  if (lpTarget) {
    lpTarget.style.transform = '';
    lpTarget.style.background = '';
    lpTarget = null;
  }
}

document.addEventListener('mousedown', function(e) {
  var btn = e.target.closest('.btn-kc-fast-followup');
  if (btn) {
    e.stopPropagation();
    lpFired = false;
    lpTarget = btn;
    btn.style.transition = 'transform 0.6s ease, background 0.6s ease';
    btn.style.transform = 'scale(1.3)';
    btn.style.background = '#fef08a';
    lpTimer = setTimeout(function() {
      lpFired = true;
      btn.style.transform = '';
      btn.style.background = '';
      agendarFastFollowup(parseInt(btn.dataset.id));
      lpTarget = null;
    }, 600);
  }
});

document.addEventListener('touchstart', function(e) {
  var btn = e.target.closest('.btn-kc-fast-followup');
  if (btn) {
    e.stopPropagation();
    lpFired = false;
    lpTarget = btn;
    btn.style.transition = 'transform 0.6s ease, background 0.6s ease';
    btn.style.transform = 'scale(1.3)';
    btn.style.background = '#fef08a';
    lpTimer = setTimeout(function() {
      lpFired = true;
      btn.style.transform = '';
      btn.style.background = '';
      agendarFastFollowup(parseInt(btn.dataset.id));
      lpTarget = null;
    }, 600);
  }
}, {passive: true});

document.addEventListener('mouseup', function(e) {
  var btn = e.target.closest('.btn-kc-fast-followup');
  if (btn && !lpFired) {
    // If they just clicked without holding, show tooltip or do nothing
    showToast('Segure o botão ⚡ por meio segundo para agendar', 'info');
  }
  cancelLongPress();
});
document.addEventListener('mouseleave', cancelLongPress);
document.addEventListener('touchend', function(e) {
  var btn = e.target.closest('.btn-kc-fast-followup');
  if (btn && !lpFired) {
    showToast('Segure o botão ⚡ por meio segundo para agendar', 'info');
  }
  cancelLongPress();
});
document.addEventListener('touchcancel', cancelLongPress);

async function agendarFastFollowup(leadId) {
  var d = new Date();
  d.setDate(d.getDate() + 1);
  if (d.getDay() === 6) d.setDate(d.getDate() + 2);
  else if (d.getDay() === 0) d.setDate(d.getDate() + 1);
  d.setHours(9, 0, 0, 0);

  var yyyy = d.getFullYear();
  var mm = String(d.getMonth() + 1).padStart(2, '0');
  var dd = String(d.getDate()).padStart(2, '0');
  var hh = String(d.getHours()).padStart(2, '0');
  var min = String(d.getMinutes()).padStart(2, '0');
  
  var data = { 
    lead_id: leadId, 
    titulo: 'Follow-up', 
    data_hora: `${yyyy}-${mm}-${dd}T${hh}:${min}`, 
    canal_sugerido: 'whatsapp' 
  };
  
  try {
    await api.post('/tenant/comercial/lembretes', data);
    showToast('Follow-up agendado para amanhã 9h!', 'success');
    if (typeof carregarLembretes === 'function') carregarLembretes();
  } catch(e) { 
    showToast('Erro ao agendar follow-up', 'error'); 
  }
}

async function dropCard(e, novoStatus) {
  e.preventDefault();
  var id = e.dataTransfer.getData('text/plain');
  try {
    await api.patch('/tenant/comercial/leads/' + id + '/status', { status: novoStatus });
    showToast('Lead movido!', 'success');
    carregarPipeline();
  } catch(err) { showToast('Erro ao mover lead', 'error'); }
}
