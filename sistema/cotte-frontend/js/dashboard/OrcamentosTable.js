/**
 * Componente OrcamentosTable - Tabela de orçamentos do dashboard
 */

import { formatarMoeda, formatarData, formatarStatusOrcamento } from '../utils/formatters.js';

export default class OrcamentosTable {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.orcamentos = [];
    this.clientes = [];
    this.limiteVisiveis = 8;
    this.statusFiltro = '';
    
    if (!this.container) {
      console.error(`[OrcamentosTable] Container não encontrado: ${containerId}`);
      throw new Error(`Container ${containerId} não encontrado`);
    }
  }

  /**
   * Carrega dados e renderiza a tabela
   * @param {Array} orcamentos - Lista de orçamentos
   * @param {Array} clientes - Lista de clientes (para mapeamento)
   */
  async load(orcamentos = [], clientes = []) {
    console.log('[OrcamentosTable] Carregando tabela...');
    
    this.orcamentos = orcamentos || [];
    this.clientes = clientes || [];
    
    // Ordenar orçamentos por data (mais recente primeiro)
    this.ordenarOrcamentos();
    
    // Renderizar tabela
    this.render();
    
    // Configurar event listeners
    this.setupEventListeners();
    
    console.log('[OrcamentosTable] Tabela carregada:', this.orcamentos.length, 'orcamentos');
  }

  /**
   * Ordena orçamentos por data (mais recente primeiro)
   */
  ordenarOrcamentos() {
    if (!Array.isArray(this.orcamentos)) return;
    
    this.orcamentos = [...this.orcamentos].sort((a, b) => {
      const dataA = new Date(a.criado_em || a.criado_em_iso || 0);
      const dataB = new Date(b.criado_em || b.criado_em_iso || 0);
      return dataB - dataA; // Ordem decrescente
    });
  }

  /**
   * Renderiza a tabela
   */
  render() {
    if (this.orcamentos.length === 0) {
      this.renderEmpty();
      return;
    }
    
    // Aplicar filtro se houver
    const orcamentosFiltrados = this.aplicarFiltro();
    
    // Limitar orçamentos visíveis
    const orcamentosVisiveis = orcamentosFiltrados.slice(0, this.limiteVisiveis);
    
    // Renderizar linhas da tabela
    this.container.innerHTML = this.renderTableRows(orcamentosVisiveis);
    
    // Atualizar botão "Carregar mais"
    this.updateCarregarMaisButton(orcamentosFiltrados.length);
  }

  /**
   * Renderiza estado vazio
   */
  renderEmpty() {
    this.container.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;padding:40px 20px;color:var(--muted)">
          <div style="display:flex;flex-direction:column;align-items:center;gap:12px">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
              stroke-linecap="round" stroke-linejoin="round" style="opacity:0.5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="3" y1="9" x2="21" y2="9"></line>
              <line x1="9" y1="21" x2="9" y2="9"></line>
            </svg>
            <div>Nenhum orçamento encontrado</div>
            <button class="btn btn-outline" onclick="window.AppState.components.modals?.abrirModal('novo-orcamento')" style="margin-top:8px">
              Criar primeiro orçamento
            </button>
          </div>
        </td>
      </tr>
    `;
    
    // Esconder botão "Carregar mais"
    const btnCarregarMais = document.getElementById('dashboard-carregar-mais');
    if (btnCarregarMais) {
      btnCarregarMais.style.display = 'none';
    }
  }

  /**
   * Renderiza as linhas da tabela
   * @param {Array} orcamentos - Orçamentos a serem renderizados
   * @returns {string} HTML das linhas da tabela
   */
  renderTableRows(orcamentos) {
    return orcamentos.map(orcamento => this.renderTableRow(orcamento)).join('');
  }

  /**
   * Renderiza uma linha da tabela
   * @param {object} orcamento - Dados do orçamento
   * @returns {string} HTML da linha
   */
  renderTableRow(orcamento) {
    const statusInfo = formatarStatusOrcamento(orcamento.status);
    const clienteNome = orcamento.cliente_nome || this.getClienteNome(orcamento.cliente_id) || '—';
    const servico = orcamento.servico || orcamento.descricao || '—';
    const valor = orcamento.total || 0;
    const dataCriacao = formatarData(orcamento.criado_em, false);
    
    return `
      <tr data-orcamento-id="${orcamento.id}" class="orcamento-row">
        <td>
          <div class="cliente-cell">
            <div class="cliente-nome">${this.escapeHtml(clienteNome)}</div>
            <div class="cliente-data">${dataCriacao}</div>
          </div>
        </td>
        <td>
          <div class="servico-cell" title="${this.escapeHtml(servico)}">
            ${this.truncarTexto(this.escapeHtml(servico), 40)}
          </div>
        </td>
        <td>
          <div class="valor-cell">${formatarMoeda(valor)}</div>
        </td>
        <td>
          <span class="status-badge ${statusInfo.classe}" title="${statusInfo.texto}">
            ${statusInfo.icone} ${statusInfo.texto}
          </span>
        </td>
        <td style="text-align:right">
          <div class="action-buttons">
            <button class="btn-icon" onclick="window.AppState.components.orcamentosTable?.abrirDetalhes(${orcamento.id})" title="Ver detalhes">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            </button>
            <button class="btn-icon" onclick="window.AppState.components.orcamentosTable?.editarOrcamento(${orcamento.id})" title="Editar">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
            <button class="btn-icon" onclick="window.AppState.components.orcamentosTable?.enviarWhatsapp(${orcamento.id})" title="Enviar por WhatsApp">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
              </svg>
            </button>
          </div>
        </td>
      </tr>
    `;
  }

  /**
   * Aplica filtro de status aos orçamentos
   * @returns {Array} Orçamentos filtrados
   */
  aplicarFiltro() {
    if (!this.statusFiltro) {
      return this.orcamentos;
    }
    
    return this.orcamentos.filter(o => o.status === this.statusFiltro);
  }

  /**
   * Atualiza o botão "Carregar mais"
   * @param {number} totalFiltrados - Total de orçamentos filtrados
   */
  updateCarregarMaisButton(totalFiltrados) {
    const btnCarregarMais = document.getElementById('dashboard-carregar-mais');
    if (!btnCarregarMais) return;
    
    if (totalFiltrados > this.limiteVisiveis) {
      btnCarregarMais.style.display = 'block';
    } else {
      btnCarregarMais.style.display = 'none';
    }
  }

  /**
   * Configura event listeners
   */
  setupEventListeners() {
    // Event listeners para as linhas da tabela
    const rows = this.container.querySelectorAll('.orcamento-row');
    rows.forEach(row => {
      row.addEventListener('click', this.handleRowClick);
      row.addEventListener('mouseenter', this.handleRowHover);
      row.addEventListener('mouseleave', this.handleRowLeave);
    });
    
    // Event listener para filtros (se existirem)
    this.setupFilterListeners();
  }

  /**
   * Handler para clique em linha
   * @param {Event} event 
   */
  handleRowClick(event) {
    const row = event.currentTarget;
    const orcamentoId = row.getAttribute('data-orcamento-id');
    
    // Não disparar se clicou em um botão de ação
    if (event.target.closest('.action-buttons')) {
      return;
    }
    
    console.log('[OrcamentosTable] Linha clicada:', orcamentoId);
    // Abrir detalhes do orçamento
    window.AppState.components.orcamentosTable?.abrirDetalhes(parseInt(orcamentoId));
  }

  /**
   * Handler para hover em linha
   * @param {Event} event 
   */
  handleRowHover(event) {
    const row = event.currentTarget;
    row.style.backgroundColor = 'var(--surface-hover)';
  }

  /**
   * Handler para sair do hover
   * @param {Event} event 
   */
  handleRowLeave(event) {
    const row = event.currentTarget;
    row.style.backgroundColor = '';
  }

  /**
   * Configura listeners para filtros
   */
  setupFilterListeners() {
    // Se houver filtros na página, conectar a este componente
    const filterSelect = document.querySelector('#table-filters-container select');
    if (filterSelect) {
      filterSelect.addEventListener('change', (event) => {
        this.aplicarFiltroStatus(event.target.value);
      });
    }
  }

  /**
   * Aplica filtro por status
   * @param {string} status - Status para filtrar
   */
  aplicarFiltroStatus(status) {
    console.log('[OrcamentosTable] Aplicando filtro:', status);
    this.statusFiltro = status;
    this.limiteVisiveis = 8; // Resetar limite
    this.render();
  }

  /**
   * Carrega mais orçamentos
   */
  carregarMais() {
    this.limiteVisiveis += 8;
    this.render();
    console.log('[OrcamentosTable] Carregando mais orçamentos. Limite:', this.limiteVisiveis);
  }

  /**
   * Obtém nome do cliente pelo ID
   * @param {number} clienteId - ID do cliente
   * @returns {string} Nome do cliente
   */
  getClienteNome(clienteId) {
    if (!clienteId || !this.clientes.length) return null;
    
    const cliente = this.clientes.find(c => c.id === clienteId);
    return cliente ? cliente.nome : null;
  }

  /**
   * Abre modal de detalhes do orçamento
   * @param {number} orcamentoId - ID do orçamento
   */
  abrirDetalhes(orcamentoId) {
    console.log('[OrcamentosTable] Abrindo detalhes do orçamento:', orcamentoId);
    
    // Disparar evento para o componente de modais
    window.AppState.dispatchEvent('modal:abrir', {
      modal: 'detalhes-orcamento',
      orcamentoId
    });
  }

  /**
   * Abre modal para editar orçamento
   * @param {number} orcamentoId - ID do orçamento
   */
  editarOrcamento(orcamentoId) {
    console.log('[OrcamentosTable] Editando orçamento:', orcamentoId);
    
    // Disparar evento para o componente de modais
    window.AppState.dispatchEvent('modal:abrir', {
      modal: 'editar-orcamento',
      orcamentoId
    });
  }

  /**
   * Envia orçamento por WhatsApp
   * @param {number} orcamentoId - ID do orçamento
   */
  async enviarWhatsapp(orcamentoId) {
    console.log('[OrcamentosTable] Enviando orçamento por WhatsApp:', orcamentoId);
    
    // Encontrar orçamento
    const orcamento = this.orcamentos.find(o => o.id === orcamentoId);
    if (!orcamento) {
      console.error('[OrcamentosTable] Orçamento não encontrado:', orcamentoId);
      return;
    }
    
    // Verificar se tem telefone do cliente
    const cliente = this.clientes.find(c => c.id === orcamento.cliente_id);
    if (!cliente || !cliente.telefone) {
      alert('Cliente não tem telefone cadastrado para envio por WhatsApp.');
      return;
    }
    
    const st = (orcamento.status || '').toLowerCase();
    const precisaConfirmar =
      !!orcamento.enviado_em || !!(st && st !== 'rascunho');
    if (precisaConfirmar) {
      let ok = true;
      if (typeof cotteConfirmarReenvioSeNecessario === 'function') {
        ok = await cotteConfirmarReenvioSeNecessario(orcamento, 'whatsapp');
      } else if (
        !confirm(
          'Este orçamento já foi enviado ao cliente antes. Deseja enviar novamente pelo WhatsApp?'
        )
      ) {
        ok = false;
      }
      if (!ok) return;
    }

    // Disparar evento para envio
    window.AppState.dispatchEvent('orcamento:enviar-whatsapp', {
      orcamentoId,
      telefone: cliente.telefone
    });
  }

  /**
   * Atualiza a tabela com novos dados
   * @param {Array} newOrcamentos - Novos orçamentos
   * @param {Array} newClientes - Novos clientes (opcional)
   */
  update(newOrcamentos, newClientes = null) {
    if (newOrcamentos) {
      this.orcamentos = newOrcamentos;
      this.ordenarOrcamentos();
    }
    
    if (newClientes) {
      this.clientes = newClientes;
    }
    
    this.render();
    console.log('[OrcamentosTable] Tabela atualizada');
  }

  /**
   * Utilitário para escapar HTML
   * @param {string} text - Texto a ser escapado
   * @returns {string} Texto escapado
   */
  escapeHtml(text) {
    if (!text) return '';
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Trunca texto se for muito longo
   * @param {string} text - Texto a ser truncado
   * @param {number} maxLength - Comprimento máximo
   * @returns {string} Texto truncado
   */
  truncarTexto(text, maxLength = 50) {
    if (!text || text.length <= maxLength) {
      return text;
    }
    
    return text.substring(0, maxLength - 3) + '...';
  }

  /**
   * Destroi o componente e limpa event listeners
   */
  destroy() {
    const rows = this.container.querySelectorAll('.orcamento-row');
    rows.forEach(row => {
      row.removeEventListener('click', this.handleRowClick);
      row.removeEventListener('mouseenter', this.handleRowHover);
      row.removeEventListener('mouseleave', this.handleRowLeave);
    });
    
    this.container.innerHTML = '';
    console.log('[OrcamentosTable] Componente destruído');
  }
}

// Exportar para uso global (opcional)
window.OrcamentosTable = OrcamentosTable;