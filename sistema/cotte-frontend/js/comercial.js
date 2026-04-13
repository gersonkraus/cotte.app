// COTTE — Comercial (CRM): estado, utils, init e switchTab estão em comercial-core.js

// ═══════════════════════════════════════════════════════════════════════════════
// IMPORT TAB
// ═══════════════════════════════════════════════════════════════════════════════
function resetImportHistoricoUI() {
  var panel = document.getElementById('import-historico-panel');
  var btn = document.getElementById('btn-toggle-historico-import');
  if (panel) panel.classList.add('import-historico-hidden');
  if (btn) btn.textContent = '\uD83D\uDCCB Exibir importa\u00E7\u00F5es anteriores';
}

function toggleHistoricoImportacoes() {
  var panel = document.getElementById('import-historico-panel');
  var btn = document.getElementById('btn-toggle-historico-import');
  if (!panel || !btn) return;
  panel.classList.toggle('import-historico-hidden');
  if (!panel.classList.contains('import-historico-hidden')) {
    btn.textContent = '\uD83D\uDCCB Ocultar importa\u00E7\u00F5es anteriores';
    carregarHistoricoImportacoes();
  } else {
    btn.textContent = '\uD83D\uDCCB Exibir importa\u00E7\u00F5es anteriores';
  }
}

async function refreshHistoricoImportSeVisivel() {
  var panel = document.getElementById('import-historico-panel');
  if (!panel || panel.classList.contains('import-historico-hidden')) return;
  await carregarHistoricoImportacoes();
}

function carregarImportacao() {
  goToStep(1);
  carregarSegmentosImportacao();
  carregarTemplatesImportacao();
  resetImportHistoricoUI();
  try {
    var salvo = localStorage.getItem('importacaoLoteAtual');
    if (salvo) {
      importacaoLoteAtual = JSON.parse(salvo);
      if (!document.getElementById('import-resumo-card') && importacaoLoteAtual.total > 0) {
        mostrarResumoImportacao(importacaoLoteAtual.total);
      }
    }
  } catch(_) {}
}

// ═══════════════════════════════════════════════════════════════════════════════
// IMPORT FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════
var importMethod = 'ia';
var importData = [];

function handleCSVUpload(input) {
  var nameEl = document.getElementById('csv-file-name');
  if (input.files.length) {
    nameEl.textContent = input.files[0].name;
    importMethod = 'csv';
  } else {
    nameEl.textContent = '';
    importMethod = 'ia';
  }
}

function goToStep(step) {
  for (var i = 1; i <= 4; i++) {
    var el = document.getElementById('step-' + i);
    if (el) el.classList.toggle('hidden', i !== step);
    var circle = document.getElementById('sc-' + i);
    if (circle) {
      if (i < step) { circle.className = 'import-step-circle done'; circle.textContent = '\u2713'; }
      else if (i === step) { circle.className = 'import-step-circle active'; circle.textContent = i; }
      else { circle.className = 'import-step-circle'; circle.textContent = i; }
    }
    if (i < 4) {
      var line = document.getElementById('sl-' + i + (i+1));
      if (line) line.className = 'import-step-line' + (i < step ? ' done' : '');
    }
  }
}

async function previewImport() {
  var textEl = document.getElementById('text-data');
  var csvInput = document.getElementById('csv-file');
  if (!textEl || !csvInput) {
    showToast('Não foi possível iniciar a importação. Recarregue a página.', 'error');
    return;
  }

  var text = textEl.value.trim();
  var csvFile = csvInput.files[0];
  
  if (!text && !csvFile) {
    showToast('Cole os contatos ou selecione um CSV', 'error');
    return;
  }
  
  try {
    if (csvFile) {
      importData = await parseCSV(csvFile);
      importMethod = 'csv';
    } else {
      var response = await api.post('/comercial/leads/analisar-importacao', { texto: text });
      importData = response.items || [];
      importMethod = 'ia';
    }
  } catch(e) {
    console.error('Erro no preview da importação', e);
    showToast('Falha ao analisar os dados. Verifique o formato e tente novamente.', 'error');
    return;
  }
  
  var stats = validateImportData(importData);
  
  document.getElementById('valid-records').textContent = stats.valid;
  document.getElementById('duplicate-records').textContent = stats.duplicates;
  document.getElementById('invalid-records').textContent = stats.invalid;
  
  var tbody = document.querySelector('#preview-table tbody');
  tbody.innerHTML = importData.map(function(item, idx) {
    var isInvalid = item.status === 'inválido';
    var isChecked = item.hasOwnProperty('selecionado') ? item.selecionado : (item.status === 'válido');
    var statusClass = item.status === 'válido' ? 'valido' : item.status === 'duplicado' ? 'duplicado' : 'invalido';
    var statusLabel = item.status === 'válido' ? 'Válido' : item.status === 'duplicado' ? 'Duplicado' : 'Inválido';
    return '<tr style="' + (isInvalid ? 'opacity:.5' : '') + '">' +
      '<td class="td-center">' +
        '<input type="checkbox" class="lead-checkbox" data-idx="' + idx + '" ' + (isChecked ? 'checked' : '') + ' ' + (isInvalid ? 'disabled' : '') + '>' +
      '</td>' +
      '<td>' + esc(item.nome_responsavel || item.nome || '') + '</td>' +
      '<td>' + esc(item.nome_empresa || item.empresa || '') + '</td>' +
      '<td>' + esc(item.whatsapp || '\u2014') + '</td>' +
      '<td>' + esc(item.email || '\u2014') + '</td>' +
      '<td>' + esc(item.cidade || '\u2014') + '</td>' +
      '<td class="td-center">' +
        '<span class="preview-status-badge ' + statusClass + '">' + statusLabel + '</span>' +
        (item.error ? '<div class="preview-error-msg">' + esc(item.error) + '</div>' : '') +
      '</td>' +
    '</tr>';
  }).join('');

  function updateSelectionCount() {
    var all = document.querySelectorAll('.lead-checkbox:not([disabled])');
    var checked = document.querySelectorAll('.lead-checkbox:not([disabled]):checked');
    document.getElementById('selection-info').textContent = checked.length + ' de ' + importData.length + ' selecionados';
    document.getElementById('btn-importar').textContent = 'Importar ' + checked.length + ' leads';
    var selectAll = document.getElementById('select-all-leads');
    selectAll.checked = all.length > 0 && checked.length === all.length;
    selectAll.indeterminate = checked.length > 0 && checked.length < all.length;
  }
  document.querySelectorAll('.lead-checkbox').forEach(function(cb) { cb.onchange = updateSelectionCount; });
  document.getElementById('select-all-leads').onchange = function() {
    document.querySelectorAll('.lead-checkbox:not([disabled])').forEach(function(cb) { cb.checked = this.checked; }.bind(this));
    updateSelectionCount();
  };
  updateSelectionCount();

  goToStep(2); // CORREÇÃO: era goToStep(3), agora vai para step 2 (Revisar)
}

async function parseCSV(file) {
  return new Promise(function(resolve) {
    var reader = new FileReader();
    reader.onload = function(e) {
      var text = e.target.result;
      var lines = text.split('\n').filter(function(line) { return line.trim(); });
      var headers = lines[0].split(',').map(function(h) { return h.trim().toLowerCase(); });
      var data = lines.slice(1).map(function(line) {
        var values = line.split(',').map(function(v) { return v.trim(); });
        var item = {};
        headers.forEach(function(header, idx) { item[header] = values[idx] || ''; });
        return item;
      });
      resolve(data);
    };
    reader.readAsText(file);
  });
}

function limparResumoPropostaVinculadaLead() {
  var info = document.getElementById('lead-proposta-vinculada-info');
  if (!info) return;
  window.leadPropostaVinculadaAtualId = null;
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
    window.leadPropostaVinculadaAtualId = ultima.proposta_publica_id || null;
    var selectProposta = document.getElementById('lead-proposta-publica-id');
    if (selectProposta && window.leadPropostaVinculadaAtualId) {
      var propostaSelecionada = String(window.leadPropostaVinculadaAtualId);
      var opcaoExistente = selectProposta.querySelector('option[value="' + propostaSelecionada + '"]');
      if (!opcaoExistente && ultima.proposta_template && ultima.proposta_template.nome) {
        var option = document.createElement('option');
        option.value = propostaSelecionada;
        option.textContent = ultima.proposta_template.nome + ' (inativa)';
        selectProposta.appendChild(option);
      }
      selectProposta.value = propostaSelecionada;
    }
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

function validateImportData(data) {
  var seenWhatsApp = new Set();
  var seenEmail = new Set();

  data.forEach(function(item) {
    if (item.duplicado === true && !item.status) {
      item.status = 'duplicado';
      item.error = 'Já existe no sistema';
    }
    var nr = (item.nome_responsavel || item.nome || '').trim();
    var ne = (item.nome_empresa || item.empresa || '').trim();
    if (!nr && !ne) { item.status = 'inválido'; item.error = 'Nome ou empresa obrigatório'; return; }
    if (!nr && ne) { item.nome_responsavel = ne; }
    if (!item.whatsapp || !item.whatsapp.toString().trim()) { item.status = 'inválido'; item.error = 'Telefone obrigatório'; return; }
    item.whatsapp = item.whatsapp.toString().replace(/\D/g, '');
    if (item.whatsapp.length < 10) { item.status = 'inválido'; item.error = 'Telefone inválido'; return; }
    if (seenWhatsApp.has(item.whatsapp)) { item.status = 'duplicado'; item.error = 'WhatsApp duplicado na lista'; return; }
    seenWhatsApp.add(item.whatsapp);
    if (item.email) {
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(item.email)) { item.status = 'inválido'; item.error = 'Email inválido'; return; }
      if (seenEmail.has(item.email)) { item.status = 'duplicado'; item.error = 'Email duplicado na lista'; return; }
      seenEmail.add(item.email);
    }
    if (!item.status) { item.status = 'válido'; }
  });
  
  return {
    total: data.length,
    valid: data.filter(function(d) { return d.status === 'válido'; }).length,
    duplicates: data.filter(function(d) { return d.status === 'duplicado'; }).length,
    invalid: data.filter(function(d) { return d.status === 'inválido'; }).length
  };
}

