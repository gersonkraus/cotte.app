// COTTE — Comercial Mensagens
// WhatsApp/Email, Templates CRUD
// Requer: comercial-core.js

// ═══════════════════════════════════════════════════════════════════════════════
// WHATSAPP & EMAIL
// ═══════════════════════════════════════════════════════════════════════════════
function parseTemplateSelection(value) {
  var raw = String(value || '').trim();
  if (!raw) return { tipo: '', id: null, raw: '' };
  if (raw.indexOf('pp-') === 0) return { tipo: 'pp', id: parseInt(raw.slice(3), 10), raw: raw };
  if (raw.indexOf('tpl-') === 0) return { tipo: 'tpl', id: parseInt(raw.slice(4), 10), raw: raw };
  return { tipo: 'tpl', id: parseInt(raw, 10), raw: raw };
}

function populateTplSelect(selectId, canal, incluirPropostas) {
  var sel = document.getElementById(selectId);
  if (!sel) return [];
  var filtered = (templatesCache || []).filter(function(t) { return t.canal === canal || t.canal === 'ambos'; });
  var html = '<option value="">Escrever manualmente</option>' + filtered.map(function(t) { return '<option value="tpl-' + t.id + '">' + esc(t.nome) + '</option>'; }).join('');
  if (incluirPropostas && Array.isArray(propostasPublicasCache) && propostasPublicasCache.length) {
    html += propostasPublicasCache.map(function(p) { return '<option value="pp-' + p.id + '">Proposta: ' + esc(p.nome) + '</option>'; }).join('');
  }
  sel.innerHTML = html;
  return filtered;
}

function toggleTemplateAttachmentNotice(prefix, preview) {
  var notice = document.getElementById(prefix + '-template-anexo-aviso');
  if (!notice) return;
  if (preview && preview.anexo_nome_original) {
    notice.textContent = 'Este template inclui anexo: ' + preview.anexo_nome_original;
    notice.style.display = 'block';
    return;
  }
  notice.textContent = '';
  notice.style.display = 'none';
}

async function aplicarTemplate(prefix) {
  var sel = document.getElementById(prefix + '-template');
  var selected = parseTemplateSelection(sel && sel.value);
  if (!selected.raw || !leadAtualId) {
    toggleTemplateAttachmentNotice(prefix, null);
    return;
  }
  if (selected.tipo === 'pp') {
    var proposta = (propostasPublicasCache || []).find(function(p) { return p.id === selected.id; });
    if (proposta) {
      document.getElementById(prefix + '-mensagem').value = 'Vou enviar a proposta: ' + proposta.nome + '\n\n(Clique em Enviar para prosseguir com o envio da proposta pública)';
      if (prefix === 'em') document.getElementById('em-assunto').value = 'Proposta Comercial - ' + proposta.nome;
    }
    toggleTemplateAttachmentNotice(prefix, null);
    return;
  }
  if (!selected.id) {
    toggleTemplateAttachmentNotice(prefix, null);
    return;
  }
  try {
    var preview = await api.post('/tenant/comercial/templates/' + selected.id + '/preview', { lead_id: leadAtualId });
    document.getElementById(prefix + '-mensagem').value = preview.conteudo || '';
    if (prefix === 'em' && preview.assunto) document.getElementById('em-assunto').value = preview.assunto;
    toggleTemplateAttachmentNotice(prefix, preview);
  } catch(e) { showToast('Erro ao carregar template', 'error'); }
}

async function abrirModalWhatsApp(leadId) {
  leadAtualId = leadId;
  document.getElementById('wa-mensagem').value = '';
  toggleTemplateAttachmentNotice('wa', null);
  await Promise.all([garantirTemplatesModal(), garantirPropostasPublicasCache()]);
  populateTplSelect('wa-template', 'whatsapp', true);
  document.getElementById('modal-whatsapp').classList.add('open');
}

async function enviarWhatsApp() {
  var msg = document.getElementById('wa-mensagem').value;
  var selected = parseTemplateSelection(document.getElementById('wa-template').value);
  if (selected.tipo === 'pp') {
    var propostaId = selected.id;
    if (!propostaId) { showToast('Proposta inválida', 'error'); return; }
    var btnPp = document.querySelector('#modal-whatsapp .btn-primary');
    await withBtnLoading(btnPp, async function() {
      try {
        var resp = await api.post('/tenant/comercial/propostas-publicas/leads/' + leadAtualId + '/propostas', {
          proposta_publica_id: propostaId,
          dados_personalizados: {},
          validade_dias: 7
        });
        var nomeProposta = '';
        var prop = (propostasPublicasCache || []).find(function(p) { return p.id === propostaId; });
        if (prop) nomeProposta = prop.nome || '';
        var textoWa = mensagemWhatsAppComLinkProposta(resp.slug, nomeProposta);
        await api.post('/tenant/comercial/leads/' + leadAtualId + '/whatsapp', { mensagem: textoWa });
        showToast('Proposta registrada e link enviado por WhatsApp!', 'success');
        fecharModal('modal-whatsapp');
      } catch(e) {
        var errorMsg = e.message || 'Erro ao enviar proposta';
        if (erroIndicaPropostaJaEnviada(errorMsg)) {
          abrirConfirmacaoReenvioProposta(errorMsg, {
            leadId: leadAtualId,
            propostaId: propostaId,
            canal: 'whatsapp'
          });
          return;
        }
        showToast(errorMsg, 'error');
      }
    });
    return;
  }
  if (!msg.trim()) { showToast('Digite uma mensagem', 'error'); return; }
  var btn = document.querySelector('#modal-whatsapp .btn-primary');
  await withBtnLoading(btn, async function() {
    try {
      await api.post('/tenant/comercial/leads/' + leadAtualId + '/whatsapp', {
        mensagem: msg,
        template_id: selected.tipo === 'tpl' && selected.id ? selected.id : null
      });
      showToast('WhatsApp enviado!', 'success');
      fecharModal('modal-whatsapp');
    } catch(e) { showToast(e.message || 'Erro ao enviar', 'error'); }
  });
}

