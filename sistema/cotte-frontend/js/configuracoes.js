// ── BUSCA INTELIGENTE ──────────────────────────────────────────────────────
let searchTimeout;
let searchIndex = [];
let selectedSearchIndex = -1;

// Inicializar busca
function initBuscaInteligente() {
  const searchInput = document.getElementById('cfg-search-input');
  const dropdown = document.getElementById('cfg-search-dropdown');
  
  if (!searchInput || !dropdown) {
    return;
  }
  
  // Criar índice de busca
  criarIndiceBusca();
  
  // Event listeners
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => realizarBusca(e.target.value), 300);
  });
  
  searchInput.addEventListener('focus', () => {
    if (searchInput.value.trim()) {
      realizarBusca(searchInput.value);
    }
  });
  
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      navegarResultado(1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      navegarResultado(-1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      selecionarResultado();
    } else if (e.key === 'Escape') {
      limparBusca();
    }
  });
  
  // Fechar dropdown ao clicar fora
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.cfg-search-wrap')) {
      dropdown.classList.remove('active');
    }
  });
}

// Criar índice de busca
function criarIndiceBusca() {
  searchIndex = [];
  
  // Indexar seções da navegação
  document.querySelectorAll('.cfg-nav-item[data-secao]').forEach(item => {
    const secao = item.dataset.secao;
    const title = item.textContent.trim();
    const searchTerms = item.dataset.searchTerms || '';
    
    searchIndex.push({
      type: 'section',
      id: secao,
      title: title,
      searchTerms: searchTerms,
      element: item,
      sectionName: getSectionGroupName(item)
    });
  });
  
  // Indexar cards de configuração
  document.querySelectorAll('.cfg-card').forEach(card => {
    const title = card.querySelector('.cfg-card-title')?.textContent || '';
    const subtitle = card.querySelector('.cfg-card-subtitle')?.textContent || '';
    const searchTerms = card.dataset.searchTerms || gerarSearchTerms(title + ' ' + subtitle);
    const section = card.closest('.cfg-section');
    const sectionId = section ? section.id.replace('sec-', '') : '';
    
    searchIndex.push({
      type: 'card',
      id: sectionId,
      title: title,
      subtitle: subtitle,
      searchTerms: searchTerms,
      element: card,
      sectionName: getSectionTitle(sectionId)
    });
  });
  
  // Indexar campos de formulário
  document.querySelectorAll('.cfg-form-group').forEach(group => {
    const label = group.querySelector('label')?.textContent || '';
    const hint = group.querySelector('.cfg-field-hint')?.textContent || '';
    const searchTerms = group.dataset.searchTerms || gerarSearchTerms(label + ' ' + hint);
    const section = group.closest('.cfg-section');
    const sectionId = section ? section.id.replace('sec-', '') : '';
    const card = group.closest('.cfg-card');
    const cardTitle = card ? card.querySelector('.cfg-card-title')?.textContent || '' : '';
    
    searchIndex.push({
      type: 'field',
      id: sectionId,
      title: label,
      subtitle: hint,
      cardTitle: cardTitle,
      searchTerms: searchTerms,
      element: group,
      sectionName: getSectionTitle(sectionId)
    });
  });
  
  // Indexar campos inline
  document.querySelectorAll('.cfg-inline-row').forEach(row => {
    const title = row.querySelector('.cfg-inline-title')?.textContent || '';
    const subtitle = row.querySelector('.cfg-inline-sub')?.textContent || '';
    const searchTerms = row.dataset.searchTerms || gerarSearchTerms(title + ' ' + subtitle);
    const section = row.closest('.cfg-section');
    const sectionId = section ? section.id.replace('sec-', '') : '';
    const card = row.closest('.cfg-card');
    const cardTitle = card ? card.querySelector('.cfg-card-title')?.textContent || '' : '';
    
    searchIndex.push({
      type: 'field',
      id: sectionId,
      title: title,
      subtitle: subtitle,
      cardTitle: cardTitle,
      searchTerms: searchTerms,
      element: row,
      sectionName: getSectionTitle(sectionId)
    });
  });
}

// Gerar termos de busca automaticamente
function gerarSearchTerms(texto) {
  if (!texto) return '';
  
  // Converter para minúsculas e remover acentos
  const normalized = texto.toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
  
  // Extrair palavras-chave
  const palavras = normalized
    .split(/\s+/)
    .filter(p => p.length > 2)
    .filter(p => !['para', 'com', 'sem', 'mais', 'menos', 'todo', 'toda', 'todos', 'todas'].includes(p));
  
  // Adicionar sinônimos comuns
  const sinonimos = {
    'email': ['e-mail', 'correio'],
    'whatsapp': ['zap', 'whats', 'mensagem'],
    'telefone': ['fone', 'celular', 'contato'],
    'desconto': ['descontos'],
    'validade': ['prazo', 'expira'],
    'assinatura': ['rubrica', 'firma'],
    'proposta': ['orçamento', 'orcamento'],
    'agendamento': ['agenda', 'marcar', 'horario'],
    'pagamento': ['pagar', 'parcela', 'cobrança'],
    'logo': ['marca', 'imagem', 'icone']
  };
  
  // Adicionar sinônimos
  palavras.forEach(palavra => {
    if (sinonimos[palavra]) {
      palavras.push(...sinonimos[palavra]);
    }
  });
  
  // Remover duplicados e juntar
  return [...new Set(palavras)].join(' ');
}

// Obter nome do grupo da seção
function getSectionGroupName(item) {
  const prevLabel = item.previousElementSibling;
  if (prevLabel && prevLabel.classList.contains('cfg-nav-group-label')) {
    return prevLabel.textContent;
  }
  return 'Outros';
}

// Obter título da seção
function getSectionTitle(sectionId) {
  const section = document.getElementById('sec-' + sectionId);
  if (section) {
    const titleEl = section.querySelector('.cfg-section-title');
    return titleEl ? titleEl.textContent : sectionId;
  }
  return sectionId;
}

// Realizar busca
function realizarBusca(query) {
  const dropdown = document.getElementById('cfg-search-dropdown');
  
  if (!query.trim()) {
    dropdown.classList.remove('active');
    return;
  }
  
  const normalizedQuery = query.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const results = [];
  
  // Buscar no índice com score de relevância
  searchIndex.forEach(item => {
    const searchText = `${item.title} ${item.subtitle || ''} ${item.cardTitle || ''} ${item.searchTerms}`;
    const normalizedText = searchText.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    
    // Calcular score de relevância
    let score = 0;
    
    // Correspondência exata no título
    if (item.title.toLowerCase() === query.toLowerCase()) {
      score = 100;
    }
    // Correspondência exata parcial no título
    else if (item.title.toLowerCase().includes(query.toLowerCase())) {
      score = 80;
    }
    // Correspondência exata nos termos de busca
    else if (item.searchTerms.toLowerCase().includes(query.toLowerCase())) {
      score = 60;
    }
    // Correspondência normalizada no título
    else if (normalizedText.includes(normalizedQuery)) {
      score = 40;
    }
    
    if (score > 0) {
      results.push({ ...item, score });
    }
  });
  
  // Ordenar por score (maior primeiro)
  results.sort((a, b) => b.score - a.score);
  
  // Agrupar resultados por seção
  const groupedResults = {};
  results.forEach(result => {
    if (!groupedResults[result.sectionName]) {
      groupedResults[result.sectionName] = [];
    }
    groupedResults[result.sectionName].push(result);
  });
  
  // Renderizar resultados
  renderizarResultados(groupedResults, query);
}

// Renderizar resultados da busca
function renderizarResultados(groupedResults, query) {
  const dropdown = document.getElementById('cfg-search-dropdown');
  selectedSearchIndex = -1;
  
  if (Object.keys(groupedResults).length === 0) {
    dropdown.innerHTML = `
      <div class="cfg-search-group">
        <div class="cfg-search-item" style="color:var(--muted);justify-content:center">
          Nenhum resultado encontrado para "${query}"
        </div>
      </div>
    `;
    dropdown.classList.add('active');
    return;
  }
  
  let html = '';
  
  Object.entries(groupedResults).forEach(([sectionName, items]) => {
    html += `
      <div class="cfg-search-group">
        <div class="cfg-search-group-title">${sectionName}</div>
    `;
    
    items.forEach((item, index) => {
      const icon = getItemIcon(item);
      const highlightedTitle = highlightText(item.title, query);
      const subtitle = item.subtitle ? `<small style="color:var(--muted)">${highlightText(item.subtitle, query)}</small>` : '';
      const cardTitle = item.cardTitle ? `<small style="color:var(--muted2)">em ${highlightText(item.cardTitle, query)}</small>` : '';
      
      html += `
        <div class="cfg-search-item" data-index="${selectedSearchIndex + index + 1}" data-section="${item.id}" data-element="${item.type}" data-title="${item.title.replace(/"/g, '&quot;')}" onclick="navegarParaResultado('${item.id}', '${item.type}', this.dataset.title)">
          <div class="cfg-search-item-icon">${icon}</div>
          <div class="cfg-search-item-text">
            ${highlightedTitle}
            ${subtitle}
            ${cardTitle}
          </div>
        </div>
      `;
    });
    
    selectedSearchIndex += items.length;
    html += '</div>';
  });
  
  dropdown.innerHTML = html;
  dropdown.classList.add('active');
  dropdown.style.display = 'block';
  dropdown.style.visibility = 'visible';
  dropdown.style.opacity = '1';
  dropdown.style.zIndex = '9999';
}

// Obter ícone para tipo de item
function getItemIcon(item) {
  if (item.type === 'section') {
    return '📁';
  } else if (item.type === 'card') {
    return '📋';
  } else if (item.type === 'field') {
    return '⚙️';
  }
  return '📄';
}

// Destacar texto no resultado
function highlightText(text, query) {
  if (!text || !query) return text;
  
  const regex = new RegExp(`(${query})`, 'gi');
  return text.replace(regex, '<span class="cfg-search-highlight">$1</span>');
}

// Navegar para resultado selecionado
function navegarParaResultado(sectionId, elementType, elementTitle) {
  const dropdown = document.getElementById('cfg-search-dropdown');
  dropdown.classList.remove('active');
  dropdown.style.background = ''; // Remove fundo vermelho
  
  // Mudar para seção
  irSecao(sectionId);
  
  // Encontrar e destacar elemento
  setTimeout(() => {
    let targetElement;
    
    if (elementType === 'section') {
      // Seção já está ativa
      targetElement = document.querySelector('.cfg-section.active');
    } else {
      // Encontrar elemento específico pelo título
      const section = document.getElementById('sec-' + sectionId);
      if (section) {
        if (elementType === 'card') {
          targetElement = Array.from(section.querySelectorAll('.cfg-card')).find(card => {
            const title = card.querySelector('.cfg-card-title')?.textContent || '';
            return title.trim() === elementTitle;
          });
        } else if (elementType === 'field') {
          // Tentar cfg-form-group primeiro
          targetElement = Array.from(section.querySelectorAll('.cfg-form-group')).find(group => {
            const label = group.querySelector('label')?.textContent || '';
            return label.trim() === elementTitle;
          });
          
          // Se não encontrar, tentar cfg-inline-row
          if (!targetElement) {
            targetElement = Array.from(section.querySelectorAll('.cfg-inline-row')).find(row => {
              const title = row.querySelector('.cfg-inline-title')?.textContent || '';
              return title.trim() === elementTitle;
            });
          }
        }
      }
    }
    
    if (targetElement) {
      // Scroll suave até elemento
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Adicionar destaque visual
      targetElement.classList.add('cfg-search-target-highlight');
      setTimeout(() => {
        targetElement.classList.remove('cfg-search-target-highlight');
      }, 2000);
    }
  }, 100);
  
  // Limpar busca
  limparBusca();
}

// Navegar pelos resultados com setas
function navegarResultado(direction) {
  const items = document.querySelectorAll('.cfg-search-item[data-index]');
  if (items.length === 0) return;
  
  // Remover seleção atual
  items.forEach(item => item.classList.remove('active'));
  
  // Calcular novo índice
  selectedSearchIndex += direction;
  if (selectedSearchIndex < 0) selectedSearchIndex = items.length - 1;
  if (selectedSearchIndex >= items.length) selectedSearchIndex = 0;
  
  // Selecionar novo item
  items[selectedSearchIndex].classList.add('active');
  items[selectedSearchIndex].scrollIntoView({ block: 'nearest' });
}

// Selecionar resultado com Enter
function selecionarResultado() {
  const activeItem = document.querySelector('.cfg-search-item.active[data-index]');
  if (activeItem) {
    activeItem.click();
  }
}

// Limpar busca
function limparBusca() {
  const searchInput = document.getElementById('cfg-search-input');
  const dropdown = document.getElementById('cfg-search-dropdown');
  
  searchInput.value = '';
  dropdown.classList.remove('active');
  selectedSearchIndex = -1;
}

// Inicializar busca ao carregar página
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBuscaInteligente);
} else {
  initBuscaInteligente();
}

