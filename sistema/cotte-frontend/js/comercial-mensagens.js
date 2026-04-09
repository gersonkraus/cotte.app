// COTTE — Comercial Mensagens
// WhatsApp/Email, Templates CRUD
// Requer: comercial-core.js

// ═══════════════════════════════════════════════════════════════════════════════
// WHATSAPP & EMAIL
// ═══════════════════════════════════════════════════════════════════════════════
function populateTplSelect(selectId, canal) {
  var sel = document.getElementById(selectId);
  var filtered = templatesCache.filter(function(t) { return t.canal === canal || t.canal === 'ambos'; });
  sel.innerHTML = '<option value="">Escrever manualmente</option>' + filtered.map(function(t) { return '<option value="' + t.id + '">' + esc(t.nome) + '</option>'; }).join('');
}

async function aplicarTemplate(prefix) {
  var sel = document.getElementById(prefix + '-template');
  var tplId = sel.value;
  if (!tplId || !leadAtualId) return;
  try {
    var preview = await api.post('/comercial/templates/' + tplId + '/preview', { lead_id: leadAtualId });
    document.getElementById(prefix + '-mensagem').value = preview.conteudo || '';
    if (prefix === 'em' && preview.assunto) document.getElementById('em-assunto').value = preview.assunto;
  } catch(e) { showToast('Erro ao carregar template', 'error'); }
}

function abrirModalWhatsApp(leadId) {
  leadAtualId = leadId;
  document.getElementById('wa-mensagem').value = '';
  populateTplSelect('wa-template', 'whatsapp');
  document.getElementById('modal-whatsapp').classList.add('open');
}

async function enviarWhatsApp() {
  var msg = document.getElementById('wa-mensagem').value;
  if (!msg.trim()) { showToast('Digite uma mensagem', 'error'); return; }
  var btn = document.querySelector('#modal-whatsapp .btn-primary');
  await withBtnLoading(btn, async function() {
    try {
      await api.post('/comercial/leads/' + leadAtualId + '/whatsapp', { mensagem: msg });
      showToast('WhatsApp enviado!', 'success');
      fecharModal('modal-whatsapp');
    } catch(e) { showToast(e.message || 'Erro ao enviar', 'error'); }
  });
}

function abrirModalEmail(leadId) {
  leadAtualId = leadId;
  document.getElementById('em-assunto').value = '';
  document.getElementById('em-mensagem').value = '';
  populateTplSelect('em-template', 'email');
  document.getElementById('modal-email').classList.add('open');
}

