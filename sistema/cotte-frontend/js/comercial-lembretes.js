// COTTE — Comercial Lembretes
// Lembretes CRUD
// Requer: comercial-core.js, comercial-leads.js (abrirDetalhe, concluirLembrete)

// ═══════════════════════════════════════════════════════════════════════════════
// LEMBRETES CRUD
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarLembretes() {
  var statusFiltro = document.getElementById('lembretes-filter-status')?.value || '';
  var url = '/comercial/lembretes';
  if (statusFiltro) url += '?status=' + statusFiltro;
  try {
    var items = await api.get(url);
    var el = document.getElementById('lembretes-list');
    if (!items.length) { el.innerHTML = '<div class="empty"><div class="empty-icon">\u2705</div><p>Nenhum lembrete</p></div>'; return; }

    var hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    var amanha = new Date(hoje); amanha.setDate(amanha.getDate() + 1);
    var semana = new Date(hoje); semana.setDate(semana.getDate() + 7);

    var grupos = { atrasados:[], hoje:[], amanha:[], semana:[], depois:[], concluidos:[] };
    items.forEach(function(r) {
      var s = (r.status || '').toLowerCase();
      if (s === 'concluido' || s === 'concluído') { grupos.concluidos.push(r); return; }
      if (s === 'atrasado') { grupos.atrasados.push(r); return; }
      var dt = new Date(r.data_hora); dt.setHours(0, 0, 0, 0);
      if (dt < hoje) grupos.atrasados.push(r);
      else if (dt.getTime() === hoje.getTime()) grupos.hoje.push(r);
      else if (dt.getTime() === amanha.getTime()) grupos.amanha.push(r);
      else if (dt <= semana) grupos.semana.push(r);
      else grupos.depois.push(r);
    });

    var renderItem = function(r) {
      var concluido = (r.status || '').toLowerCase().startsWith('conclu');
      var atrasado = (r.status || '').toLowerCase() === 'atrasado' || new Date(r.data_hora) < new Date();
      var canalEmoji = r.canal_sugerido === 'whatsapp' ? '\uD83D\uDCF1' : r.canal_sugerido === 'email' ? '\uD83D\uDCE7' : r.canal_sugerido === 'ligacao' ? '\uD83D\uDCDE' : '';
      return '<div class="action-item' + (!concluido && atrasado ? ' urgente' : '') + '" style="' + (concluido ? 'opacity:.6' : '') + '">' +
        '<div class="ai-info"><h4>' + esc(r.titulo) + ' ' + canalEmoji + '</h4><p>' + esc(r.lead_nome_empresa || '') + ' \u00B7 ' + fmtDataHora(r.data_hora) + '</p></div>' +
        '<div class="ai-actions">' +
          (!concluido ? '<button class="btn btn-sm btn-ghost btn-concluir-lemb-list" data-id="' + r.id + '">\u2705</button>' : '') +
          '<button class="btn btn-sm btn-ghost btn-ver-lead-lemb" data-id="' + r.lead_id + '">\uD83D\uDC41</button>' +
        '</div>' +
      '</div>';
    };

    var renderGrupo = function(titulo, lista, cor) {
      if (!lista.length) return '';
      return '<div style="margin-bottom:16px"><div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:' + (cor || 'var(--muted)') + ';margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid var(--border)">' + titulo + ' <span style="font-weight:400">(' + lista.length + ')</span></div>' + lista.map(renderItem).join('') + '</div>';
    };

    el.innerHTML =
      renderGrupo('\u26A0\uFE0F Atrasados', grupos.atrasados, '#dc2626') +
      renderGrupo('\uD83D\uDCC5 Hoje', grupos.hoje, '#d97706') +
      renderGrupo('\uD83D\uDCC5 Amanhã', grupos.amanha, '#0891b2') +
      renderGrupo('\uD83D\uDCC5 Esta semana', grupos.semana, 'var(--text)') +
      renderGrupo('\uD83D\uDCC5 Depois', grupos.depois, 'var(--muted)') +
      renderGrupo('\u2705 Concluídos', grupos.concluidos, 'var(--muted)');

    el.querySelectorAll('.btn-concluir-lemb-list').forEach(function(btn) {
      btn.addEventListener('click', function(e) { e.stopPropagation(); concluirLembrete(parseInt(this.dataset.id)); });
    });
    el.querySelectorAll('.btn-ver-lead-lemb').forEach(function(btn) {
      btn.addEventListener('click', function(e) { e.stopPropagation(); abrirDetalhe(parseInt(this.dataset.id)); });
    });
  } catch(e) { showToast('Erro ao carregar lembretes', 'error'); }
}

function abrirModalLembrete(preLeadId) {
  document.getElementById('lemb-id').value = '';
  document.getElementById('modal-lemb-title').textContent = 'Novo Lembrete';
  document.getElementById('lemb-titulo').value = '';
  document.getElementById('lemb-descricao').value = '';
  document.getElementById('lemb-data-hora').value = '';
  document.getElementById('lemb-canal').value = '';
  document.getElementById('lemb-lead-id').value = '';
  document.getElementById('lemb-lead-search').value = '';
  document.getElementById('lemb-lead-dropdown').style.display = 'none';
  if (preLeadId) {
    api.get('/comercial/leads/' + preLeadId).then(function(l) {
      document.getElementById('lemb-lead-id').value = l.id;
      document.getElementById('lemb-lead-search').value = l.nome_empresa + ' \u2014 ' + l.nome_responsavel;
    }).catch(function() {});
  }
  document.getElementById('modal-lembrete').classList.add('open');
}

async function salvarLembrete() {
  var leadId = parseInt(document.getElementById('lemb-lead-id').value);
  var titulo = document.getElementById('lemb-titulo').value;
  var dataHora = document.getElementById('lemb-data-hora').value;
  if (!leadId || !titulo || !dataHora) { showToast('Preencha lead, título e data', 'error'); return; }
  var data = { lead_id: leadId, titulo: titulo, descricao: document.getElementById('lemb-descricao').value || null, data_hora: dataHora, canal_sugerido: document.getElementById('lemb-canal').value || null };
  try {
    await api.post('/comercial/lembretes', data);
    showToast('Lembrete criado!', 'success');
    fecharModal('modal-lembrete');
    carregarLembretes();
  } catch(e) { showToast(e.message || 'Erro', 'error'); }
}