async function executeImport() {
  var checkedBoxes = document.querySelectorAll('.lead-checkbox:checked');
  var selectedIndices = Array.from(checkedBoxes).map(function(cb) { return parseInt(cb.dataset.idx); });
  var selectedData = selectedIndices.map(function(i) { return importData[i]; });

  if (!selectedData.length) {
    showToast('Selecione pelo menos um lead para importar', 'error');
    return;
  }

  var btn = document.getElementById('btn-importar');
  await withBtnLoading(btn, async function() {
    try {
      var segmentEl = document.getElementById('segment-select');
      var templatePrefEl = document.getElementById('template-select-import');
      var segmentId = segmentEl && segmentEl.value ? parseInt(segmentEl.value, 10) : null;
      var templatePreferidoId = templatePrefEl && templatePrefEl.value
        ? parseInt(templatePrefEl.value, 10)
        : null;
      if (templatePreferidoId !== null && Number.isNaN(templatePreferidoId)) {
        templatePreferidoId = null;
      }

      var result = await api.post('/comercial/leads/importar', {
        leads: selectedData.map(function(item) {
          return {
            nome_responsavel: (item.nome_responsavel || item.nome || item.nome_empresa || item.empresa || '').trim(),
            nome_empresa: (item.nome_empresa || item.empresa || '').trim(),
            whatsapp: item.whatsapp || null,
            email: item.email || null,
            cidade: item.cidade || null,
            segmento_id: segmentId || item.segmento_id || null,
            origem_lead_id: item.origem_lead_id || null,
            observacoes: item.observacoes || null
          };
        })
      });
      
      importacaoLoteAtual = {
        leads_criados: result.leads_criados || [],
        total: result.sucesso || 0,
        erros: result.erros || 0,
        importacao_id: result.importacao_id || null,
        template_preferido_id: templatePreferidoId
      };
      try { localStorage.setItem('importacaoLoteAtual', JSON.stringify(importacaoLoteAtual)); } catch(_) {}
      
      document.getElementById('success-count').textContent = result.sucesso || 0;
      document.getElementById('error-count').textContent = result.erros || 0;
      
      var successUl = document.getElementById('success-ul');
      var errorUl = document.getElementById('error-ul');
      
      successUl.innerHTML = (result.leads_criados || []).map(function(l) {
        return '<li>' + esc(l.nome_empresa) + ' - ' + esc(l.nome_responsavel) + '</li>';
      }).join('');
      
      errorUl.innerHTML = (result.erros_detalhes || []).map(function(e) {
        return '<li>' + esc(e.lead || '') + ': ' + esc(e.erro || '') + '</li>';
      }).join('');
      
      if (result.sucesso > 0) { mostrarResumoImportacao(result.sucesso); }
      
      goToStep(4);
      refreshHistoricoImportSeVisivel();
    } catch(e) {
      showToast('Erro na importação: ' + (e.message || 'Desconhecido'), 'error');
    }
  });
}

function mostrarResumoImportacao(total) {
  var existing = document.getElementById('import-resumo-card');
  if (existing) existing.remove();
  
  var resumoCard = document.createElement('div');
  resumoCard.id = 'import-resumo-card';
  resumoCard.className = 'm-card';
  resumoCard.style.cssText = 'margin-top:16px;cursor:pointer;border-left:3px solid #10b981;';
  resumoCard.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center">' +
      '<div>' +
        '<h4 style="margin:0 0 4px 0;font-size:14px;font-weight:600">\uD83D\uDCE5 ' + total + ' contatos importados</h4>' +
        '<p style="margin:0;font-size:12px;color:var(--muted)">Status: CONTATO NÃO FEITO</p>' +
      '</div>' +
      '<button class="btn btn-sm btn-primary" id="btn-ver-contatos-importados">Ver contatos \u2192</button>' +
    '</div>';
  resumoCard.querySelector('#btn-ver-contatos-importados').addEventListener('click', function(e) {
    e.stopPropagation();
    abrirContatosImportados();
  });
  resumoCard.addEventListener('click', function() { abrirContatosImportados(); });
  
  var step4 = document.getElementById('step-4');
  step4.parentNode.insertBefore(resumoCard, step4.nextSibling);
}

async function abrirContatosImportados() {
  if (!importacaoLoteAtual || !importacaoLoteAtual.leads_criados.length) {
    showToast('Nenhum contato importado neste lote', 'error');
    return;
  }

  if (!templatesCache.length) { await carregarTemplatesImportacao(); }

  var modal = document.createElement('div');
  modal.className = 'modal-overlay open';
  modal.id = 'modal-contatos-importados';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-label', 'Contatos Importados');
  modal.innerHTML =
    '<div class="modal wide">' +
      '<div class="modal-header">' +
        '<h3 class="modal-title">\uD83D\uDCE5 Contatos Importados (' + importacaoLoteAtual.total + ')</h3>' +
        '<button class="modal-close" id="btn-fechar-modal-contatos" aria-label="Fechar">&times;</button>' +
      '</div>' +
      '<div class="modal-body">' +
        '<div style="margin-bottom:16px;padding:12px;background:var(--surface2,#f1f5f9);border-radius:8px">' +
          '<label style="display:block;font-size:12px;font-weight:500;margin-bottom:6px">Template de Mensagem *</label>' +
          '<select id="lote-template-select" class="fs" style="width:100%">' +
            '<option value="">Selecione um template para habilitar envios</option>' +
            templatesCache.map(function(t) { return '<option value="' + t.id + '">' + esc(t.nome) + '</option>'; }).join('') +
          '</select>' +
        '</div>' +
        '<div style="margin-bottom:16px;padding:12px;background:var(--surface2,#f1f5f9);border-radius:8px">' +
          '<label style="display:block;font-size:12px;font-weight:500;margin-bottom:8px">\u23F1 Intervalo entre mensagens (segundos)</label>' +
          '<div style="display:flex;gap:12px;align-items:center">' +
            '<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Mínimo</label><input type="number" id="lote-delay-min" class="fi" value="9" min="1" max="60" style="width:100%"></div>' +
            '<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Máximo</label><input type="number" id="lote-delay-max" class="fi" value="15" min="1" max="60" style="width:100%"></div>' +
          '</div>' +
          '<p style="font-size:11px;color:var(--muted);margin:8px 0 0 0">\u2139\uFE0F O sistema aguarda um tempo aleatório entre o mínimo e máximo para cada mensagem.</p>' +
        '</div>' +
        '<div style="max-height:300px;overflow-y:auto">' +
          '<table style="width:100%;border-collapse:collapse;font-size:13px">' +
            '<thead><tr>' +
              '<th style="padding:8px;text-align:center;width:36px"><input type="checkbox" id="select-all-lote" checked></th>' +
              '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">Nome</th>' +
              '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">Empresa</th>' +
              '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">WhatsApp</th>' +
              '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">E-mail</th>' +
              '<th style="text-align:center;padding:8px;width:44px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">Ação</th>' +
            '</tr></thead>' +
            '<tbody id="lote-leads-tbody">' +
              importacaoLoteAtual.leads_criados.map(function(l) {
                return '<tr id="lote-lead-row-' + l.id + '">' +
                  '<td style="padding:8px;text-align:center"><input type="checkbox" class="lote-lead-checkbox" data-id="' + l.id + '" ' + (l.whatsapp || l.email ? 'checked' : 'disabled') + '></td>' +
                  '<td style="padding:8px">' + esc(l.nome_responsavel) + '</td>' +
                  '<td style="padding:8px">' + esc(l.nome_empresa) + '</td>' +
                  '<td style="padding:8px">' + (l.whatsapp ? esc(l.whatsapp) : '\u2014') + '</td>' +
                  '<td style="padding:8px">' + (l.email ? esc(l.email) : '\u2014') + '</td>' +
                  '<td style="padding:8px;text-align:center"><button class="btn btn-sm btn-ghost btn-excluir-lote-lead" data-id="' + l.id + '" style="color:#ef4444;font-size:14px;padding:2px 6px" title="Excluir lead">\uD83D\uDDD1</button></td>' +
                '</tr>';
              }).join('') +
            '</tbody>' +
          '</table>' +
        '</div>' +
        '<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">' +
          '<button class="btn btn-primary" id="btn-enviar-whatsapp-lote" disabled>\uD83D\uDCF1 Enviar WhatsApp</button>' +
          '<button class="btn btn-secondary" id="btn-enviar-email-lote" disabled>\uD83D\uDCE7 Enviar E-mail</button>' +
          '<button class="btn btn-ghost" id="btn-excluir-todos-lote" style="color:#ef4444;margin-left:auto">\uD83D\uDDD1 Excluir todos</button>' +
          '<button class="btn btn-ghost" id="btn-fechar-modal-contatos-2">Fechar</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  document.body.appendChild(modal);

  // Event listeners (sem onclick inline)
  document.getElementById('btn-fechar-modal-contatos').addEventListener('click', fecharModalContatos);
  document.getElementById('btn-fechar-modal-contatos-2').addEventListener('click', fecharModalContatos);
  document.getElementById('btn-enviar-whatsapp-lote').addEventListener('click', enviarWhatsAppLote);
  document.getElementById('btn-enviar-email-lote').addEventListener('click', enviarEmailLote);
  document.getElementById('btn-excluir-todos-lote').addEventListener('click', excluirTodosLote);

  modal.querySelectorAll('.btn-excluir-lote-lead').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      excluirLeadLote(parseInt(this.dataset.id));
    });
  });

  document.getElementById('lote-template-select').addEventListener('change', function() {
    var hasTemplate = !!this.value;
    document.getElementById('btn-enviar-whatsapp-lote').disabled = !hasTemplate;
    document.getElementById('btn-enviar-email-lote').disabled = !hasTemplate;
  });

  document.getElementById('select-all-lote').addEventListener('change', function() {
    document.querySelectorAll('.lote-lead-checkbox:not([disabled])').forEach(function(cb) { cb.checked = this.checked; }.bind(this));
  });

  var loteTpl = document.getElementById('lote-template-select');
  if (loteTpl && importacaoLoteAtual.template_preferido_id) {
    loteTpl.value = String(importacaoLoteAtual.template_preferido_id);
    loteTpl.dispatchEvent(new Event('change', { bubbles: true }));
  }
}

function fecharModalContatos() {
  var modal = document.getElementById('modal-contatos-importados');
  if (modal) modal.remove();
}

