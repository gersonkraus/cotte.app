// COTTE — Comercial Cadastros
// Segmentos, Origens, Pipeline Stages, Config
// Requer: comercial-core.js

// ═══════════════════════════════════════════════════════════════════════════════
// CADASTROS
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarSegmentos() {
  try {
    var items = await api.get('/comercial/segmentos');
    var tbody = document.getElementById('segmentos-tbody');
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="3"><div class="empty"><p>Nenhum segmento</p></div></td></tr>'; renderSegmentosMobile([]); return; }
    tbody.innerHTML = items.map(function(s) {
      return '<tr>' +
        '<td>' + esc(s.nome) + '</td>' +
        '<td><span class="badge-active ' + (s.ativo ? 'on' : 'off') + '">' + (s.ativo ? 'Ativo' : 'Inativo') + '</span></td>' +
        '<td><button class="btn btn-sm btn-ghost btn-edit-seg" data-id="' + s.id + '" data-nome="' + esc(s.nome) + '">\u270F\uFE0F</button> ' +
        '<button class="btn btn-sm btn-ghost btn-toggle-seg" data-id="' + s.id + '" data-ativo="' + !s.ativo + '">' + (s.ativo ? '\u23F8' : '\u25B6\uFE0F') + '</button></td>' +
      '</tr>';
    }).join('');
    tbody.querySelectorAll('.btn-edit-seg').forEach(function(btn) {
      btn.addEventListener('click', function() { editarSegmento(parseInt(this.dataset.id), this.dataset.nome); });
    });
    tbody.querySelectorAll('.btn-toggle-seg').forEach(function(btn) {
      btn.addEventListener('click', function() { toggleSegmento(parseInt(this.dataset.id), this.dataset.ativo === 'true'); });
    });
    renderSegmentosMobile(items);
  } catch(e) { showToast('Erro', 'error'); }
}

function abrirModalSegmento() {
  document.getElementById('seg-id').value = '';
  document.getElementById('seg-nome').value = '';
  document.getElementById('modal-seg-title').textContent = 'Novo Segmento';
  document.getElementById('modal-segmento').classList.add('open');
}
function editarSegmento(id, nome) {
  document.getElementById('seg-id').value = id;
  document.getElementById('seg-nome').value = nome;
  document.getElementById('modal-seg-title').textContent = 'Editar Segmento';
  document.getElementById('modal-segmento').classList.add('open');
}

async function salvarSegmento() {
  var nome = document.getElementById('seg-nome').value.trim();
  if (!nome) { showToast('Nome obrigatório', 'error'); return; }
  var id = document.getElementById('seg-id').value;
  try {
    if (id) { await api.patch('/comercial/segmentos/' + id, { nome: nome }); showToast('Segmento atualizado!', 'success'); }
    else { await api.post('/comercial/segmentos', { nome: nome }); showToast('Segmento criado!', 'success'); }
    fecharModal('modal-segmento'); carregarSegmentos(); await carregarCadastrosCache();
  } catch(e) { showToast(e.message || 'Erro', 'error'); }
}

async function toggleSegmento(id, ativo) {
  try { await api.patch('/comercial/segmentos/' + id, { ativo: ativo }); carregarSegmentos(); await carregarCadastrosCache(); }
  catch(e) { showToast('Erro', 'error'); }
}

