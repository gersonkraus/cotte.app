// ── TEMA (aplicado antes do render para evitar flash) ────────────────────
(function() {
  var t = localStorage.getItem('cotte_tema');
  if (t) document.documentElement.setAttribute('data-theme', t);
})();

// ── CONFIGURAÇÃO DA API ─────────────────────────────────────────────────
function isLocalDevHostname(hostname) {
  return (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '[::1]' ||
    hostname === '::1'
  );
}

// Tenta detectar automaticamente a URL da API
function getApiBaseUrl() {
  const origin = window.location.origin;
  const hostname = window.location.hostname;

  // Dev local: frontend e API em portas diferentes (ex.: 5500 vs 8000)
  if (
    origin.includes('localhost') ||
    origin.includes('127.0.0.1') ||
    origin.includes('[::1]') ||
    isLocalDevHostname(hostname)
  ) {
    return `http://${hostname}:8000`;
  }

  return '';
}

const API_URL = getApiBaseUrl();
const API_PREFIX = '/api/v1';

/** Compara hosts ignorando www (apex vs www em produção). */
function normalizeApiHostname(hostname) {
  return String(hostname || '')
    .replace(/^www\./i, '')
    .toLowerCase();
}

/**
 * Origem para montar URLs absolutas de fetch (ignora &lt;base href&gt; do documento).
 * Prioriza location.protocol: se a aba está em HTTPS, a API no mesmo host deve ser HTTPS
 * (evita Mixed Content). isSecureContext entra como fallback para casos atípicos.
 */
function getApiFetchOrigin() {
  if (API_URL) return API_URL;
  const loc = window.location;
  const host = loc.hostname + (loc.port ? ':' + loc.port : '');
  const local = isLocalDevHostname(loc.hostname);

  if (loc.protocol === 'https:') {
    return 'https://' + host;
  }

  if (local) {
    return 'http://' + loc.hostname + ':8000';
  }

  if (loc.protocol === 'http:') {
    return 'http://' + host;
  }

  if (window.isSecureContext) {
    return 'https://' + host;
  }

  return loc.origin;
}

/**
 * Última defesa: página HTTPS + URL http no mesmo host → promove a HTTPS (evita Mixed Content).
 */
function pageRequiresHttpsApi() {
  const loc = window.location;
  if (loc.protocol === 'https:') return true;
  if (typeof document !== 'undefined' && String(document.URL || '').startsWith('https:')) return true;
  return false;
}

function coerceFetchUrlIfMixedContent(url) {
  if (typeof window === 'undefined' || !url) return url;
  try {
    const loc = window.location;
    if (!pageRequiresHttpsApi()) return url;
    const u = new URL(String(url), loc.href);
    if (u.protocol === 'http:') {
      const sameHost =
        normalizeApiHostname(u.hostname) === normalizeApiHostname(loc.hostname);
      if (sameHost) {
        u.protocol = 'https:';
        return u.href;
      }
    }
  } catch (e) {
    /* ignore */
  }
  return url;
}

/**
 * Última barreira antes do fetch: nunca pedir http no mesmo site se a aba é HTTPS.
 */
function finalizeFetchUrlForMixedContent(url) {
  return coerceFetchUrlIfMixedContent(url);
}

/**
 * Produção: monta URL absoluta a partir da raiz usando window.location.href como base.
 * O fetch() com string só com path resolve contra document.baseURI (&lt;base href&gt;); aqui ignoramos isso.
 */
function resolveAppPathAgainstDocument(pathFromRoot) {
  const p = pathFromRoot.startsWith('/') ? pathFromRoot : '/' + pathFromRoot;
  const loc = window.location;
  let base = loc.href;
  if (loc.protocol === 'https:') {
    base = loc.origin + '/';
  } else if (typeof document !== 'undefined' && String(document.URL || '').startsWith('https:')) {
    try {
      base = new URL(document.URL).origin + '/';
    } catch (e) {
      /* mantém loc.href */
    }
  }
  const href = new URL(p, base).href;
  return coerceFetchUrlIfMixedContent(href);
}

/** endpoint: ex. '/comercial/propostas-publicas' → URL para fetch. */
function buildApiRequestUrl(endpoint) {
  const ep = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
  const path = API_PREFIX + ep;
  if (!API_URL) return resolveAppPathAgainstDocument(path);
  const href = new URL(path, getApiFetchOrigin() + '/').href;
  return coerceFetchUrlIfMixedContent(href);
}

/** Path já completo a partir da raiz, ex. '/api/v1/health' ou '/docs'. */
function buildAbsoluteAppUrl(path) {
  const p = path.startsWith('/') ? path : '/' + path;
  if (!API_URL) return resolveAppPathAgainstDocument(p);
  const href = new URL(p, getApiFetchOrigin() + '/').href;
  return coerceFetchUrlIfMixedContent(href);
}

/** Logo/caminho relativo no mesmo host que a API. */
function buildPublicAssetUrl(path) {
  if (!path || String(path).startsWith('http')) return path || '';
  const p = path.startsWith('/') ? path : '/' + path;
  if (!API_URL) return resolveAppPathAgainstDocument(p);
  const href = new URL(p, getApiFetchOrigin() + '/').href;
  return coerceFetchUrlIfMixedContent(href);
}

