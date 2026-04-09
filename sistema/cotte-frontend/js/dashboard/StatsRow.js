/**
 * Componente StatsRow - Linha de estatísticas do dashboard
 */

import { formatarMoeda, formatarPorcentagem } from '../utils/formatters.js';

export default class StatsRow {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.stats = null;
    this.orcamentos = [];
    this.clientes = [];
    
    if (!this.container) {
      console.error(`[StatsRow] Container não encontrado: ${containerId}`);
      throw new Error(`Container ${containerId} não encontrado`);
    }
  }

  /**
   * Carrega dados e renderiza o componente
   * @param {object} resumo - Dados resumidos do dashboard
   * @param {Array} orcamentos - Lista de orçamentos
   * @param {Array} clientes - Lista de clientes
   */
  async load(resumo, orcamentos = [], clientes = []) {
    console.log('[StatsRow] Carregando dados...');
    
    this.orcamentos = orcamentos || [];
    this.clientes = clientes || [];
    
    // Se não tiver resumo, calcular com base nos orçamentos
    if (!resumo) {
      this.stats = this.calcularStats();
    } else {
      this.stats = {
        faturamento: resumo.faturamento || 0,
        orcamentosTotal: resumo.orcamentosTotal || orcamentos.length || 0,
        aprovados: resumo.aprovados || 0,
        clientesTotal: resumo.clientesTotal || clientes.length || 0,
        taxaAprovacao: resumo.taxaAprovacao || 0,
        ticketMedio: resumo.ticketMedio || 0
      };
    }
    
    this.render();
    this.setupEventListeners();
    
    console.log('[StatsRow] Componente carregado:', this.stats);
  }

  /**
   * Calcula estatísticas com base nos orçamentos
   * @returns {object} Estatísticas calculadas
   */
  calcularStats() {
    const orcamentos = this.orcamentos || [];
    const clientes = this.clientes || [];
    
    const aprovados = orcamentos.filter(o => o.status === 'aprovado');
    const faturamento = aprovados.reduce((sum, o) => sum + (o.total || 0), 0);
    const ticketMedio = aprovados.length > 0 ? faturamento / aprovados.length : 0;
    const taxaAprovacao = orcamentos.length > 0 
      ? Math.round((aprovados.length / orcamentos.length) * 100) 
      : 0;
    
    return {
      faturamento,
      orcamentosTotal: orcamentos.length,
      aprovados: aprovados.length,
      clientesTotal: clientes.length,
      taxaAprovacao,
      ticketMedio,
      ultimaAtualizacao: new Date().toISOString()
    };
  }

  /**
   * Renderiza o componente
   */
  render() {
    if (!this.stats) {
      this.container.innerHTML = this.renderLoading();
      return;
    }
    
    this.container.innerHTML = this.renderStats();
  }

  /**
   * Renderiza estado de carregamento
   * @returns {string} HTML do loading
   */
  renderLoading() {
    return `
      <div class="stat-card" style="opacity:0.7">
        <div class="stat-value">—</div>
        <div class="stat-label">Carregando...</div>
      </div>
      <div class="stat-card" style="opacity:0.7">
        <div class="stat-value">—</div>
        <div class="stat-label">Carregando...</div>
      </div>
      <div class="stat-card" style="opacity:0.7">
        <div class="stat-value">—</div>
        <div class="stat-label">Carregando...</div>
      </div>
      <div class="stat-card" style="opacity:0.7">
        <div class="stat-value">—</div>
        <div class="stat-label">Carregando...</div>
      </div>
      <div class="stat-card" style="opacity:0.7">
        <div class="stat-value">—</div>
        <div class="stat-label">Carregando...</div>
      </div>
      <div class="stat-card" style="opacity:0.7">
        <div class="stat-value">—</div>
        <div class="stat-label">Carregando...</div>
      </div>
    `;
  }

  /**
   * Renderiza as estatísticas
   * @returns {string} HTML das stats
   */
  renderStats() {
    const { faturamento, orcamentosTotal, aprovados, clientesTotal, taxaAprovacao, ticketMedio } = this.stats;
    
    return `
      <!-- Faturamento -->
      <div class="stat-card green" onclick="location.href='relatorios.html?filtro_aprovacao=aprovados'" title="Ver apenas orçamentos aprovados">
        <div class="stat-icon green">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="1" x2="12" y2="23"></line>
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
          </svg>
        </div>
        <div class="stat-value">${formatarMoeda(faturamento)}</div>
        <div class="stat-label">Faturamento</div>
      </div>
      
      <!-- Total de Orçamentos -->
      <div class="stat-card blue" onclick="location.href='relatorios.html'" title="Ver todos os orçamentos">
        <div class="stat-icon blue">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="9" y1="21" x2="9" y2="9"></line>
          </svg>
        </div>
        <div class="stat-value">${orcamentosTotal}</div>
        <div class="stat-label">Orçamentos</div>
      </div>
      
      <!-- Aprovados -->
      <div class="stat-card orange" onclick="location.href='relatorios.html?filtro_aprovacao=aprovados'" title="Ver orçamentos aprovados">
        <div class="stat-icon orange">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
        <div class="stat-value">${aprovados}</div>
        <div class="stat-label">Aprovados</div>
      </div>
      
      <!-- Clientes -->
      <div class="stat-card purple" onclick="location.href='relatorios.html'" title="Ver relatório por cliente">
        <div class="stat-icon purple">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </div>
        <div class="stat-value">${clientesTotal}</div>
        <div class="stat-label">Clientes</div>
      </div>
      
      <!-- Taxa de Aprovação -->
      <div class="stat-card cyan" onclick="location.href='relatorios.html?filtro_aprovacao=aprovados'" title="Ver taxa de conversão">
        <div class="stat-icon cyan">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
        <div class="stat-value">${formatarPorcentagem(taxaAprovacao)}</div>
        <div class="stat-label">Taxa de Aprovação</div>
      </div>
      
      <!-- Ticket Médio -->
      <div class="stat-card" style="cursor:pointer" onclick="location.href='relatorios.html?filtro_aprovacao=aprovados'" title="Ver ticket médio por cliente">
        <div class="stat-icon purple">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="1" x2="12" y2="23"></line>
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
          </svg>
        </div>
        <div class="stat-value">${formatarMoeda(ticketMedio)}</div>
        <div class="stat-label">Ticket Médio</div>
      </div>
    `;
  }

  /**
   * Configura event listeners
   */
  setupEventListeners() {
    // Tooltips para os cards
    const cards = this.container.querySelectorAll('.stat-card');
    cards.forEach(card => {
      card.addEventListener('mouseenter', this.handleCardHover);
      card.addEventListener('mouseleave', this.handleCardLeave);
      card.addEventListener('click', this.handleCardClick);
    });
    
    // Atualizar tooltip dinâmico
    this.setupDynamicTooltips();
  }

  /**
   * Handler para hover nos cards
   * @param {Event} event 
   */
  handleCardHover(event) {
    const card = event.currentTarget;
    card.style.transform = 'translateY(-2px)';
    card.style.boxShadow = '0 8px 25px rgba(0,0,0,0.1)';
  }

  /**
   * Handler para sair do hover
   * @param {Event} event 
   */
  handleCardLeave(event) {
    const card = event.currentTarget;
    card.style.transform = 'translateY(0)';
    card.style.boxShadow = '';
  }

  /**
   * Handler para clique nos cards
   * @param {Event} event 
   */
  handleCardClick(event) {
    const card = event.currentTarget;
    console.log('[StatsRow] Card clicado:', card.querySelector('.stat-label').textContent);
    
    // Adicionar efeito visual de clique
    card.style.transform = 'scale(0.98)';
    setTimeout(() => {
      card.style.transform = '';
    }, 150);
  }

  /**
   * Configura tooltips dinâmicos com mais informações
   */
  setupDynamicTooltips() {
    // Tooltip customizado para faturamento
    const faturamentoCard = this.container.querySelector('.stat-card.green');
    if (faturamentoCard && this.stats) {
      const tooltipText = `Faturamento total de ${this.stats.aprovados} orçamentos aprovados`;
      faturamentoCard.setAttribute('data-tooltip', tooltipText);
    }
    
    // Tooltip para taxa de aprovação
    const taxaCard = this.container.querySelector('.stat-card.cyan');
    if (taxaCard && this.stats) {
      const tooltipText = `${this.stats.aprovados} aprovados de ${this.stats.orcamentosTotal} orçamentos`;
      taxaCard.setAttribute('data-tooltip', tooltipText);
    }
    
    // Tooltip para ticket médio
    const ticketCard = this.container.querySelector('.stat-card:last-child');
    if (ticketCard && this.stats) {
      const tooltipText = `Valor médio por orçamento aprovado`;
      ticketCard.setAttribute('data-tooltip', tooltipText);
    }
  }

  /**
   * Atualiza as estatísticas com novos dados
   * @param {object} newStats - Novas estatísticas
   */
  update(newStats) {
    if (newStats) {
      this.stats = { ...this.stats, ...newStats };
    } else {
      this.stats = this.calcularStats();
    }
    
    this.render();
    console.log('[StatsRow] Estatísticas atualizadas:', this.stats);
  }

  /**
   * Atualiza apenas uma estatística específica
   * @param {string} key - Chave da estatística
   * @param {any} value - Novo valor
   */
  updateStat(key, value) {
    if (this.stats && key in this.stats) {
      this.stats[key] = value;
      
      // Atualizar apenas o card correspondente
      this.updateCard(key, value);
    }
  }

  /**
   * Atualiza um card específico
   * @param {string} statKey - Chave da estatística
   * @param {any} value - Novo valor
   */
  updateCard(statKey, value) {
    const cardMap = {
      faturamento: '.stat-card.green .stat-value',
      orcamentosTotal: '.stat-card.blue .stat-value',
      aprovados: '.stat-card.orange .stat-value',
      clientesTotal: '.stat-card.purple .stat-value',
      taxaAprovacao: '.stat-card.cyan .stat-value',
      ticketMedio: '.stat-card:last-child .stat-value'
    };
    
    const selector = cardMap[statKey];
    if (!selector) return;
    
    const element = this.container.querySelector(selector);
    if (!element) return;
    
    // Formatar o valor baseado na chave
    let formattedValue = value;
    if (statKey === 'faturamento' || statKey === 'ticketMedio') {
      formattedValue = formatarMoeda(value);
    } else if (statKey === 'taxaAprovacao') {
      formattedValue = formatarPorcentagem(value);
    } else {
      formattedValue = value.toString();
    }
    
    // Animação de atualização
    element.style.opacity = '0.5';
    element.style.transform = 'scale(0.9)';
    
    setTimeout(() => {
      element.textContent = formattedValue;
      element.style.opacity = '1';
      element.style.transform = 'scale(1)';
    }, 150);
  }

  /**
   * Destroi o componente e limpa event listeners
   */
  destroy() {
    const cards = this.container.querySelectorAll('.stat-card');
    cards.forEach(card => {
      card.removeEventListener('mouseenter', this.handleCardHover);
      card.removeEventListener('mouseleave', this.handleCardLeave);
      card.removeEventListener('click', this.handleCardClick);
    });
    
    this.container.innerHTML = '';
    console.log('[StatsRow] Componente destruído');
  }
}

// Exportar para uso global (opcional)
window.StatsRow = StatsRow;