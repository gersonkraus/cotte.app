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
  var titEl = document.getElementById('lemb-titulo');
  titEl.value = '';
  delete titEl.dataset.auto;
  document.getElementById('lemb-descricao').value = '';
  var dtEl = document.getElementById('lemb-data-hora');
  dtEl.value = '';
  delete dtEl.dataset.auto;
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

function setLembreteData(dias, hora) {
  var d = new Date();
  d.setDate(d.getDate() + dias);
  // Pula fim de semana se for adicionar dias (opcional, mas comum em vendas)
  if (dias > 0) {
    if (d.getDay() === 6) d.setDate(d.getDate() + 2);
    else if (d.getDay() === 0) d.setDate(d.getDate() + 1);
  }
  d.setHours(hora, 0, 0, 0);
  
  // Formatar para datetime-local YYYY-MM-DDThh:mm
  var yyyy = d.getFullYear();
  var mm = String(d.getMonth() + 1).padStart(2, '0');
  var dd = String(d.getDate()).padStart(2, '0');
  var hh = String(d.getHours()).padStart(2, '0');
  var min = String(d.getMinutes()).padStart(2, '0');
  
  document.getElementById('lemb-data-hora').value = `${yyyy}-${mm}-${dd}T${hh}:${min}`;
}

async function salvarLembrete() {
  var leadId = parseInt(document.getElementById('lemb-lead-id').value);
  var titulo = document.getElementById('lemb-titulo').value;
  var dataHora = document.getElementById('lemb-data-hora').value;
  if (!leadId || isNaN(leadId)) { showToast('Selecione um lead válido', 'error'); return; }
  if (!titulo) { showToast('Preencha o título', 'error'); return; }
  if (!dataHora) { showToast('Preencha a data/hora', 'error'); return; }
  var data = { lead_id: leadId, titulo: titulo, descricao: document.getElementById('lemb-descricao').value || null, data_hora: dataHora, canal_sugerido: document.getElementById('lemb-canal').value || null };
  try {
    await api.post('/comercial/lembretes', data);
    showToast('Lembrete criado!', 'success');
    fecharModal('modal-lembrete');
    carregarLembretes();
    carregarLeadsTabela();
    carregarPipeline();
    if (document.getElementById('modal-detail').classList.contains('open')) {
      abrirDetalhe(leadId);
    }
  } catch(e) { showToast(e.message || 'Erro', 'error'); }
}

// ═══════════════════════════════════════════════════════════════════════════════
// NLU - Parser de Texto para Lembretes
// ═══════════════════════════════════════════════════════════════════════════════
function extrairIntencaoLembrete(texto) {
  if (!texto) return { intencao: null, canal: null, data: null };
  var t = texto.toLowerCase();
  var intencao = null;
  var canal = null;
  var dataObj = null;

  // 1. Extrair Intenção/Canal
  if (t.match(/ligar/i)) { intencao = "Ligar"; canal = "ligacao"; }
  else if (t.match(/reunião|reuniao/i)) { intencao = "Reunião"; canal = "reuniao"; }
  else if (t.match(/visita/i)) { intencao = "Visita técnica"; canal = "reuniao"; }
  else if (t.match(/follow[- ]?up/i)) { intencao = "Follow-up"; canal = "whatsapp"; }
  else if (t.match(/whatsapp|whats|zap/i)) { intencao = "Enviar WhatsApp"; canal = "whatsapp"; }
  else if (t.match(/e-?mail/i)) { intencao = "Enviar E-mail"; canal = "email"; }

  // 2. Extrair Data e Hora
  var matchAmanha = t.match(/amanhã|amanha/i);
  var matchHoje = t.match(/hoje/i);
  var matchDias = t.match(/daqui a (\d+) dias?/i);
  
  var matchHora = t.match(/(?:às|ás|as) (\d{1,2})(?:h|:(\d{2}))?/i);
  var horaParse = matchHora ? parseInt(matchHora[1], 10) : null;
  var minParse = (matchHora && matchHora[2]) ? parseInt(matchHora[2], 10) : 0;

  if (matchAmanha || matchHoje || matchDias) {
    dataObj = new Date();
    if (matchAmanha) {
      dataObj.setDate(dataObj.getDate() + 1);
      if (dataObj.getDay() === 6) dataObj.setDate(dataObj.getDate() + 2);
      else if (dataObj.getDay() === 0) dataObj.setDate(dataObj.getDate() + 1);
    } else if (matchDias) {
      dataObj.setDate(dataObj.getDate() + parseInt(matchDias[1], 10));
    }
    
    if (horaParse !== null) {
      dataObj.setHours(horaParse, minParse, 0, 0);
    } else {
      // Se for amanhã ou daqui a x dias e não tem hora, bota 9h
      if (!matchHoje) dataObj.setHours(9, 0, 0, 0);
    }
  }

  return { intencao: intencao, canal: canal, data: dataObj };
}

document.addEventListener('DOMContentLoaded', function() {
  var descEl = document.getElementById('lemb-descricao');
  var titEl = document.getElementById('lemb-titulo');
  var dtEl = document.getElementById('lemb-data-hora');
  var canEl = document.getElementById('lemb-canal');
  
  if (descEl && titEl && dtEl) {
    var timeout = null;
    
    // Clear auto flag on manual edit
    titEl.addEventListener('input', function() { delete titEl.dataset.auto; });
    dtEl.addEventListener('input', function() { delete dtEl.dataset.auto; });
    canEl.addEventListener('change', function() { delete canEl.dataset.auto; });

    descEl.addEventListener('input', function() {
      clearTimeout(timeout);
      timeout = setTimeout(function() {
        var ext = extrairIntencaoLembrete(descEl.value);
        var changed = false;
        
        if (ext.intencao && (!titEl.value || titEl.dataset.auto === '1')) {
          titEl.value = ext.intencao;
          titEl.dataset.auto = '1';
          if (ext.canal && (!canEl.value || canEl.dataset.auto === '1')) {
            canEl.value = ext.canal;
            canEl.dataset.auto = '1';
          }
          
          titEl.style.transition = 'background 0.3s, border-color 0.3s';
          titEl.style.backgroundColor = '#ecfdf5';
          titEl.style.borderColor = '#10b981';
          setTimeout(function() { titEl.style.backgroundColor = ''; titEl.style.borderColor = ''; }, 1000);
          changed = true;
        }
        
        if (ext.data && (!dtEl.value || dtEl.dataset.auto === '1')) {
          var d = ext.data;
          var yyyy = d.getFullYear();
          var mm = String(d.getMonth() + 1).padStart(2, '0');
          var dd = String(d.getDate()).padStart(2, '0');
          var hh = String(d.getHours()).padStart(2, '0');
          var min = String(d.getMinutes()).padStart(2, '0');
          dtEl.value = `${yyyy}-${mm}-${dd}T${hh}:${min}`;
          dtEl.dataset.auto = '1';
          
          dtEl.style.transition = 'background 0.3s, border-color 0.3s';
          dtEl.style.backgroundColor = '#ecfdf5';
          dtEl.style.borderColor = '#10b981';
          setTimeout(function() { dtEl.style.backgroundColor = ''; dtEl.style.borderColor = ''; }, 1000);
          changed = true;
        }
      }, 400);
    });
  }
});