async function excluirLeadLote(leadId) {
  if (!confirm('Excluir este lead?')) return;
  try {
    await api.delete('/comercial/leads/' + leadId);
    var row = document.getElementById('lote-lead-row-' + leadId);
    if (row) row.remove();
    if (importacaoLoteAtual) {
      importacaoLoteAtual.leads_criados = importacaoLoteAtual.leads_criados.filter(function(l) { return l.id !== leadId; });
      importacaoLoteAtual.total = importacaoLoteAtual.leads_criados.length;
      try { localStorage.setItem('importacaoLoteAtual', JSON.stringify(importacaoLoteAtual)); } catch(_) {}
      var titleEl = document.querySelector('#modal-contatos-importados .modal-title');
      if (titleEl) titleEl.textContent = '\uD83D\uDCE5 Contatos Importados (' + importacaoLoteAtual.total + ')';
      if (importacaoLoteAtual.total === 0) {
        fecharModalContatos();
        var resumoCard = document.getElementById('import-resumo-card');
        if (resumoCard) resumoCard.remove();
      }
    }
    showToast('Lead excluído!', 'success');
  } catch(e) {
    showToast('Erro ao excluir: ' + (e.message || ''), 'error');
  }
}

async function excluirTodosLote() {
  if (!importacaoLoteAtual || !importacaoLoteAtual.leads_criados.length) return;
  var total = importacaoLoteAtual.leads_criados.length;
  if (!confirm('Excluir TODOS os ' + total + ' leads importados?\n\nEsta ação é irreversível.')) return;
  try {
    var ids = importacaoLoteAtual.leads_criados.map(function(l) { return l.id; });
    await Promise.all(ids.map(function(id) { return api.delete('/comercial/leads/' + id); }));
    importacaoLoteAtual = null;
    try { localStorage.removeItem('importacaoLoteAtual'); } catch(_) {}
    fecharModalContatos();
    var resumoCard = document.getElementById('import-resumo-card');
    if (resumoCard) resumoCard.remove();
    showToast(total + ' leads excluídos!', 'success');
  } catch(e) {
    showToast('Erro ao excluir: ' + (e.message || ''), 'error');
  }
}

async function enviarWhatsAppLote() {
  var templateId = document.getElementById('lote-template-select').value;
  if (!templateId) { showToast('Selecione um template', 'error'); return; }
  var checkedBoxes = document.querySelectorAll('.lote-lead-checkbox:checked');
  var leadIds = Array.from(checkedBoxes).map(function(cb) { return parseInt(cb.dataset.id); });
  if (!leadIds.length) { showToast('Selecione pelo menos um contato', 'error'); return; }
  var delayMin = parseInt(document.getElementById('lote-delay-min').value) || 9;
  var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;
  var btn = document.getElementById('btn-enviar-whatsapp-lote');
  if(btn) setLoading(btn, true);
  try {
    var result = await api.post('/comercial/leads/enviar-lote', {
      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'whatsapp', delay_min: delayMin, delay_max: delayMax
    });
    var delayInfo = result.delay_configurado ? ' (intervalo: ' + result.delay_configurado.min + 's - ' + result.delay_configurado.max + 's)' : '';
    showToast(result.enviados + '/' + result.total + ' WhatsApps enviados!' + delayInfo, result.falhas > 0 ? 'error' : 'success');
    fecharModalContatos();
    if (result.falhas === 0) {
      importacaoLoteAtual = null;
      try { localStorage.removeItem('importacaoLoteAtual'); } catch(_) {}
      var resumoCard = document.getElementById('import-resumo-card');
      if (resumoCard) resumoCard.remove();
    }
  } catch(e) {
    showToast('Erro ao enviar WhatsApps: ' + (e.message || 'Desconhecido'), 'error');
  } finally { if(btn) setLoading(btn, false, 'Enviar ✉️'); }
}

async function enviarEmailLote() {
  var templateId = document.getElementById('lote-template-select').value;
  if (!templateId) { showToast('Selecione um template', 'error'); return; }
  var checkedBoxes = document.querySelectorAll('.lote-lead-checkbox:checked');
  var leadIds = Array.from(checkedBoxes).map(function(cb) { return parseInt(cb.dataset.id); });
  if (!leadIds.length) { showToast('Selecione pelo menos um contato', 'error'); return; }
  var delayMin = parseInt(document.getElementById('lote-delay-min').value) || 9;
  var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;
  var btn = document.getElementById('btn-enviar-whatsapp-lote');
  if(btn) setLoading(btn, true);
  try {
    var result = await api.post('/comercial/leads/enviar-lote', {
      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'email', delay_min: delayMin, delay_max: delayMax
    });
    showToast(result.enviados + '/' + result.total + ' e-mails enviados!', result.falhas > 0 ? 'error' : 'success');
    fecharModalContatos();
    if (result.falhas === 0) {
      importacaoLoteAtual = null;
      try { localStorage.removeItem('importacaoLoteAtual'); } catch(_) {}
      var resumoCard = document.getElementById('import-resumo-card');
      if (resumoCard) resumoCard.remove();
    }
  } catch(e) {
    showToast('Erro ao enviar e-mails: ' + (e.message || 'Desconhecido'), 'error');
  } finally { if(btn) setLoading(btn, false, 'Enviar ✉️'); }
}

function resetImport() {
  importMethod = 'ia';
  importData = [];
  importacaoLoteAtual = null;
  try { localStorage.removeItem('importacaoLoteAtual'); } catch(_) {}
  document.getElementById('text-data').value = '';
  document.getElementById('csv-file').value = '';
  document.getElementById('csv-file-name').textContent = '';
  document.getElementById('segment-select').value = '';
  var resumoCard = document.getElementById('import-resumo-card');
  if (resumoCard) resumoCard.remove();
  goToStep(1);
}

async function carregarSegmentosImportacao() {
  try {
    var segmentos = await api.get('/comercial/segmentos?ativo=true');
    var select = document.getElementById('segment-select');
    if (!select) {
      console.warn('Elemento segment-select não encontrado na aba importação');
      return;
    }
    var valorAtual = select.value;
    select.innerHTML = '<option value="">Selecione um segmento</option>' +
      segmentos.map(function(s) { return '<option value="' + s.id + '">' + esc(s.nome) + '</option>'; }).join('');
    if (valorAtual) select.value = valorAtual;
  } catch(e) { console.warn('Erro ao carregar segmentos para importação', e); }
}

async function carregarTemplatesImportacao() {
  try {
    var templates = await api.get('/comercial/templates?ativo=true');
    templatesCache = templates || [];
    var select = document.getElementById('template-select-import');
    if (!select) return;
    var valorAtual = select.value;
    select.innerHTML = '<option value="">Nenhum</option>' +
      templatesCache.map(function(t) { return '<option value="' + t.id + '">' + esc(t.nome) + '</option>'; }).join('');
    if (valorAtual) select.value = valorAtual;
  } catch(e) {
    console.warn('Erro ao carregar templates para importação', e);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// HISTÓRICO DE IMPORTAÇÕES
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarHistoricoImportacoes() {
  var tbody = document.getElementById('historico-importacoes-tbody');
  try {
    var importacoes = await api.get('/comercial/import/list');
    if (!importacoes || !importacoes.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--muted)">Nenhuma importação realizada ainda.</td></tr>';
      renderHistoricoMobile([]);
      return;
    }
    tbody.innerHTML = importacoes.map(function(imp) {
      var data = imp.criado_em ? new Date(imp.criado_em).toLocaleDateString('pt-BR', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}) : '\u2014';
      var metodoLabel = imp.metodo === 'ia' ? '\uD83E\uDD16 IA' : imp.metodo === 'csv' ? '\uD83D\uDCC4 CSV' : '\uD83D\uDCCB Colar';
      return '<tr class="importacao-row" data-id="' + imp.id + '" data-nome="' + esc(imp.nome) + '" style="cursor:pointer">' +
        '<td>' + esc(imp.nome) + '</td>' +
        '<td>' + metodoLabel + '</td>' +
        '<td style="text-align:center">' + imp.total_importados + '</td>' +
        '<td style="text-align:center;color:#10b981">' + imp.total_validos + '</td>' +
        '<td style="text-align:center;color:#ef4444">' + imp.total_invalidos + '</td>' +
        '<td style="color:var(--muted)">' + data + '</td>' +
      '</tr>';
    }).join('');

    tbody.querySelectorAll('.importacao-row').forEach(function(row) {
      row.addEventListener('click', function() {
        abrirImportacaoLeads(parseInt(this.dataset.id), this.dataset.nome);
      });
    });
    renderHistoricoMobile(importacoes);
  } catch(e) {
    console.warn('Erro ao carregar histórico de importações', e);
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--red)">Erro ao carregar importações.</td></tr>';
    renderHistoricoMobile([]);
  }
}

function renderHistoricoMobile(importacoes) {
  var container = document.getElementById('historico-cards-mobile');
  if (!container) return;
  if (!importacoes.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhuma importação</div>'; return; }
  container.innerHTML = importacoes.map(function(imp) {
    var data = imp.criado_em ? new Date(imp.criado_em).toLocaleDateString('pt-BR', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}) : '\u2014';
    var metodoLabel = imp.metodo === 'ia' ? '🤖 IA' : imp.metodo === 'csv' ? '📄 CSV' : '📋 Colar';
    return '<div class="crud-mobile-card" data-id="' + imp.id + '">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + esc(imp.nome) + '</div>' +
        '<span style="font-size:11px;color:var(--muted)">' + metodoLabel + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-body">' +
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center">' +
          '<div><strong style="color:#10b981">' + imp.total_importados + '</strong><div style="font-size:10px">Importados</div></div>' +
          '<div><strong style="color:#3b82f6">' + imp.total_validos + '</strong><div style="font-size:10px">Válidos</div></div>' +
          '<div><strong style="color:#ef4444">' + imp.total_invalidos + '</strong><div style="font-size:10px">Erros</div></div>' +
        '</div>' +
        '<div style="margin-top:8px;font-size:11px;color:var(--muted)">' + data + '</div>' +
      '</div></div>';
  }).join('');

  container.querySelectorAll('.crud-mobile-card').forEach(function(card) {
    card.addEventListener('click', function() {
      abrirImportacaoLeads(parseInt(this.dataset.id), card.querySelector('.crud-mobile-card-title').textContent);
    });
  });
}