async function carregarOrigens() {
  try {
    var items = await api.get('/comercial/origens');
    var tbody = document.getElementById('origens-tbody');
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="3"><div class="empty"><p>Nenhuma origem</p></div></td></tr>'; renderOrigensMobile([]); return; }
    tbody.innerHTML = items.map(function(o) {
      return '<tr>' +
        '<td>' + esc(o.nome) + '</td>' +
        '<td><span class="badge-active ' + (o.ativo ? 'on' : 'off') + '">' + (o.ativo ? 'Ativo' : 'Inativo') + '</span></td>' +
        '<td><button class="btn btn-sm btn-ghost btn-edit-ori" data-id="' + o.id + '" data-nome="' + esc(o.nome) + '">\u270F\uFE0F</button> ' +
        '<button class="btn btn-sm btn-ghost btn-toggle-ori" data-id="' + o.id + '" data-ativo="' + !o.ativo + '">' + (o.ativo ? '\u23F8' : '\u25B6\uFE0F') + '</button></td>' +
      '</tr>';
    }).join('');
    tbody.querySelectorAll('.btn-edit-ori').forEach(function(btn) {
      btn.addEventListener('click', function() { editarOrigem(parseInt(this.dataset.id), this.dataset.nome); });
    });
    tbody.querySelectorAll('.btn-toggle-ori').forEach(function(btn) {
      btn.addEventListener('click', function() { toggleOrigem(parseInt(this.dataset.id), this.dataset.ativo === 'true'); });
    });
    renderOrigensMobile(items);
  } catch(e) { showToast('Erro', 'error'); }
}

function abrirModalOrigem() {
  document.getElementById('ori-id').value = '';
  document.getElementById('ori-nome').value = '';
  document.getElementById('modal-ori-title').textContent = 'Nova Origem';
  document.getElementById('modal-origem').classList.add('open');
}
function editarOrigem(id, nome) {
  document.getElementById('ori-id').value = id;
  document.getElementById('ori-nome').value = nome;
  document.getElementById('modal-ori-title').textContent = 'Editar Origem';
  document.getElementById('modal-origem').classList.add('open');
}

async function salvarOrigem() {
  var nome = document.getElementById('ori-nome').value.trim();
  if (!nome) { showToast('Nome obrigatório', 'error'); return; }
  var id = document.getElementById('ori-id').value;
  try {
    if (id) { await api.patch('/comercial/origens/' + id, { nome: nome }); showToast('Origem atualizada!', 'success'); }
    else { await api.post('/comercial/origens', { nome: nome }); showToast('Origem criada!', 'success'); }
    fecharModal('modal-origem'); carregarOrigens(); await carregarCadastrosCache();
  } catch(e) { showToast(e.message || 'Erro', 'error'); }
}

async function toggleOrigem(id, ativo) {
  try { await api.patch('/comercial/origens/' + id, { ativo: ativo }); carregarOrigens(); await carregarCadastrosCache(); }
  catch(e) { showToast('Erro', 'error'); }
}

