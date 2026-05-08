/**
 * nfe.js — Emissão de NF-e/NFC-e/NFS-e a partir de orçamentos.
 * Usa api.get / api.post do padrão COTTE (js/api.js).
 */
const NFeService = (() => {
  let _orcamentoId = null;

  function abrirModal(orcamentoId) {
    _orcamentoId = orcamentoId;
    const modal = document.getElementById('modal-nfe');
    if (!modal) return;
    modal.removeAttribute('hidden');
    modal.setAttribute('aria-hidden', 'false');
    carregarNotasExistentes(orcamentoId);
  }

  function fecharModal() {
    const modal = document.getElementById('modal-nfe');
    if (modal) {
      modal.setAttribute('hidden', '');
      modal.setAttribute('aria-hidden', 'true');
    }
    const statusMsg = document.getElementById('nfe-status-msg');
    if (statusMsg) statusMsg.textContent = '';
    _orcamentoId = null;
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
      resp = null;
    }

    if (btn) { btn.disabled = false; btn.textContent = 'Emitir NF'; }

    if (resp && resp.id) {
      if (statusMsg) statusMsg.textContent = 'Processando... aguardando SEFAZ.';
      _aguardarStatus(resp.id);
    } else {
      const errMsg = resp?.detail || resp?.error || 'Falha na emissão';
      if (statusMsg) statusMsg.textContent = `Erro: ${errMsg}`;
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
    } else {
      if (statusMsg) statusMsg.textContent = `Processando... (${tentativas + 1}/20)`;
      _aguardarStatus(notaId, tentativas + 1);
    }
  }

  async function _cancelar(notaId) {
    const motivo = prompt('Motivo do cancelamento (mín. 15 caracteres):');
    if (!motivo || motivo.length < 15) {
      alert('Motivo deve ter pelo menos 15 caracteres.');
      return;
    }
    let resp = null;
    try {
      resp = await api.post(`/notas-fiscais/${notaId}/cancelar`, { motivo });
    } catch (_) {
      resp = null;
    }
    if (resp && (resp.id || resp.success)) {
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
    } else {
      alert(resp?.detail || resp?.error || 'Erro ao cancelar nota');
    }
  }

  function _badgeClass(status) {
    const map = { emitida: 'success', erro: 'danger', cancelada: 'warning', processando: 'info', pendente: 'secondary' };
    return map[status] || 'secondary';
  }

  return { abrirModal, fecharModal, emitir, _cancelar };
})();

// Expõe no escopo global para uso em onclick= attributes
window.NFeService = NFeService;