async function abrirImportacaoLeads(importacaoId, nome) {
  try {
    var data = await api.get('/comercial/import/' + importacaoId + '/leads');
    var leads = data.leads || [];

    if (!leads.length) {
      showToast('Nenhum lead encontrado nesta importação', 'error');
      return;
    }

    if (!templatesCache.length) { await carregarTemplatesImportacao(); }

    var modal = document.createElement('div');
    modal.className = 'modal-overlay open';
    modal.id = 'modal-contatos-importados';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-label', 'Contatos da Importação');

    var html =
      '<div class="modal wide">' +
        '<div class="modal-header">' +
          '<h3 class="modal-title">\uD83D\uDCE5 ' + esc(nome) + ' (' + leads.length + ' contatos)</h3>' +
          '<button class="modal-close" id="btn-fechar-modal-contatos" aria-label="Fechar">&times;</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">' +
            '<div style="padding:12px;background:var(--surface2,#f1f5f9);border-radius:8px">' +
              '<label style="display:block;font-size:12px;font-weight:500;margin-bottom:6px">Segmento atribuído</label>' +
              '<div style="font-size:13px;font-weight:600;color:var(--accent)">' + (data.segmento_nome ? esc(data.segmento_nome) : '<span style="color:var(--muted);font-weight:400">Nenhum segmento</span>') + '</div>' +
            '</div>' +
            '<div style="padding:12px;background:var(--surface2,#f1f5f9);border-radius:8px">' +
              '<label style="display:block;font-size:12px;font-weight:500;margin-bottom:6px">Data da importação</label>' +
              '<div style="font-size:13px;color:var(--muted)">' + (data.criado_em ? fmtDataHora(data.criado_em) : '\u2014') + '</div>' +
            '</div>' +
          '</div>' +
          '<div style="margin-bottom:16px;padding:12px;background:var(--surface2,#f1f5f9);border-radius:8px">' +
            '<label style="display:block;font-size:12px;font-weight:500;margin-bottom:6px">Template de Mensagem *</label>' +
            '<select id="lote-template-select" class="fs" style="width:100%">' +
              '<option value="">Selecione um template para habilitar envios</option>' +
              templatesCache.map(function(t) { return '<option value="' + t.id + '">' + esc(t.nome) + '</option>'; }).join('') +
            '</select>' +
          '</div>' +
          '<div style="margin-bottom:16px;padding:12px;background:var(--surface2,#f1f5f9);border-radius:8px">' +
            '<label style="display:block;font-size:12px;font-weight:500;margin-bottom:8px">\u23F1 Intervalo entre mensagens (segundos)</label>' +
            '<div style="display:flex;gap:12px;align-items:center">' +
              '<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Mínimo</label><input type="number" id="lote-delay-min" class="fi" value="9" min="1" max="60" style="width:100%"></div>' +
              '<div style="flex:1"><label style="font-size:11px;color:var(--muted)">Máximo</label><input type="number" id="lote-delay-max" class="fi" value="15" min="1" max="60" style="width:100%"></div>' +
            '</div>' +
          '</div>' +
          '<div style="max-height:300px;overflow-y:auto">' +
            '<table style="width:100%;border-collapse:collapse;font-size:13px">' +
              '<thead><tr>' +
                '<th style="padding:8px;text-align:center;width:36px"><input type="checkbox" id="select-all-lote" checked></th>' +
                '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">Nome</th>' +
                '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">Empresa</th>' +
                '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">WhatsApp</th>' +
                '<th style="text-align:left;padding:8px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted)">E-mail</th>' +
              '</tr></thead>' +
              '<tbody id="lote-leads-tbody">' +
                leads.map(function(l) {
                  return '<tr>' +
                    '<td style="padding:8px;text-align:center"><input type="checkbox" class="lote-lead-checkbox" data-id="' + l.id + '" ' + (l.whatsapp || l.email ? 'checked' : 'disabled') + '></td>' +
                    '<td style="padding:8px">' + esc(l.nome_responsavel) + '</td>' +
                    '<td style="padding:8px">' + esc(l.nome_empresa) + '</td>' +
                    '<td style="padding:8px">' + (l.whatsapp ? esc(l.whatsapp) : '\u2014') + '</td>' +
                    '<td style="padding:8px">' + (l.email ? esc(l.email) : '\u2014') + '</td>' +
                  '</tr>';
                }).join('') +
              '</tbody>' +
            '</table>' +
          '</div>' +
          '<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">' +
            '<button class="btn btn-primary" id="btn-enviar-whatsapp-lote" disabled>\uD83D\uDCF1 Enviar WhatsApp</button>' +
            '<button class="btn btn-secondary" id="btn-enviar-email-lote" disabled>\uD83D\uDCE7 Enviar E-mail</button>' +
            '<button class="btn btn-ghost" id="btn-excluir-importacao-lote" data-id="' + importacaoId + '" data-nome="' + esc(nome) + '" style="color:#ef4444;margin-left:auto">\uD83D\uDDD1 Excluir importação</button>' +
            '<button class="btn btn-ghost" id="btn-fechar-modal-contatos-2">Fechar</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    modal.innerHTML = html;
    document.body.appendChild(modal);

    document.getElementById('btn-fechar-modal-contatos').addEventListener('click', fecharModalContatos);
    document.getElementById('btn-fechar-modal-contatos-2').addEventListener('click', fecharModalContatos);
    document.getElementById('btn-enviar-whatsapp-lote').addEventListener('click', function() { enviarWhatsAppLoteHistorico(leads); });
    document.getElementById('btn-enviar-email-lote').addEventListener('click', function() { enviarEmailLoteHistorico(leads); });
    document.getElementById('btn-excluir-importacao-lote').addEventListener('click', function() {
      excluirImportacao(parseInt(this.dataset.id), this.dataset.nome);
      fecharModalContatos();
    });

    document.getElementById('lote-template-select').addEventListener('change', function() {
      var hasTemplate = !!this.value;
      document.getElementById('btn-enviar-whatsapp-lote').disabled = !hasTemplate;
      document.getElementById('btn-enviar-email-lote').disabled = !hasTemplate;
    });

    document.getElementById('select-all-lote').addEventListener('change', function() {
      document.querySelectorAll('.lote-lead-checkbox:not([disabled])').forEach(function(cb) { cb.checked = this.checked; }.bind(this));
    });

  } catch(e) {
    showToast('Erro ao carregar contatos: ' + (e.message || ''), 'error');
  }
}

async function enviarWhatsAppLoteHistorico(leads) {
  var templateId = document.getElementById('lote-template-select').value;
  if (!templateId) { showToast('Selecione um template', 'error'); return; }
  var checkedBoxes = document.querySelectorAll('.lote-lead-checkbox:checked');
  var leadIds = Array.from(checkedBoxes).map(function(cb) { return parseInt(cb.dataset.id); });
  if (!leadIds.length) { showToast('Selecione pelo menos um contato', 'error'); return; }
  var delayMin = parseInt(document.getElementById('lote-delay-min').value) || 9;
  var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;
  var btn = document.getElementById('btn-enviar-whatsapp-lote');
  if(btn) setLoading(btn, true);
  try {
    var result = await api.post('/comercial/leads/enviar-lote', {
      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'whatsapp', delay_min: delayMin, delay_max: delayMax
    });
    showToast(result.enviados + '/' + result.total + ' WhatsApps enviados!', result.falhas > 0 ? 'error' : 'success');
    fecharModalContatos();
  } catch(e) { showToast('Erro: ' + (e.message || 'Desconhecido'), 'error'); }
}

async function enviarEmailLoteHistorico(leads) {
  var templateId = document.getElementById('lote-template-select').value;
  if (!templateId) { showToast('Selecione um template', 'error'); return; }
  var checkedBoxes = document.querySelectorAll('.lote-lead-checkbox:checked');
  var leadIds = Array.from(checkedBoxes).map(function(cb) { return parseInt(cb.dataset.id); });
  if (!leadIds.length) { showToast('Selecione pelo menos um contato', 'error'); return; }
  var delayMin = parseInt(document.getElementById('lote-delay-min').value) || 9;
  var delayMax = parseInt(document.getElementById('lote-delay-max').value) || 15;
  var btn = document.getElementById('btn-enviar-whatsapp-lote');
  if(btn) setLoading(btn, true);
  try {
    var result = await api.post('/comercial/leads/enviar-lote', {
      lead_ids: leadIds, campaign_id: parseInt(templateId, 10), canal: 'email', delay_min: delayMin, delay_max: delayMax
    });
    showToast(result.enviados + '/' + result.total + ' e-mails enviados!', result.falhas > 0 ? 'error' : 'success');
    fecharModalContatos();
  } catch(e) { showToast('Erro: ' + (e.message || 'Desconhecido'), 'error'); }
}