// ═══════════════════════════════════════════════════════════════════════════════
// PIPELINE STAGES
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarPipelineStagesUI() {
  try {
    var items = await api.get('/comercial/pipeline-stages');
    pipelineStages = items || [];
    reconstruirStatusMaps();
    var tbody = document.getElementById('pipeline-stages-tbody');
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="8"><div class="empty"><p>Nenhuma etapa</p></div></td></tr>'; renderEtapasMobile([]); return; }
    tbody.innerHTML = items.map(function(s) {
      return '<tr>' +
        '<td style="font-size:18px">' + (s.emoji || '') + '</td>' +
        '<td><strong>' + esc(s.label) + '</strong></td>' +
        '<td><code style="font-size:11px;background:#f1f5f9;padding:2px 6px;border-radius:4px">' + esc(s.slug) + '</code></td>' +
        '<td><span style="display:inline-block;width:20px;height:20px;border-radius:4px;background:' + s.cor + ';vertical-align:middle;border:1px solid #e2e8f0"></span> ' + s.cor + '</td>' +
        '<td>' + s.ordem + '</td>' +
        '<td>' + (s.fechado ? '<span style="color:#ef4444;font-size:11px">Fechamento</span>' : '<span style="color:#64748b;font-size:11px">Normal</span>') + '</td>' +
        '<td><span class="badge-active ' + (s.ativo ? 'on' : 'off') + '">' + (s.ativo ? 'Ativa' : 'Inativa') + '</span></td>' +
        '<td style="white-space:nowrap">' +
          '<button class="btn btn-sm btn-ghost btn-edit-ps" data-id="' + s.id + '" title="Editar">\u270F\uFE0F</button> ' +
          '<button class="btn btn-sm btn-ghost btn-toggle-ps" data-id="' + s.id + '" data-ativo="' + !s.ativo + '" title="' + (s.ativo ? 'Desativar' : 'Ativar') + '">' + (s.ativo ? '\u23F8' : '\u25B6\uFE0F') + '</button> ' +
          '<button class="btn btn-sm btn-ghost btn-del-ps" data-id="' + s.id + '" data-label="' + esc(s.label) + '" title="Excluir" style="color:#ef4444">\uD83D\uDDD1</button>' +
        '</td>' +
      '</tr>';
    }).join('');
    tbody.querySelectorAll('.btn-edit-ps').forEach(function(btn) {
      btn.addEventListener('click', function() { editarPipelineStage(parseInt(this.dataset.id)); });
    });
    tbody.querySelectorAll('.btn-toggle-ps').forEach(function(btn) {
      btn.addEventListener('click', function() { togglePipelineStage(parseInt(this.dataset.id), this.dataset.ativo === 'true'); });
    });
    tbody.querySelectorAll('.btn-del-ps').forEach(function(btn) {
      btn.addEventListener('click', function() { excluirPipelineStage(parseInt(this.dataset.id), this.dataset.label); });
    });
    renderEtapasMobile(items);
  } catch(e) { showToast('Erro ao carregar etapas', 'error'); }
}

function abrirModalPipelineStage() {
  document.getElementById('ps-id').value = '';
  document.getElementById('ps-label').value = '';
  document.getElementById('ps-slug').value = '';
  document.getElementById('ps-emoji').value = '';
  document.getElementById('ps-cor').value = '#94a3b8';
  document.getElementById('ps-ordem').value = pipelineStages.length;
  document.getElementById('ps-fechado').checked = false;
  document.getElementById('modal-ps-title').textContent = 'Nova Etapa';
  document.getElementById('ps-slug').disabled = false;
  document.getElementById('modal-pipeline-stage').classList.add('open');
}

async function editarPipelineStage(id) {
  var s = pipelineStages.find(function(x) { return x.id === id; });
  if (!s) return;
  document.getElementById('ps-id').value = s.id;
  document.getElementById('ps-label').value = s.label;
  document.getElementById('ps-slug').value = s.slug;
  document.getElementById('ps-emoji').value = s.emoji || '';
  document.getElementById('ps-cor').value = s.cor;
  document.getElementById('ps-ordem').value = s.ordem;
  document.getElementById('ps-fechado').checked = s.fechado;
  document.getElementById('modal-ps-title').textContent = 'Editar Etapa';
  document.getElementById('ps-slug').disabled = true;
  document.getElementById('modal-pipeline-stage').classList.add('open');
}

async function salvarPipelineStage() {
  var id = document.getElementById('ps-id').value;
  var label = document.getElementById('ps-label').value.trim();
  var slug = document.getElementById('ps-slug').value.trim().replace(/\s+/g, '_').toLowerCase();
  if (!label) { showToast('Nome obrigatório', 'error'); return; }
  if (!id && !slug) { showToast('Slug obrigatório', 'error'); return; }
  var payload = {
    label: label,
    cor: document.getElementById('ps-cor').value,
    emoji: document.getElementById('ps-emoji').value.trim(),
    ordem: parseInt(document.getElementById('ps-ordem').value) || 0,
    fechado: document.getElementById('ps-fechado').checked,
  };
  try {
    if (id) {
      await api.patch('/comercial/pipeline-stages/' + id, payload);
      showToast('Etapa atualizada!', 'success');
    } else {
      payload.slug = slug;
      await api.post('/comercial/pipeline-stages', payload);
      showToast('Etapa criada!', 'success');
    }
    fecharModal('modal-pipeline-stage');
    await carregarPipelineStagesUI();
  } catch(e) { showToast(e.message || 'Erro', 'error'); }
}

