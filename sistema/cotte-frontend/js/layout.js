/**
 * layout.js — Componente de sidebar compartilhado (FE-01)
 *
 * Uso em qualquer página autenticada:
 *
 *   <aside class="sidebar" id="sidebar"></aside>
 *   <script src="js/api.js?v=8"></script>
 *   <script src="js/layout.js?v=5"></script>
 *   <script>
 *     inicializarLayout('orcamentos');   // passa a chave da página ativa
 *     // ... resto do init da página
 *   </script>
 *
 * Chaves válidas: dashboard | orcamentos | clientes | catalogo |
 *                 documentos | relatorios | financeiro | agendamentos |
 *                 assistente-ia | copiloto-tecnico | usuarios | configuracoes |
 *                 comercial | admin | admin-planos | admin-config
 * (whatsapp.html usa admin-config para destacar Config Admin no menu)
 */

// ── HTML canônico da sidebar ───────────────────────────────────────────────
const _SIDEBAR_HTML = `
  <div class="logo">
    <div id="sidebar-logo-default" class="logo-mark">cotte<span>//</span></div>
    <img id="sidebar-logo-img" src="" alt="" style="display:none;max-height:40px;max-width:100%;object-fit:contain;">
    <div class="logo-sub" id="sidebar-empresa-nome"></div>
  </div>

  <nav class="nav">
    <a id="nav-voltar-admin" class="nav-item nav-admin-back" onclick="voltarAoAdmin()" style="display:none">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </span>
      Voltar ao Admin
    </a>
    <div id="nav-voltar-divider" class="nav-divider" style="display:none"></div>
    <a id="nav-dashboard" class="nav-item" data-page="dashboard" href="./">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
        </svg>
      </span>
      Dashboard
    </a>
    <a class="nav-item" data-page="orcamentos" href="orcamentos.html" id="nav-orcamentos">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      </span>
      Orçamentos
    </a>
    <a class="nav-item" data-page="clientes" href="clientes.html" id="nav-clientes">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
      </span>
      Clientes
    </a>
    <a class="nav-item" data-page="catalogo" href="catalogo.html" id="nav-catalogo">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
          <line x1="12" y1="22.08" x2="12" y2="12"/>
        </svg>
      </span>
      Catálogo
    </a>
    <a class="nav-item" data-page="documentos" href="documentos.html" id="nav-documentos">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      </span>
      Documentos
    </a>
    <a class="nav-item" data-page="relatorios" href="relatorios.html" id="nav-relatorios">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="20" x2="18" y2="10"/>
          <line x1="12" y1="20" x2="12" y2="4"/>
          <line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
      </span>
      Relatórios
    </a>
    <a class="nav-item" data-page="financeiro" href="financeiro.html" id="nav-financeiro">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/>
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
      </span>
      Financeiro
    </a>
    <a class="nav-item" data-page="agendamentos" href="agendamentos.html" id="nav-agendamentos">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
      </span>
      Agendamentos
    </a>

    <a class="nav-item nav-ia-link" data-page="assistente-ia" href="assistente-ia.html" id="nav-ia">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z"/>
          <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
          <line x1="9" y1="9" x2="9.01" y2="9"/>
          <line x1="15" y1="9" x2="15.01" y2="9"/>
        </svg>
      </span>
      Assistente IA
    </a>
    <a class="nav-item nav-ia-link" data-page="copiloto-tecnico" href="copiloto-tecnico.html" id="nav-copiloto" style="display:none">
      <span class="nav-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2 3 7v10l9 5 9-5V7z"/>
          <path d="M9 12h6"/>
          <path d="M12 9v6"/>
        </svg>
      </span>
      Copiloto Técnico
    </a>

    <div style="margin-top:auto;padding-top:8px">
      <div class="nav-divider"></div>
      <a class="nav-item" data-page="usuarios" href="usuarios.html" id="nav-equipe">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="8" r="4"/><path d="M6 20v-2a6 6 0 0 1 12 0v2"/>
          </svg>
        </span>
        Equipe
      </a>
      <a class="nav-item" data-page="configuracoes" href="configuracoes.html" id="nav-config">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </span>
        Configurações
      </a>
      <a id="nav-admin-link" class="nav-item nav-admin-link" data-page="admin" href="admin.html" style="display:none">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="16" height="20" x="4" y="2" rx="2" ry="2"/>
            <path d="M9 22v-4h6v4"/>
            <path d="M8 6h.01"/><path d="M16 6h.01"/>
            <path d="M8 10h.01"/><path d="M16 10h.01"/>
            <path d="M8 14h.01"/><path d="M16 14h.01"/>
            <path d="M8 18h.01"/><path d="M16 18h.01"/>
          </svg>
        </span>
        Empresas
      </a>
      <a id="nav-admin-planos-link" class="nav-item nav-planos-link" data-page="admin-planos" href="admin-planos.html" style="display:none">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>
          </svg>
        </span>
        Pacotes
      </a>
      <a id="nav-admin-config-link" class="nav-item nav-config-admin-link" data-page="admin-config" href="admin-config.html" style="display:none">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </span>
        Configurações Admin
      </a>
      <a id="nav-comercial-link" class="nav-item nav-comercial-link" data-page="comercial" href="comercial.html" style="display:none">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="20" x2="12" y2="10"/>
            <line x1="18" y1="20" x2="18" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="16"/>
          </svg>
        </span>
        Comercial
      </a>
      <div class="nav-item" onclick="logout()">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </span>
        Sair
      </div>
    </div>
  </nav>

  <div id="sidebar-plan-card" class="sidebar-plan-card" style="display:none">
    <div class="spc-row">
      <div class="spc-label"><span>Orçamentos</span><span id="plan-orc-text">--</span></div>
      <div class="spc-bar"><div id="plan-orc-bar" class="spc-bar-fill accent" style="width:0%"></div></div>
    </div>
    <div class="spc-row">
      <div class="spc-label"><span>Usuários</span><span id="plan-usr-text">--</span></div>
      <div class="spc-bar"><div id="plan-usr-bar" class="spc-bar-fill blue" style="width:0%"></div></div>
    </div>
    <div id="plan-validade" class="spc-validade" style="display:none"></div>
  </div>
  <div id="sidebar-broadcasts" style="display:none"></div>
  <div class="sidebar-footer">
    <div class="user-card">
      <div class="user-avatar" id="sidebar-user-avatar">--</div>
      <div class="user-text">
        <div class="user-name" id="sidebar-user-name">Carregando...</div>
        <div class="user-card-sub">
          <span class="user-plan" id="sidebar-user-plan">✦ Plano</span>
        </div>
      </div>
    </div>
  </div>
`;