async function excluirImportacao(id, nome) {
  if (!confirm('Excluir a importação "' + nome + '" e TODOS os leads vinculados a ela?\n\nEsta ação é irreversível.')) return;
  try {
    await api.delete('/comercial/import/' + id);
    showToast('Importação e leads excluídos!', 'success');
    await refreshHistoricoImportSeVisivel();
  } catch(e) {
    showToast(e.message || 'Erro ao excluir importação', 'error');
  }
}

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
      '<div class="dash-kpi-card dash-kpi-followups" role="button" tabindex="0" aria-label="Ver leads com follow-up vencido ou para agora">' +
        '<div class="dk-icon red">\uD83D\uDCCC</div>' +
        '<div class="dk-value" style="color:' + (m.follow_ups_hoje > 0 ? '#dc2626' : 'var(--text)') + '">' + (m.follow_ups_hoje || 0) + '</div>' +
        '<div class="dk-label">Follow-ups hoje</div><div class="dk-sub">Pr\u00F3ximo contato do lead (atrasados inclusos)</div>' +
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
      '<div class="dash-kpi-card" data-tab="lembretes" role="button" tabindex="0" aria-label="Ver lembretes da agenda">' +
        '<div class="dk-icon purple">\u23F0</div>' +
        '<div class="dk-value">' + (m.lembretes_pendentes || 0) + '</div>' +
        '<div class="dk-label">Lembretes em aberto</div><div class="dk-sub">Pendentes + atrasados (agenda, n\u00E3o \u00E9 o campo do lead)</div>' +
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
  grid.querySelectorAll('.dash-kpi-followups').forEach(function(card) {
    var handler = function() { irParaLeadsFollowUpHoje(); };
    card.addEventListener('click', handler);
    card.addEventListener('keydown', function(e) { if (e.key === 'Enter') handler(); });
  });
  grid.querySelectorAll('.dash-kpi-card[data-tab]').forEach(function(card) {
    var handler = function() {
      if (card.dataset.tab === 'leads') {
        leadsFilterFollowUpHoje = false;
        leadsFilterOrigemId = null;
        leadsFilterEmpresaTrial = false;
        _fromDashboard = true;
      }
      switchTab(card.dataset.tab, card.dataset.tab === 'leads');
      if (card.dataset.tab === 'leads') carregarLeadsTabela();
    };
    card.addEventListener('click', handler);
    card.addEventListener('keydown', function(e) { if (e.key === 'Enter') handler(); });
  });
  grid.querySelectorAll('.dash-kpi-empresas-trial').forEach(function(card) {
    var handler = function() { irParaLeadsEmpresasTrial(); };
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
  leadsFilterOrigemId = null;
  leadsFilterFollowUpHoje = false;
  leadsFilterEmpresaTrial = false;
  var el = document.getElementById('leads-filter-status');
  if (el) el.value = status;
  _fromDashboard = true;
  switchTab('leads', true);
  carregarLeadsTabela();
}

/** Abre a aba Leads com o mesmo crit\u00E9rio do bloco "O que fazer hoje" / lista follow-ups. */
function irParaLeadsFollowUpHoje() {
  leadsPage = 1;
  leadsFilterFollowUpHoje = true;
  leadsFilterOrigemId = null;
  leadsFilterEmpresaTrial = false;
  var st = document.getElementById('leads-filter-status');
  if (st) st.value = '';
  leadsOrderBy = 'proximo_contato_em';
  leadsOrderDir = 'asc';
  _fromDashboard = true;
  switchTab('leads', true);
  carregarLeadsTabela();
}

/** Leads vinculados a empresas em trial ativo. */
function irParaLeadsEmpresasTrial() {
  leadsPage = 1;
  leadsFilterFollowUpHoje = false;
  leadsFilterOrigemId = null;
  leadsFilterEmpresaTrial = true;
  var st = document.getElementById('leads-filter-status');
  if (st) st.value = '';
  _fromDashboard = true;
  switchTab('leads', true);
  carregarLeadsTabela();
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

// ═══════════════════════════════════════════════════════════════════════════════
// PIPELINE
// ═══════════════════════════════════════════════════════════════════════════════
function irParaGerarOrcamento(id, valor, desc) {
  window.location.href = 'orcamentos.html?lead_id=' + id + '&valor=' + valor + '&desc=' + encodeURIComponent(desc);
}

async function carregarPipeline() {
  try {
    var res = await api.get('/comercial/leads?per_page=200');
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
    var colLeads = groups[slug] || [];
    var totalValor = colLeads.reduce(function(sum, l) { return sum + (l.valor_proposto || 0); }, 0);
    var valorStr = totalValor > 0 ? '<span style="font-size:10px;color:#10b981;font-weight:600">R$ ' + fmtMoeda(totalValor) + '</span>' : '';
    var cardsHtml = colLeads.length
      ? colLeads.map(function(l) { return kanbanCard(l); }).join('')
      : '<div class="k-empty">Nenhum lead nesta etapa</div>';
    return '<div class="k-col" data-s="' + slug + '" role="region" aria-label="' + esc(s.label) + '">' +
      '<div class="k-head">' +
        '<div class="k-head-left"><div class="k-title">' + (s.emoji || '') + ' ' + esc(s.label) + '</div>' +
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
      board.querySelectorAll('.k-cards').forEach(function(c) { c.style.background = ''; });
    });
  });

  board.querySelectorAll('.k-cards').forEach(function(col) {
    col.addEventListener('dragover', function(e) { e.preventDefault(); });
    col.addEventListener('dragenter', function() { this.style.background = 'var(--accent-dim)'; });
    col.addEventListener('dragleave', function() { this.style.background = ''; });
    var slug = col.id.replace('col-', '');
    col.addEventListener('drop', function(e) { dropCard(e, slug); });
  });
}

