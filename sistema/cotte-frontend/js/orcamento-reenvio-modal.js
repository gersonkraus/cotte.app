/**
 * Modal de confirmação para reenvio de orçamento (WhatsApp / e-mail).
 * Exige no DOM: #modal-reenvio-orcamento e elementos listados em bindReenvioModalHandlers.
 */
(function () {
  'use strict';

  var _resolvePending = null;

  function precisaConfirmarReenvioOrcamento(orc) {
    if (!orc) return false;
    if (orc.enviado_em) return true;
    var st = (orc.status || '').toLowerCase();
    return !!(st && st !== 'rascunho');
  }

  function mensagemFallback(canal) {
    var wa = (canal || '').toLowerCase() === 'whatsapp';
    return wa
      ? 'Este orçamento já foi enviado ao cliente antes. Deseja enviar novamente pelo WhatsApp?'
      : 'Este orçamento já foi enviado ao cliente antes. Deseja enviar novamente por e-mail?';
  }

  function fecharModalReenvioOrcamento(confirmed) {
    var overlay = document.getElementById('modal-reenvio-orcamento');
    if (overlay) overlay.classList.remove('open');
    document.removeEventListener('keydown', onKeydownReenvio);
    var fn = _resolvePending;
    _resolvePending = null;
    if (fn) fn(!!confirmed);
  }

  function onKeydownReenvio(ev) {
    if (ev.key === 'Escape') {
      ev.preventDefault();
      fecharModalReenvioOrcamento(false);
    }
  }

  function abrirModalReenvioOrcamento(canal) {
    return new Promise(function (resolve) {
      var overlay = document.getElementById('modal-reenvio-orcamento');
      if (!overlay) {
        resolve(window.confirm(mensagemFallback(canal)));
        return;
      }
      if (_resolvePending) {
        _resolvePending(false);
        _resolvePending = null;
      }
      _resolvePending = resolve;
      var isWa = (canal || '').toLowerCase() === 'whatsapp';
      var titleEl = document.getElementById('reenvio-orc-titulo');
      var msgEl = document.getElementById('reenvio-orc-mensagem');
      if (titleEl) {
        titleEl.textContent = isWa
          ? 'Enviar novamente pelo WhatsApp?'
          : 'Enviar novamente por e-mail?';
      }
      if (msgEl) {
        msgEl.textContent = mensagemFallback(canal);
      }
      overlay.classList.add('open');
      document.addEventListener('keydown', onKeydownReenvio);
    });
  }

  function cotteConfirmarReenvioSeNecessario(orc, canal) {
    if (!precisaConfirmarReenvioOrcamento(orc)) {
      return Promise.resolve(true);
    }
    return abrirModalReenvioOrcamento(canal);
  }

  function bindReenvioModalHandlers() {
    var overlay = document.getElementById('modal-reenvio-orcamento');
    if (!overlay || overlay.dataset.cotteBound) return;
    overlay.dataset.cotteBound = '1';
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) fecharModalReenvioOrcamento(false);
    });
    var btnNao = document.getElementById('reenvio-orc-btn-cancelar');
    var btnSim = document.getElementById('reenvio-orc-btn-confirmar');
    var btnClose = document.getElementById('reenvio-orc-btn-fechar');
    if (btnNao) btnNao.addEventListener('click', function () { fecharModalReenvioOrcamento(false); });
    if (btnSim) btnSim.addEventListener('click', function () { fecharModalReenvioOrcamento(true); });
    if (btnClose) btnClose.addEventListener('click', function () { fecharModalReenvioOrcamento(false); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindReenvioModalHandlers);
  } else {
    bindReenvioModalHandlers();
  }

  window.precisaConfirmarReenvioOrcamento = precisaConfirmarReenvioOrcamento;
  window.cotteConfirmarReenvioSeNecessario = cotteConfirmarReenvioSeNecessario;
})();