async function togglePipelineStage(id, ativo) {
  try {
    await api.patch('/comercial/pipeline-stages/' + id, { ativo: ativo });
    await carregarPipelineStagesUI();
  } catch(e) { showToast('Erro', 'error'); }
}

async function excluirPipelineStage(id, label) {
  if (!confirm('Excluir a etapa "' + label + '"? Isso é irreversível e só é permitido se não houver leads nessa etapa.')) return;
  try {
    await api.delete('/comercial/pipeline-stages/' + id);
    showToast('Etapa excluída!', 'success');
    await carregarPipelineStagesUI();
  } catch(e) { showToast(e.message || 'Erro ao excluir', 'error'); }
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarConfig() {
  try {
    var c = await api.get('/comercial/config');
    document.getElementById('cfg-link-demo').value = c.link_demo || '';
    document.getElementById('cfg-link-proposta').value = c.link_proposta || '';
    document.getElementById('cfg-canal-pref').value = c.canal_preferencial || 'whatsapp';
    document.getElementById('cfg-assinatura').value = c.assinatura_comercial || '';
  } catch(e) {}
}

async function salvarConfig() {
  var data = {
    link_demo: document.getElementById('cfg-link-demo').value || null,
    link_proposta: document.getElementById('cfg-link-proposta').value || null,
    canal_preferencial: document.getElementById('cfg-canal-pref').value,
    assinatura_comercial: document.getElementById('cfg-assinatura').value || null,
  };
  try { await api.patch('/comercial/config', data); showToast('Configurações salvas!', 'success'); }
  catch(e) { showToast('Erro ao salvar', 'error'); }
}

// ═══════════════════════════════════════════════════════════════════════════════
// MOBILE CARDS
// ═══════════════════════════════════════════════════════════════════════════════

function renderSegmentosMobile(items) {
  var container = document.getElementById('segmentos-cards-mobile');
  if (!container) return;
  if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhum segmento</div>'; return; }
  container.innerHTML = items.map(function(s) {
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + esc(s.nome) + '</div>' +
        '<span class="badge-active ' + (s.ativo ? 'on' : 'off') + '">' + (s.ativo ? 'Ativo' : 'Inativo') + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="editarSegmento(' + s.id + ', \'' + esc(s.nome).replace(/'/g, "\\'") + '\')">✏️ Editar</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="toggleSegmento(' + s.id + ', ' + !s.ativo + ')">' + (s.ativo ? '⏸ Desativar' : '▶️ Ativar') + '</button>' +
      '</div></div>';
  }).join('');
}

function renderOrigensMobile(items) {
  var container = document.getElementById('origens-cards-mobile');
  if (!container) return;
  if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhuma origem</div>'; return; }
  container.innerHTML = items.map(function(o) {
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + esc(o.nome) + '</div>' +
        '<span class="badge-active ' + (o.ativo ? 'on' : 'off') + '">' + (o.ativo ? 'Ativo' : 'Inativo') + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="editarOrigem(' + o.id + ', \'' + esc(o.nome).replace(/'/g, "\\'") + '\')">✏️ Editar</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="toggleOrigem(' + o.id + ', ' + !o.ativo + ')">' + (o.ativo ? '⏸ Desativar' : '▶️ Ativar') + '</button>' +
      '</div></div>';
  }).join('');
}

function renderEtapasMobile(items) {
  var container = document.getElementById('etapas-cards-mobile');
  if (!container) return;
  if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhuma etapa</div>'; return; }
  container.innerHTML = items.map(function(s) {
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + (s.emoji || '') + ' ' + esc(s.label) + '</div>' +
        '<span class="badge-active ' + (s.ativo ? 'on' : 'off') + '">' + (s.ativo ? 'Ativa' : 'Inativa') + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-body">' +
        '<div><strong>Slug:</strong> <code>' + esc(s.slug) + '</code></div>' +
        '<div><strong>Ordem:</strong> ' + s.ordem + ' | <strong>Cor:</strong> <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:' + s.cor + ';vertical-align:middle"></span> ' + s.cor + '</div>' +
        (s.fechado ? '<div style="color:#ef4444;font-size:11px">Etapa de fechamento</div>' : '') +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="editarPipelineStage(' + s.id + ')">✏️ Editar</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="togglePipelineStage(' + s.id + ', ' + !s.ativo + ')">' + (s.ativo ? '⏸' : '▶️') + '</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="excluirPipelineStage(' + s.id + ', \'' + esc(s.label).replace(/'/g, "\\'") + '\')" style="color:var(--red)">🗑️</button>' +
      '</div></div>';
  }).join('');
}

// ═══════════════════════════════════════════════════════════════════════════════
// MOBILE CARDS
// ═══════════════════════════════════════════════════════════════════════════════

function renderSegmentosMobile(items) {
  var container = document.getElementById('segmentos-cards-mobile');
  if (!container) return;
  if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhum segmento</div>'; return; }
  container.innerHTML = items.map(function(s) {
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + esc(s.nome) + '</div>' +
        '<span class="badge-active ' + (s.ativo ? 'on' : 'off') + '">' + (s.ativo ? 'Ativo' : 'Inativo') + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="editarSegmento(' + s.id + ', \'' + esc(s.nome).replace(/'/g, "\\'") + '\')">✏️ Editar</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="toggleSegmento(' + s.id + ', ' + !s.ativo + ')">' + (s.ativo ? '⏸ Desativar' : '▶️ Ativar') + '</button>' +
      '</div></div>';
  }).join('');
}

function renderOrigensMobile(items) {
  var container = document.getElementById('origens-cards-mobile');
  if (!container) return;
  if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhuma origem</div>'; return; }
  container.innerHTML = items.map(function(o) {
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + esc(o.nome) + '</div>' +
        '<span class="badge-active ' + (o.ativo ? 'on' : 'off') + '">' + (o.ativo ? 'Ativo' : 'Inativo') + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="editarOrigem(' + o.id + ', \'' + esc(o.nome).replace(/'/g, "\\'") + '\')">✏️ Editar</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="toggleOrigem(' + o.id + ', ' + !o.ativo + ')">' + (o.ativo ? '⏸ Desativar' : '▶️ Ativar') + '</button>' +
      '</div></div>';
  }).join('');
}

function renderEtapasMobile(items) {
  var container = document.getElementById('etapas-cards-mobile');
  if (!container) return;
  if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhuma etapa</div>'; return; }
  container.innerHTML = items.map(function(s) {
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + (s.emoji || '') + ' ' + esc(s.label) + '</div>' +
        '<span class="badge-active ' + (s.ativo ? 'on' : 'off') + '">' + (s.ativo ? 'Ativa' : 'Inativa') + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-body">' +
        '<div><strong>Slug:</strong> <code>' + esc(s.slug) + '</code></div>' +
        '<div><strong>Ordem:</strong> ' + s.ordem + ' | <strong>Cor:</strong> <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:' + s.cor + ';vertical-align:middle"></span> ' + s.cor + '</div>' +
        (s.fechado ? '<div style="color:#ef4444;font-size:11px">Etapa de fechamento</div>' : '') +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="editarPipelineStage(' + s.id + ')">✏️ Editar</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="togglePipelineStage(' + s.id + ', ' + !s.ativo + ')">' + (s.ativo ? '⏸' : '▶️') + '</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="excluirPipelineStage(' + s.id + ', \'' + esc(s.label).replace(/'/g, "\\'") + '\')" style="color:var(--red)">🗑️</button>' +
      '</div></div>';
  }).join('');
}