function kanbanCard(l) {
  var scoreClass = l.lead_score ? 'score-' + l.lead_score : '';
  var diasNoSistema = Math.floor((Date.now() - new Date(l.criado_em)) / (1000*60*60*24));
  var diasStr = diasNoSistema === 0 ? 'hoje' : diasNoSistema === 1 ? '1d' : diasNoSistema + 'd';
  var diasCls = diasNoSistema >= 14 ? 'danger' : diasNoSistema >= 7 ? 'warn' : '';
  var proxVencido = l.proximo_contato_em && new Date(l.proximo_contato_em) < new Date();

  return '<div class="k-card" draggable="true" data-id="' + l.id + '" style="' + (proxVencido ? 'border-color:#fca5a5;background:rgba(254,242,242,0.4)' : '') + '" title="' + (proxVencido ? '\u26A0\uFE0F Próximo contato vencido' : '') + '">' +
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:3px">' +
      '<div class="kc-company" style="flex:1;min-width:0">' + esc(l.nome_empresa) + '</div>' +
      '<span class="kc-days ' + diasCls + '">' + diasStr + '</span>' +
    '</div>' +
    '<div class="kc-person">' + esc(l.nome_responsavel) + '</div>' +
    '<div class="kc-meta">' +
      (l.lead_score ? '<span class="kc-badge ' + scoreClass + '">' + esc(l.lead_score) + '</span>' : '') +
      (l.segmento_nome ? '<span class="kc-badge">' + esc(l.segmento_nome) + '</span>' : '') +
      (l.interesse_plano ? '<span class="kc-badge">' + esc(l.interesse_plano.toUpperCase()) + '</span>' : '') +
      (proxVencido ? '<span class="kc-badge" style="background:#fef2f2;color:#dc2626;border-color:transparent">\u26A0\uFE0F vencido</span>' : '') +
    '</div>' +
    (l.valor_proposto ? '<div class="kc-value">\uD83D\uDCB0 R$ ' + fmtMoeda(l.valor_proposto) + '</div>' : '') +
    '<div class="kc-actions">' +
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

async function dropCard(e, novoStatus) {
  e.preventDefault();
  var id = e.dataTransfer.getData('text/plain');
  try {
    await api.patch('/comercial/leads/' + id + '/status', { status: novoStatus });
    showToast('Lead movido!', 'success');
    carregarPipeline();
  } catch(err) { showToast('Erro ao mover lead', 'error'); }
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEADS TABLE
// ═══════════════════════════════════════════════════════════════════════════════
function debounceLeads() { clearTimeout(debounceTimer); leadsFilterEmpresaTrial = false; debounceTimer = setTimeout(function() { carregarLeadsTabela(); }, 300); }

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
    var propostasLead = [];
    var ultimaPropostaLead = null;
    try {
      propostasLead = await api.get('/comercial/propostas-publicas/leads/' + id + '/propostas');
      if (Array.isArray(propostasLead) && propostasLead.length > 0) {
        ultimaPropostaLead = propostasLead[0];
      }
    } catch (_) {}

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
    var propostaNomeDetalhe = ultimaPropostaLead && ultimaPropostaLead.proposta_template
      ? ultimaPropostaLead.proposta_template.nome
      : '';
    var propostaStatusDetalhe = ultimaPropostaLead ? ({
      enviada: 'Enviada',
      visualizada: 'Visualizada',
      aceita: 'Aceita',
      expirada: 'Expirada',
      rascunho: 'Rascunho'
    }[ultimaPropostaLead.status] || ultimaPropostaLead.status || '') : '';
    var propostaResumoDetalhe = propostaNomeDetalhe
      ? esc(propostaNomeDetalhe) + (propostaStatusDetalhe ? ' (' + esc(propostaStatusDetalhe) + ')' : '')
      : '<span class="lead-field-value empty">—</span>';

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
      '<div class="lead-field"><span class="lead-field-label">Proposta Pública</span><span class="lead-field-value">' + propostaResumoDetalhe + '</span></div>' +
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
    detailContent.querySelectorAll('.btn-concluir-lembrete').forEach(function(btn) {
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
  } catch(e) { showToast('Erro ao arquivar lead', 'error'); }
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
    window.leadPropostaVinculadaAtualId = null;
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
      var propostaVinculada = false;
      var propostaJaVinculada = false;

      if (leadAtualId) {
        await api.patch('/comercial/leads/' + leadAtualId, data);
      } else {
        var leadCriado = await api.post('/comercial/leads', data);
        leadIdVinculo = leadCriado.id;
      }

      if (propostaPublicaId && leadIdVinculo) {
        var mesmaPropostaJaVinculada = Boolean(
          leadAtualId
          && window.leadPropostaVinculadaAtualId
          && Number(window.leadPropostaVinculadaAtualId) === Number(propostaPublicaId)
        );

        if (mesmaPropostaJaVinculada) {
          propostaJaVinculada = true;
        } else {
          try {
            await vincularPropostaAoLead(leadIdVinculo, propostaPublicaId, validadeProposta, data);
            propostaVinculada = true;
            window.leadPropostaVinculadaAtualId = propostaPublicaId;
          } catch (e) {
            var msgErroVinculo = (e && e.message) ? e.message : '';
            if (msgErroVinculo.indexOf('Proposta já enviada para este lead') !== -1) {
              propostaJaVinculada = true;
              window.leadPropostaVinculadaAtualId = propostaPublicaId;
            } else {
              throw e;
            }
          }
        }
      }

      if (propostaVinculada) {
        showToast(leadAtualId ? 'Lead atualizado e proposta vinculada!' : 'Lead criado e proposta vinculada!', 'success');
      } else if (propostaJaVinculada) {
        showToast(leadAtualId ? 'Lead atualizado! Esta proposta já estava vinculada.' : 'Lead criado! Esta proposta já estava vinculada.', 'success');
      } else {
        showToast(leadAtualId ? 'Lead atualizado!' : 'Lead criado!', 'success');
      }

      fecharModal('modal-lead');
      carregarPipeline(); carregarDashboard(); carregarLeadsTabela();
    } catch(e) { showToast(e.message || 'Erro ao salvar lead', 'error'); }
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// WHATSAPP & EMAIL
// ═══════════════════════════════════════════════════════════════════════════════
function linkPropostaPublicaPorSlug(slug) {
  var base = (typeof window !== 'undefined' && window.location && window.location.origin)
    ? window.location.origin
    : '';
  return base + '/p/' + slug;
}

function mensagemWhatsAppComLinkProposta(slug, nomeProposta) {
  var link = linkPropostaPublicaPorSlug(slug);
  var nome = (nomeProposta || '').trim();
  if (nome) {
    return 'Segue o link da proposta "' + nome + '":\n' + link;
  }
  return 'Segue o link da sua proposta:\n' + link;
}

/** Resposta 400 do backend quando a mesma proposta pública já foi enviada ao lead (sem force). */
function erroIndicaPropostaJaEnviada(msg) {
  if (!msg || typeof msg !== 'string') return false;
  var m = msg.toLowerCase();
  var folded = typeof m.normalize === 'function'
    ? m.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    : m;
  return (
    folded.indexOf('ja enviada') !== -1 ||
    folded.indexOf('deseja enviar') !== -1 ||
    folded.indexOf('enviar novamente') !== -1
  );
}

function abrirConfirmacaoReenvioProposta(errorMsg, pendente) {
  propostasReenvioPendente = pendente;
  var el = document.getElementById('msg-reenvio');
  if (el) el.textContent = errorMsg;
  fecharModal('modal-email');
  fecharModal('modal-whatsapp');
  /* Abre no próximo microtask: evita o listener global (click no overlay) fechar
   * este modal no mesmo ciclo do clique em "Enviar" após o await. */
  var schedule =
    typeof queueMicrotask === 'function'
      ? queueMicrotask
      : function (fn) {
          Promise.resolve().then(fn);
        };
  schedule(function () {
    var mod = document.getElementById('modal-confirmar-reenvio');
    if (mod) mod.classList.add('open');
  });
}

function populateTplSelect(selectId, canal, incluirPropostas) {
  var sel = document.getElementById(selectId);
  if (!sel) return [];

  var canalDesejado = (canal || '').toLowerCase();
  var filtered = (templatesCache || []).filter(function(t) {
    var canalTpl = String(t.canal || '').toLowerCase();
    return canalTpl === canalDesejado || canalTpl === 'ambos';
  });
  
  var optionsHTML = '<option value="">Escrever manualmente</option>';
  
  if (filtered.length > 0) {
    var tplGroupLabel = canalDesejado === 'whatsapp' ? 'Templates de WhatsApp' : 'Templates de E-mail';
    optionsHTML += '<optgroup label="' + tplGroupLabel + '">';
    optionsHTML += filtered.map(function(t) {
      return '<option value="tpl-' + t.id + '">' + esc(t.nome) + '</option>';
    }).join('');
    optionsHTML += '</optgroup>';
  }
  
  if (incluirPropostas && propostasPublicasCache.length > 0) {
    optionsHTML += '<optgroup label="Propostas Públicas">';
    optionsHTML += propostasPublicasCache.map(function(p) {
      return '<option value="pp-' + p.id + '"> Proposta: ' + esc(p.nome) + '</option>';
    }).join('');
    optionsHTML += '</optgroup>';
  }

  sel.innerHTML = optionsHTML;

  return filtered;
}

async function garantirTemplatesModal() {
  if (Array.isArray(templatesCache) && templatesCache.length > 0) return templatesCache;
  try {
    templatesCache = await api.get('/comercial/templates?ativo=true');
    console.log('[DEBUG] Templates carregados da API:', templatesCache);
  } catch (e) {
    console.error('[DEBUG] Erro ao carregar templates:', e);
    templatesCache = [];
  }
  return templatesCache;
}

var propostasPublicasCache = [];

async function garantirPropostasPublicasCache() {
  if (Array.isArray(propostasPublicasCache) && propostasPublicasCache.length > 0) return propostasPublicasCache;
  try {
    propostasPublicasCache = await api.get('/comercial/propostas-publicas');
    propostasPublicasCache = (propostasPublicasCache || []).filter(function(p) { return p.ativo !== false; });
    console.log('[DEBUG] Propostas públicas carregadas:', propostasPublicasCache);
  } catch (e) {
    console.error('[DEBUG] Erro ao carregar propostas públicas:', e);
    propostasPublicasCache = [];
  }
  return propostasPublicasCache;
}

async function aplicarTemplate(prefix) {
  var sel = document.getElementById(prefix + '-template');
  var value = sel.value;
  if (!value || !leadAtualId) return;
  
  if (value.startsWith('pp-')) {
    var propostaId = parseInt(value.replace('pp-', ''));
    var proposta = propostasPublicasCache.find(function(p) { return p.id === propostaId; });
    if (proposta) {
      document.getElementById(prefix + '-mensagem').value = 'Vou enviar a proposta: ' + proposta.nome + '\n\n(Clique em Enviar para prosseguir com o envio da proposta pública)';
      if (prefix === 'em') document.getElementById('em-assunto').value = 'Proposta Comercial - ' + proposta.nome;
    }
    return;
  }
  
  var tplId = parseInt(value.replace('tpl-', ''));
  if (!tplId) return;
  
  try {
    var preview = await api.post('/comercial/templates/' + tplId + '/preview', { lead_id: leadAtualId });
    document.getElementById(prefix + '-mensagem').value = preview.conteudo || '';
    if (prefix === 'em' && preview.assunto) document.getElementById('em-assunto').value = preview.assunto;
  } catch(e) { showToast('Erro ao carregar template', 'error'); }
}

async function abrirModalWhatsApp(leadId) {
  leadAtualId = leadId;
  document.getElementById('wa-mensagem').value = '';
  await Promise.all([garantirTemplatesModal(), garantirPropostasPublicasCache()]);
  populateTplSelect('wa-template', 'whatsapp', true);
  document.getElementById('modal-whatsapp').classList.add('open');
}

async function enviarWhatsApp() {
  var templateValue = document.getElementById('wa-template').value;

  if (templateValue.startsWith('pp-')) {
    var propostaId = parseInt(templateValue.replace('pp-', ''), 10);
    if (!propostaId) {
      showToast('Proposta inválida', 'error');
      return;
    }
    var btnPp = document.querySelector('#modal-whatsapp .btn-primary');
    await withBtnLoading(btnPp, async function() {
      try {
        var resp = await api.post('/comercial/propostas-publicas/leads/' + leadAtualId + '/propostas', {
          proposta_publica_id: propostaId,
          dados_personalizados: {},
          validade_dias: 7
        });
        var nomeProposta = '';
        var prop = propostasPublicasCache.find(function(p) { return p.id === propostaId; });
        if (prop) nomeProposta = prop.nome || '';
        var textoWa = mensagemWhatsAppComLinkProposta(resp.slug, nomeProposta);
        await api.post('/comercial/leads/' + leadAtualId + '/whatsapp', { mensagem: textoWa });
        showToast('Proposta registrada e link enviado por WhatsApp!', 'success');
        fecharModal('modal-whatsapp');
      } catch (e) {
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

async function abrirModalEmail(leadId) {
  leadAtualId = leadId;
  document.getElementById('em-assunto').value = '';
  document.getElementById('em-mensagem').value = '';
  await Promise.all([garantirTemplatesModal(), garantirPropostasPublicasCache()]);
  var templatesEmail = populateTplSelect('em-template', 'email', true);

  if (!templatesEmail.length && !propostasPublicasCache.length) {
    showToast('Nenhum template de e-mail ou proposta pública ativa encontrado', 'error');
  }

  document.getElementById('modal-email').classList.add('open');
}

var propostasReenvioPendente = null;

async function enviarEmail() {
  var assunto = document.getElementById('em-assunto').value;
  var msg = document.getElementById('em-mensagem').value;
  var templateValue = document.getElementById('em-template').value;
  
  if (templateValue.startsWith('pp-')) {
    var propostaId = parseInt(templateValue.replace('pp-', ''), 10);
    if (!propostaId) {
      showToast('Proposta inválida', 'error');
      return;
    }
    var btnPpEm = document.querySelector('#modal-email .btn-primary');
    await withBtnLoading(btnPpEm, async function() {
      try {
        var resp = await api.post('/comercial/propostas-publicas/leads/' + leadAtualId + '/propostas', {
          proposta_publica_id: propostaId,
          dados_personalizados: {},
          validade_dias: 7
        });
        var prop = propostasPublicasCache.find(function(p) { return p.id === propostaId; });
        var nomeProp = (prop && prop.nome) ? prop.nome : 'Proposta';
        var link = linkPropostaPublicaPorSlug(resp.slug);
        var assuntoPp = 'Proposta comercial — ' + nomeProp;
        var corpoPp =
          'Olá,\n\nSegue o link para visualizar nossa proposta:\n\n' +
          link +
          '\n\nQualquer dúvida, estamos à disposição.';
        await api.post('/comercial/leads/' + leadAtualId + '/email', {
          assunto: assuntoPp,
          mensagem: corpoPp
        });
        showToast('Proposta registrada e link enviado por e-mail!', 'success');
        fecharModal('modal-email');
      } catch (e) {
        console.error('[DEBUG] Erro ao enviar proposta/e-mail:', e);
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
      await api.post('/comercial/leads/' + leadAtualId + '/email', { assunto: assunto, mensagem: msg });
      showToast('E-mail enviado!', 'success');
      fecharModal('modal-email');
    } catch(e) { showToast(e.message || 'Erro ao enviar', 'error'); }
  });
}

async function confirmarReenvioProposta() {
  if (!propostasReenvioPendente) return;

  var pend = propostasReenvioPendente;
  propostasReenvioPendente = null;

  try {
    var resp = await api.post('/comercial/propostas-publicas/leads/' + pend.leadId + '/propostas?force=true', {
      proposta_publica_id: pend.propostaId,
      dados_personalizados: {},
      validade_dias: 7
    });
    fecharModal('modal-confirmar-reenvio');

    var canal = pend.canal || 'email';
    if (canal === 'whatsapp') {
      var nomeProposta = '';
      var p = propostasPublicasCache.find(function(x) { return x.id === pend.propostaId; });
      if (p) nomeProposta = p.nome || '';
      var textoWa = mensagemWhatsAppComLinkProposta(resp.slug, nomeProposta);
      try {
        await api.post('/comercial/leads/' + pend.leadId + '/whatsapp', { mensagem: textoWa });
        showToast('Proposta reenviada e link enviado por WhatsApp!', 'success');
      } catch (waErr) {
        showToast(waErr.message || 'Proposta reenviada, mas falha ao enviar WhatsApp', 'error');
      }
      fecharModal('modal-whatsapp');
    } else {
      var nomeRe = '';
      var pr = propostasPublicasCache.find(function(x) { return x.id === pend.propostaId; });
      if (pr) nomeRe = pr.nome || '';
      var linkRe = linkPropostaPublicaPorSlug(resp.slug);
      var assuntoRe = 'Proposta comercial — ' + (nomeRe || 'Proposta');
      var corpoRe =
        'Olá,\n\nSegue o link para visualizar nossa proposta:\n\n' +
        linkRe +
        '\n\nQualquer dúvida, estamos à disposição.';
      await api.post('/comercial/leads/' + pend.leadId + '/email', {
        assunto: assuntoRe,
        mensagem: corpoRe
      });
      showToast('Proposta reenviada e link enviado por e-mail!', 'success');
      fecharModal('modal-email');
    }
  } catch(e) {
    propostasReenvioPendente = pend;
    showToast(e.message || 'Erro ao reenviar proposta', 'error');
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TEMPLATES CRUD
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarTemplates() {
  try {
    var tpls = await api.get('/comercial/templates');
    var tbody = document.getElementById('templates-tbody');
    if (!tpls.length) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty"><p>Nenhum template</p></div></td></tr>'; return; }
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

// ═══════════════════════════════════════════════════════════════════════════════
// CADASTROS
// ═══════════════════════════════════════════════════════════════════════════════
async function carregarSegmentos() {
  try {
    var items = await api.get('/comercial/segmentos');
    var tbody = document.getElementById('segmentos-tbody');
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="3"><div class="empty"><p>Nenhum segmento</p></div></td></tr>'; return; }
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
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="3"><div class="empty"><p>Nenhuma origem</p></div></td></tr>'; return; }
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
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="8"><div class="empty"><p>Nenhuma etapa</p></div></td></tr>'; return; }
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
// GLOBAL EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════════════════════

// Fechar autocomplete ao clicar fora
document.addEventListener('click', function(e) {
  var dd = document.getElementById('lemb-lead-dropdown');
  var wrapper = document.getElementById('lemb-lead-search')?.closest('.lead-ac-wrapper');
  if (dd && wrapper && !wrapper.contains(e.target)) dd.style.display = 'none';
});

// Fechar modais ao clicar no overlay
document.addEventListener('click', function(e) {
  if (e.target.classList && e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// Toggle fechados do pipeline
var btnToggleFechados = document.getElementById('btn-toggle-fechados');
if (btnToggleFechados) btnToggleFechados.addEventListener('click', toggleFechados);

// Botão novo lead
var btnNovoLead = document.getElementById('btn-novo-lead') || document.querySelector('.crm-topbar .btn-primary');
if (btnNovoLead && btnNovoLead.textContent.includes('Novo Lead')) {
  btnNovoLead.addEventListener('click', abrirModalLead);
}

// Modais - botões de ação
document.querySelector('#modal-lead .btn-primary')?.addEventListener('click', salvarLead);
document.querySelector('#modal-lead .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-lead'); });
document.querySelector('#modal-lead .modal-close')?.addEventListener('click', function() { fecharModal('modal-lead'); });

document.querySelector('#modal-whatsapp .btn-primary')?.addEventListener('click', enviarWhatsApp);
document.querySelector('#modal-whatsapp .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-whatsapp'); });
document.querySelector('#modal-whatsapp .modal-close')?.addEventListener('click', function() { fecharModal('modal-whatsapp'); });

document.querySelector('#modal-email .btn-primary')?.addEventListener('click', enviarEmail);
document.querySelector('#modal-email .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-email'); });
document.querySelector('#modal-email .modal-close')?.addEventListener('click', function() { fecharModal('modal-email'); });

document.querySelector('#modal-template .btn-primary')?.addEventListener('click', salvarTemplate);
document.querySelector('#modal-template .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-template'); });
document.querySelector('#modal-template .modal-close')?.addEventListener('click', function() { fecharModal('modal-template'); });

document.querySelector('#modal-lembrete .btn-primary')?.addEventListener('click', salvarLembrete);
document.querySelector('#modal-lembrete .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-lembrete'); });
document.querySelector('#modal-lembrete .modal-close')?.addEventListener('click', function() { fecharModal('modal-lembrete'); });

document.querySelector('#modal-segmento .btn-primary')?.addEventListener('click', salvarSegmento);
document.querySelector('#modal-segmento .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-segmento'); });
document.querySelector('#modal-segmento .modal-close')?.addEventListener('click', function() { fecharModal('modal-segmento'); });

document.querySelector('#modal-origem .btn-primary')?.addEventListener('click', salvarOrigem);
document.querySelector('#modal-origem .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-origem'); });
document.querySelector('#modal-origem .modal-close')?.addEventListener('click', function() { fecharModal('modal-origem'); });

document.querySelector('#modal-pipeline-stage .btn-primary')?.addEventListener('click', salvarPipelineStage);
document.querySelector('#modal-pipeline-stage .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-pipeline-stage'); });
document.querySelector('#modal-pipeline-stage .modal-close')?.addEventListener('click', function() { fecharModal('modal-pipeline-stage'); });

// Botões "+ Novo" da tab Cadastros
document.getElementById('btn-novo-segmento')?.addEventListener('click', abrirModalSegmento);
document.getElementById('btn-nova-origem')?.addEventListener('click', abrirModalOrigem);

// Botões de config
document.querySelector('#tab-config .btn-primary')?.addEventListener('click', salvarConfig);

// Botões da importação
document.getElementById('btn-importar')?.addEventListener('click', function() { goToStep(3); });

// Leads filters
document.getElementById('leads-search')?.addEventListener('input', debounceLeads);
document.getElementById('leads-filter-status')?.addEventListener('change', function() {
  leadsFilterOrigemId = null;
  leadsFilterFollowUpHoje = false;
  leadsFilterEmpresaTrial = false;
  leadsPage = 1;
  carregarLeadsTabela();
});
document.getElementById('leads-filter-score')?.addEventListener('change', function() {
  leadsFilterOrigemId = null;
  leadsFilterFollowUpHoje = false;
  leadsFilterEmpresaTrial = false;
  carregarLeadsTabela();
});
document.getElementById('leads-filter-arquivados')?.addEventListener('change', function() {
  leadsFilterOrigemId = null;
  leadsFilterFollowUpHoje = false;
  leadsFilterEmpresaTrial = false;
  leadsPage = 1;
  carregarLeadsTabela();
});

// Lembretes filter
document.getElementById('lembretes-filter-status')?.addEventListener('change', carregarLembretes);
document.getElementById('btn-novo-lembrete')?.addEventListener('click', function() { abrirModalLembrete(); });

document.getElementById('btn-nova-campanha-mensagem')?.addEventListener('click', function() { abrirModalTemplate(); });

// Import CSV file input
document.getElementById('csv-file')?.addEventListener('change', function() { handleCSVUpload(this); });

// Import form submit
document.getElementById('import-config-form')?.addEventListener('submit', function(e) { e.preventDefault(); executeImport(); });

// Lead form submit prevention
document.getElementById('form-lead')?.addEventListener('submit', function(e) { e.preventDefault(); });

// Template selects in WhatsApp/Email modals
document.getElementById('wa-template')?.addEventListener('change', function() { aplicarTemplate('wa'); });
document.getElementById('em-template')?.addEventListener('change', function() { aplicarTemplate('em'); });

// Lembrete lead search
document.getElementById('lemb-lead-search')?.addEventListener('input', buscarLeadLembrete);
document.getElementById('lemb-lead-search')?.addEventListener('focus', buscarLeadLembrete);

// Leads table sort headers
document.querySelectorAll('#leads-table thead th[data-col]').forEach(function(th) {
  th.addEventListener('click', function() { sortLeads(this.dataset.col); });
});

// Import step buttons
document.getElementById('btn-voltar-import-step1')?.addEventListener('click', function() { goToStep(1); });
document.getElementById('btn-voltar-import-step2')?.addEventListener('click', function() { goToStep(2); });

// Import buttons
var btnPreview = document.getElementById('btn-analisar-import');
if (btnPreview) btnPreview.addEventListener('click', function() { withBtnLoading(btnPreview, previewImport); });

var btnResetImport = document.querySelector('#step-4 .btn-ghost');
if (btnResetImport && btnResetImport.textContent.includes('Nova')) btnResetImport.addEventListener('click', resetImport);

var btnVerLeads = document.querySelector('#step-4 .btn-primary');
if (btnVerLeads && btnVerLeads.textContent.includes('Ver leads')) btnVerLeads.addEventListener('click', function() { switchTab('leads'); });

document.getElementById('btn-toggle-historico-import')?.addEventListener('click', toggleHistoricoImportacoes);
document.getElementById('btn-atualizar-historico-import')?.addEventListener('click', carregarHistoricoImportacoes);
document.getElementById('btn-dash-from-import')?.addEventListener('click', function() { switchTab('dashboard'); });

// CSV file label fallback (alguns browsers/contextos podem falhar no label escondido)
var csvTrigger = document.getElementById('btn-csv-trigger');
var csvInput = document.getElementById('csv-file');
if (csvTrigger && csvInput) {
  csvTrigger.addEventListener('click', function(e) {
    if (e.target !== csvInput) {
      e.preventDefault();
      csvInput.click();
    }
  });
}

// ═══════════════════════════════════════════════════════════════
// CAMPANHAS (Campaigns)
// ═══════════════════════════════════════════════════════════════

var campanhasCache = [];

async function carregarCampanhas() {
  try {
    var res = await api.get('/comercial/campaigns/');
    campanhasCache = res || [];
    renderCampanhasTable(campanhasCache);
    renderCampanhasMobile(campanhasCache);
  } catch (e) {
    console.error('Erro ao carregar campanhas:', e);
    document.getElementById('campanhas-tbody').innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--red)">Erro ao carregar</td></tr>';
  }
}