async function abrirModalEmail(leadId) {
  leadAtualId = leadId;
  document.getElementById('em-assunto').value = '';
  document.getElementById('em-mensagem').value = '';
  toggleTemplateAttachmentNotice('em', null);
  await Promise.all([garantirTemplatesModal(), garantirPropostasPublicasCache()]);
  populateTplSelect('em-template', 'email', true);
  document.getElementById('modal-email').classList.add('open');
}

async function enviarEmail() {
  var assunto = document.getElementById('em-assunto').value;
  var msg = document.getElementById('em-mensagem').value;
  var selected = parseTemplateSelection(document.getElementById('em-template').value);
  if (selected.tipo === 'pp') {
    var propostaId = selected.id;
    if (!propostaId) { showToast('Proposta inválida', 'error'); return; }
    var btnPpEm = document.querySelector('#modal-email .btn-primary');
    await withBtnLoading(btnPpEm, async function() {
      try {
        var resp = await api.post('/tenant/comercial/propostas-publicas/leads/' + leadAtualId + '/propostas', {
          proposta_publica_id: propostaId,
          dados_personalizados: {},
          validade_dias: 7
        });
        var prop = (propostasPublicasCache || []).find(function(p) { return p.id === propostaId; });
        var nomeProp = (prop && prop.nome) ? prop.nome : 'Proposta';
        var link = linkPropostaPublicaPorSlug(resp.slug);
        await api.post('/tenant/comercial/leads/' + leadAtualId + '/email', {
          assunto: 'Proposta comercial — ' + nomeProp,
          mensagem: 'Olá,\n\nSegue o link para visualizar nossa proposta:\n\n' + link + '\n\nQualquer dúvida, estamos à disposição.'
        });
        showToast('Proposta registrada e link enviado por e-mail!', 'success');
        fecharModal('modal-email');
      } catch(e) {
        var errorMsg = e.message || 'Erro ao enviar proposta';
        if (erroIndicaPropostaJaEnviada(errorMsg)) {
          abrirConfirmacaoReenvioProposta(errorMsg, {
            leadId: leadAtualId,
            propostaId: propostaId,
            canal: 'email'
          });
          return;
        }
        showToast(errorMsg, 'error');
      }
    });
    return;
  }
  if (!assunto.trim() || !msg.trim()) { showToast('Preencha assunto e mensagem', 'error'); return; }
  var btn = document.querySelector('#modal-email .btn-primary');
  await withBtnLoading(btn, async function() {
    try {
      await api.post('/tenant/comercial/leads/' + leadAtualId + '/email', {
        assunto: assunto,
        mensagem: msg,
        template_id: selected.tipo === 'tpl' && selected.id ? selected.id : null
      });
      showToast('E-mail enviado!', 'success');
      fecharModal('modal-email');
    } catch(e) { showToast(e.message || 'Erro ao enviar', 'error'); }
  });
}

function rebindModalPrimaryButton(modalId, handlerName) {
  var modal = document.getElementById(modalId);
  if (!modal) return;
  var oldBtn = modal.querySelector('.btn-primary');
  if (!oldBtn || !oldBtn.parentNode) return;

  var newBtn = oldBtn.cloneNode(true);
  oldBtn.parentNode.replaceChild(newBtn, oldBtn);
  newBtn.addEventListener('click', function(event) {
    event.preventDefault();
    var handler = window[handlerName];
    if (typeof handler === 'function') return handler(event);
  });
}

function rebindMensagensModalButtons() {
  rebindModalPrimaryButton('modal-whatsapp', 'enviarWhatsApp');
  rebindModalPrimaryButton('modal-email', 'enviarEmail');
}

function assignMensagensGlobals() {
  window.populateTplSelect = populateTplSelect;
  window.aplicarTemplate = aplicarTemplate;
  window.abrirModalWhatsApp = abrirModalWhatsApp;
  window.enviarWhatsApp = enviarWhatsApp;
  window.abrirModalEmail = abrirModalEmail;
  window.enviarEmail = enviarEmail;
  rebindMensagensModalButtons();
}

assignMensagensGlobals();
window.addEventListener('load', assignMensagensGlobals);

// ═══════════════════════════════════════════════════════════════════════════════
// TEMPLATES CRUD
// ═══════════════════════════════════════════════════════════════════════════════
