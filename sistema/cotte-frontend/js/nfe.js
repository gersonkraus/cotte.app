/**
 * nfe.js — Emissão de NF-e/NFC-e/NFS-e a partir de orçamentos.
 * Usa api.get / api.post do padrão COTTE (js/api.js).
 */
const NFeService = (() => {
  let _orcamentoId = null;
  let _preparadoOk = false;

  function abrirModal(orcamentoId) {
    _orcamentoId = orcamentoId;
    const modal = document.getElementById('modal-nfe');
    if (!modal) return;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    carregarNotasExistentes(orcamentoId);
  }

  function fecharModal() {
    const modal = document.getElementById('modal-nfe');
    if (modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
    const statusMsg = document.getElementById('nfe-status-msg');
    if (statusMsg) statusMsg.textContent = '';
    _orcamentoId = null;
    _preparadoOk = false;
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    if (btnEmitir) btnEmitir.disabled = true;
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
  }

  async function carregarNotasExistentes(orcamentoId) {
    const lista = document.getElementById('nfe-lista-notas');
    if (!lista) return;
    lista.innerHTML = '<p style="color:var(--text-muted,#888)">Carregando...</p>';

    let notas = [];
    try {
      const resp = await api.get(`/notas-fiscais/orcamento/${orcamentoId}`);
      notas = Array.isArray(resp) ? resp : (resp?.data || []);
    } catch (_) {
      notas = [];
    }

    if (!notas.length) {
      lista.innerHTML = '<p style="color:var(--text-muted,#888)">Nenhuma nota emitida para este orçamento.</p>';
      return;
    }
    lista.innerHTML = notas.map(n => `
      <div class="nfe-item" style="display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid var(--border,#eee)">
        <span style="font-weight:600;text-transform:uppercase;font-size:0.8rem">${n.tipo}</span>
        <span>${n.numero ? `N\xba ${n.numero} \xb7 S\xe9rie ${n.serie}` : '—'}</span>
        <span class="badge badge-${_badgeClass(n.status)}" style="margin-left:auto">${n.status}</span>
        ${n.danfe_url ? `<a href="${n.danfe_url}" target="_blank" class="btn btn-ghost btn-sm">DANFE</a>` : ''}
        ${n.xml_url ? `<a href="${n.xml_url}" target="_blank" class="btn btn-ghost btn-sm">XML</a>` : ''}
        ${n.status === 'emitida' ? `<button class="btn btn-ghost btn-sm" onclick="NFeService._cancelar(${n.id})">Cancelar</button>` : ''}
        ${n.status === 'erro' ? `<span style="font-size:0.75rem;color:var(--danger,red)">Erro: ${n.erro_mensagem || n.erro_codigo || ''}</span>` : ''}
      </div>
    `).join('');
  }

  async function emitir() {
    const tipo = document.getElementById('nfe-tipo')?.value;
    const natureza = document.getElementById('nfe-natureza')?.value || 'Venda de Serviços';
    const serie = document.getElementById('nfe-serie')?.value || '1';
    const codigoServico = document.getElementById('nfe-codigo-servico')?.value;
    const aliquotaIss = document.getElementById('nfe-aliquota-iss')?.value;
    const btn = document.getElementById('btn-emitir-nfe');
    const statusMsg = document.getElementById('nfe-status-msg');

    if (!_preparadoOk) {
      if (statusMsg) statusMsg.textContent = 'Clique em Verificar primeiro.';
      return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Emitindo...'; }
    if (statusMsg) statusMsg.textContent = 'Enviando para a SEFAZ, aguarde...';

    const payload = {
      orcamento_id: _orcamentoId,
      tipo,
      natureza_operacao: natureza,
      serie,
      ...(codigoServico ? { codigo_servico_lc116: codigoServico } : {}),
      ...(aliquotaIss ? { aliquota_iss: parseFloat(aliquotaIss) } : {}),
    };

    let resp = null;
    try {
      resp = await api.post('/notas-fiscais/emitir', payload);
    } catch (e) {
      if (btn) { btn.disabled = false; btn.textContent = '✅ Confirmar e Emitir'; }
      if (statusMsg) statusMsg.textContent = `Erro: ${e.message || 'Falha na emissão'}`;
      return;
    }

    if (btn) { btn.disabled = false; btn.textContent = '✅ Confirmar e Emitir'; }

    if (resp && resp.id) {
      if (statusMsg) statusMsg.textContent = 'Processando... aguardando SEFAZ.';
      _aguardarStatus(resp.id);
    } else {
      if (statusMsg) statusMsg.textContent = 'Erro: resposta inesperada do servidor';
    }
  }

  async function _aguardarStatus(notaId, tentativas = 0) {
    if (tentativas > 20) {
      const statusMsg = document.getElementById('nfe-status-msg');
      if (statusMsg) statusMsg.textContent = 'Timeout: verifique o status manualmente.';
      return;
    }
    await new Promise(r => setTimeout(r, 3000));

    let nota = null;
    try {
      const resp = await api.get(`/notas-fiscais/${notaId}`);
      nota = resp?.data || resp;
    } catch (_) {
      nota = null;
    }
    if (!nota) return;

    const statusMsg = document.getElementById('nfe-status-msg');
    if (nota.status === 'emitida') {
      if (statusMsg) statusMsg.textContent = `✓ NF emitida com sucesso! N\xfamero: ${nota.numero || '—'}`;
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
    } else if (nota.status === 'erro') {
      if (statusMsg) statusMsg.textContent = `Erro SEFAZ: ${nota.erro_mensagem || nota.erro_codigo || 'desconhecido'}`;
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
      _mostrarBotaoAnalise(notaId);
    } else {
      if (statusMsg) statusMsg.textContent = `Processando... (${tentativas + 1}/20)`;
      _aguardarStatus(notaId, tentativas + 1);
    }
  }

  function _mostrarBotaoAnalise(notaId) {
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (!areaPrep) return;
    areaPrep.innerHTML = `
      <div style="margin-top:8px">
        <button id="btn-analisar-erro-nfe" class="btn btn-sm btn-warning" style="width:100%">
          Analisar Erro e Ver O Que Corrigir
        </button>
        <div id="nfe-analise-resultado" style="margin-top:8px"></div>
      </div>`;
    document.getElementById('btn-analisar-erro-nfe').onclick = async function() {
      const btn = this;
      btn.disabled = true;
      btn.textContent = 'Analisando...';
      const area = document.getElementById('nfe-analise-resultado');
      try {
        const analise = await api.post(`/notas-fiscais/${notaId}/analisar-erro`, {});
        const sugestoes = analise.sugestoes || [];
        if (!sugestoes.length) {
          if (area) area.innerHTML = '<p style="font-size:12px;color:var(--text-muted,#888)">Nenhuma sugestão automática disponível.</p>';
        } else {
          if (area) area.innerHTML = sugestoes.map(s =>
            `<div style="margin-bottom:8px;padding:8px 10px;background:rgba(255,200,0,0.07);border-left:3px solid #f59e0b;border-radius:4px;font-size:12px">
              <div style="color:#f59e0b;font-weight:600;margin-bottom:2px">${s.campo}</div>
              <div>${s.acao}</div>
            </div>`
          ).join('');
        }
        btn.textContent = 'Atualizar Análise';
        btn.disabled = false;
      } catch(e) {
        btn.disabled = false;
        btn.textContent = 'Analisar Erro e Ver O Que Corrigir';
        if (area) area.innerHTML = `<p style="font-size:12px;color:#ef4444">Erro ao analisar: ${e.message || 'tente novamente'}</p>`;
      }
    };
  }

  async function _cancelar(notaId) {
    const motivo = prompt('Motivo do cancelamento (mín. 15 caracteres):');
    if (!motivo || motivo.length < 15) {
      alert('Motivo deve ter pelo menos 15 caracteres.');
      return;
    }
    try {
      await api.post(`/notas-fiscais/${notaId}/cancelar`, { motivo });
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
    } catch (e) {
      alert(e.message || 'Erro ao cancelar nota');
    }
  }

  async function _preparar() {
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    const btnVerificar = document.getElementById('btn-verificar-nfe');
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (!_orcamentoId) return;

    if (btnVerificar) { btnVerificar.disabled = true; btnVerificar.textContent = 'Verificando...'; }
    _preparadoOk = false;
    if (btnEmitir) btnEmitir.disabled = true;
    if (areaPrep) areaPrep.innerHTML = '';

    try {
      const resultado = await api.post('/notas-fiscais/preparar', {
        orcamento_id: _orcamentoId,
        tipo,
      });

      _preparadoOk = resultado.pronto === true;
      if (btnEmitir) btnEmitir.disabled = !_preparadoOk;

      let html = '';

      if (resultado.bloqueios && resultado.bloqueios.length) {
        html += resultado.bloqueios.map(b =>
          `<div style="color:#ef4444;font-size:12px;padding:4px 0">❌ ${b}</div>`
        ).join('');
      }
      if (resultado.avisos && resultado.avisos.length) {
        html += resultado.avisos.map(a =>
          `<div style="color:#f59e0b;font-size:12px;padding:4px 0">⚠️ ${a}</div>`
        ).join('');
      }
      if (_preparadoOk && !html) {
        html = `<div style="color:#00e5a0;font-size:12px;font-weight:600">✅ ${resultado.resumo || 'Pronto para emitir'}</div>`;
      } else if (_preparadoOk) {
        html = `<div style="color:#00e5a0;font-size:12px;font-weight:600;margin-bottom:4px">✅ ${resultado.resumo}</div>` + html;
      }

      if (areaPrep) areaPrep.innerHTML = html;
    } catch (e) {
      _preparadoOk = false;
      if (btnEmitir) btnEmitir.disabled = true;
      if (areaPrep) areaPrep.innerHTML = `<div style="color:#ef4444;font-size:12px">❌ Erro ao verificar: ${e.message || 'Tente novamente'}</div>`;
    } finally {
      if (btnVerificar) { btnVerificar.disabled = false; btnVerificar.textContent = '🔍 Verificar'; }
    }
  }

  function _toggleCamposNfse() {
    const tipo = document.getElementById('nfe-tipo')?.value;
    const campos = document.getElementById('campos-nfse');
    const natureza = document.getElementById('nfe-natureza');
    if (!campos) return;
    if (tipo === 'nfse') {
      campos.style.display = 'flex';
      if (natureza && natureza.value === 'Venda de Mercadorias') natureza.value = 'Prestação de Serviços';
    } else {
      campos.style.display = 'none';
      if (natureza && natureza.value === 'Prestação de Serviços') natureza.value = 'Venda de Mercadorias';
    }
    // Resetar verificação ao mudar tipo
    _preparadoOk = false;
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    if (btnEmitir) btnEmitir.disabled = true;
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
  }

  function _badgeClass(status) {
    const map = { emitida: 'success', erro: 'danger', cancelada: 'warning', processando: 'info', pendente: 'secondary' };
    return map[status] || 'secondary';
  }

  return { abrirModal, fecharModal, emitir, _cancelar, verificar: _preparar, _toggleCamposNfse };
})();

// Expõe no escopo global para uso em onclick= attributes
window.NFeService = NFeService;