function renderCampanhasTable(campanhas) {
  var tbody = document.getElementById('campanhas-tbody');
  if (!campanhas.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--muted)">Nenhuma campanha criada</td></tr>';
    return;
  }
  var statusLabels = { agendada: 'Agendada', em_andamento: 'Em Andamento', concluida: 'Concluída', cancelada: 'Cancelada' };
  var canalLabels = { whatsapp: '📱 WhatsApp', email: '📧 E-mail', ambos: '📱📧 Ambos' };
  tbody.innerHTML = campanhas.map(function(c) {
    return '<tr>' +
      '<td>' + escapeHtml(c.nome) + '</td>' +
      '<td>' + (canalLabels[c.canal] || c.canal) + '</td>' +
      '<td><span class="badge badge-' + c.status + '">' + (statusLabels[c.status] || c.status) + '</span></td>' +
      '<td>' + (c.total_leads || 0) + '</td>' +
      '<td>' + (c.enviados || 0) + '</td>' +
      '<td>' + (c.entregues || 0) + '</td>' +
      '<td>' + (c.respondidos || 0) + '</td>' +
      '<td>' +
        '<button class="btn btn-sm btn-ghost" onclick="verMetricasCampanha(' + c.id + ')" title="Métricas">📊</button>' +
        (c.status === 'agendada' ? '<button class="btn btn-sm btn-primary" onclick="dispararCampanha(' + c.id + ')" title="Disparar">🚀</button>' : '') +
        '<button class="btn btn-sm btn-ghost" onclick="excluirCampanha(' + c.id + ')" title="Excluir" style="color:var(--red)">🗑️</button>' +
      '</td></tr>';
  }).join('');
}

