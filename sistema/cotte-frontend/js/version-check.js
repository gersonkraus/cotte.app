/**
 * version-check.js
 * Detecta novos deploys comparando APP_VERSION com o backend a cada 5 minutos.
 * Exibe um banner discreto no topo da página pedindo que o usuário recarregue.
 */
(function () {
  'use strict';

  const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutos
  const DISMISS_KEY      = 'cotte_version_banner_dismissed';
  const VERSION_ENDPOINT = '/api/v1/version';

  let _currentVersion = null;
  let _bannerVisible  = false;

  // ── Banner ────────────────────────────────────────────────────────────────

  function _createBanner() {
    const bar = document.createElement('div');
    bar.id = 'cotte-update-banner';
    bar.setAttribute('role', 'alert');
    bar.style.cssText = [
      'position:fixed',
      'top:0',
      'left:0',
      'right:0',
      'z-index:9999',
      'display:flex',
      'align-items:center',
      'justify-content:center',
      'gap:12px',
      'padding:10px 16px',
      'background:linear-gradient(90deg,#1e40af,#2563eb)',
      'color:#fff',
      'font-size:13px',
      'font-family:inherit',
      'box-shadow:0 2px 8px rgba(0,0,0,.25)',
      'animation:_cvb-slide-in .3s ease',
    ].join(';');

    bar.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.28"/>
      </svg>
      <span>Nova versão disponível — recarregue para aplicar as atualizações.</span>
      <button id="cotte-update-reload"
        style="padding:4px 12px;border-radius:6px;border:none;background:#fff;
               color:#1e40af;font-weight:600;font-size:12px;cursor:pointer;white-space:nowrap;">
        Recarregar agora
      </button>
      <button id="cotte-update-dismiss" aria-label="Fechar"
        style="background:none;border:none;color:rgba(255,255,255,.7);
               font-size:18px;line-height:1;cursor:pointer;padding:0 4px;">
        &times;
      </button>`;

    // Injeta keyframe uma só vez
    if (!document.getElementById('_cvb-style')) {
      const s = document.createElement('style');
      s.id = '_cvb-style';
      s.textContent = '@keyframes _cvb-slide-in{from{transform:translateY(-100%)}to{transform:translateY(0)}}';
      document.head.appendChild(s);
    }

    document.body.prepend(bar);

    bar.querySelector('#cotte-update-reload').addEventListener('click', () => {
      window.location.reload();
    });

    bar.querySelector('#cotte-update-dismiss').addEventListener('click', () => {
      bar.remove();
      _bannerVisible = false;
      // Guarda dismiss para não voltar a mostrar nesta sessão
      try { sessionStorage.setItem(DISMISS_KEY, _currentVersion || ''); } catch (_) {}
    });
  }

  function _showBanner() {
    if (_bannerVisible) return;
    // Não mostrar se o usuário já dispensou esta versão na sessão
    try {
      const dismissed = sessionStorage.getItem(DISMISS_KEY);
      if (dismissed === _currentVersion) return;
    } catch (_) {}
    _bannerVisible = true;
    _createBanner();
  }

  // ── Polling ───────────────────────────────────────────────────────────────

  async function _checkVersion() {
    try {
      const res = await fetch(VERSION_ENDPOINT, { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      const serverVersion = data.version;
      if (!serverVersion) return;

      if (_currentVersion === null) {
        // Primeira chamada: registra versão atual do servidor
        _currentVersion = serverVersion;
      } else if (serverVersion !== _currentVersion) {
        // Versão mudou = novo deploy
        _currentVersion = serverVersion;
        _showBanner();
      }
    } catch (_) {
      // Silencia erros de rede — não deve interferir com a UX
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  function _init() {
    _checkVersion();
    setInterval(_checkVersion, POLL_INTERVAL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }
})();
