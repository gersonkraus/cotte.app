with open('sistema/cotte-frontend/js/comercial.js', 'r') as f:
    content = f.read()

# 1. enviarWhatsAppLote
content = content.replace(
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  try {",
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  var btn = document.getElementById('btn-enviar-whatsapp-lote');\n  if(btn) setLoading(btn, true);\n  try {"
)
content = content.replace(
    "showToast('Erro ao enviar WhatsApps: ' + (e.message || 'Desconhecido'), 'error');\n  }",
    "showToast('Erro ao enviar WhatsApps: ' + (e.message || 'Desconhecido'), 'error');\n  } finally { if(btn) setLoading(btn, false, 'Enviar \u2709\ufe0f'); }"
)

# 2. enviarEmailLote
content = content.replace(
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  try {\n    var result = await api.post('/comercial/leads/enviar-lote', {\n      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'email', delay_min: delayMin, delay_max: delayMax\n    });\n    showToast(result.enviados + '/' + result.total + ' e-mails enviados!', result.falhas > 0 ? 'error' : 'success');",
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  var btn = document.getElementById('btn-enviar-email-lote');\n  if(btn) setLoading(btn, true);\n  try {\n    var result = await api.post('/comercial/leads/enviar-lote', {\n      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'email', delay_min: delayMin, delay_max: delayMax\n    });\n    showToast(result.enviados + '/' + result.total + ' e-mails enviados!', result.falhas > 0 ? 'error' : 'success');"
)
content = content.replace(
    "showToast('Erro ao enviar e-mails: ' + (e.message || 'Desconhecido'), 'error');\n  }",
    "showToast('Erro ao enviar e-mails: ' + (e.message || 'Desconhecido'), 'error');\n  } finally { if(btn) setLoading(btn, false, 'Enviar \u2709\ufe0f'); }"
)

# 3. enviarWhatsAppLoteHistorico
content = content.replace(
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  try {\n    var result = await api.post('/comercial/leads/enviar-lote', {\n      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'whatsapp', delay_min: delayMin, delay_max: delayMax\n    });\n    showToast(result.enviados + '/' + result.total + ' WhatsApps enviados!', result.falhas > 0 ? 'error' : 'success');\n    fecharModalContatos();\n  } catch(e) { showToast('Erro: ' + (e.message || 'Desconhecido'), 'error'); }",
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  var btn = document.getElementById('btn-enviar-whatsapp-lote');\n  if(btn) setLoading(btn, true);\n  try {\n    var result = await api.post('/comercial/leads/enviar-lote', {\n      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'whatsapp', delay_min: delayMin, delay_max: delayMax\n    });\n    showToast(result.enviados + '/' + result.total + ' WhatsApps enviados!', result.falhas > 0 ? 'error' : 'success');\n    fecharModalContatos();\n  } catch(e) { showToast('Erro: ' + (e.message || 'Desconhecido'), 'error'); } finally { if(btn) setLoading(btn, false, 'Enviar \u2709\ufe0f'); }"
)

# 4. enviarEmailLoteHistorico
content = content.replace(
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  try {\n    var result = await api.post('/comercial/leads/enviar-lote', {\n      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'email', delay_min: delayMin, delay_max: delayMax\n    });\n    showToast(result.enviados + '/' + result.total + ' e-mails enviados!', result.falhas > 0 ? 'error' : 'success');\n    fecharModalContatos();\n  } catch(e) { showToast('Erro: ' + (e.message || 'Desconhecido'), 'error'); }",
    "var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;\n  var btn = document.getElementById('btn-enviar-email-lote');\n  if(btn) setLoading(btn, true);\n  try {\n    var result = await api.post('/comercial/leads/enviar-lote', {\n      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'email', delay_min: delayMin, delay_max: delayMax\n    });\n    showToast(result.enviados + '/' + result.total + ' e-mails enviados!', result.falhas > 0 ? 'error' : 'success');\n    fecharModalContatos();\n  } catch(e) { showToast('Erro: ' + (e.message || 'Desconhecido'), 'error'); } finally { if(btn) setLoading(btn, false, 'Enviar \u2709\ufe0f'); }"
)

with open('sistema/cotte-frontend/js/comercial.js', 'w') as f:
    f.write(content)
