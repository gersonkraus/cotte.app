/**
 * Componente Modals - Gerencia todos os modais do dashboard
 */
export class Modals {
  constructor() {
    this.modals = {};
    this.currentModal = null;
    this.modalOverlay = null;
  }

  /**
   * Inicializa o componente
   */
  async init() {
    // Cria overlay global se não existir
    this.createGlobalOverlay();
    
    // Registra todos os modais
    this.registerModals();
    
    // Configura eventos globais
    this.setupGlobalEvents();
    
    console.log('[Modals] Componente inicializado');
  }

  /**
   * Cria overlay global para modais
   */
  createGlobalOverlay() {
    // Verifica se já existe
    this.modalOverlay = document.getElementById('modal-global-overlay');
    
    if (!this.modalOverlay) {
      this.modalOverlay = document.createElement('div');
      this.modalOverlay.id = 'modal-global-overlay';
      this.modalOverlay.className = 'modal-overlay';
      this.modalOverlay.style.display = 'none';
      this.modalOverlay.innerHTML = `
        <div class="modal" id="modal-global-container">
          <div class="modal-header">
            <h3 id="modal-global-title">Modal</h3>
            <button class="btn-icon modal-close" onclick="Modals.close()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="m15 9-6 6m0-6 6 6"/>
              </svg>
            </button>
          </div>
          <div class="modal-body" id="modal-global-body">
            <!-- Conteúdo dinâmico será injetado aqui -->
          </div>
          <div class="modal-footer" id="modal-global-footer">
            <!-- Rodapé dinâmico -->
          </div>
        </div>
      `;
      
      document.body.appendChild(this.modalOverlay);
    }
  }

  /**
   * Registra todos os modais disponíveis
   */
  registerModals() {
    this.modals = {
      // Modal de novo orçamento
      novoOrcamento: {
        title: 'Novo Orçamento',
        size: 'large',
        content: this.getNovoOrcamentoContent(),
        footer: this.getNovoOrcamentoFooter()
      },
      
      // Modal de detalhes do orçamento
      detalhesOrcamento: {
        title: 'Detalhes do Orçamento',
        size: 'medium',
        content: this.getDetalhesOrcamentoContent(),
        footer: this.getDetalhesOrcamentoFooter()
      },
      
      // Modal de timeline
      timeline: {
        title: 'Timeline Completa',
        size: 'medium',
        content: this.getTimelineContent(),
        footer: this.getTimelineFooter()
      },
      
      // Modal de catálogo
      catalogo: {
        title: 'Catálogo de Serviços',
        size: 'medium',
        content: this.getCatalogoContent(),
        footer: this.getCatalogoFooter()
      },
      
      // Modal de planos
      planos: {
        title: 'Planos e Preços',
        size: 'large',
        content: this.getPlanosContent(),
        footer: this.getPlanosFooter()
      },
      
      // Modal de configurações do WhatsApp
      whatsappConfig: {
        title: 'Configurações do WhatsApp',
        size: 'small',
        content: this.getWhatsAppConfigContent(),
        footer: this.getWhatsAppConfigFooter()
      }
    };
  }