/**
 * configuracoes.js — JavaScript da página configuracoes.html
 * Extraído do inline para arquivo separado.
 */

/* global api, apiRequest, getToken, API_URL, setLoading, showNotif, Financeiro */

inicializarLayout('configuracoes');

// Papéis: só gestor/superadmin (API exige o mesmo em /papeis)
(function ajustarNavPapeisConfiguracoes() {
  const link = document.getElementById('cfg-nav-papeis');
  const grp = document.getElementById('cfg-nav-group-papeis');
  if (!link) return;
  const u = typeof getUsuario === 'function' ? getUsuario() : null;
  const pode = u && (u.is_gestor || u.is_superadmin);
  if (!pode) {
    link.remove();
    if (grp) grp.remove();
  }
})();

// ── NAVEGAÇÃO INTERNA ─────────────────────────────────────────────────
function irSecao(id) {
  document.querySelectorAll('.cfg-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.cfg-nav-item').forEach(n => n.classList.remove('active'));

  const sec = document.getElementById('sec-' + id);
  if (sec) sec.classList.add('active');

  const navItem = document.querySelector('[data-secao="' + id + '"]');
  if (navItem) navItem.classList.add('active');

  if (window.innerWidth <= 768) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Carrega dados sob demanda por seção
  if (id === 'formas-pagamento') carregarFormasPagamento();
  if (id === 'cfg-financeiro') carregarConfiguracaoFinanceira();
  if (id === 'catalogo-modelos') cfgCarregarSegmentos();
}

// ── TEMA ──────────────────────────────────────────────────────────────
function definirTema(tema) {
  document.documentElement.setAttribute('data-theme', tema);
  localStorage.setItem('cotte_tema', tema);
  atualizarVisualizacaoTema(tema);
  if (typeof atualizarBtnTema === 'function') atualizarBtnTema();
}

function atualizarVisualizacaoTema(tema) {
  const isLight = (tema !== 'dark');
  const cardLight = document.getElementById('tema-card-light');
  const cardDark  = document.getElementById('tema-card-dark');
  const checkLight = document.getElementById('tema-check-light');
  const checkDark  = document.getElementById('tema-check-dark');

  if (!cardLight || !cardDark) return;

  if (isLight) {
    cardLight.style.borderColor = 'var(--accent)';
    cardLight.style.background  = 'var(--accent-dim)';
    checkLight.style.background = 'var(--accent)';
    checkLight.innerHTML = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
    cardDark.style.borderColor  = 'var(--border)';
    cardDark.style.background   = '';
    checkDark.style.background  = 'var(--border)';
    checkDark.innerHTML = '';
  } else {
    cardDark.style.borderColor  = 'var(--accent)';
    cardDark.style.background   = 'var(--accent-dim)';
    checkDark.style.background  = 'var(--accent)';
    checkDark.innerHTML = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
    cardLight.style.borderColor = 'var(--border)';
    cardLight.style.background  = '';
    checkLight.style.background = 'var(--border)';
    checkLight.innerHTML = '';
  }
}

function toggleTema() {
  const atual = document.documentElement.getAttribute('data-theme');
  definirTema(atual === 'dark' ? 'light' : 'dark');
}

function atualizarBtnTema() {
  const btn = document.getElementById('btn-tema');
  if (!btn) return;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  btn.setAttribute('data-label', isDark ? 'Tema claro' : 'Tema escuro');
  btn.querySelector('svg').innerHTML = isDark
    ? '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
    : '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
}

function _normalizarModoAgendamento(valor) {
  const v = (valor || '').toString().trim().toUpperCase().replace(/-/g, '_');
  const modos = ['NAO_USA', 'OPCIONAL', 'OBRIGATORIO'];
  return modos.includes(v) ? v : 'NAO_USA';
}

/** Converte política salva na empresa para valor do select de configurações. */
function _empresaParaPoliticaAgendamentoSelect(emp) {
  if (emp && emp.agendamento_escolha_obrigatoria === true) return 'EXIGE_ESCOLHA';
  const m = _normalizarModoAgendamento(emp && emp.agendamento_modo_padrao);
  if (m === 'OBRIGATORIO') return 'PADRAO_OBRIGATORIO';
  if (m === 'OPCIONAL') return 'PADRAO_SIM';
  return 'PADRAO_NAO';
}

/** Payload PATCH /empresa/ a partir do select de política. */
function _politicaAgendamentoSelectParaPayload(valorSelect) {
  const v = (valorSelect || '').toString().trim().toUpperCase();
  switch (v) {
    case 'PADRAO_SIM':
      return { agendamento_escolha_obrigatoria: false, agendamento_modo_padrao: 'OPCIONAL' };
    case 'EXIGE_ESCOLHA':
      return { agendamento_escolha_obrigatoria: true, agendamento_modo_padrao: 'NAO_USA' };
    case 'PADRAO_OBRIGATORIO':
      return { agendamento_escolha_obrigatoria: false, agendamento_modo_padrao: 'OBRIGATORIO' };
    case 'PADRAO_NAO':
    default:
      return { agendamento_escolha_obrigatoria: false, agendamento_modo_padrao: 'NAO_USA' };
  }
}