// Variável para controlar se a API está disponível
let API_DISPONIVEL = true;

// Prefixo para endpoints admin
const ADMIN_PREFIX = '/admin';

// ── HELPERS DE REQUISIÇÃO ───────────────────────────────────────────────

async function apiRequest(method, endpoint, body = null, options = {}) {
  const { bypassAutoLogout = false, useMock = false } = options;
  const token = localStorage.getItem('cotte_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    // Token não é mais logado por segurança
  } else {
    console.warn('[API] Token não encontrado no localStorage');
  }

  const fetchOptions = { method, headers };
  if (body) fetchOptions.body = JSON.stringify(body);

  const url = finalizeFetchUrlForMixedContent(buildApiRequestUrl(endpoint));

  // Se useMock for true, retornar dados simulados para endpoints de IA
  if (useMock && endpoint.includes('/ai/')) {
    console.log('[API] Usando dados simulados para', endpoint);
    return mockAIResponse(endpoint, body);
  }

  let response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (networkError) {
    console.error('[API] Erro de rede:', networkError);
    API_DISPONIVEL = false;
    throw new Error('Erro de conexão. Verifique sua internet e se o servidor está rodando.');
  }

  let data;
  const text = await response.text();
  try {
    data = text ? JSON.parse(text) : null;
  } catch (_) {
    data = null;
  }

  // Token expirado ou não autenticado → mostra erro e redireciona para login
  if (response.status === 401 && !bypassAutoLogout) {
    logout();
    const msg = (data && typeof data.detail === 'string') ? data.detail
      : (data && data.error && typeof data.error.message === 'string') ? data.error.message
      : 'Sessão expirada. Faça login novamente.';
    throw new Error(msg);
  }

  if (!response.ok) {
    // Extrai mensagem de erro (suporta formato padrão FastAPI e handler customizado)
    const errorMsg = (data && typeof data.detail === 'string') ? data.detail
      : (data && data.error && typeof data.error.message === 'string') ? data.error.message
      : '';

    // Assinatura expirada ou empresa inativa — exibe modal de planos
    if (response.status === 402 || (response.status === 403 && errorMsg.toLowerCase().includes('empresa inativa'))) {
      if (typeof exibirModalPlanos === 'function') exibirModalPlanos();
      const errPlan = new Error(errorMsg || 'Assinatura expirada ou inativa.');
      errPlan.statusCode = response.status;
      throw errPlan;
    }

    // Se for erro 404 ou 405 em endpoints de IA, tentar usar mock
    if ((response.status === 404 || response.status === 405) && endpoint.includes('/ai/')) {
      console.log('[API] Endpoint de IA não encontrado, usando dados simulados');
      return mockAIResponse(endpoint, body);
    }

    const msg = errorMsg || (Array.isArray(data?.detail) ? data.detail.map(d => d.msg || d).join(', ') : '') || `Erro ${response.status}: ${response.statusText}`;
    throw new Error(msg);
  }

  API_DISPONIVEL = true;
  return data;
}

const api = {
  get:    (endpoint, options)       => apiRequest('GET',    endpoint, null, options),
  post:   (endpoint, body, options) => apiRequest('POST',   endpoint, body, options),
  put:    (endpoint, body, options) => apiRequest('PUT',    endpoint, body, options),
  patch:  (endpoint, body, options) => apiRequest('PATCH',  endpoint, body, options),
  delete: (endpoint, options)       => apiRequest('DELETE', endpoint, null, options),
  resolveUrl: (path) => {
    if (!path) return '';
    return path.startsWith('http') ? path : buildPublicAssetUrl(path);
  }
};

// ── AUTENTICAÇÃO ─────────────────────────────────────────────────────────

function getToken()    { return localStorage.getItem('cotte_token'); }
function getUsuario()  { return JSON.parse(localStorage.getItem('cotte_usuario') || 'null'); }

function salvarSessao(token, usuario) {
  localStorage.setItem('cotte_token', token);
  localStorage.setItem('cotte_usuario', JSON.stringify(usuario));
}

function logout() {
  localStorage.removeItem('cotte_token');
  localStorage.removeItem('cotte_usuario');
  window.location.href = 'login.html';
}