  /**
   * Configura eventos globais
   */
  setupGlobalEvents() {
    // Fecha modal ao clicar no overlay
    this.modalOverlay.addEventListener('click', (e) => {
      if (e.target === this.modalOverlay) {
        this.close();
      }
    });
    
    // Fecha modal com ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.currentModal) {
        this.close();
      }
    });
  }

  /**
   * Abre um modal específico
   * @param {string} modalName - Nome do modal
   * @param {Object} data - Dados para o modal
   */
  open(modalName, data = {}) {
    const modal = this.modals[modalName];
    if (!modal) {
      console.error(`[Modals] Modal "${modalName}" não encontrado`);
      return;
    }
    
    this.currentModal = modalName;
    
    // Atualiza título
    const titleEl = document.getElementById('modal-global-title');
    if (titleEl) {
      titleEl.textContent = modal.title;
    }
    
    // Atualiza conteúdo
    const bodyEl = document.getElementById('modal-global-body');
    if (bodyEl) {
      bodyEl.innerHTML = typeof modal.content === 'function' 
        ? modal.content(data) 
        : modal.content;
    }
    
    // Atualiza rodapé
    const footerEl = document.getElementById('modal-global-footer');
    if (footerEl) {
      footerEl.innerHTML = typeof modal.footer === 'function'
        ? modal.footer(data)
        : modal.footer || '';
    }
    
    // Ajusta tamanho
    const modalContainer = document.getElementById('modal-global-container');
    if (modalContainer) {
      modalContainer.className = 'modal';
      if (modal.size) {
        modalContainer.classList.add(`modal-${modal.size}`);
      }
    }
    
    // Mostra overlay
    this.modalOverlay.style.display = 'flex';
    
    // Dispara evento personalizado
    document.dispatchEvent(new CustomEvent('modalOpened', {
      detail: { modal: modalName, data }
    }));
    
    console.log(`[Modals] Modal "${modalName}" aberto`);
  }

  /**
   * Fecha o modal atual
   */
  close() {
    if (!this.currentModal) return;
    
    // Dispara evento antes de fechar
    document.dispatchEvent(new CustomEvent('modalClosing', {
      detail: { modal: this.currentModal }
    }));
    
    // Esconde overlay
    this.modalOverlay.style.display = 'none';
    
    // Limpa referência
    const previousModal = this.currentModal;
    this.currentModal = null;
    
    // Dispara evento após fechar
    document.dispatchEvent(new CustomEvent('modalClosed', {
      detail: { modal: previousModal }
    }));
    
    console.log(`[Modals] Modal "${previousModal}" fechado`);
  }

  /**
   * Retorna conteúdo HTML para modal de novo orçamento
   */
  getNovoOrcamentoContent() {
    return (data) => `
      <div class="tabs" id="modal-tabs">
        <button class="tab active" onclick="Modals.switchTab('manual')">Manual</button>
        <button class="tab" onclick="Modals.switchTab('ia')">Com IA</button>
      </div>
      
      <div id="tab-manual" style="display:flex;flex-direction:column;gap:18px">
        <div class="form-row">
          <div class="form-group full">
            <label>Cliente</label>
            <div class="cliente-autocomplete">
              <input type="text" id="orc-cliente" placeholder="Digite nome, telefone ou email..." 
                     oninput="Modals.buscarClientes(this.value)">
              <div class="autocomplete-results" id="clientes-results"></div>
            </div>
          </div>
        </div>
        
        <div class="form-group">
          <label>Itens do Orçamento</label>
          <div class="items-section" id="items-list">
            <div class="item-row">
              <div style="position:relative">
                <input type="text" placeholder="Descrição do serviço (digite para buscar no catálogo)" 
                       oninput="Modals.buscarCatalogo(this.value)">
                <div class="autocomplete-results" id="catalogo-results"></div>
              </div>
              <input type="number" placeholder="Qtd" value="1" min="1" style="width:70px" onchange="Modals.calcularTotal()">
              <input type="text" placeholder="R$ 0,00" style="width:120px" oninput="Modals.formatarValor(this)" onchange="Modals.calcularTotal()">
              <button class="btn-icon" onclick="Modals.removerItem(this)" title="Remover">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="m15 9-6 6m0-6 6 6"/>
                </svg>
              </button>
            </div>
          </div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button class="btn-text" onclick="Modals.adicionarItem()">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              Adicionar item
            </button>
            <button class="btn-text" onclick="Modals.open('catalogo')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m21 21-6-6m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z"/>
              </svg>
              Buscar no catálogo
            </button>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>Validade</label>
            <select id="orc-validade" onchange="Modals.calcularTotal()">
              <option value="7">7 dias</option>
              <option value="15" selected>15 dias</option>
              <option value="30">30 dias</option>
              <option value="60">60 dias</option>
            </select>
          </div>
          <div class="form-group">
            <label>Forma de Pagamento</label>
            <select id="orc-pagamento">
              <option value="pix">PIX</option>
              <option value="credito">Cartão de Crédito</option>
              <option value="debito">Cartão de Débito</option>
              <option value="boleto">Boleto</option>
              <option value="dinheiro">Dinheiro</option>
            </select>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>Desconto</label>
            <div style="display:flex;gap:8px;align-items:center">
              <select id="orc-desconto-tipo" onchange="Modals.calcularTotal()" style="width:130px;flex-shrink:0">
                <option value="percentual">Percentual</option>
                <option value="valor">Valor Fixo</option>
              </select>
              <input type="text" id="orc-desconto-valor" placeholder="0" style="flex:1" 
                     oninput="Modals.formatarDesconto(this)" onchange="Modals.calcularTotal()">
            </div>
          </div>
          <div class="form-group">
            <label>Observações</label>
            <textarea id="orc-observacoes" placeholder="Observações adicionais..." rows="2"></textarea>
          </div>
        </div>
        
        <div class="total-row" style="flex-direction:column;align-items:stretch;gap:4px">
          <div style="display:flex;justify-content:space-between">
            <span>Subtotal:</span>
            <span id="subtotal-display">R$ 0,00</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Desconto:</span>
            <span id="desconto-display">R$ 0,00</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border);padding-top:8px;margin-top:4px">
            <strong>Total:</strong>
            <strong style="font-size:18px" id="total-display">R$ 0,00</strong>
          </div>
        </div>
      </div>
      
      <div id="tab-ia" style="display:none;flex-direction:column;gap:14px">
        <div style="background:var(--surface-alt);border-radius:8px;padding:16px;text-align:center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:8px">
            <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8Z"/>
            <path d="M12 8v4l3 3"/>
          </svg>
          <div style="font-size:14px;color:var(--text);margin-bottom:4px">Descreva o orçamento em linguagem natural</div>
          <div style="font-size:12px;color:var(--muted)">Ex: "Orçamento para João Silva, instalação de ar condicionado split 12.000 BTUs"</div>
        </div>
        <div class="form-group">
          <textarea id="orc-ia-texto" placeholder="Descreva o orçamento..." rows="4" 
                    style="width:100%;resize:vertical"></textarea>
        </div>
        <button class="btn btn-primary" style="width:100%;justify-content:center" onclick="Modals.processarIA()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px">
            <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8Z"/>
            <path d="M12 8v4l3 3"/>
          </svg>
          Processar com IA
        </button>
      </div>
    `;
  }

  /**
   * Retorna rodapé para modal de novo orçamento
   */
  getNovoOrcamentoFooter() {
    return () => `
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button class="btn" onclick="Modals.close()">Cancelar</button>
        <button class="btn btn-primary" onclick="Modals.salvarOrcamento()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          Salvar Orçamento
        </button>
      </div>
    `;
  }

  /**
   * Retorna conteúdo HTML para modal de detalhes do orçamento
   */
  getDetalhesOrcamentoContent() {
    return (data) => {
      const orcamento = data.orcamento || {};
      return `
        <div style="display:flex;flex-direction:column;gap:16px">
          <div class="orcamento-header">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <h4 style="margin:0">${orcamento.numero || 'ORC-XXXX-XXX'}</h4>
              <span class="badge badge-${orcamento.status || 'pendente'}">
                ${orcamento.status ? orcamento.status.charAt(0).toUpperCase() + orcamento.status.slice(1) : 'Pendente'}
              </span>
            </div>
            <div style="font-size:13px;color:var(--muted);margin-top:4px">
              Cliente: <strong>${orcamento.cliente_nome || 'Não informado'}</strong>
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>Data de Criação</label>
              <div>${orcamento.data_criacao || new Date().toLocaleDateString('pt-BR')}</div>
            </div>
            <div class="form-group">
              <label>Validade</label>
              <div>${orcamento.validade || '15 dias'}</div>
            </div>