function renderCampanhasMobile(campanhas) {
  var container = document.getElementById('campanhas-cards-mobile');
  if (!container) return;
  if (!campanhas.length) {
    container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhuma campanha criada</div>';
    return;
  }
  var statusLabels = { agendada: 'Agendada', em_andamento: 'Em Andamento', concluida: 'Concluída', cancelada: 'Cancelada' };
  var canalLabels = { whatsapp: '📱 WhatsApp', email: '📧 E-mail', ambos: '📱📧 Ambos' };
  container.innerHTML = campanhas.map(function(c) {
    var pct = c.total_leads ? Math.round((c.enviados || 0) / c.total_leads * 100) : 0;
    return '<div class="crud-mobile-card">' +
      '<div class="crud-mobile-card-header">' +
        '<div class="crud-mobile-card-title">' + escapeHtml(c.nome) + '</div>' +
        '<span class="badge badge-' + c.status + '">' + (statusLabels[c.status] || c.status) + '</span>' +
      '</div>' +
      '<div class="crud-mobile-card-body">' +
        '<div><strong>Canal:</strong> ' + (canalLabels[c.canal] || c.canal) + '</div>' +
        '<div><strong>Leads:</strong> ' + (c.total_leads || 0) + ' | Enviados: ' + (c.enviados || 0) + ' (' + pct + '%)</div>' +
        '<div><strong>Entregues:</strong> ' + (c.entregues || 0) + ' | Respondidos: ' + (c.respondidos || 0) + '</div>' +
        '<div style="background:var(--bg);border-radius:4px;height:6px;margin-top:8px"><div style="background:var(--green);height:100%;border-radius:4px;width:' + pct + '%"></div></div>' +
      '</div>' +
      '<div class="crud-mobile-card-actions">' +
        '<button class="btn btn-sm btn-ghost" onclick="verMetricasCampanha(' + c.id + ')">📊 Métricas</button>' +
        (c.status === 'agendada' ? '<button class="btn btn-sm btn-primary" onclick="dispararCampanha(' + c.id + ')">🚀 Disparar</button>' : '') +
        '<button class="btn btn-sm btn-ghost" onclick="excluirCampanha(' + c.id + ')" style="color:var(--red)">🗑️</button>' +
      '</div></div>';
  }).join('');
}

function abrirModalCampanha() {
  document.getElementById('camp-id').value = '';
  document.getElementById('camp-nome').value = '';
  document.getElementById('camp-template').value = '';
  document.getElementById('camp-canal').value = 'whatsapp';
  document.getElementById('camp-leads').innerHTML = '';
  document.getElementById('modal-camp-title').textContent = 'Nova Campanha';
  carregarTemplatesCampanha();
  carregarLeadsParaCampanha();
  document.getElementById('modal-campanha').classList.add('open');
}

async function carregarTemplatesCampanha() {
  try {
    var res = await api.get('/comercial/templates');
    var sel = document.getElementById('camp-template');
    sel.innerHTML = '<option value="">Selecione...</option>';
    (res || []).forEach(function(t) {
      sel.innerHTML += '<option value="' + t.id + '">' + escapeHtml(t.nome) + ' (' + t.canal + ')</option>';
    });
  } catch (e) {
    console.error('Erro ao carregar templates:', e);
  }
}

async function carregarLeadsParaCampanha() {
  try {
    var res = await api.get('/comercial/leads?per_page=1000&status_pipeline_notin=fechado_ganho,fechado_perdido');
    var sel = document.getElementById('camp-leads');
    sel.innerHTML = '';
    (res.items || res || []).forEach(function(l) {
      var nome = l.nome_responsavel || l.nome_empresa || 'Lead #' + l.id;
      sel.innerHTML += '<option value="' + l.id + '">' + escapeHtml(nome) + ' - ' + (l.whatsapp || l.email || '') + '</option>';
    });
  } catch (e) {
    console.error('Erro ao carregar leads:', e);
  }
}

async function salvarCampanha() {
  var id = document.getElementById('camp-id').value;
  var nome = document.getElementById('camp-nome').value.trim();
  var templateId = document.getElementById('camp-template').value;
  var canal = document.getElementById('camp-canal').value;
  var leadsSel = document.getElementById('camp-leads');
  var leadIds = Array.from(leadsSel.selectedOptions).map(function(o) { return parseInt(o.value); });

  if (!nome || !templateId) {
    showToast('Preencha nome e template', 'error');
    return;
  }

  try {
    var body = { nome: nome, template_id: parseInt(templateId), canal: canal, lead_ids: leadIds };
    if (id) {
      await api.put('/comercial/campaigns/' + id, body);
      showToast('Campanha atualizada!');
    } else {
      await api.post('/comercial/campaigns/', body);
      showToast('Campanha criada!');
    }
    fecharModal('modal-campanha');
    carregarCampanhas();
  } catch (e) {
    showToast('Erro: ' + (e.message || 'Falha ao salvar campanha'), 'error');
  }
}

async function dispararCampanha(id) {
  if (!confirm('Disparar campanha agora? Esta ação enviará mensagens para os leads selecionados.')) return;
  try {
    await api.post('/comercial/campaigns/' + id + '/disparo', {});
    showToast('Disparo iniciado! Acompanhe nas métricas.');
    carregarCampanhas();
  } catch (e) {
    showToast('Erro ao disparar: ' + (e.message || 'Falha'), 'error');
  }
}

async function verMetricasCampanha(id) {
  try {
    var camp = campanhasCache.find(function(c) { return c.id === id; });
    document.getElementById('modal-camp-metricas-title').textContent = camp ? camp.nome : 'Métricas';

    var metrics = await api.get('/comercial/campaigns/' + id + '/metrics');
    var content = document.getElementById('camp-metricas-content');
    content.innerHTML = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">' +
      '<div style="padding:16px;background:var(--bg);border-radius:8px;text-align:center"><div style="font-size:24px;font-weight:700">' + (metrics.total_leads || 0) + '</div><div style="font-size:11px;color:var(--muted)">Total Leads</div></div>' +
      '<div style="padding:16px;background:var(--bg);border-radius:8px;text-align:center"><div style="font-size:24px;font-weight:700;color:var(--green)">' + (metrics.enviados || 0) + '</div><div style="font-size:11px;color:var(--muted)">Enviados</div></div>' +
      '<div style="padding:16px;background:var(--bg);border-radius:8px;text-align:center"><div style="font-size:24px;font-weight:700;color:var(--blue)">' + (metrics.entregues || 0) + '</div><div style="font-size:11px;color:var(--muted)">Entregues</div></div>' +
      '<div style="padding:16px;background:var(--bg);border-radius:8px;text-align:center"><div style="font-size:24px;font-weight:700;color:var(--yellow)">' + (metrics.respondidos || 0) + '</div><div style="font-size:11px;color:var(--muted)">Respondidos</div></div>' +
    '</div>' +
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">' +
      '<div style="padding:12px;background:var(--bg);border-radius:8px;text-align:center"><div style="font-size:18px;font-weight:700">' + (metrics.taxa_entrega || 0).toFixed(1) + '%</div><div style="font-size:11px;color:var(--muted)">Taxa Entrega</div></div>' +
      '<div style="padding:12px;background:var(--bg);border-radius:8px;text-align:center"><div style="font-size:18px;font-weight:700">' + (metrics.taxa_resposta || 0).toFixed(1) + '%</div><div style="font-size:11px;color:var(--muted)">Taxa Resposta</div></div>' +
    '</div>';

    var leads = await api.get('/comercial/campaigns/' + id + '/leads');
    var tbody = document.getElementById('camp-leads-tbody');
    var statusLabels = { pendente: 'Pendente', enviado: 'Enviado', entregue: 'Entregue', respondido: 'Respondido', erro: 'Erro' };
    tbody.innerHTML = (leads || []).map(function(l) {
      return '<tr>' +
        '<td>' + escapeHtml(l.lead_nome_empresa || l.lead_nome_responsavel || 'Lead #' + l.lead_id) + '</td>' +
        '<td><span class="badge badge-' + l.status + '">' + (statusLabels[l.status] || l.status) + '</span></td>' +
        '<td>' + (l.data_envio ? new Date(l.data_envio).toLocaleDateString('pt-BR') : '-') + '</td>' +
        '<td>' + (l.data_entrega ? new Date(l.data_entrega).toLocaleDateString('pt-BR') : '-') + '</td>' +
        '<td>' + (l.data_resposta ? new Date(l.data_resposta).toLocaleDateString('pt-BR') : '-') + '</td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--muted)">Nenhum lead</td></tr>';

    document.getElementById('modal-campanha-metricas').classList.add('open');
  } catch (e) {
    showToast('Erro ao carregar métricas: ' + (e.message || 'Falha'), 'error');
  }
}

async function excluirCampanha(id) {
  if (!confirm('Excluir esta campanha? Esta ação não pode ser desfeita.')) return;
  try {
    await api.delete('/comercial/campaigns/' + id);
    showToast('Campanha excluída!');
    carregarCampanhas();
  } catch (e) {
    showToast('Erro ao excluir: ' + (e.message || 'Falha'), 'error');
  }
}

// Event listeners para campanhas
document.getElementById('btn-nova-campanha')?.addEventListener('click', function() { abrirModalCampanha(); });
document.getElementById('modal-campanha')?.querySelector('.btn-primary')?.addEventListener('click', function() { salvarCampanha(); });
document.querySelector('#modal-campanha .modal-close')?.addEventListener('click', function() { fecharModal('modal-campanha'); });
document.querySelector('#modal-campanha .btn-secondary')?.addEventListener('click', function() { fecharModal('modal-campanha'); });
document.querySelector('#modal-campanha-metricas .modal-close')?.addEventListener('click', function() { fecharModal('modal-campanha-metricas'); });

document.getElementById('btn-confirmar-reenvio')?.addEventListener('click', confirmarReenvioProposta);
document.querySelector('#modal-confirmar-reenvio .modal-close')?.addEventListener('click', function() { fecharModal('modal-confirmar-reenvio'); });

// Leads filter selects - already handled above in GLOBAL LISTENERS
