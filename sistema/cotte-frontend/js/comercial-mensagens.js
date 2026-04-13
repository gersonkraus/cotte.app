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