// Protege páginas que exigem login
function requireAuth() {
  if (!getToken()) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

// Preenche dados do usuário na sidebar
function preencherUsuarioSidebar() {
  const usuario = getUsuario();
  if (!usuario) return;
  const nomeEl = document.getElementById('sidebar-user-name');
  const avatarEl = document.getElementById('sidebar-user-avatar');
  if (nomeEl) nomeEl.textContent = usuario.nome;
  if (avatarEl) avatarEl.textContent = usuario.nome.slice(0, 2).toUpperCase();

  // Mostra links admin e comercial se superadmin (WhatsApp global: só em admin-config.html)
  if (usuario.is_superadmin) {
    const adminLink = document.getElementById('nav-admin-link');
    if (adminLink) adminLink.style.display = 'flex';
    const comercialLink = document.getElementById('nav-comercial-link');
    if (comercialLink) comercialLink.style.display = 'flex';
    const planEl = document.querySelector('.user-plan');
    if (planEl) { planEl.textContent = 'Superadmin'; planEl.style.color = '#f97316'; }

    // Oculta itens de empresa — superadmin não opera em empresa própria
    ['nav-dashboard','nav-orcamentos','nav-clientes','nav-catalogo',
     'nav-documentos','nav-relatorios','nav-financeiro','nav-agendamentos',
     'nav-ia','nav-equipe','nav-config'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
  }

  // Exibe "Voltar ao Admin" quando superadmin está impersonando uma empresa
  const backupToken = sessionStorage.getItem('superadmin_token_backup');
  if (backupToken) {
    const btnVoltar = document.getElementById('nav-voltar-admin');
    const divVoltar = document.getElementById('nav-voltar-divider');
    if (btnVoltar) btnVoltar.style.display = 'flex';
    if (divVoltar) divVoltar.style.display = 'block';
  }
}

// Restaura sessão do superadmin após impersonar uma empresa
function voltarAoAdmin() {
  const token = sessionStorage.getItem('superadmin_token_backup');
  const usuarioStr = sessionStorage.getItem('superadmin_usuario_backup');
  if (!token || !usuarioStr) return;
  sessionStorage.removeItem('superadmin_token_backup');
  sessionStorage.removeItem('superadmin_usuario_backup');
  salvarSessao(token, JSON.parse(usuarioStr));
  window.location.href = 'admin.html';
}

// Busca dados da empresa e exibe a logo no topo da sidebar (onde está "COTTE")
async function preencherLogoSidebar() {
  const defaultEl = document.getElementById('sidebar-logo-default');
  const imgEl = document.getElementById('sidebar-logo-img');
  const nomeEl = document.getElementById('sidebar-empresa-nome');
  if (!defaultEl && !imgEl && !nomeEl) return;
  try {
    const emp = await api.get('/empresa/');
    if (emp) {
      if (nomeEl) nomeEl.textContent = emp.nome || '';
      if (emp.logo_url) {
        if (imgEl) {
          imgEl.src = emp.logo_url.startsWith('http') ? emp.logo_url : buildPublicAssetUrl(emp.logo_url);
          imgEl.alt = emp.nome || 'Logo';
          imgEl.style.display = 'block';
        }
        if (defaultEl) defaultEl.style.display = 'none';
      } else {
        if (imgEl) imgEl.style.display = 'none';
        if (defaultEl) defaultEl.style.display = '';
      }

      // ── Plano na sidebar ────────────────────────────────────────────────
      if (!getUsuario()?.is_superadmin) {
        const NOMES = { trial: 'Avaliação', starter: 'Starter', pro: 'Pro', business: 'Business' };
        const CORES = { trial: '#6b7280',   starter: '#3b82f6', pro: '#00e5a0', business: '#f97316' };
        const plano     = (emp.plano || 'trial').toLowerCase();
        const nomePlano = NOMES[plano] || plano;
        const cor       = CORES[plano] || 'var(--accent)';

        // Atualiza texto do plano no user-card
        const planEl = document.getElementById('sidebar-user-plan') || document.querySelector('.user-plan');
        if (planEl) { planEl.textContent = '✦ ' + nomePlano; planEl.style.color = cor; }

        // Injeta link "Upgrade" ao lado do nome do plano (Trial, Starter e Pro)
        const sub = planEl && planEl.closest('.user-card-sub');
        if (sub && !sub.querySelector('.sidebar-upgrade-link')) {
          if (plano === 'trial' || plano === 'starter' || plano === 'pro') {
            const link = document.createElement('a');
            link.href = '#';
            link.className = 'sidebar-upgrade-link';
            link.textContent = 'Upgrade';
            link.onclick = function(e) {
              e.preventDefault();
              window.location.href = 'configuracoes.html#plano';
            };
            sub.appendChild(link);
          }
        }
      }
      // ────────────────────────────────────────────────────────────────────

      // Busca e exibe uso do plano (barras de progresso)
      _preencherUsoPlano();
    } else {
      if (nomeEl) nomeEl.textContent = '';
      if (imgEl) imgEl.style.display = 'none';
      if (defaultEl) defaultEl.style.display = '';
    }
  } catch (e) {
    if (nomeEl) nomeEl.textContent = '';
    if (imgEl) imgEl.style.display = 'none';
    if (defaultEl) defaultEl.style.display = '';
  }
}

// Carrega sidebar em uma única requisição (empresa + uso + notificações)
async function carregarSidebar() {
  preencherUsuarioSidebar();
  const u = getUsuario();
  const impersonando = typeof sessionStorage !== 'undefined' && sessionStorage.getItem('superadmin_token_backup');
  // Superadmin fora do modo "impersonar empresa" não consome dados de empresa na sidebar
  if (u?.is_superadmin && !impersonando) return;
  try {
    const dados = await api.get('/empresa/resumo-sidebar');
    if (!dados) return;
    const emp = dados.empresa;

    // ── Logo e nome ──
    const defaultEl = document.getElementById('sidebar-logo-default');
    const imgEl = document.getElementById('sidebar-logo-img');
    const nomeEl = document.getElementById('sidebar-empresa-nome');
    if (nomeEl) nomeEl.textContent = emp.nome || '';
    if (emp.logo_url) {
      if (imgEl) {
        imgEl.src = emp.logo_url.startsWith('http') ? emp.logo_url : buildPublicAssetUrl(emp.logo_url);
        imgEl.alt = emp.nome || 'Logo';
        imgEl.style.display = 'block';
      }
      if (defaultEl) defaultEl.style.display = 'none';
    } else {
      if (imgEl) imgEl.style.display = 'none';
      if (defaultEl) defaultEl.style.display = '';
    }

    // ── Plano na sidebar ──
    const NOMES = { trial: 'Avaliação', starter: 'Starter', pro: 'Pro', business: 'Business' };
    const CORES = { trial: '#6b7280', starter: '#3b82f6', pro: '#00e5a0', business: '#f97316' };
    const plano = (emp.plano || 'trial').toLowerCase();
    const planEl = document.getElementById('sidebar-user-plan') || document.querySelector('.user-plan');
    if (planEl) { planEl.textContent = '✦ ' + (NOMES[plano] || plano); planEl.style.color = CORES[plano] || 'var(--accent)'; }

    const sub = planEl && planEl.closest('.user-card-sub');
    if (sub && !sub.querySelector('.sidebar-upgrade-link')) {
      if (plano === 'trial' || plano === 'starter' || plano === 'pro') {
        const link = document.createElement('a');
        link.href = '#'; link.className = 'sidebar-upgrade-link'; link.textContent = 'Upgrade';
        link.onclick = function(e) { e.preventDefault(); window.location.href = 'configuracoes.html#plano'; };
        sub.appendChild(link);
      }
    }

    // ── Uso do plano ──
    await _preencherUsoPlano(dados.uso);

    // ── Contagem de notificações ──
    const notifEl = document.getElementById('topbar-notificacoes');
    if (notifEl) {
      const count = dados.notificacoes_nao_lidas || 0;
      notifEl.innerHTML = count > 0
        ? `<button type="button" onclick="abrirDropdownNotificacoes(event)" style="position:relative;display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border:none;border-radius:10px;background:var(--surface2);color:var(--text);cursor:pointer;font-size:16px">🔔<span style="position:absolute;top:2px;right:2px;background:#ef4444;color:#fff;font-size:10px;min-width:16px;height:16px;border-radius:8px;display:flex;align-items:center;justify-content:center">${count > 99 ? '99+' : count}</span></button>`
        : `<button type="button" onclick="abrirDropdownNotificacoes(event)" style="display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border:none;border-radius:10px;background:var(--surface2);color:var(--muted);cursor:pointer;font-size:16px">🔔</button>`;
    }
  } catch (_) { /* silencia — sidebar mostra dados parciais */ }
}

async function _preencherUsoPlano(uso) {
  try {
    if (!uso) uso = await api.get('/empresa/uso');
    if (!uso) return;

    const card = document.getElementById('sidebar-plan-card');
    if (!card) return;
    card.style.display = 'block';

    // ── Orçamentos ──
    const orcText = document.getElementById('plan-orc-text');
    const orcBar  = document.getElementById('plan-orc-bar');
    if (uso.orcamentos_limite === null) {
      if (orcText) orcText.textContent = uso.orcamentos_usados + ' / ∞';
      if (orcBar)  orcBar.style.width = '20%';
    } else {
      const pct = uso.orcamentos_limite > 0
        ? Math.min(100, Math.round(uso.orcamentos_usados / uso.orcamentos_limite * 100))
        : 100;
      if (orcText) orcText.textContent = uso.orcamentos_usados + ' / ' + uso.orcamentos_limite;
      if (orcBar) {
        orcBar.style.width = pct + '%';
        orcBar.style.background = pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : 'var(--accent)';
      }
    }

    // ── Usuários ──
    const usrText = document.getElementById('plan-usr-text');
    const usrBar  = document.getElementById('plan-usr-bar');
    if (uso.usuarios_limite === null) {
      if (usrText) usrText.textContent = uso.usuarios_usados + ' / ∞';
      if (usrBar)  usrBar.style.width = '20%';
    } else {
      const pct = uso.usuarios_limite > 0
        ? Math.min(100, Math.round(uso.usuarios_usados / uso.usuarios_limite * 100))
        : 100;
      if (usrText) usrText.textContent = uso.usuarios_usados + ' / ' + uso.usuarios_limite;
      if (usrBar) {
        usrBar.style.width = pct + '%';
        usrBar.style.background = pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : '#3b82f6';
      }
    }

    // ── Validade / Trial ──
    const valEl = document.getElementById('plan-validade');
    if (valEl) {
      const data = uso.trial_ate || uso.assinatura_valida_ate;
      if (data) {
        const d = new Date(data);
        const label = uso.trial_ate ? 'Trial até' : 'Renova em';
        const hoje = new Date();
        const diff = Math.ceil((d - hoje) / 86400000);
        const fmt = d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
        valEl.style.display = 'block';
        valEl.style.color = diff <= 3 ? '#ef4444' : '#9ca3af';
        valEl.textContent = label + ' ' + fmt + (diff > 0 && diff <= 7 ? ' (' + diff + 'd)' : '');
      }
    }

    // ── Verificar Trial Expirado e Exibir Modal ──
    verificarTrialExpirado(uso);
  } catch (_) { /* silencia erros de uso */ }
}

// Verifica se o trial expirou e não há assinatura ativa
function verificarTrialExpirado(uso) {
  const usuario = getUsuario();
  
  // Não exibir modal para superadmins
  if (usuario && usuario.is_superadmin) {
    return;
  }

  const hoje = new Date();
  let trialExpirado = false;
  let semAssinaturaAtiva = true;

  // Verificar se trial_ate existe e está no passado
  if (uso.trial_ate) {
    const trialDate = new Date(uso.trial_ate);
    if (trialDate < hoje) {
      trialExpirado = true;
    }
  }

  // Verificar se há assinatura ativa
  if (uso.assinatura_valida_ate) {
    const assinaturaDate = new Date(uso.assinatura_valida_ate);
    if (assinaturaDate >= hoje) {
      semAssinaturaAtiva = false;
    }
  }

  // Se trial expirou E não há assinatura ativa, exibir modal
  if (trialExpirado && semAssinaturaAtiva) {
    exibirModalPlanos();
  }
}

// Exibe o modal de seleção de planos
function exibirModalPlanos() {
  let modal = document.getElementById('modal-planos');
  
  // Se o modal não existir, injetar no DOM
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'modal-planos';
    modal.className = 'modal-planos-overlay';
    modal.style.display = 'none';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'modal-planos-titulo');
    modal.innerHTML = `
      <div class="modal-planos-container">
        <div class="modal-planos-header">
          <div class="modal-planos-icon-wrap">
            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
            </svg>
          </div>
          <p class="modal-planos-subtitle-top">Período de teste encerrado</p>
          <h2 id="modal-planos-titulo">Continue crescendo com o COTTE</h2>
          <p>Escolha o plano ideal e volte a aproveitar todos os recursos</p>
        </div>
        
        <div class="modal-planos-grid">
          
          <!-- PLANO STARTER -->
          <div class="plano-card">
            <div class="plano-header">
              <div class="plano-nome">Starter</div>
              <div class="plano-preco">
                <span class="preco-valor">R$ 89,90</span>
                <span class="preco-periodo">/mês</span>
              </div>
              <div class="plano-desc">Para autônomos que querem enviar orçamentos rápido</div>
            </div>
            <div class="plano-features">
              <div class="feature-item">Até 200 orçamentos/mês</div>
              <div class="feature-item">3 usuários</div>
              <div class="feature-item">Envio por WhatsApp</div>
              <div class="feature-item">Lembretes automáticos</div>
              <div class="feature-item">Relatórios básicos</div>
            </div>
            <a href="https://pay.kiwify.com.br/mlUv9Ox" target="_blank" class="plano-btn">
              Escolher Starter
            </a>
          </div>

          <!-- PLANO PRO (RECOMENDADO) -->
          <div class="plano-card plano-destaque">
            <div class="plano-header">
              <div class="plano-badge">Mais escolhido</div>
              <div class="plano-nome">Pro</div>
              <div class="plano-preco">
                <span class="preco-valor">R$ 129</span>
                <span class="preco-periodo">/mês</span>
              </div>
              <div class="plano-desc">Para quem quer escalar sem contratar mais gente</div>
            </div>
            <div class="plano-features">
              <div class="feature-item">Até 1.000 orçamentos/mês</div>
              <div class="feature-item">10 usuários</div>
              <div class="feature-item">IA automática (Claude)</div>
              <div class="feature-item">Lembretes automáticos</div>
              <div class="feature-item">Relatórios avançados</div>
              <div class="feature-item">WhatsApp próprio</div>
            </div>
            <a href="https://pay.kiwify.com.br/GEEDagv" target="_blank" class="plano-btn plano-btn-destaque">
              Escolher Pro
            </a>
          </div>

          <!-- PLANO BUSINESS -->
          <div class="plano-card">
            <div class="plano-header">
              <div class="plano-nome">Business</div>
              <div class="plano-preco">
                <span class="preco-valor">R$ 189</span>
                <span class="preco-periodo">/mês</span>
              </div>
              <div class="plano-desc">Para empresas com equipe maior e alto volume</div>
            </div>
            <div class="plano-features">
              <div class="feature-item">Orçamentos ilimitados</div>
              <div class="feature-item">Usuários ilimitados</div>
              <div class="feature-item">Tudo do Pro</div>
              <div class="feature-item">Suporte prioritário</div>
              <div class="feature-item">Onboarding personalizado</div>
            </div>
            <a href="https://pay.kiwify.com.br/pA85TDN" target="_blank" class="plano-btn">
              Escolher Business
            </a>
          </div>

        </div>

        <div class="modal-planos-footer">
          <div class="footer-trust">
            <span class="trust-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              Pagamento seguro via Kiwify
            </span>
            <span class="trust-sep">·</span>
            <span class="trust-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
              Cancele quando quiser
            </span>
            <span class="trust-sep">·</span>
            <span class="trust-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              Sem fidelidade
            </span>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
  
  modal.style.display = 'flex';
}

// Salva usuario atualizado (chama /auth/me e persiste)
async function atualizarUsuarioLocal() {
  try {
    const u = await api.get('/auth/me');
    localStorage.setItem('cotte_usuario', JSON.stringify(u));
    return u;
  } catch(e) { return null; }
}

/**
 * ── GERENCIADOR DE PERMISSÕES (RBAC/Scopes) ─────────────────────────────
 * Lógica centralizada para controle de acesso no frontend.
 * Recursos: 'catalogo', 'financeiro', 'clientes', 'orcamentos', 'equipe'.
 * Níveis: 'leitura' (1), 'escrita' (2), 'admin' (3).
 */
window.Permissoes = {
  pode: function(recurso, acao = 'leitura') {
    const u = getUsuario();
    if (!u) return false;
    
    // Superadmin e Gestor sempre podem tudo
    if (u.is_superadmin || u.is_gestor) return true;
    
    // Verificação no novo campo JSON 'permissoes'
    const perms = u.permissoes || {};
    let userAcao = perms[recurso]; // ex: 'escrita'
    
    if (!userAcao) return false;

    
    // 'meus' (1.5) permite leitura, bloqueia escrita — espelha o backend
    const niveis = { 'leitura': 1, 'meus': 1.5, 'escrita': 2, 'admin': 3 };
    const nivelExigido = niveis[acao] || 1;
    const nivelUsuario  = niveis[userAcao] || 0;
    
    return nivelUsuario >= nivelExigido;
  },
  
  // Helper para esconder elementos sem permissão
  protegerUI: function(seletor, recurso, acao = 'leitura') {
    if (!this.pode(recurso, acao)) {
      document.querySelectorAll(seletor).forEach(el => el.style.display = 'none');
    }
  }
};

// ── UTILITÁRIOS ──────────────────────────────────────────────────────────
// Funções utilitárias movidas para js/utils.js (carregado antes de api.js).
// Mantidas aqui como comentário de referência:
// escapeHtml, escapeHtmlWithBreaks, safeClass, formatarMoeda, formatarData,
// diasRestantes, iniciaisDe, corAvatar — todas já definidas em utils.js.

function showNotif(icon, title, sub, type = 'success') {
  const n = document.getElementById('notif');
  if (!n) return;
  n.querySelector('.notif-icon').textContent = icon;
  n.querySelector('.notif-title').textContent = title;
  n.querySelector('.notif-sub').textContent = sub;
  n.style.borderColor = type === 'error' ? 'rgba(239,68,68,0.3)' : 'rgba(0,229,160,0.3)';
  n.classList.add('show');
  setTimeout(() => n.classList.remove('show'), 3500);
}

/**
 * Abre a tela de detalhes de um orçamento a partir de uma linha clicável.
 * - Em páginas que possuem `abrirDetalhesOrcamento` (ex: orcamentos.html), usa o modal de detalhes.
 * - Nas demais páginas (ex: dashboard), navega para `orcamento-view.html?id={id}`.
 */
function handleOrcamentoRowClick(event, id) {
  if (!id) return;
  // Garante que futuros elementos internos que não chamem stopPropagation
  // ainda possam bloquear o clique da linha se precisarem.
  if (event && event.defaultPrevented) return;

  if (typeof abrirDetalhesOrcamento === 'function') {
    abrirDetalhesOrcamento(id);
  } else {
    const url = 'orcamento-view.html?id=' + encodeURIComponent(id);
    if (event && (event.ctrlKey || event.metaKey || event.button === 1)) {
      window.open(url, '_blank');
    } else {
      window.location.href = url;
    }
  }
}

function setLoading(btn, loading, textoFinal) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.original = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px;margin-right:6px"></span> Aguarde...';
  } else {
    btn.disabled = false;
    btn.textContent = textoFinal || btn.dataset.original || 'Salvar';
  }
}

// ── DADOS SIMULADOS PARA IA ─────────────────────────────────────────────
function mockAIResponse(endpoint, body) {
  // Simular um atraso de rede
  return new Promise(resolve => {
    setTimeout(() => {
      let response;
      
      if (endpoint.includes('/financeiro/')) {
        response = {
          sucesso: true,
          dados: {
            resumo: "Análise financeira simulada",
            kpi_principal: {
              nome: "Saldo Disponível",
              valor: 12500.75,
              comparacao: "Crescimento de 12% em relação ao mês anterior"
            },
            taxa_conversao: 0.65,
            orcamentos_enviados: 45,
            orcamentos_aprovados: 29,
            ticket_medio: 850.50,
            servico_mais_vendido: "Pintura Residencial",
            insights: [
              "Maior receita no período da tarde",
              "Cliente João Silva é o mais lucrativo",
              "Aumento de 15% em serviços de manutenção"
            ]
          }
        };
      } else if (endpoint.includes('/conversao/')) {
        response = {
          sucesso: true,
          dados: {
            resumo: "Análise de conversão simulada",
            taxa_conversao: 0.72,
            orcamentos_enviados: 38,
            orcamentos_aprovados: 27,
            ticket_medio: 920.00,
            servico_mais_vendido: "Instalação Elétrica",
            insights: [
              "Taxa de conversão acima da média do setor",
              "WhatsApp é o canal mais eficiente",
              "Orçamentos com fotos têm 40% mais aprovação"
            ]
          }
        };
      } else if (endpoint.includes('/negocio/')) {
        response = {
          sucesso: true,
          dados: {
            resumo: "Sugestões de negócio simuladas",
            sugestao: "Aumente seu ticket médio oferecendo pacotes de serviços",
            tipo_sugestao: "vendas",
            justificativa: "Clientes que compram pacotes têm 30% mais retenção",
            impacto_estimado: "Aumento de R$ 2.500/mês em receita",
            acao_imediata: "Crie 3 pacotes de serviços e ofereça na próxima proposta",
            insights: [
              "Pacote 'Manutenção Completa' tem maior aceitação",
              "Clientes empresariais preferem contratos mensais",
              "Oferecer garantia estendida aumenta conversão em 25%"
            ]
          }
        };
      } else {
        // Resposta genérica para outros endpoints
        response = {
          sucesso: true,
          dados: {
            resumo: "Resposta simulada do assistente COTTE",
            mensagem: "Estou em modo de demonstração. Quando o servidor estiver disponível, poderei fornecer análises em tempo real.",
            insights: [
              "Sistema em modo de demonstração",
              "Os dados apresentados são simulados",
              "Funcionalidades principais estão disponíveis no menu lateral"
            ]
          }
        };
      }
      
      resolve(response);
    }, 800); // Simular atraso de rede
  });
}

// ── TESTAR CONEXÃO COM API ──────────────────────────────────────────────
async function testarConexaoAPI() {
  // Tentar vários endpoints públicos
  const endpoints = ['/api/v1/health', '/health', '/docs', '/openapi.json'];
  
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(finalizeFetchUrlForMixedContent(buildAbsoluteAppUrl(endpoint)), { 
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(3000)
      });
      if (response.ok) {
        console.log(`Conexão com API OK via ${endpoint}`);
        API_DISPONIVEL = true;
        return true;
      }
    } catch (error) {
      // Continuar para o próximo endpoint
      console.warn(`Não foi possível conectar a ${endpoint}:`, error);
    }
  }
  
  console.warn('Não foi possível conectar à API via nenhum endpoint público');
  API_DISPONIVEL = false;
  return false;
}

// Expor função globalmente
if (typeof window !== 'undefined') {
  window.API_PREFIX = API_PREFIX;
  window.testarConexaoAPI = testarConexaoAPI;
}

// Teste de conectividade: páginas já autenticadas não precisam do ping (evita concorrência no load).
// Sem token, agenda após idle (ou fallback por timeout).
function agendarTesteConexaoAposIdle() {
  const executar = () => {
    testarConexaoAPI();
  };
  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(() => executar(), { timeout: 30000 });
  } else {
    setTimeout(executar, 5000);
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    if (getToken()) return;
    agendarTesteConexaoAposIdle();
  });
}

// ── EXPORTAR CSV (download com auth) ─────────────────────────────────────
function baixarExportar(endpoint, filename) {
  const token = getToken();
  if (!token) return;
  fetch(finalizeFetchUrlForMixedContent(buildApiRequestUrl(endpoint)), { headers: { 'Authorization': 'Bearer ' + token } })
    .then(r => { if (!r.ok) throw new Error('Erro ao exportar'); return r.blob(); })
    .then(blob => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename || 'exportacao.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch(() => { if (typeof showNotif === 'function') showNotif('❌', 'Erro ao exportar', '', 'error'); });
}

// ── NOTIFICAÇÕES ──────────────────────────────────────────────────────────
let _notifDropdownAberto = null;

async function preencherNotificacoes() {
  const el = document.getElementById('topbar-notificacoes');
  if (!el) return;
  try {
    const r = await api.get('/notificacoes/contagem-nao-lidas');
    const count = r.contagem || 0;
    el.innerHTML = count > 0
      ? `<button type="button" onclick="abrirDropdownNotificacoes(event)" style="position:relative;display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border:none;border-radius:10px;background:var(--surface2);color:var(--text);cursor:pointer;font-size:16px">🔔<span style="position:absolute;top:2px;right:2px;background:#ef4444;color:#fff;font-size:10px;min-width:16px;height:16px;border-radius:8px;display:flex;align-items:center;justify-content:center">${count > 99 ? '99+' : count}</span></button>`
      : `<button type="button" onclick="abrirDropdownNotificacoes(event)" style="display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border:none;border-radius:10px;background:var(--surface2);color:var(--muted);cursor:pointer;font-size:16px">🔔</button>`;
  } catch (_) { el.innerHTML = ''; }
}

async function abrirDropdownNotificacoes(ev) {
  if (_notifDropdownAberto) { _notifDropdownAberto.remove(); _notifDropdownAberto = null; return; }
  const btn = ev.currentTarget;
  const rect = btn.getBoundingClientRect();
  const div = document.createElement('div');
  div.id = 'dropdown-notificacoes';

  // Calcular posição do dropdown garantindo que fica sempre visível
  const dropdownWidth = 320;
  const minMargin = 8;
  let left = rect.right - dropdownWidth; // tenta alinhar à direita do botão

  // Se não couber à direita, tenta à esquerda
  if (left + dropdownWidth > window.innerWidth - minMargin) {
    left = rect.left - dropdownWidth;
  }

  // Se ainda assim não couber, garante margem mínima
  left = Math.max(minMargin, Math.min(left, window.innerWidth - dropdownWidth - minMargin));

  div.style.cssText = 'position:fixed;top:' + (rect.bottom + 6) + 'px;left:' + left + 'px;width:320px;max-height:360px;background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.2);z-index:9999;overflow:hidden;display:flex;flex-direction:column';
  div.innerHTML = '<div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px">Notificações</div><div id="dropdown-notif-list" style="overflow-y:auto;flex:1;padding:8px"><div class="loading"><div class="spinner"></div></div></div><button type="button" id="dropdown-notif-marcar-todas" style="padding:10px 16px;border:none;border-top:1px solid var(--border);background:transparent;color:var(--muted);font-size:12px;cursor:pointer;text-align:center">Marcar todas como lidas</button>';
  document.body.appendChild(div);
  _notifDropdownAberto = div;

  const fechar = () => { div.remove(); _notifDropdownAberto = null; document.removeEventListener('click', fecharFora); };
  const fecharFora = (e) => { if (!div.contains(e.target) && e.target !== btn) fechar(); };
  setTimeout(() => document.addEventListener('click', fecharFora), 100);

  try {
    const lista = await api.get('/notificacoes/?limit=15');
    const listEl = document.getElementById('dropdown-notif-list');
    if (!lista || lista.length === 0) {
      listEl.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Nenhuma notificação</div>';
    } else {
      listEl.innerHTML = lista.map(n => `
        <div style="padding:10px 12px;border-radius:8px;margin-bottom:4px;background:${n.lida ? 'transparent' : 'rgba(0,229,160,0.06)'};border-left:3px solid ${n.lida ? 'transparent' : 'var(--green)'}">
          <div style="font-weight:600;font-size:12px">${escapeHtml(n.titulo || '')}</div>
          <div style="font-size:11px;color:var(--muted);margin-top:2px">${escapeHtml(n.mensagem || '')}</div>
          <div style="font-size:10px;color:var(--muted);margin-top:4px">${n.criado_em ? new Date(n.criado_em).toLocaleString('pt-BR') : ''}</div>
        </div>
      `).join('');
    }
    document.getElementById('dropdown-notif-marcar-todas').onclick = async () => {
      await api.patch('/notificacoes/marcar-todas-lidas');
      preencherNotificacoes();
      fechar();
    };
  } catch (_) {
    document.getElementById('dropdown-notif-list').innerHTML = '<div style="padding:16px;color:#ef4444;font-size:12px">Erro ao carregar</div>';
  }
}

// ── TOGGLE DE TEMA ───────────────────────────────────────────────────────
function toggleTema() {
  const html    = document.documentElement;
  const isDark  = html.getAttribute('data-theme') === 'dark';
  const novoTema = isDark ? 'light' : 'dark';

  html.setAttribute('data-theme', novoTema);
  localStorage.setItem('cotte_tema', novoTema);

  // Atualiza ícone do botão em qualquer página
  sincronizarBtnTema();

  // Dispara evento para páginas que precisam atualizar gráficos etc.
  document.dispatchEvent(new CustomEvent('cotte:tema', { detail: { tema: novoTema } }));
}

function sincronizarBtnTema() {
  const tema = document.documentElement.getAttribute('data-theme') || 'light';
  const icone = tema === 'dark' ? '☀️' : '🌙';
  const label = tema === 'dark' ? 'Tema claro' : 'Tema escuro';
  document.querySelectorAll('.btn-tema').forEach(function(btn) {
    btn.innerHTML  = icone;
    btn.setAttribute('data-label', label);
    btn.title      = label;
  });
}

// ── INJETA BOTÃO DE TEMA NO RODAPÉ DA SIDEBAR ────────────────────────────
(function() {
  const footer = document.querySelector('.sidebar-footer');
  if (!footer) return;

  const btn = document.createElement('button');
  btn.className = 'btn-tema';
  btn.setAttribute('aria-label', 'Alternar tema');
  btn.addEventListener('click', function() { toggleTema(); });

  // Insere antes do user-card
  const userCard = footer.querySelector('.user-card');
  if (userCard) {
    footer.insertBefore(btn, userCard);
  } else {
    footer.appendChild(btn);
  }
  sincronizarBtnTema();
})();

// ── MENU MOBILE (hambúrguer) ──────────────────────────────────────────────
(function() {
  const sidebar = document.querySelector('.sidebar');
  const topbar  = document.querySelector('.topbar');
  if (!sidebar || !topbar) return;

  // Overlay escurece o fundo ao abrir o menu
  const overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  overlay.addEventListener('click', fecharMenu);
  document.body.appendChild(overlay);

  // Botão hambúrguer inserido no início do topbar
  const btn = document.createElement('button');
  btn.className = 'btn-hamburger';
  btn.setAttribute('aria-label', 'Abrir menu');
  btn.innerHTML = '&#9776;';
  btn.addEventListener('click', function() {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('open');
  });
  topbar.insertBefore(btn, topbar.firstChild);

  // Fecha o menu ao clicar em qualquer link da sidebar (mobile)
  sidebar.querySelectorAll('a.nav-item').forEach(function(link) {
    link.addEventListener('click', fecharMenu);
  });

  function fecharMenu() {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  }
})();