/**
 * Inicializa o layout da página:
 * - Injeta a sidebar canônica no elemento <aside id="sidebar">
 * - Marca o item de nav ativo conforme `pageKey`
 * - Chama requireAuth() e carregarSidebar() (1 GET: empresa + uso + contagem de notificações)
 *
 * @param {string} pageKey - Chave da página ativa (ex: 'orcamentos')
 * @param {object} [opts]
 * @param {boolean} [opts.skipAuth=false] - Se true, não chama requireAuth()
 * @param {boolean} [opts.skipNotif=false] - Se true, não chama preencherNotificacoes()
 */
function inicializarLayout(pageKey, opts = {}) {
  const { skipAuth = false, skipNotif = false } = opts;

  // 1. Autentica
  if (!skipAuth && typeof requireAuth === 'function') {
    if (!requireAuth()) return; // redireciona para login.html
  }

  // 2. Injeta sidebar no placeholder
  const sidebarEl = document.getElementById('sidebar');
  if (sidebarEl) {
    sidebarEl.innerHTML = _SIDEBAR_HTML;
  }

  // 3. Marca item ativo
  if (pageKey) {
    document.querySelectorAll('.nav-item[data-page]').forEach(el => {
      if (el.dataset.page === pageKey) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });
  }

  // 4. Preenche dados do usuário + empresa + notificações (1 request combinado)
  if (typeof carregarSidebar === 'function') {
    carregarSidebar();
  } else if (typeof preencherUsuarioSidebar === 'function') {
    preencherUsuarioSidebar();
    if (typeof preencherLogoSidebar === 'function') preencherLogoSidebar();
    if (!skipNotif && typeof preencherNotificacoes === 'function') preencherNotificacoes();
  }

  // 5.1 Proteger itens do menu baseados em permissões
    if (typeof Permissoes !== 'undefined') {
      const p = Permissoes;
      if (!p.pode('orcamentos')) document.getElementById('nav-orcamentos')?.remove();
      if (!p.pode('clientes'))   document.getElementById('nav-clientes')?.remove();
      if (!p.pode('catalogo'))   document.getElementById('nav-catalogo')?.remove();
      if (!p.pode('documentos')) document.getElementById('nav-documentos')?.remove();
      if (!p.pode('relatorios')) document.getElementById('nav-relatorios')?.remove();
      if (!p.pode('financeiro')) document.getElementById('nav-financeiro')?.remove();
      if (!p.pode('agendamentos')) document.getElementById('nav-agendamentos')?.remove();
      if (!p.pode('ia'))         document.getElementById('nav-ia')?.remove();
      if (!p.pode('ia'))         document.getElementById('nav-copiloto')?.remove();
      if (!p.pode('equipe'))     document.getElementById('nav-equipe')?.remove();
      if (!p.pode('configuracoes')) document.getElementById('nav-config')?.remove();
      
      const u = getUsuario();
      if (u && u.is_superadmin) {
        document.getElementById('nav-admin-link').style.display = 'flex';
        document.getElementById('nav-admin-planos-link').style.display = 'flex';
        document.getElementById('nav-admin-config-link').style.display = 'flex';
      }
    }

    // Capability flags de IA (Sprint 3): controla visibilidade do copiloto interno.
    (function aplicarCapabilitiesIA() {
      const navCopiloto = document.getElementById('nav-copiloto');
      if (!navCopiloto) return;

      const client = window.ApiService || window.api;
      if (!client || typeof client.get !== 'function') return;

      client.get('/ai/assistente/capabilities')
        .then((resp) => {
          const data = (resp && resp.data) ? resp.data : resp;
          const components = (data && data.components) ? data.components : {};
          const availableEngines = (data && data.available_engines) ? data.available_engines : {};
          const canShowComponent = !!components['nav.copiloto_interno'];
          const canUseEngine = !!availableEngines['internal_copilot'];
          if (canShowComponent && canUseEngine) {
            navCopiloto.style.display = 'flex';
          } else {
            navCopiloto.remove();
          }
        })
        .catch(() => {
          navCopiloto.remove();
        });
    })();

    // Agendamentos não aparece no painel admin (fora do bloco de permissões)
    if (typeof pageKey === 'string' && pageKey.startsWith('admin')) {
      document.getElementById('nav-agendamentos')?.remove();
    }

  // 6. Strip de setup — aparece em todas as páginas enquanto onboarding pendente
  if (localStorage.getItem('onboarding_pending') === '1' && sidebarEl) {
    // Renderiza imediatamente com valor em cache (sem delay visual)
    const cachedPct = parseInt(localStorage.getItem('onboarding_pct') || '0', 10);
    _renderSetupStrip(sidebarEl, cachedPct);

    // Atualiza com dado real da API (reflete etapas concluídas em outras páginas)
    const token = localStorage.getItem('cotte_token');
    if (token) {
      const apiBase = typeof getApiBaseUrl === 'function' ? getApiBaseUrl() : '';
      fetch(apiBase + '/ai/onboarding', {
        headers: { 'Authorization': 'Bearer ' + token },
      })
        .then(r => r.ok ? r.json() : null)
        .then(res => {
          if (!res) return;
          const dados = res.dados || {};
          localStorage.setItem('onboarding_pending', dados.concluido ? '0' : '1');
          localStorage.setItem('onboarding_pct', dados.progresso_pct || 0);
          const strip = document.getElementById('setup-strip');
          if (dados.concluido) {
            if (strip) strip.remove();
            // Remove bolinha laranja do nav assistente (se presente)
            document.querySelectorAll('.onboarding-badge').forEach(el => el.remove());
          } else if (strip) {
            // Atualiza % e barra sem re-renderizar o elemento inteiro
            const pctSpan = strip.querySelector('[data-pct]');
            const bar     = strip.querySelector('[data-bar]');
            const pct     = dados.progresso_pct || 0;
            if (pctSpan) pctSpan.textContent = pct + '%';
            if (bar)     bar.style.width = pct + '%';
          }
        })
        .catch(() => {/* silencia — strip com cache já está visível */});
    }
  }
}