// ── CARREGAR DADOS ────────────────────────────────────────────────────
async function carregarEmpresa() {
  try {
    const emp = await api.get('/empresa/');
    document.getElementById('emp-nome').value     = emp.nome     || '';
    document.getElementById('emp-telefone').value = emp.telefone || '';
    document.getElementById('emp-email').value    = emp.email    || '';
    const cor = emp.cor_primaria || '#00e5a0';
    document.getElementById('emp-cor').value     = cor;
    document.getElementById('emp-cor-hex').value = cor;

    document.getElementById('emp-validade').value       = emp.validade_padrao_dias != null ? emp.validade_padrao_dias : 7;
    const descMaxEl = document.getElementById('emp-desconto-max');
    if (descMaxEl) descMaxEl.value = emp.desconto_max_percent != null ? emp.desconto_max_percent : 100;
    const agPoliticaEl = document.getElementById('emp-politica-agendamento-orc');
    if (agPoliticaEl) {
      agPoliticaEl.value = _empresaParaPoliticaAgendamentoSelect(emp);
    }
    const agAutoEl = document.getElementById('emp-utilizar-agendamento-auto');
    if (agAutoEl) {
      agAutoEl.value = emp.utilizar_agendamento_automatico === false ? 'false' : 'true';
    }
    const agSomenteLib = document.getElementById('emp-agendamento-somente-pos-liberacao');
    if (agSomenteLib) {
      agSomenteLib.value = emp.agendamento_opcoes_somente_apos_liberacao === true ? 'true' : 'false';
    }
    document.getElementById('emp-lembrete').value       = emp.lembrete_dias != null ? emp.lembrete_dias : '';
    document.getElementById('emp-lembrete-texto').value = emp.lembrete_texto || '';

    // Numeração personalizável
    const prefixoEl = document.getElementById('emp-numero-prefixo');
    const incluirAnoEl = document.getElementById('emp-numero-incluir-ano');
    const prefixoApEl = document.getElementById('emp-numero-prefixo-aprovado');
    if (prefixoEl) prefixoEl.value = emp.numero_prefixo || 'ORC';
    if (incluirAnoEl) incluirAnoEl.checked = emp.numero_incluir_ano !== false;
    if (prefixoApEl) prefixoApEl.value = emp.numero_prefixo_aprovado || '';
    atualizarPreviewNumero();

    // Template único (Web + PDF)
    const tplOrcamento = emp.template_orcamento || 'classico';
    _templateSelecionado = tplOrcamento;
    selecionarTemplate(tplOrcamento);

    const notifWhatsVis = document.getElementById('notif-whats-visualizacao');
    if (notifWhatsVis) notifWhatsVis.checked = (emp.notif_whats_visualizacao ?? true);

    const anexarPdf = document.getElementById('anexar-pdf-email');
    if (anexarPdf) anexarPdf.checked = (emp.anexar_pdf_email ?? false);

    const anexarPdfWa = document.getElementById('enviar-pdf-whatsapp');
    if (anexarPdfWa) anexarPdfWa.checked = (emp.enviar_pdf_whatsapp ?? false);

    // Mensagem de boas-vindas
    const boasAtivoEl = document.getElementById('boas-vindas-ativo');
    const boasTextoEl = document.getElementById('msg-boas-vindas');
    if (boasAtivoEl) boasAtivoEl.checked = (emp.boas_vindas_ativo ?? true);
    if (boasTextoEl) boasTextoEl.value   = emp.msg_boas_vindas || '';

    // Comunicação com o cliente
    const descPub = document.getElementById('descricao-publica-empresa');
    const txtAssin = document.getElementById('texto-assinatura-proposta');
    const telOp = document.getElementById('telefone-operador');
    const mostrarWa = document.getElementById('mostrar-botao-whatsapp');
    const txtAviso = document.getElementById('texto-aviso-aceite');
    const msgConf = document.getElementById('mensagem-confianca-proposta');
    const mostrarConf = document.getElementById('mostrar-mensagem-confianca');
    if (descPub) descPub.value = emp.descricao_publica_empresa || '';
    if (txtAssin) txtAssin.value = emp.texto_assinatura_proposta || '';
    const assinaturaEmailEl = document.getElementById('assinatura-email');
    if (assinaturaEmailEl) assinaturaEmailEl.value = emp.assinatura_email || '';
    if (telOp) telOp.value = emp.telefone_operador || '';
    if (mostrarWa) mostrarWa.checked = (emp.mostrar_botao_whatsapp !== false);
    if (txtAviso) txtAviso.value = emp.texto_aviso_aceite ?? txtAviso.placeholder ?? '';
    if (msgConf) msgConf.value = emp.mensagem_confianca_proposta ?? msgConf.placeholder ?? '';
    if (mostrarConf) mostrarConf.checked = (emp.mostrar_mensagem_confianca !== false);

    const exigirOtp = document.getElementById('exigir-otp-aceite');
    const otpMinEl = document.getElementById('otp-valor-minimo');
    const wrapOtpMin = document.getElementById('wrap-otp-minimo');
    
    if (exigirOtp) {
      exigirOtp.checked = !!emp.exigir_otp_aceite;
      if (wrapOtpMin) wrapOtpMin.style.display = exigirOtp.checked ? 'flex' : 'none';
      
      exigirOtp.onchange = () => {
        if (wrapOtpMin) wrapOtpMin.style.display = exigirOtp.checked ? 'flex' : 'none';
      };
    }
    if (otpMinEl) otpMinEl.value = emp.otp_valor_minimo || 0;

    // ── Card de plano ──────────────────────────────────────────────────
    const NOMES   = { trial: 'Avaliação', starter: 'Starter', pro: 'Pro', business: 'Business' };
    const CORES   = { trial: '#6b7280', starter: '#3b82f6', pro: '#00e5a0', business: '#f97316' };
    const LIM_ORC = { trial: 50, starter: 200, pro: 1000, business: null };
    const LIM_USR = { trial: 1,  starter: 3,   pro: 10,   business: null };
    const plano     = (emp.plano || 'trial').toLowerCase();
    const nomePlano = NOMES[plano] || plano;
    const planoCor  = CORES[plano] || 'var(--accent)';

    const badgeEl = document.getElementById('cfg-plano-badge');
    if (badgeEl) {
      badgeEl.textContent     = '✦ ' + nomePlano;
      badgeEl.style.color     = planoCor;
      badgeEl.style.borderColor = planoCor + '44';
      badgeEl.style.background  = planoCor + '14';
    }

    const valEl = document.getElementById('cfg-plano-validade');
    if (valEl) {
      if (plano === 'trial' && emp.trial_ate) {
        valEl.textContent = '⏳ Trial até ' + new Date(emp.trial_ate).toLocaleDateString('pt-BR');
      } else if (emp.assinatura_valida_ate) {
        valEl.textContent = '📅 Válido até ' + new Date(emp.assinatura_valida_ate).toLocaleDateString('pt-BR');
      } else {
        valEl.textContent = plano === 'trial' ? '—' : '✅ Sem vencimento';
      }
    }

    const limOrc = emp.limite_orcamentos_custom ?? LIM_ORC[plano];
    const limUsr = emp.limite_usuarios_custom   ?? LIM_USR[plano];
    const orcEl = document.getElementById('cfg-plano-orc');
    const usrEl = document.getElementById('cfg-plano-usr');
    if (orcEl) orcEl.textContent = limOrc != null ? limOrc + ' / mês' : '∞ ilimitado';
    if (usrEl) usrEl.textContent = limUsr != null ? limUsr + (limUsr === 1 ? ' usuário' : ' usuários') : '∞ ilimitado';

    const ORDEM_PLANOS = ['trial', 'starter', 'pro', 'business'];
    const idxAtual = ORDEM_PLANOS.indexOf(plano);
    const upgradeSection = document.getElementById('cfg-upgrade-section');
    const planCtaEl = document.querySelector('.cfg-plan-cta');
    if (plano === 'business') {
      if (planCtaEl) planCtaEl.style.display = 'none';
    } else if (upgradeSection) {
      upgradeSection.style.display = '';
      let visivel = 0;
      upgradeSection.querySelectorAll('.cfg-upgrade-card').forEach(function(card) {
        const idxCard = ORDEM_PLANOS.indexOf(card.dataset.plano);
        if (idxCard > idxAtual) { card.style.display = ''; visivel++; }
        else { card.style.display = 'none'; }
      });
      const grid = upgradeSection.querySelector('.cfg-upgrade-grid');
      if (grid && visivel > 0) grid.style.gridTemplateColumns = 'repeat(' + visivel + ', 1fr)';
      if (window.location.hash === '#cfg-upgrade-section') {
        setTimeout(function() { upgradeSection.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 300);
      }
    }

    if (emp.logo_url) {
      mostrarLogo(emp.logo_url);
    } else {
      atualizarPreview();
    }

    const isAdmin = localStorage.getItem('cotte_role') === 'admin' || localStorage.getItem('cotte_is_admin') === 'true';
    if (isAdmin) {
      const navAdmin = document.getElementById('nav-admin-link');
      if (navAdmin) navAdmin.style.display = 'flex';
    }

    await carregarBancosPix();

  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

// ── BANCOS / PIX DA EMPRESA ───────────────────────────────────────────

let _bancosPix = [];
let _bancoPixEditandoId = null;

async function carregarBancosPix() {
  try {
    const listaEl = document.getElementById('bancos-pix-lista');
    const vazioEl = document.getElementById('bancos-pix-vazio');
    const loadingEl = document.getElementById('bancos-pix-loading');
    if (loadingEl) loadingEl.style.display = 'block';

    _bancosPix = await api.get('/empresa/pix/bancos');

    if (loadingEl) loadingEl.style.display = 'none';
    if (!_bancosPix || _bancosPix.length === 0) {
      if (vazioEl) vazioEl.style.display = 'block';
      if (listaEl) listaEl.innerHTML = '';
      return;
    }

    if (vazioEl) vazioEl.style.display = 'none';
    if (!listaEl) return;

    // Verifica permissão admin para exibir botão de remover
    const isAdminPix = localStorage.getItem('cotte_role') === 'admin'
      || localStorage.getItem('cotte_is_admin') === 'true'
      || (typeof Permissoes !== 'undefined' && Permissoes.pode('empresa', 'admin'));

    listaEl.innerHTML = _bancosPix.map(b => {
      const nome = b.apelido || b.nome_banco;
      const detalhes = [b.nome_banco, b.agencia && `Agência ${b.agencia}`, b.conta && `Conta ${b.conta}`]
        .filter(Boolean)
        .join(' • ');
      const pixInfo = b.pix_chave
        ? `${(b.pix_tipo || '').toUpperCase() || 'PIX'} · ${b.pix_chave}`
        : 'PIX não configurado';
      const padraoBadge = b.padrao_pix
        ? '<span style="font-size:11px;font-weight:600;padding:3px 8px;border-radius:999px;background:var(--green-dim);color:var(--green);border:1px solid rgba(16,185,129,0.2);white-space:nowrap">PIX padrão</span>'
        : '';

      const btnRemover = isAdminPix
        ? `<button class="btn btn-ghost" style="font-size:12px;padding:5px 10px;color:var(--red);border-color:rgba(239,68,68,0.3)" onclick="confirmarExcluirBancoPix(${b.id})">Remover</button>`
        : '';

      return `
        <div class="cfg-inline-row" style="align-items:flex-start">
          <div class="cfg-inline-info">
            <div class="cfg-inline-title" style="display:flex;align-items:center;gap:8px">
              <span>${nome}</span>
              ${padraoBadge}
            </div>
            <div class="cfg-inline-sub">
              ${detalhes || 'Conta bancária da empresa'}
              <br>
              <span style="color:var(--muted)">PIX: ${pixInfo}</span>
            </div>
          </div>
          <div style="display:flex;gap:6px;white-space:nowrap">
            <button class="btn btn-ghost" style="font-size:12px;padding:5px 10px" onclick="abrirModalBancoPix(${b.id})">
              Editar
            </button>
            ${btnRemover}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    showNotif('❌', 'Erro', err.message || 'Falha ao carregar bancos PIX', 'error');
  }
}

function abrirModalBancoPix(id) {
  _bancoPixEditandoId = id || null;

  const tituloEl = document.getElementById('modal-banco-pix-titulo');
  const nomeBancoEl = document.getElementById('banco-nome');
  const apelidoEl = document.getElementById('banco-apelido');
  const agenciaEl = document.getElementById('banco-agencia');
  const contaEl = document.getElementById('banco-conta');
  const tipoContaEl = document.getElementById('banco-tipo-conta');
  const pixTipoEl = document.getElementById('banco-pix-tipo');
  const pixChaveEl = document.getElementById('banco-pix-chave');
  const pixTitularEl = document.getElementById('banco-pix-titular');
  const padraoEl = document.getElementById('banco-padrao-pix');

  if (!nomeBancoEl || !pixChaveEl) return;

  if (id) {
    const banco = _bancosPix.find(b => b.id === id);
    if (!banco) return;
    if (tituloEl) tituloEl.textContent = 'Editar banco / PIX';
    nomeBancoEl.value = banco.nome_banco || '';
    apelidoEl.value = banco.apelido || '';
    agenciaEl.value = banco.agencia || '';
    contaEl.value = banco.conta || '';
    tipoContaEl.value = banco.tipo_conta || '';
    pixTipoEl.value = banco.pix_tipo || '';
    pixChaveEl.value = banco.pix_chave || '';
    pixTitularEl.value = banco.pix_titular || '';
    padraoEl.checked = !!banco.padrao_pix;
  } else {
    if (tituloEl) tituloEl.textContent = 'Novo banco com PIX';
    nomeBancoEl.value = '';
    apelidoEl.value = '';
    agenciaEl.value = '';
    contaEl.value = '';
    tipoContaEl.value = '';
    pixTipoEl.value = '';
    pixChaveEl.value = '';
    pixTitularEl.value = '';
    padraoEl.checked = false;
  }

  const modal = document.getElementById('modal-banco-pix');
  if (modal) modal.classList.add('open');
}

function fecharModalBancoPix() {
  const modal = document.getElementById('modal-banco-pix');
  if (modal) modal.classList.remove('open');
  _bancoPixEditandoId = null;
}

async function salvarBancoPix() {
  const nomeBancoEl = document.getElementById('banco-nome');
  const apelidoEl = document.getElementById('banco-apelido');
  const agenciaEl = document.getElementById('banco-agencia');
  const contaEl = document.getElementById('banco-conta');
  const tipoContaEl = document.getElementById('banco-tipo-conta');
  const pixTipoEl = document.getElementById('banco-pix-tipo');
  const pixChaveEl = document.getElementById('banco-pix-chave');
  const pixTitularEl = document.getElementById('banco-pix-titular');
  const padraoEl = document.getElementById('banco-padrao-pix');
  const btn = document.getElementById('btn-salvar-banco-pix');

  if (!nomeBancoEl) return;
  const nome = nomeBancoEl.value.trim();
  if (!nome) {
    showNotif('❌', 'Preencha o nome do banco', 'Informe um nome para identificar esta conta.', 'error');
    return;
  }

  const payload = {
    nome_banco: nome,
    apelido: apelidoEl.value.trim() || null,
    agencia: agenciaEl.value.trim() || null,
    conta: contaEl.value.trim() || null,
    tipo_conta: tipoContaEl.value.trim() || null,
    pix_tipo: pixTipoEl.value || null,
    pix_chave: pixChaveEl.value.trim() || null,
    pix_titular: pixTitularEl.value.trim() || null,
    padrao_pix: padraoEl.checked,
  };

  try {
    if (btn) { btn.disabled = true; btn.textContent = 'Salvando...'; }
    if (_bancoPixEditandoId) {
      await api.patch(`/empresa/pix/bancos/${_bancoPixEditandoId}`, payload);
      showNotif('✅', 'Banco atualizado', 'Dados do banco e PIX atualizados com sucesso.');
    } else {
      await api.post('/empresa/pix/bancos', payload);
      showNotif('✅', 'Banco criado', 'Novo banco com PIX cadastrado com sucesso.');
    }
    fecharModalBancoPix();
    await carregarBancosPix();
  } catch (err) {
    showNotif('❌', 'Erro', err.message || 'Falha ao salvar banco/PIX', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Salvar banco'; }
  }
}

async function confirmarExcluirBancoPix(id) {
  // Verificação de segurança no frontend (defesa em profundidade)
  const isAdmin = localStorage.getItem('cotte_role') === 'admin'
    || localStorage.getItem('cotte_is_admin') === 'true'
    || (typeof Permissoes !== 'undefined' && Permissoes.pode('empresa', 'admin'));
  if (!isAdmin) {
    showNotif('❌', 'Sem permissão', 'Apenas administradores podem remover bancos/PIX.', 'error');
    return;
  }
  if (!window.confirm('Tem certeza que deseja remover este banco? Esta ação não afeta orçamentos já emitidos.')) {
    return;
  }
  try {
    await api.delete(`/empresa/pix/bancos/${id}`);
    showNotif('✅', 'Banco removido', 'O banco foi removido com sucesso.');
    await carregarBancosPix();
  } catch (err) {
    showNotif('❌', 'Erro', err.message || 'Falha ao remover banco', 'error');
  }
}

// ── WHATSAPP PRÓPRIO ─────────────────────────────────────────────────
let _wpQrTimer = null;

async function carregarStatusWhatsapp() {
  try {
    const st = await api.get('/empresa/whatsapp/status');
    _renderizarWhatsapp(st);
  } catch (err) {
    // Silencioso — não bloqueia o carregamento da página
  }
}

function _renderizarWhatsapp(st) {
  const upgrade    = document.getElementById('wp-upgrade-state');
  const desconect  = document.getElementById('wp-desconectado-state');
  const qrcodeEl   = document.getElementById('wp-qrcode-state');
  const conectEl   = document.getElementById('wp-conectado-state');
  const badge      = document.getElementById('wp-plano-badge');

  [upgrade, desconect, qrcodeEl, conectEl].forEach(el => el && (el.style.display = 'none'));

  if (!st.habilitado) {
    if (upgrade) {
      upgrade.style.display = 'block';
      if (badge) badge.style.display = 'inline-block';
    }
    return;
  }

  if (st.conectado) {
    if (conectEl) {
      conectEl.style.display = 'block';
      const numEl = document.getElementById('wp-numero-display');
      if (numEl && st.numero) numEl.textContent = '· +' + st.numero;
    }
  } else if (st.ativo && st.qrcode) {
    _exibirQrCode(st.qrcode);
  } else {
    if (desconect) desconect.style.display = 'block';
  }
}

function _exibirQrCode(base64) {
  const qrcodeEl = document.getElementById('wp-qrcode-state');
  const img      = document.getElementById('wp-qrcode-img');
  if (qrcodeEl) qrcodeEl.style.display = 'block';
  const desconect = document.getElementById('wp-desconectado-state');
  if (desconect) desconect.style.display = 'none';
  if (img && base64) {
    img.src = 'data:image/png;base64,' + base64;
  }
  _iniciarPollingConexao();
}

function _iniciarPollingConexao() {
  if (_wpQrTimer) clearInterval(_wpQrTimer);
  _wpQrTimer = setInterval(async () => {
    try {
      const st = await api.get('/empresa/whatsapp/status');
      if (st.conectado) {
        clearInterval(_wpQrTimer);
        _wpQrTimer = null;
        _renderizarWhatsapp(st);
        showNotif('✅', 'WhatsApp conectado!', 'Seu número foi vinculado com sucesso.', 'success');
      }
    } catch (_) {}
  }, 4000);
}

// FIX 6.7 — Limpar polling ao navegar para outra página
window.addEventListener('beforeunload', () => {
  if (_wpQrTimer) { clearInterval(_wpQrTimer); _wpQrTimer = null; }
});

async function wpConectar() {
  const btn = document.getElementById('wp-btn-conectar');
  if (btn) { btn.disabled = true; btn.textContent = 'Conectando...'; }
  try {
    const st = await api.post('/empresa/whatsapp/conectar', {});
    _renderizarWhatsapp(st);
    if (st.qrcode) _exibirQrCode(st.qrcode);
  } catch (err) {
    showNotif('❌', 'Erro', err.message || 'Falha ao iniciar conexão', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Conectar WhatsApp'; }
  }
}

async function wpAtualizarQR() {
  try {
    const data = await api.get('/empresa/whatsapp/qrcode');
    if (data.qrcode) {
      const img = document.getElementById('wp-qrcode-img');
      if (img) img.src = 'data:image/png;base64,' + data.qrcode;
      showNotif('🔄', 'QR Code atualizado', 'Escaneie o novo código', 'info');
    }
  } catch (err) {
    showNotif('❌', 'Erro', err.message || 'Falha ao atualizar QR code', 'error');
  }
}

async function wpCancelar() {
  if (_wpQrTimer) { clearInterval(_wpQrTimer); _wpQrTimer = null; }
  const qrcodeEl  = document.getElementById('wp-qrcode-state');
  const desconect = document.getElementById('wp-desconectado-state');
  if (qrcodeEl)  qrcodeEl.style.display  = 'none';
  if (desconect) desconect.style.display = 'block';
}

async function wpDesconectar() {
  if (!confirm('Deseja desconectar o WhatsApp da sua empresa? Os envios voltarão a usar o número da plataforma.')) return;
  try {
    await api.delete('/empresa/whatsapp/desconectar');
    if (_wpQrTimer) { clearInterval(_wpQrTimer); _wpQrTimer = null; }
    showNotif('✅', 'WhatsApp desconectado', 'Os envios voltarão a usar o número da plataforma.', 'success');
    await carregarStatusWhatsapp();
  } catch (err) {
    showNotif('❌', 'Erro', err.message || 'Falha ao desconectar', 'error');
  }
}

// ── LOGO ──────────────────────────────────────────────────────────────
function mostrarLogo(url) {
  const img        = document.getElementById('logo-img');
  const placeholder = document.getElementById('logo-placeholder');
  const btnRemover  = document.getElementById('btn-remover-logo');
  const logoSrc = api.resolveUrl(url);
  img.src = logoSrc;
  img.style.display = 'block';
  placeholder.style.display = 'none';
  btnRemover.style.display  = 'flex';

  const pLogo = document.getElementById('preview-logo');
  pLogo.src = logoSrc;
  pLogo.style.display = 'block';
  atualizarPreview();
}

function ocultarLogo() {
  document.getElementById('logo-img').style.display         = 'none';
  document.getElementById('logo-placeholder').style.display = 'block';
  document.getElementById('btn-remover-logo').style.display  = 'none';
  document.getElementById('preview-logo').style.display      = 'none';
  document.getElementById('preview-logo').src                = '';
  atualizarPreview();
}

// ── UPLOAD LOGO ───────────────────────────────────────────────────────
async function uploadLogo(input) {
  if (!input.files.length) return;
  const btn = document.getElementById('btn-upload-logo');
  setLoading(btn, true);

  const formData = new FormData();
  formData.append('file', input.files[0]);

  try {
    const token = getToken();
    const res   = await fetch(API_URL + API_PREFIX + '/empresa/logo', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro no upload');
    mostrarLogo(data.logo_url);
    showNotif('✅', 'Logo enviada!', 'Será exibida nos orçamentos.');
    if (typeof carregarSidebar === 'function') carregarSidebar();
    const u = typeof getUsuario === 'function' ? getUsuario() : null;
    const impersonando =
      typeof sessionStorage !== 'undefined' && sessionStorage.getItem('superadmin_token_backup');
    if (u && u.is_superadmin && !impersonando && typeof preencherLogoSidebar === 'function') {
      preencherLogoSidebar();
    }
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    setLoading(btn, false, 'Enviar nova logo');
    input.value = '';
  }
}

async function removerLogo() {
  try {
    await api.delete('/empresa/logo');
    ocultarLogo();
    showNotif('✅', 'Logo removida', '');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

// ── COR ───────────────────────────────────────────────────────────────
document.getElementById('emp-cor').addEventListener('input', function () {
  document.getElementById('emp-cor-hex').value = this.value;
  atualizarPreview();
});

function sincronizarCor(hex) {
  if (/^#[0-9A-Fa-f]{6}$/.test(hex)) {
    document.getElementById('emp-cor').value = hex;
    atualizarPreview();
  }
}

async function salvarBoasVindas() {
  try {
    await api.patch('/empresa/', {
      boas_vindas_ativo: document.getElementById('boas-vindas-ativo').checked,
      msg_boas_vindas: document.getElementById('msg-boas-vindas').value.trim() || null,
    });
    showNotif('✅', 'Salvo!', 'Mensagem de boas-vindas atualizada.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

async function salvarNotifWhatsVisualizacao() {
  try {
    await api.patch('/empresa/', {
      notif_whats_visualizacao: document.getElementById('notif-whats-visualizacao').checked,
    });
    showNotif('✅', 'Salvo!', 'Configuração de notificação atualizada.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

async function salvarAnexoPdfEmail() {
  try {
    await api.patch('/empresa/', {
      anexar_pdf_email: document.getElementById('anexar-pdf-email').checked,
    });
    showNotif('✅', 'Salvo!', 'Configuração de anexo em e-mail atualizada.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

async function salvarComunicacao() {
  const btn = document.getElementById('btn-salvar-comunicacao');
  if (btn) setLoading(btn, true);
  try {
    const payload = {
      descricao_publica_empresa: document.getElementById('descricao-publica-empresa').value.trim() || null,
      texto_assinatura_proposta: document.getElementById('texto-assinatura-proposta').value.trim() || null,
      telefone_operador: document.getElementById('telefone-operador').value.trim() || null,
      mostrar_botao_whatsapp: Boolean(document.getElementById('mostrar-botao-whatsapp').checked),
      texto_aviso_aceite: document.getElementById('texto-aviso-aceite').value.trim() || null,
      mensagem_confianca_proposta: document.getElementById('mensagem-confianca-proposta').value.trim() || null,
      mostrar_mensagem_confianca: Boolean(document.getElementById('mostrar-mensagem-confianca').checked),
      exigir_otp_aceite: Boolean(document.getElementById('exigir-otp-aceite').checked),
      otp_valor_minimo: parseFloat(document.getElementById('otp-valor-minimo').value) || 0,
      enviar_pdf_whatsapp: Boolean(document.getElementById('enviar-pdf-whatsapp').checked),
    };
    console.debug('[DEBUG] Payload de comunicação:', JSON.stringify(payload, null, 2));
    await api.patch('/empresa/', payload);
    showNotif('✅', 'Salvo!', 'Comunicação com o cliente atualizada.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    if (btn) setLoading(btn, false, 'Salvar apresentação');
  }
}

async function salvarAssinaturaEmail() {
  const val = document.getElementById('assinatura-email').value.trim();
  try {
    await api.patch('/empresa/', { assinatura_email: val || null });
    showNotif('✅', 'Salvo!', 'Assinatura de e-mail atualizada.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

// ── PREVIEW NUMERAÇÃO ─────────────────────────────────────────────────
function atualizarPreviewNumero() {
  const prefixo   = (document.getElementById('emp-numero-prefixo')?.value || 'ORC').trim() || 'ORC';
  const incluiAno = document.getElementById('emp-numero-incluir-ano')?.checked !== false;
  const prefixoAp = (document.getElementById('emp-numero-prefixo-aprovado')?.value || '').trim();
  const anoAtual  = String(new Date().getFullYear()).slice(-2);
  const numero    = incluiAno ? `${prefixo}-5-${anoAtual}` : `${prefixo}-5`;
  const el = document.getElementById('preview-numero-orc-valor');
  if (el) el.textContent = numero;
  const elAp = document.getElementById('preview-numero-orc-ap');
  const elApVal = document.getElementById('preview-numero-orc-ap-valor');
  if (elAp && elApVal) {
    if (prefixoAp) {
      const numeroAp = incluiAno ? `${prefixoAp}-5-${anoAtual}` : `${prefixoAp}-5`;
      elApVal.textContent = numeroAp;
      elAp.style.display = 'inline';
    } else {
      elAp.style.display = 'none';
    }
  }
}

// ── SALVAR NUMERAÇÃO ──────────────────────────────────────────────────
async function salvarNumeracao() {
  const btn = document.getElementById('btn-salvar-numeracao');
  if (btn) setLoading(btn, true);
  try {
    const prefixo   = (document.getElementById('emp-numero-prefixo')?.value || 'ORC').trim() || 'ORC';
    const incluiAno = document.getElementById('emp-numero-incluir-ano')?.checked !== false;
    const prefixoAp = (document.getElementById('emp-numero-prefixo-aprovado')?.value || '').trim() || null;
    await api.patch('/empresa/', {
      numero_prefixo:           prefixo,
      numero_incluir_ano:       incluiAno,
      numero_prefixo_aprovado:  prefixoAp,
    });
    showNotif('✅', 'Salvo!', 'Numeração de orçamentos atualizada.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    if (btn) setLoading(btn, false, 'Salvar numeração');
  }
}

// ── SALVAR EMPRESA ─────────────────────────────────────────────────────
// FIX 6.8 — Cada botão só desabilita a si mesmo (não mais botões cruzados)
async function salvarEmpresa(btnEl) {
  const btn = btnEl || document.getElementById('btn-salvar-empresa');
  const nomeVal = document.getElementById('emp-nome')?.value?.trim();
  if (!nomeVal) {
    showNotif('⚠️', 'Nome obrigatório', 'O nome da empresa não pode ficar vazio.', 'warning');
    return;
  }
  if (btn) setLoading(btn, true);

  try {
    const lembreteVal   = document.getElementById('emp-lembrete').value.trim();
    const lembreteTexto = document.getElementById('emp-lembrete-texto').value.trim();
    
    const payload = {
      nome:                 nomeVal,
      telefone:             document.getElementById('emp-telefone').value.trim() || null,
      email:                document.getElementById('emp-email').value.trim()    || null,
      cor_primaria:         document.getElementById('emp-cor').value,
      validade_padrao_dias: parseInt(document.getElementById('emp-validade').value) || 7,
      desconto_max_percent: (() => { const el = document.getElementById('emp-desconto-max'); return el ? (parseInt(el.value) ?? 100) : 100; })(),
      ..._politicaAgendamentoSelectParaPayload(
        document.getElementById('emp-politica-agendamento-orc')?.value
      ),
      utilizar_agendamento_automatico:
        document.getElementById('emp-utilizar-agendamento-auto')?.value === 'true',
      agendamento_opcoes_somente_apos_liberacao:
        document.getElementById('emp-agendamento-somente-pos-liberacao')?.value === 'true',
      lembrete_dias:        lembreteVal   !== '' ? parseInt(lembreteVal)   : null,
      lembrete_texto:       lembreteTexto !== '' ? lembreteTexto           : null,
    };
    console.debug('[DEBUG] Salvando empresa:', payload);
    await api.patch('/empresa/', payload);

    const indicator = document.getElementById('save-indicator');
    if (indicator) {
      indicator.classList.add('visible');
      setTimeout(() => indicator.classList.remove('visible'), 3000);
    }

    showNotif('✅', 'Salvo!', 'Dados da empresa atualizados.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    if (btn) setLoading(btn, false, btn.dataset.originalLabel || btn.textContent || 'Salvar');
  }
}

async function salvarPixPadrao() {
  const btn = document.getElementById('btn-salvar-pix-padrao');
  if (btn) setLoading(btn, true);
  try {
    const chave   = (document.getElementById('pix-chave-padrao')?.value || '').trim();
    const tipo    = document.getElementById('pix-tipo-padrao')?.value || null;
    const titular = (document.getElementById('pix-titular-padrao')?.value || '').trim();
    await api.patch('/empresa/', {
      pix_chave_padrao:   chave   || null,
      pix_tipo_padrao:    chave ? (tipo || null) : null,
      pix_titular_padrao: titular || null,
    });
    showNotif('✅', 'Salvo!', 'Chave PIX padrão atualizada.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    if (btn) setLoading(btn, false, 'Salvar PIX');
  }
}

// ── PREVIEW AO VIVO ───────────────────────────────────────────────────
function atualizarPreview() {
  const nome     = document.getElementById('emp-nome').value.trim();
  const telefone = document.getElementById('emp-telefone').value.trim();
  const email    = document.getElementById('emp-email').value.trim();
  const cor      = document.getElementById('emp-cor').value || '#00e5a0';

  const header = document.getElementById('preview-header');
  header.style.setProperty('--cor', cor);
  header.style.borderBottomColor = cor;

  document.getElementById('preview-empresa-info').textContent =
    [telefone, email].filter(Boolean).join('  ·  ') || '';

  const nomeEl = document.getElementById('preview-nome-fallback');
  nomeEl.textContent = nome || 'Empresa';
  nomeEl.style.color = cor;

  const hoje = new Date();
  const validade = new Date(hoje);
  validade.setDate(validade.getDate() + 7);
  document.getElementById('preview-orc-datas').innerHTML =
    'Emissão: ' + hoje.toLocaleDateString('pt-BR') + '<br>Validade: ' + validade.toLocaleDateString('pt-BR');
}

// Listeners de preview ao vivo
['emp-nome', 'emp-telefone', 'emp-email'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('input', atualizarPreview);
});

// ── INICIALIZAÇÃO ─────────────────────────────────────────────────────
(function () {
  const hash = window.location.hash.replace('#', '');
  const secoes = ['empresa', 'orcamentos', 'aparencia', 'comunicacao', 'integracoes', 'plano', 'seguranca', 'preferencias'];
  if (secoes.includes(hash)) irSecao(hash);
})();

(function () {
  const tema = localStorage.getItem('cotte_tema') || 'light';
  atualizarVisualizacaoTema(tema);
  atualizarBtnTema();
})();

carregarEmpresa();
carregarStatusWhatsapp();

// ── FORMAS DE PAGAMENTO ──────────────────────────────────────────────────

const _METODO_LABEL = {
  pix: '🏦 PIX', dinheiro: '💵 Dinheiro', cartao: '💳 Cartão',
  transferencia: '🏛️ TED/DOC', boleto: '📄 Boleto',
  na_execucao: '🔧 Na execução', na_entrega: '📦 Na entrega', outro: 'Outro',
};

// Usa Financeiro.listarFormasPagamento() com cache TTL de 5min
async function carregarFormasPagamento() {
  const lista = document.getElementById('formas-lista');
  if (!lista) return;
  lista.innerHTML = '<div style="color:var(--muted);font-size:13px;text-align:center;padding:20px 0">Carregando...</div>';
  try {
    const formas = await Financeiro.listarFormasPagamento();
    const arr = Array.isArray(formas) ? formas : [];
    if (arr.length === 0) {
      lista.innerHTML = '<div style="color:var(--muted);font-size:13px;text-align:center;padding:20px 0">Nenhuma forma cadastrada. Clique em "+ Nova forma".</div>';
      return;
    }
    lista.innerHTML = arr.map(f => _renderFormaCard(f)).join('');
  } catch (e) {
    lista.innerHTML = '<div style="color:var(--red);font-size:13px;padding:10px 0">Erro ao carregar formas de pagamento.</div>';
  }
}

function _resumoRegra(f) {
  if (!f.exigir_entrada_na_aprovacao || !f.percentual_entrada) return '<span style="color:var(--muted);font-size:11px">Sem regra de entrada automática</span>';
  const metEnt = _METODO_LABEL[f.metodo_entrada] || f.metodo_entrada || '—';
  let txt = `<span style="color:var(--green);font-size:11px">Entrada ${f.percentual_entrada}% via ${metEnt}`;
  if (f.percentual_saldo > 0) {
    const metSal = _METODO_LABEL[f.metodo_saldo] || f.metodo_saldo || '—';
    txt += ` · Saldo ${f.percentual_saldo}% via ${metSal}`;
    if (f.dias_vencimento_saldo) txt += ` (${f.dias_vencimento_saldo}d)`;
  }
  txt += '</span>';
  return txt;
}

function _renderFormaCard(f) {
  const badgePadrao = f.padrao ? '<span style="font-size:10px;padding:2px 8px;border-radius:12px;background:rgba(0,229,160,.15);color:var(--green);font-weight:700;margin-left:6px">PADRÃO</span>' : '';
  const badgeInativo = !f.ativo ? '<span style="font-size:10px;padding:2px 8px;border-radius:12px;background:rgba(239,68,68,.12);color:#ef4444;font-weight:600;margin-left:6px">INATIVO</span>' : '';
  return `<div style="display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid var(--border);border-radius:10px;background:var(--surface2)">
    <div style="font-size:24px;flex-shrink:0;width:36px;text-align:center">${f.icone || '💳'}</div>
    <div style="flex:1;min-width:0">
      <div style="font-size:14px;font-weight:600;margin-bottom:2px">${escapeHtml(f.nome)}${badgePadrao}${badgeInativo}</div>
      <div style="margin-top:2px">${_resumoRegra(f)}</div>
    </div>
    <div style="display:flex;gap:6px;flex-shrink:0">
      ${!f.padrao ? `<button onclick="setPadrao(${f.id})" title="Definir como padrão" style="background:none;border:1px solid var(--border);border-radius:6px;padding:5px 8px;cursor:pointer;font-size:11px;color:var(--muted)">★ Padrão</button>` : ''}
      <button onclick="editarForma(${f.id})" style="background:none;border:1px solid var(--border);border-radius:6px;padding:5px 8px;cursor:pointer;font-size:11px;color:var(--muted)">✏️ Editar</button>
      <button onclick="toggleFormaAtivo(${f.id},${f.ativo})" style="background:none;border:1px solid var(--border);border-radius:6px;padding:5px 8px;cursor:pointer;font-size:11px;color:${f.ativo ? '#ef4444' : 'var(--green)'}">
        ${f.ativo ? '⏸ Desativar' : '▶ Ativar'}
      </button>
    </div>
  </div>`;
}

function abrirModalNovaForma() {
  document.getElementById('forma-id').value = '';
  document.getElementById('forma-nome').value = '';
  document.getElementById('forma-icone').value = '💳';
  document.getElementById('forma-cor').value = '#00e5a0';
  document.getElementById('forma-descricao').value = '';
  document.getElementById('forma-padrao').checked = false;
  document.getElementById('forma-exigir-entrada').checked = false;
  document.getElementById('forma-pct-entrada').value = '';
  document.getElementById('forma-pct-saldo').value = '';
  document.getElementById('forma-metodo-entrada').value = 'pix';
  document.getElementById('forma-metodo-saldo').value = '';
  document.getElementById('forma-dias-saldo').value = '';
  document.getElementById('forma-campos-entrada').style.display = 'none';
  document.getElementById('forma-preview').style.display = 'none';
  document.getElementById('forma-erro-percentual').style.display = 'none';
  document.getElementById('modal-forma-titulo').textContent = 'Nova forma de pagamento';
  document.getElementById('modal-forma-pagamento').style.display = 'flex';
}

async function editarForma(id) {
  let formas;
  try {
    formas = await Financeiro.listarFormasPagamento();
  } catch (_) {
    formas = [];
  }
  const f = (Array.isArray(formas) ? formas : []).find(x => x.id === id);
  if (!f) { showNotif('⚠️', 'Não encontrado', 'Forma não encontrada', 'error'); return; }
  document.getElementById('forma-id').value = f.id;
  document.getElementById('forma-nome').value = f.nome || '';
  document.getElementById('forma-icone').value = f.icone || '💳';
  document.getElementById('forma-cor').value = f.cor || '#00e5a0';
  document.getElementById('forma-descricao').value = f.descricao || '';
  document.getElementById('forma-padrao').checked = !!f.padrao;
  document.getElementById('forma-exigir-entrada').checked = !!f.exigir_entrada_na_aprovacao;
  document.getElementById('forma-pct-entrada').value = f.percentual_entrada > 0 ? f.percentual_entrada : '';
  document.getElementById('forma-pct-saldo').value = f.percentual_saldo > 0 ? f.percentual_saldo : '';
  document.getElementById('forma-metodo-entrada').value = f.metodo_entrada || 'pix';
  document.getElementById('forma-metodo-saldo').value = f.metodo_saldo || '';
  document.getElementById('forma-dias-saldo').value = f.dias_vencimento_saldo || '';
  document.getElementById('forma-campos-entrada').style.display = f.exigir_entrada_na_aprovacao ? '' : 'none';
  document.getElementById('modal-forma-titulo').textContent = 'Editar forma de pagamento';
  document.getElementById('modal-forma-pagamento').style.display = 'flex';
  atualizarPreviewForma();
}

function fecharModalForma() {
  document.getElementById('modal-forma-pagamento').style.display = 'none';
}

function atualizarPctSaldo() {
  const pctEnt = parseFloat(document.getElementById('forma-pct-entrada').value) || 0;
  const saldo = Math.max(100 - pctEnt, 0);
  document.getElementById('forma-pct-saldo').value = saldo > 0 ? saldo : '';
}

function atualizarPreviewForma() {
  const camposEnt = document.getElementById('forma-campos-entrada');
  const exigir = document.getElementById('forma-exigir-entrada').checked;
  camposEnt.style.display = exigir ? '' : 'none';
  if (!exigir) {
    document.getElementById('forma-preview').style.display = 'none';
    return;
  }
  const pctEnt = parseFloat(document.getElementById('forma-pct-entrada').value) || 0;
  const pctSal = parseFloat(document.getElementById('forma-pct-saldo').value) || 0;
  const metEnt = document.getElementById('forma-metodo-entrada').value;
  const metSal = document.getElementById('forma-metodo-saldo').value;
  const dias   = parseInt(document.getElementById('forma-dias-saldo').value) || null;
  const erroEl = document.getElementById('forma-erro-percentual');
  if (pctEnt + pctSal > 100) {
    erroEl.textContent = 'A soma de entrada + saldo não pode ultrapassar 100%.';
    erroEl.style.display = '';
  } else {
    erroEl.style.display = 'none';
  }
  let preview = '';
  if (pctEnt > 0) preview += `Entrada ${pctEnt}% via ${_METODO_LABEL[metEnt] || metEnt}`;
  if (pctSal > 0) {
    if (preview) preview += ' · ';
    preview += `Saldo ${pctSal}% via ${_METODO_LABEL[metSal] || metSal}`;
    if (dias) preview += ` (vence em ${dias} dias)`;
  }
  const prevEl = document.getElementById('forma-preview');
  if (preview) { prevEl.textContent = '📋 ' + preview; prevEl.style.display = ''; }
  else { prevEl.style.display = 'none'; }
}

async function salvarForma() {
  const nome = document.getElementById('forma-nome').value.trim();
  if (!nome) { showNotif('⚠️', 'Campo obrigatório', 'Informe o nome da forma', 'error'); return; }
  const exigir = document.getElementById('forma-exigir-entrada').checked;
  const pctEnt = parseFloat(document.getElementById('forma-pct-entrada').value) || 0;
  const pctSal = parseFloat(document.getElementById('forma-pct-saldo').value) || 0;
  if (exigir && pctEnt + pctSal > 100) {
    showNotif('⚠️', 'Percentuais inválidos', 'A soma de entrada + saldo não pode ultrapassar 100%', 'error'); return;
  }
  const metEnt = document.getElementById('forma-metodo-entrada').value;
  const slug = nome.toLowerCase().replace(/[^a-z0-9]/g, '_').slice(0, 50) || ('forma_' + Date.now());
  const payload = {
    nome,
    slug,
    icone: document.getElementById('forma-icone').value || '💳',
    cor: document.getElementById('forma-cor').value || '#00e5a0',
    descricao: document.getElementById('forma-descricao').value.trim() || null,
    padrao: document.getElementById('forma-padrao').checked,
    exigir_entrada_na_aprovacao: exigir,
    percentual_entrada: exigir ? pctEnt : 0,
    metodo_entrada: exigir ? (metEnt || null) : null,
    percentual_saldo: exigir ? pctSal : 0,
    metodo_saldo: exigir ? (document.getElementById('forma-metodo-saldo').value || null) : null,
    dias_vencimento_saldo: parseInt(document.getElementById('forma-dias-saldo').value) || null,
    gera_pix_qrcode: exigir && metEnt === 'pix',
  };
  const btn = document.getElementById('btn-salvar-forma');
  btn.disabled = true; btn.textContent = 'Salvando...';
  try {
    const formaId = document.getElementById('forma-id').value;
    if (formaId) {
      await apiRequest('PATCH', `/financeiro/formas-pagamento/${formaId}`, payload);
    } else {
      await apiRequest('POST', '/financeiro/formas-pagamento', payload);
    }
    showNotif('✅', 'Forma salva!', nome, 'success');
    fecharModalForma();
    Financeiro.invalidarFormas();
    await carregarFormasPagamento();
  } catch (e) {
    showNotif('❌', 'Erro ao salvar', e.message || 'falha ao salvar forma', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Salvar';
  }
}

async function setPadrao(id) {
  try {
    await apiRequest('POST', `/financeiro/formas-pagamento/${id}/padrao`);
    showNotif('⭐', 'Padrão definido!', 'Esta forma será aplicada automaticamente nos novos orçamentos', 'success');
    Financeiro.invalidarFormas();
    await carregarFormasPagamento();
  } catch (e) {
    showNotif('❌', 'Erro', e.message || 'falha ao definir padrão', 'error');
  }
}

async function toggleFormaAtivo(id, ativoAtual) {
  try {
    await apiRequest('PATCH', `/financeiro/formas-pagamento/${id}`, { ativo: !ativoAtual });
    showNotif(ativoAtual ? '🔕' : '✅', ativoAtual ? 'Forma desativada' : 'Forma ativada', '', 'success');
    Financeiro.invalidarFormas();
    await carregarFormasPagamento();
  } catch (e) {
    showNotif('❌', 'Erro', e.message || 'falha ao alterar status', 'error');
  }
}

// ── CONFIGURAÇÕES FINANCEIRAS ─────────────────────────────────────────

async function carregarConfiguracaoFinanceira() {
  try {
    const cfg = await apiRequest('GET', '/financeiro/configuracoes');
    document.getElementById('fin-gerar-ao-aprovar').checked = cfg.gerar_contas_ao_aprovar !== false;
    document.getElementById('fin-dias-vencimento').value    = cfg.dias_vencimento_padrao ?? 7;
    document.getElementById('fin-automacoes-ativas').checked = cfg.automacoes_ativas === true;
    document.getElementById('fin-dias-antes').value         = cfg.dias_lembrete_antes ?? 2;
    document.getElementById('fin-dias-apos').value          = cfg.dias_lembrete_apos  ?? 3;
    _toggleAutomacoesFinanceiro(document.getElementById('fin-automacoes-ativas'));
  } catch(e) {
    console.error('Erro config financeiro:', e);
  }
}

function _toggleGerarAoAprovar(el) { /* apenas visual; salvo com o botão */ }

function _toggleAutomacoesFinanceiro(el) {
  const cfg = document.getElementById('fin-lembrete-config');
  if (cfg) cfg.style.display = el.checked ? 'block' : 'none';
}

async function salvarConfiguracaoFinanceira() {
  const btn = document.getElementById('btn-salvar-cfg-financeiro');
  btn.disabled = true; btn.textContent = 'Salvando...';
  try {
    await apiRequest('PATCH', '/financeiro/configuracoes', {
      gerar_contas_ao_aprovar: document.getElementById('fin-gerar-ao-aprovar').checked,
      dias_vencimento_padrao:  parseInt(document.getElementById('fin-dias-vencimento').value) || 7,
      automacoes_ativas:       document.getElementById('fin-automacoes-ativas').checked,
      dias_lembrete_antes:     parseInt(document.getElementById('fin-dias-antes').value) || 2,
      dias_lembrete_apos:      parseInt(document.getElementById('fin-dias-apos').value) || 3,
    });
    showNotif('✅', 'Configurações salvas!', 'Preferências financeiras atualizadas', 'success');
  } catch(e) {
    showNotif('❌', 'Erro', e.message || 'Falha ao salvar', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Salvar configurações';
  }
}

// Carregar se hash apontar para financeiro ao abrir a página
if (window.location.hash === '#cfg-financeiro') carregarConfiguracaoFinanceira();

// ── CATÁLOGO — MODELOS DE SEGMENTO ────────────────────────────────────
let _cfgSegmentosCache = [];
let _cfgTemplateSelecionado = null;
const _cfgIcones = {
  'eletricista': '⚡', 'pedreiro': '🧱', 'pintor': '🎨',
  'encanador': '🔧', 'marceneiro': '🪚', 'geral': '📦',
};

async function cfgCarregarSegmentos() {
  const lista = document.getElementById('cfg-templates-lista');
  if (!lista) return;
  lista.innerHTML = '<div style="text-align:center;padding:20px"><div class="spinner"></div></div>';
  document.getElementById('cfg-templates-preview').style.display = 'none';
  lista.style.display = 'flex';
  try {
    _cfgSegmentosCache = await api.get('/catalogo/templates/segmentos') || [];
    cfgRenderizarSegmentos();
  } catch (err) {
    lista.innerHTML = `<div style="text-align:center;padding:20px;color:var(--muted)">Erro ao carregar modelos: ${err.message}</div>`;
  }
}

function cfgRenderizarSegmentos() {
  const lista = document.getElementById('cfg-templates-lista');
  if (!_cfgSegmentosCache.length) {
    lista.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted)">Nenhum modelo disponível</div>';
    return;
  }
  lista.innerHTML = _cfgSegmentosCache.map(seg => `
    <div style="display:flex;align-items:center;gap:14px;padding:14px 16px;background:var(--surface2);border-radius:12px;cursor:pointer;transition:background 0.15s"
      onmouseover="this.style.background='var(--surface3)'"
      onmouseout="this.style.background='var(--surface2)'"
      onclick="cfgPreviewTemplate('${seg.slug}')">
      <div style="font-size:28px;width:44px;height:44px;display:flex;align-items:center;justify-content:center;background:var(--surface);border-radius:10px">${_cfgIcones[seg.slug] || '📦'}</div>
      <div style="flex:1;min-width:0">
        <div style="font-weight:600;font-size:15px;color:var(--text)">${seg.nome}</div>
        <div style="font-size:12px;color:var(--muted);margin-top:2px">${seg.descricao}</div>
      </div>
      <div style="color:var(--muted);font-size:18px">→</div>
    </div>
  `).join('');
}

async function cfgPreviewTemplate(slug) {
  try {
    const template = await api.get(`/catalogo/templates/${slug}`);
    _cfgTemplateSelecionado = slug;
    document.getElementById('cfg-template-nome').textContent = template.nome;
    document.getElementById('cfg-template-descricao').textContent = template.descricao;
    document.getElementById('cfg-template-total').textContent =
      `${template.servicos.length} itens · ${template.categorias.length} categorias`;

    const categoriasMap = {};
    template.categorias.forEach(cat => { categoriasMap[cat] = []; });
    template.servicos.forEach(srv => {
      const cat = srv.categoria || 'Sem categoria';
      if (!categoriasMap[cat]) categoriasMap[cat] = [];
      categoriasMap[cat].push(srv);
    });
    let html = '';
    for (const [cat, servicos] of Object.entries(categoriasMap)) {
      html += `
        <div style="margin-bottom:14px">
          <div style="font-weight:600;font-size:13px;color:var(--green);margin-bottom:6px;padding-left:4px">${cat}</div>
          <div style="display:flex;flex-direction:column;gap:4px">
            ${servicos.map(s => `
              <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:var(--surface2);border-radius:8px;font-size:13px">
                <span>${s.nome}</span>
                <span style="font-weight:600;color:var(--text)">${s.unidade}</span>
              </div>
            `).join('')}
          </div>
        </div>`;
    }
    document.getElementById('cfg-template-conteudo').innerHTML = html;
    document.getElementById('cfg-templates-lista').style.display = 'none';
    document.getElementById('cfg-templates-preview').style.display = '';
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

function cfgVoltarTemplates() {
  document.getElementById('cfg-templates-lista').style.display = 'flex';
  document.getElementById('cfg-templates-preview').style.display = 'none';
  _cfgTemplateSelecionado = null;
}

async function cfgConfirmarImportarTemplate() {
  if (!_cfgTemplateSelecionado) return;
  const btn = document.getElementById('cfg-btn-importar-template');
  setLoading(btn, true);
  try {
    const resultado = await api.post(`/catalogo/templates/${_cfgTemplateSelecionado}/importar`);
    const msgs = [];
    if (resultado.categorias_criadas > 0) msgs.push(`${resultado.categorias_criadas} categorias`);
    if (resultado.servicos_criados > 0) msgs.push(`${resultado.servicos_criados} itens`);
    const msg = msgs.length ? msgs.join(' e ') + ' importados' : 'Nenhum item novo (já existiam)';
    showNotif('✅', 'Modelo importado!', msg);
    cfgVoltarTemplates();
  } catch (err) {
    showNotif('❌', 'Erro ao importar', err.message, 'error');
  } finally {
    setLoading(btn, false, '✅ Importar Modelo');
  }
}

// ── TEMPLATE PÚBLICO DO ORÇAMENTO ─────────────────────────────────────
let _templateSelecionado = 'classico';

function _normalizarTemplatePublico(valor) {
  const tpl = String(valor || '').trim().toLowerCase();
  return tpl === 'moderno' ? 'moderno' : 'classico';
}

function selecionarTemplate(tpl) {
  _templateSelecionado = _normalizarTemplatePublico(tpl);
  const grid = document.getElementById('template-selector-grid');
  if (!grid) return;

  grid.querySelectorAll('.template-option').forEach(opt => {
    const optTpl = opt.getAttribute('data-template');
    const isSelected = optTpl === _templateSelecionado;

    // Atualiza container
    opt.style.borderColor = isSelected ? 'var(--accent)' : 'var(--border)';
    opt.style.background = isSelected ? 'var(--accent-dim)' : 'var(--surface)';
    opt.setAttribute('aria-pressed', isSelected ? 'true' : 'false');

    // Atualiza ícone de check
    const check = opt.querySelector('[id^="check-"]');
    if (check) {
      if (isSelected) {
        check.classList.remove('hidden');
        check.style.display = 'flex';
        check.style.background = 'var(--accent)';
        // Garante o SVG se sumiu
        if (!check.innerHTML.includes('svg')) {
          check.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
        }
      } else {
        check.classList.add('hidden');
        check.style.display = 'none';
      }
    }
  });
}


function _escCfgHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function _fmtBrlCfg(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return 'R$ 0,00';
  return 'R$ ' + x.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

function _formatQtdCfg(q) {
  const n = Number(q);
  if (!Number.isFinite(n)) return '0';
  return n === Math.floor(n) ? String(Math.floor(n)) : n.toFixed(2).replace('.', ',');
}

/** Blocos extras alinhados à página pública (prazo, obs, docs, confiança, ações ilustrativas, sobre, PDF, assinatura, etc.). */
function _buildStaticPreviewExtras(m, cor, nomeEsc) {
  const emp = m.empresa || {};
  const tel = _escCfgHtml(emp.telefone_operador || emp.telefone || '');
  const em = _escCfgHtml(emp.email || '');
  const contatoTopo = [tel, em].filter(Boolean).join(' · ');

  const emissaoD = new Date(m.criado_em);
  const validadeD = new Date(emissaoD);
  validadeD.setDate(validadeD.getDate() + (m.validade_dias || 7));
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  validadeD.setHours(0, 0, 0, 0);
  let dias = Math.round((validadeD - hoje) / 86400000);
  if (!Number.isFinite(dias)) dias = Number(m.validade_dias) || 7;

  let prazoTitulo;
  if (dias < 0) prazoTitulo = 'Esta proposta expirou.';
  else if (dias === 0) prazoTitulo = 'Último dia! Esta proposta vence hoje.';
  else if (dias === 1) prazoTitulo = 'Esta proposta é válida por mais 1 dia.';
  else prazoTitulo = 'Esta proposta é válida por mais ' + dias + ' dias.';
  const prazoSub = 'Quando estiver pronto, aceite ou solicite um ajuste na página pública.';
  const bgP = dias <= 1 ? '#fffbeb' : '#f0fdf4';
  const bdP = dias <= 1 ? '#fde68a' : '#bbf7d0';

  const prazoHtml =
    '<div style="padding:14px 16px;border-radius:14px;border:2px solid ' +
    bdP +
    ';background:' +
    bgP +
    ';display:flex;gap:12px;align-items:flex-start;margin-bottom:12px">' +
    '<span style="font-size:22px;line-height:1" aria-hidden="true">⏳</span><div style="min-width:0"><div style="font-size:13px;font-weight:700;color:#1f2937">' +
    _escCfgHtml(prazoTitulo) +
    '</div><div style="font-size:11px;color:#6b7280;margin-top:4px;line-height:1.4">' +
    _escCfgHtml(prazoSub) +
    '</div></div></div>';

  const topoContato = contatoTopo || '';

  const obsHtml = m.observacoes
    ? '<div style="padding:14px;background:#fffbeb;border:1px solid #fde68a;border-radius:14px;margin-bottom:12px">' +
      '<div style="font-size:10px;font-weight:700;color:#92400e;letter-spacing:0.06em;margin-bottom:6px">OBSERVAÇÕES</div>' +
      '<div style="font-size:12px;color:#78350f;line-height:1.5">' +
      _escCfgHtml(m.observacoes) +
      '</div></div>'
    : '';

  const docs = m.documentos || [];
  let docsHtml = '';
  if (docs.length) {
    docsHtml =
      '<div style="padding:16px;background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:12px;border:1px solid #f3f4f6">' +
      '<div style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:0.06em;margin-bottom:12px">DOCUMENTOS DA PROPOSTA</div>';
    docs.forEach((d) => {
      const dn = _escCfgHtml(d.documento_nome || 'Documento');
      const tipo = _escCfgHtml(d.documento_tipo || '');
      const ver = d.documento_versao != null ? 'v' + _escCfgHtml(String(d.documento_versao)) : '';
      const meta = [tipo, ver].filter(Boolean).join(' · ');
      const obr = d.obrigatorio
        ? '<span style="display:inline-block;font-size:9px;font-weight:700;padding:2px 8px;border-radius:999px;background:#fee2e2;color:#991b1b;margin-left:6px;vertical-align:middle">Obrigatório</span>'
        : '';
      const chk = d.obrigatorio
        ? '<div style="margin-top:10px;display:flex;align-items:center;gap:8px;font-size:11px;color:#6b7280">' +
          '<span style="width:14px;height:14px;border:2px solid #d1d5db;border-radius:4px;background:#f9fafb;flex-shrink:0"></span> Li e aceito este documento</div>'
        : '';
      docsHtml +=
        '<div style="padding:12px;border:1px solid #f3f4f6;border-radius:12px;margin-bottom:10px;background:rgba(0,0,0,0.015)">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap">' +
        '<div style="min-width:0"><div style="font-weight:600;font-size:13px;color:#1f2937;line-height:1.3">' +
        dn +
        obr +
        '</div>' +
        (meta ? '<div style="font-size:11px;color:#9ca3af;margin-top:4px">' + meta + '</div>' : '') +
        '</div>' +
        '<div style="display:flex;gap:8px;flex-shrink:0;align-items:center">' +
        '<span style="padding:6px 12px;border-radius:10px;font-size:11px;font-weight:700;color:#fff;background:' +
        cor +
        '">Abrir</span>' +
        (d.permite_download
          ? '<span style="padding:6px 12px;border-radius:10px;font-size:11px;font-weight:600;border:1px solid #e5e7eb;color:#4b5563;background:#fff">Baixar</span>'
          : '<span style="padding:6px 10px;border-radius:10px;font-size:10px;color:#9ca3af;border:1px solid #f3f4f6;background:#fafafa">Download off</span>') +
        '</div></div>' +
        chk +
        '</div>';
    });
    docsHtml += '</div>';
  }

  const mostrarConf = emp.mostrar_mensagem_confianca !== false;
  const txtConf = (emp.mensagem_confianca_proposta && emp.mensagem_confianca_proposta.trim())
    ? emp.mensagem_confianca_proposta.trim()
    : 'Você está recebendo uma proposta organizada, com valores claros.';
  const confHtml =
    mostrarConf && m.status === 'enviado'
      ? '<div style="padding:14px 16px;border-radius:14px;border:2px solid ' +
        cor +
        '44;background:' +
        cor +
        '14;display:flex;gap:12px;align-items:flex-start;margin-bottom:12px">' +
        '<span style="font-size:20px;line-height:1" aria-hidden="true">🛡️</span>' +
        '<p style="margin:0;font-size:12px;color:#374151;line-height:1.5;min-width:0">' +
        _escCfgHtml(txtConf) +
        '</p></div>'
      : '';

  const step = (n, t, s) =>
    '<div style="display:flex;gap:10px;align-items:flex-start">' +
    '<div style="width:22px;height:22px;border-radius:50%;background:' +
    cor +
    ';color:#fff;font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0">' +
    n +
    '</div><div style="min-width:0"><div style="font-size:12px;font-weight:700;color:#1f2937">' +
    _escCfgHtml(t) +
    '</div><div style="font-size:11px;color:#6b7280;margin-top:2px;line-height:1.35">' +
    _escCfgHtml(s) +
    '</div></div></div>';

  const timelineHtml =
    '<div style="padding:14px;border-radius:12px;border:1px dashed #e5e7eb;background:#fafafa;margin-bottom:12px">' +
    '<div style="font-size:11px;font-weight:700;color:#6b7280;margin-bottom:12px">ETAPAS APÓS O ACEITE</div>' +
    '<div style="display:flex;flex-direction:column;gap:10px">' +
    step('1', 'Você aceita a proposta', 'Confirme pela página pública (nome e, se exigido, código).') +
    step('2', 'Nossa equipe recebe', 'Notificação automática para a empresa.') +
    step('3', 'Início da execução', 'Contato para alinhar prazos e detalhes finais.') +
    '</div></div>';

  const acoesHtml =
    m.status === 'enviado'
      ? '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:12px">' +
        '<div style="width:100%;padding:14px;border-radius:14px;text-align:center;font-weight:700;font-size:14px;color:#fff;background:' +
        cor +
        ';opacity:0.93">✅ Aceitar este orçamento</div>' +
        '<div style="width:100%;padding:12px;border-radius:14px;text-align:center;font-weight:600;font-size:13px;color:#374151;border:1px solid #e5e7eb;background:#fff">✏️ Solicitar ajuste</div>' +
        '<div style="width:100%;padding:12px;border-radius:14px;text-align:center;font-weight:600;font-size:13px;color:#dc2626;border:1px solid #fecaca;background:#fff">✕ Recusar proposta</div>' +
        '<p style="text-align:center;font-size:10px;color:#9ca3af;margin:2px 0 0">Somente ilustração · sem ação neste preview</p></div>'
      : '';

  const avisoAceite = (emp.texto_aviso_aceite && emp.texto_aviso_aceite.trim())
    ? emp.texto_aviso_aceite.trim()
    : 'Seu aceite é registrado com data e hora pelo nome informado (aceite autodeclarado).';
  const avisoHtml =
    '<div style="padding:10px 12px;background:#f8fafc;border-radius:10px;font-size:10px;color:#64748b;line-height:1.45;border-left:3px solid ' +
    cor +
    ';margin-bottom:12px">🔒 ' +
    _escCfgHtml(avisoAceite) +
    '</div>';

  const descSobre = (emp.descricao_publica_empresa && emp.descricao_publica_empresa.trim())
    ? emp.descricao_publica_empresa.trim()
    : 'Texto público da empresa.';
  const sobreHtml =
    '<div style="padding:16px;background:#fff;border-radius:14px;border:1px solid #f3f4f6;margin-bottom:12px">' +
    '<div style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:0.06em;margin-bottom:10px">SOBRE A EMPRESA</div>' +
    '<div style="font-weight:800;font-size:15px;color:#111">' +
    nomeEsc +
    '</div>' +
    '<div style="font-size:12px;color:#4b5563;line-height:1.55;margin-top:8px">' +
    _escCfgHtml(descSobre) +
    '</div></div>';

  const mostrarWa = emp.mostrar_botao_whatsapp !== false;
  const waHtml = mostrarWa
    ? '<div style="padding:14px;border-radius:14px;text-align:center;font-weight:700;color:#fff;background:' +
      cor +
      ';margin-bottom:10px;font-size:14px;display:flex;align-items:center;justify-content:center;gap:8px">💬 Tirar dúvidas pelo WhatsApp</div>'
    : '';

  const pdfHtml =
    '<div style="padding:12px;border-radius:14px;text-align:center;font-weight:600;font-size:13px;color:#374151;border:1px solid #e5e7eb;background:#fff;margin-bottom:12px">📄 Baixar PDF do orçamento</div>';

  const lblAss = (emp.texto_assinatura_proposta && emp.texto_assinatura_proposta.trim())
    ? emp.texto_assinatura_proposta.trim()
    : 'Proposta elaborada por';
  const assHtml =
    '<div style="padding:14px;background:#f9fafb;border-radius:12px;border:1px solid #f1f5f9;display:flex;align-items:center;gap:12px;margin-bottom:12px">' +
    '<div style="flex:1;min-width:0">' +
    '<div style="font-size:10px;color:#6b7280;font-weight:700;letter-spacing:0.05em">' +
    _escCfgHtml(lblAss) +
    '</div>' +
    '<div style="font-weight:800;font-size:14px;color:#111;margin-top:4px">' +
    nomeEsc +
    '</div>' +
    (mostrarWa
      ? '<div style="font-size:12px;font-weight:600;margin-top:6px;color:' + cor + '">Fale conosco pelo WhatsApp →</div>'
      : '') +
    '</div></div>';

  const posAprovHtml =
    '<div style="padding:12px;border-radius:12px;background:#f1f5f9;border:1px dashed #cbd5e1;margin-bottom:8px">' +
    '<div style="font-size:10px;font-weight:700;color:#64748b;margin-bottom:6px">APÓS APROVAÇÃO (NA PÁGINA REAL)</div>' +
    '<div style="font-size:11px;color:#64748b;line-height:1.5">Podem aparecer, conforme o orçamento: <strong>PIX / QR Code</strong>, ' +
    '<strong>agendamento</strong>, <strong>situação financeira</strong>, <strong>entrada</strong> e outras seções configuradas.</div></div>';

  const notaRodape =
    '<p style="font-size:10px;color:#9ca3af;text-align:center;margin:0;line-height:1.45">Preview estático · a página pública é interativa e reflete o orçamento real.</p>';

  return {
    topoContato,
    prazoHtml,
    stack:
      obsHtml +
      docsHtml +
      confHtml +
      timelineHtml +
      acoesHtml +
      avisoHtml +
      sobreHtml +
      waHtml +
      pdfHtml +
      assHtml +
      posAprovHtml +
      notaRodape,
  };
}

/** HTML estático do layout público (clássico ou moderno), sem iframe nem interação. */
function _renderStaticPreviewTemplatePublico() {
  const m = _buildMockOrcamentoPublico();
  const cor = _escCfgHtml(m.empresa.cor_primaria);
  const nome = _escCfgHtml(m.empresa.nome);
  const cliente = _escCfgHtml((m.cliente && m.cliente.nome) || '—');
  const numero = _escCfgHtml(m.numero || '—');
  const tpl = m.empresa.template_publico === 'moderno' ? 'moderno' : 'classico';
  const emissao = new Date(m.criado_em).toLocaleDateString('pt-BR');
  const vd = new Date(m.criado_em);
  vd.setDate(vd.getDate() + (m.validade_dias || 7));
  const validadeStr = vd.toLocaleDateString('pt-BR');
  const forma = _escCfgHtml(
    m.forma_pagamento === 'pix'
      ? 'PIX'
      : m.forma_pagamento === 'a_vista'
        ? 'À vista'
        : String(m.forma_pagamento || 'PIX'),
  );
  const itens = m.itens || [];
  const subtotal = itens.reduce((s, i) => s + (Number(i.total) || 0), 0);
  const desc = Number(m.desconto) || 0;
  const descTipo = m.desconto_tipo || 'percentual';
  const descVal = desc > 0 ? (descTipo === 'percentual' ? subtotal * desc / 100 : desc) : 0;
  const itensRows = itens
    .map((i) => {
      const descItem = _escCfgHtml(i.descricao);
      const qtd = _formatQtdCfg(i.quantidade);
      const unit = _fmtBrlCfg(i.valor_unit);
      const tot = _fmtBrlCfg(i.total);
      return (
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px solid #f3f4f6">' +
        '<div style="min-width:0"><div style="font-weight:600;color:#1f2937;font-size:13px;line-height:1.35">' +
        descItem +
        '</div>' +
        '<div style="font-size:11px;color:#9ca3af;margin-top:2px">' +
        qtd +
        ' × ' +
        unit +
        '</div></div>' +
        '<div style="font-weight:700;font-size:13px;color:#111;flex-shrink:0">' +
        tot +
        '</div></div>'
      );
    })
    .join('');

  const subtotalLinha =
    desc > 0
      ? '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;padding:4px 0"><span>Subtotal</span><span>' +
        _fmtBrlCfg(subtotal) +
        '</span></div>'
      : '';

  const descontoBlock =
    desc > 0
      ? '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;padding:4px 0">' +
        '<span>' +
        (descTipo === 'percentual' ? 'Desconto (' + _escCfgHtml(String(desc)) + '%)' : 'Desconto') +
        '</span>' +
        '<span style="color:#dc2626;font-weight:600">- ' +
        _fmtBrlCfg(descVal) +
        '</span></div>'
      : '';

  const extras = _buildStaticPreviewExtras(m, cor, nome);

  if (tpl === 'moderno') {
    const rowsTbl = itens
      .map((i, idx) => {
        const bg = idx % 2 === 0 ? '#ffffff' : '#fafbfc';
        return (
          '<tr style="background:' +
          bg +
          '">' +
          '<td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:12px;color:#334155">' +
          _escCfgHtml(i.descricao) +
          '</td>' +
          '<td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;text-align:center;font-size:12px">' +
          _formatQtdCfg(i.quantidade) +
          '</td>' +
          '<td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:12px">' +
          _fmtBrlCfg(i.valor_unit) +
          '</td>' +
          '<td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:12px;font-weight:600">' +
          _fmtBrlCfg(i.total) +
          '</td></tr>'
        );
      })
      .join('');
    const tfoot =
      desc > 0
        ? '<tr><td colspan="3" style="padding:8px 14px;text-align:right;font-size:12px;color:#64748b">Subtotal</td>' +
          '<td style="padding:8px 14px;font-size:12px;font-weight:600">' +
          _fmtBrlCfg(subtotal) +
          '</td></tr>' +
          '<tr><td colspan="3" style="padding:8px 14px;text-align:right;font-size:12px;color:#ef4444">Desconto</td>' +
          '<td style="padding:8px 14px;font-size:12px;font-weight:600;color:#ef4444">- ' +
          _fmtBrlCfg(descVal) +
          '</td></tr>'
        : '';
    return (
      '<div class="cfg-static-preview" style="padding:16px;background:#f1f5f9">' +
      '<div style="max-width:560px;margin:0 auto;background:white;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,0.07);overflow:hidden;padding:0 14px 18px">' +
      extras.prazoHtml +
      '<div style="text-align:center;padding:16px 8px 8px">' +
      '<div style="font-size:22px;font-weight:800;color:' +
      cor +
      ';margin-bottom:4px">' +
      nome +
      '</div>' +
      (extras.topoContato
        ? '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;line-height:1.35">' + extras.topoContato + '</div>'
        : '') +
      '<div style="font-size:13px;color:#64748b">Orçamento Nº ' +
      numero +
      '</div>' +
      '<div style="display:inline-block;margin-top:10px;padding:6px 14px;border-radius:999px;font-size:12px;font-weight:600;background:#fef9c3;color:#854d0e">⏳ Aguardando aprovação</div>' +
      '<p style="margin:12px 0 0;font-size:12px;color:#64748b"><strong>Cliente:</strong> ' +
      cliente +
      '</p></div>' +
      '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:0 0 14px">' +
      '<div style="background:#f8fafc;border-radius:10px;padding:10px"><div style="font-size:10px;color:#64748b;font-weight:600">Emissão</div>' +
      '<div style="font-size:12px;font-weight:600;margin-top:2px">' +
      emissao +
      '</div></div>' +
      '<div style="background:#f8fafc;border-radius:10px;padding:10px"><div style="font-size:10px;color:#64748b;font-weight:600">Validade</div>' +
      '<div style="font-size:12px;font-weight:600;margin-top:2px">' +
      validadeStr +
      '</div></div>' +
      '<div style="background:#f8fafc;border-radius:10px;padding:10px"><div style="font-size:10px;color:#64748b;font-weight:600">Pagamento</div>' +
      '<div style="font-size:12px;font-weight:600;margin-top:2px">' +
      forma +
      '</div></div></div>' +
      '<div style="border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;margin-bottom:14px">' +
      '<div style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:0.06em;padding:10px 12px 0;background:#fff">ITENS DO ORÇAMENTO</div>' +
      '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
      '<thead><tr>' +
      '<th style="background:#f1f5f9;padding:10px 12px;text-align:left;font-weight:600;color:#334155">Descrição</th>' +
      '<th style="background:#f1f5f9;padding:10px 8px;text-align:center;font-weight:600;color:#334155">Qtd</th>' +
      '<th style="background:#f1f5f9;padding:10px 10px;text-align:left;font-weight:600;color:#334155">Unit.</th>' +
      '<th style="background:#f1f5f9;padding:10px 12px;text-align:left;font-weight:600;color:#334155">Total</th>' +
      '</tr></thead><tbody>' +
      rowsTbl +
      '</tbody><tfoot>' +
      tfoot +
      '</tfoot></table>' +
      '<div style="padding:12px 14px;background:#fafafa;border-top:1px solid #f1f5f9">' +
      subtotalLinha +
      descontoBlock +
      '<div style="display:flex;justify-content:center;padding-top:8px"><span style="font-size:20px;font-weight:800;color:' +
      cor +
      '">' +
      _fmtBrlCfg(m.total) +
      '</span></div></div></div>' +
      extras.stack +
      '</div></div>'
    );
  }

  const grid2 =
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">' +
    '<div><div style="font-size:10px;color:#9ca3af;font-weight:600">EMISSÃO</div>' +
    '<div style="font-size:13px;font-weight:600;color:#374151;margin-top:2px">' +
    emissao +
    '</div></div>' +
    '<div><div style="font-size:10px;color:#9ca3af;font-weight:600">VALIDADE</div>' +
    '<div style="font-size:13px;font-weight:600;color:#374151;margin-top:2px">' +
    validadeStr +
    '</div></div>' +
    '<div><div style="font-size:10px;color:#9ca3af;font-weight:600">PAGAMENTO</div>' +
    '<div style="font-size:13px;font-weight:600;color:#374151;margin-top:2px">' +
    forma +
    '</div></div>' +
    '<div><div style="font-size:10px;color:#9ca3af;font-weight:600">CLIENTE</div>' +
    '<div style="font-size:13px;font-weight:600;color:#374151;margin-top:2px">' +
    cliente +
    '</div></div></div>';

  return (
    '<div class="cfg-static-preview" style="padding:14px;background:#e5e7eb">' +
    '<div style="max-width:520px;margin:0 auto">' +
    '<div style="background:' +
    cor +
    ';color:#fff;border-radius:14px 14px 0 0;padding:16px 18px">' +
    '<div style="font-weight:800;font-size:18px;letter-spacing:-0.02em">' +
    nome +
    '</div>' +
    (extras.topoContato
      ? '<div style="font-size:11px;opacity:0.9;margin-top:6px;line-height:1.35">' + extras.topoContato + '</div>'
      : '') +
    '<div style="font-size:10px;opacity:0.75;margin-top:8px;text-transform:uppercase;letter-spacing:0.06em">Preview fictício</div></div>' +
    '<div style="background:#fff;border-radius:0 0 14px 14px;box-shadow:0 8px 24px rgba(0,0,0,0.06);overflow:hidden;padding:16px 18px 18px">' +
    extras.prazoHtml +
    '<div style="padding:16px;border:1px solid #f3f4f6;border-radius:14px;background:#fff;margin-bottom:12px">' +
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">' +
    '<div><div style="font-size:10px;color:#9ca3af;font-weight:700;letter-spacing:0.06em">ORÇAMENTO</div>' +
    '<div style="font-size:20px;font-weight:800;color:#111;margin-top:4px">' +
    numero +
    '</div></div>' +
    '<span style="font-size:11px;font-weight:700;padding:6px 10px;border-radius:999px;background:#fef9c3;color:#854d0e;flex-shrink:0">Aguardando aprovação</span></div>' +
    grid2 +
    '</div>' +
    '<div style="padding:16px;border:1px solid #f3f4f6;border-radius:14px;background:#fff;margin-bottom:12px">' +
    '<div style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:0.06em;margin-bottom:12px">ITENS DO ORÇAMENTO</div>' +
    itensRows +
    subtotalLinha +
    descontoBlock +
    '<div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;margin-top:8px;border-top:2px solid #f3f4f6">' +
    '<span style="font-size:13px;font-weight:700;color:#374151">TOTAL</span>' +
    '<span style="font-size:20px;font-weight:800;color:' +
    cor +
    '">' +
    _fmtBrlCfg(m.total) +
    '</span></div></div>' +
    extras.stack +
    '</div></div></div>'
  );
}

function _buildMockOrcamentoPublico() {
  const nomeEmpresa = (document.getElementById('emp-nome')?.value || '').trim() || 'Empresa Exemplo';
  const telefone = (document.getElementById('emp-telefone')?.value || '').trim() || '(11) 99999-0000';
  const email = (document.getElementById('emp-email')?.value || '').trim() || 'contato@empresaexemplo.com';
  const cor = (document.getElementById('emp-cor')?.value || '#00e5a0').trim() || '#00e5a0';
  const validadeDias = parseInt(document.getElementById('emp-validade')?.value, 10) || 7;
  const politica = document.getElementById('emp-politica-agendamento-orc')?.value || 'PADRAO_NAO';
  const mapPreview = {
    PADRAO_NAO: 'NAO_USA',
    PADRAO_SIM: 'OPCIONAL',
    EXIGE_ESCOLHA: 'OPCIONAL',
    PADRAO_OBRIGATORIO: 'OBRIGATORIO',
  };
  const agendamentoModoMock = mapPreview[politica] || 'NAO_USA';
  const total = 1870.0;
  const desconto = 120.0;
  const criadoEm = new Date().toISOString();
  const otpMinimo = parseFloat(document.getElementById('otp-valor-minimo')?.value || '0') || 0;
  return {
    numero: 'ORC-123-26',
    status: 'enviado',
    total,
    desconto,
    desconto_tipo: 'fixo',
    forma_pagamento: 'pix',
    validade_dias: validadeDias,
    observacoes:
      'Este preview usa dados fictícios. Na página real, observações do orçamento aparecem aqui. ' +
      'Inclua prazos de execução, condições comerciais ou observações técnicas para o cliente.',
    criado_em: criadoEm,
    aceite_nome: null,
    aceite_em: null,
    aceite_mensagem: null,
    aceite_confirmado_otp: false,
    exigir_otp: false,
    recusa_motivo: null,
    agendamento_modo: agendamentoModoMock,
    has_agendamento_pendente: false,
    pix_chave: null,
    pix_tipo: null,
    pix_titular: null,
    pix_payload: null,
    pix_qrcode: null,
    pix_informado_em: null,
    valor_sinal_pix: null,
    pagamento_recebido_em: null,
    regra_pagamento_id: null,
    regra_pagamento_nome: null,
    regra_entrada_percentual: null,
    regra_entrada_metodo: null,
    regra_saldo_percentual: null,
    regra_saldo_metodo: null,
    empresa: {
      nome: nomeEmpresa,
      telefone,
      telefone_operador: telefone,
      email,
      logo_url: null,
      cor_primaria: cor,
      descricao_publica_empresa: 'Somos especialistas em atendimento rapido e execução com qualidade.',
      texto_aviso_aceite: 'Preview de aceite. Nenhuma ação será persistida.',
      mostrar_botao_whatsapp: true,
      texto_assinatura_proposta: 'Proposta elaborada por',
      mensagem_confianca_proposta: 'Você está vendo uma simulação da página pública para validar o layout.',
      mostrar_mensagem_confianca: true,
      exigir_otp_aceite: false,
      otp_valor_minimo: otpMinimo,
      template_publico: _normalizarTemplatePublico(_templateSelecionado),
    },
    cliente: {
      nome: 'Cliente Exemplo',
      telefone: '(11) 98888-7777',
    },
    itens: [
      { descricao: 'Instalação elétrica completa', quantidade: 1, valor_unit: 950, total: 950, imagem_url: null },
      { descricao: 'Quadro de distribuição e disjuntores', quantidade: 1, valor_unit: 620, total: 620, imagem_url: null },
      { descricao: 'Acabamentos e testes finais', quantidade: 1, valor_unit: 420, total: 420, imagem_url: null },
    ],
    documentos: [
      {
        id: 1,
        documento_nome: 'Termos de prestação de serviço',
        documento_tipo: 'PDF',
        documento_versao: '2',
        obrigatorio: false,
        permite_download: true,
      },
      {
        id: 2,
        documento_nome: 'Política de privacidade (LGPD)',
        documento_tipo: 'PDF',
        documento_versao: '1',
        obrigatorio: true,
        permite_download: false,
      },
    ],
    pagamentos_financeiros: [],
    contas_financeiras_publico: [],
  };
}

function abrirPreviewTemplatePublico() {
  const host = document.getElementById('static-preview-template-host');
  const modal = document.getElementById('modal-preview-template-publico');
  if (!host || !modal) return;
  try {
    host.innerHTML = _renderStaticPreviewTemplatePublico();
    modal.classList.add('open');
    host.setAttribute('aria-hidden', 'false');
  } catch (e) {
    console.error('Preview template público:', e);
    showNotif('❌', 'Preview', 'Não foi possível montar o preview.', 'error');
  }
}

function fecharModalPreviewTemplatePublico() {
  const modal = document.getElementById('modal-preview-template-publico');
  const host = document.getElementById('static-preview-template-host');
  if (modal) modal.classList.remove('open');
  if (host) {
    host.innerHTML = '';
    host.setAttribute('aria-hidden', 'true');
  }
}

function _onCfgPreviewTemplateEscape(ev) {
  if (ev.key !== 'Escape') return;
  const m = document.getElementById('modal-preview-template-publico');
  if (m && m.classList.contains('open')) fecharModalPreviewTemplatePublico();
}

async function salvarTemplateUnificado(btn) {
  if (btn) setLoading(btn, true);
  try {
    const tpl = _normalizarTemplatePublico(_templateSelecionado);
    await api.patch('/empresa/', { 
      template_publico: tpl,
      template_orcamento: tpl 
    });
    showNotif('✅', 'Template salvo!', 'O novo layout foi aplicado à página pública e aos arquivos PDF.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    if (btn) setLoading(btn, false, 'Salvar template do orçamento');
  }
}

/** Evita depender de onclick inline (CSP / pop-up blockers inconsistentes). */
function initTemplatePublicoUI() {
  const grid = document.getElementById('template-selector-grid');
  if (grid) {
    grid.addEventListener('click', (ev) => {
      const opt = ev.target.closest('.template-option[data-template]');
      if (!opt) return;
      const tpl = opt.getAttribute('data-template');
      if (tpl === 'classico' || tpl === 'moderno') selecionarTemplate(tpl);
    });
    grid.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      const opt = ev.target.closest('.template-option[data-template]');
      if (!opt || !grid.contains(opt)) return;
      ev.preventDefault();
      const tpl = opt.getAttribute('data-template');
      if (tpl === 'classico' || tpl === 'moderno') selecionarTemplate(tpl);
    });
  }
  document.getElementById('btn-preview-template')?.addEventListener('click', () => abrirPreviewTemplatePublico());
  document.getElementById('btn-fechar-preview-template')?.addEventListener('click', () => fecharModalPreviewTemplatePublico());
  document.addEventListener('keydown', _onCfgPreviewTemplateEscape);
  const btnSalvar = document.getElementById('btn-salvar-template');
  if (btnSalvar) btnSalvar.addEventListener('click', () => salvarTemplateUnificado(btnSalvar));

  // Restaurar salvamento imediato do anexo de WhatsApp
  document.getElementById('enviar-pdf-whatsapp')?.addEventListener('change', async (ev) => {
    try {
      const v = Boolean(ev.target.checked);
      console.debug('[Config] Salvando anexo WA imediato:', v);
      await api.patch('/empresa/', { enviar_pdf_whatsapp: v });
      showNotif('✅', 'Salvo!', 'Configuração de anexo atualizada.');
    } catch (err) {
      showNotif('❌', 'Erro', err.message, 'error');
      // Reverte visualmente se falhar
      ev.target.checked = !ev.target.checked;
    }
  });
}

// Handlers globais para compatibilidade com onclick em outras partes da página / testes
window.selecionarTemplate = selecionarTemplate;
window.salvarTemplateUnificado = salvarTemplateUnificado;
window.abrirPreviewTemplatePublico = abrirPreviewTemplatePublico;
window.fecharModalPreviewTemplatePublico = fecharModalPreviewTemplatePublico;

initTemplatePublicoUI();