async function enviarEmail() {
  var assunto = document.getElementById('em-assunto').value;
  var msg = document.getElementById('em-mensagem').value;
  if (!assunto.trim() || !msg.trim()) { showToast('Preencha assunto e mensagem', 'error'); return; }
  var btn = document.querySelector('#modal-email .btn-primary');
  await withBtnLoading(btn, async function() {
    try {
      await api.post('/comercial/leads/' + leadAtualId + '/email', { assunto: assunto, mensagem: msg });
      showToast('E-mail enviado!', 'success');
      fecharModal('modal-email');
    } catch(e) { showToast(e.message || 'Erro ao enviar', 'error'); }
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// TEMPLATES CRUD
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarTemplates() {
  try {
    var tpls = await api.get('/comercial/templates');
    var tbody = document.getElementById('templates-tbody');
    if (!tpls.length) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty"><p>Nenhum template</p></div></td></tr>'; renderTemplatesMobile([]); return; }
    var canalEmoji = { whatsapp:'\uD83D\uDCF1', email:'\uD83D\uDCE7', sms:'\uD83D\uDCAC' };
    tbody.innerHTML = tpls.map(function(t) {
      var preview = (t.conteudo || '').replace(/\n/g, ' ').slice(0, 80) + ((t.conteudo || '').length > 80 ? '\u2026' : '');
      return '<tr>' +
        '<td><strong>' + esc(t.nome) + '</strong><div style="font-size:11px;color:var(--muted);margin-top:2px">' + esc(preview) + '</div></td>' +
        '<td>' + (TIPO_TPL_LABELS[t.tipo] || t.tipo) + '</td>' +
        '<td>' + (canalEmoji[t.canal] || '') + ' ' + (CANAL_TPL_LABELS[t.canal] || t.canal) + '</td>' +
        '<td><span class="badge-active ' + (t.ativo ? 'on' : 'off') + '">' + (t.ativo ? 'Ativo' : 'Inativo') + '</span></td>' +
        '<td><button class="btn btn-sm btn-ghost btn-edit-tpl" data-id="' + t.id + '">\u270F\uFE0F</button> <button class="btn btn-sm btn-ghost btn-del-tpl" data-id="' + t.id + '">\uD83D\uDDD1</button></td>' +
      '</tr>';
    }).join('');

    tbody.querySelectorAll('.btn-edit-tpl').forEach(function(btn) {
      btn.addEventListener('click', function() { editarTemplate(parseInt(this.dataset.id)); });
    });
    tbody.querySelectorAll('.btn-del-tpl').forEach(function(btn) {
      btn.addEventListener('click', function() { excluirTemplate(parseInt(this.dataset.id)); });
    });
    renderTemplatesMobile(tpls);
  } catch(e) { showToast('Erro ao carregar templates', 'error'); }
}

function abrirModalTemplate() {
  document.getElementById('tpl-id').value = '';
  document.getElementById('modal-tpl-title').textContent = 'Nova Campanha';
  document.getElementById('tpl-nome').value = '';
  document.getElementById('tpl-tipo').value = 'mensagem_inicial';
  document.getElementById('tpl-canal').value = 'whatsapp';
  document.getElementById('tpl-assunto').value = '';
  document.getElementById('tpl-conteudo').value = '';
  document.getElementById('modal-template').classList.add('open');
}

async function editarTemplate(id) {
  try {
    var t = await api.get('/comercial/templates/' + id);
    document.getElementById('tpl-id').value = t.id;
    document.getElementById('modal-tpl-title').textContent = 'Editar Campanha';
    document.getElementById('tpl-nome').value = t.nome;
    document.getElementById('tpl-tipo').value = t.tipo;
    document.getElementById('tpl-canal').value = t.canal;
    document.getElementById('tpl-assunto').value = t.assunto || '';
    document.getElementById('tpl-conteudo').value = t.conteudo;
    document.getElementById('modal-template').classList.add('open');
  } catch(e) { showToast('Erro', 'error'); }
}

async function salvarTemplate() {
  var nome = document.getElementById('tpl-nome').value;
  var conteudo = document.getElementById('tpl-conteudo').value;
  if (!nome || !conteudo) { showToast('Preencha nome e conteúdo', 'error'); return; }
  var data = { nome: nome, tipo: document.getElementById('tpl-tipo').value, canal: document.getElementById('tpl-canal').value, assunto: document.getElementById('tpl-assunto').value || null, conteudo: conteudo };
  var id = document.getElementById('tpl-id').value;
  try {
    if (id) { await api.patch('/comercial/templates/' + id, data); showToast('Template atualizado!', 'success'); }
    else { await api.post('/comercial/templates', data); showToast('Template criado!', 'success'); }
    fecharModal('modal-template');
    carregarTemplates();
    await carregarCadastrosCache();
  } catch(e) { showToast(e.message || 'Erro', 'error'); }
}

async function excluirTemplate(id) {
  if (!confirm('Excluir template?')) return;
  try { await api.delete('/comercial/templates/' + id); showToast('Template excluído!', 'success'); carregarTemplates(); }
  catch(e) { showToast('Erro', 'error'); }
}

function renderTemplatesMobile(tpls) {
  var container = document.getElementById('templates-cards-mobile');
  if (!container) return;
  if (!tpls.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhum template</div>'; return; }
  var canalEmoji = { whatsapp:'📱', email:'📧', sms:'💬' };
  container.innerHTML = tpls.map(function(t) {
    var preview = (t.conteudo || '').replace(/\n/g, ' ').slice(0, 60) + ((t.conteudo || '').length > 60 ? '…' : '');
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + esc(t.nome) + '</div>' +
        '<span class="badge-active ' + (t.ativo ? 'on' : 'off') + '">' + (t.ativo ? 'Ativo' : 'Inativo') + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-body">' +
        '<div>' + (canalEmoji[t.canal] || '') + ' ' + (CANAL_TPL_LABELS[t.canal] || t.canal) + ' | ' + (TIPO_TPL_LABELS[t.tipo] || t.tipo) + '</div>' +
        '<div style="font-size:11px;color:var(--muted)">' + esc(preview) + '</div>' +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="editarTemplate(' + t.id + ')">✏️ Editar</button>' +
        '<button class="btn btn-sm btn-ghost" onclick="excluirTemplate(' + t.id + ')" style="color:var(--red)">🗑️ Excluir</button>' +
      '</div></div>';
  }).join('');
}