function _renderSetupStrip(sidebarEl, pct) {
  const strip = document.createElement('a');
  strip.href = 'assistente-ia.html';
  strip.id = 'setup-strip';
  strip.style.cssText = [
    'display:block',
    'margin:8px 8px 4px',
    'padding:10px 12px',
    'background:rgba(249,115,22,0.12)',
    'border:1px solid rgba(249,115,22,0.3)',
    'border-radius:8px',
    'text-decoration:none',
    'cursor:pointer',
  ].join(';');
  strip.innerHTML = `
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
      <span style="font-size:12px;font-weight:600;color:#f97316">🚀 Setup em andamento</span>
      <span data-pct style="font-size:11px;color:#f97316;margin-left:auto;font-weight:700">${pct}%</span>
    </div>
    <div style="height:4px;background:rgba(249,115,22,0.2);border-radius:2px;overflow:hidden;margin-bottom:6px">
      <div data-bar style="height:100%;width:${pct}%;background:#f97316;border-radius:2px"></div>
    </div>
    <div style="font-size:11px;color:var(--muted)">Clique para continuar →</div>
  `;
  const navDivider = sidebarEl.querySelector('.nav-divider');
  if (navDivider && navDivider.parentNode) {
    navDivider.parentNode.insertBefore(strip, navDivider);
  }
}
