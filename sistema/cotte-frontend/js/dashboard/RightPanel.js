/**
 * Componente RightPanel - Painel direito do dashboard com timeline e chat WhatsApp
 */
export class RightPanel {
  constructor() {
    this.container = null;
    this.timelineContainer = null;
    this.whatsappContainer = null;
    this.whatsappInput = null;
    this.whatsappMessages = [];
    this.timelineEvents = [];
  }

  /**
   * Inicializa o componente
   * @param {HTMLElement} container - Elemento container do painel direito
   */
  async init(container) {
    this.container = container;
    
    // Renderiza a estrutura HTML
    this.render();
    
    // Inicializa elementos DOM
    this.timelineContainer = this.container.querySelector('#timeline-dashboard-list');
    this.whatsappContainer = this.container.querySelector('#wpp-chat');
    this.whatsappInput = this.container.querySelector('#wpp-input');
    
    // Configura eventos
    this.setupEvents();
    
    // Carrega dados iniciais
    await this.loadInitialData();
    
    console.log('[RightPanel] Componente inicializado');
  }

  /**
   * Renderiza a estrutura HTML do painel direito
   */
  render() {
    this.container.innerHTML = `
      <div class="wpp-card">
        <div class="wpp-header">
          <div style="display:flex;align-items:center;gap:8px">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
            </svg>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:7px">
                <strong style="font-size:14px;color:var(--text)">WhatsApp</strong>
                <span class="badge badge-success" style="font-size:10px;padding:2px 6px">Online</span>
              </div>
              <div style="font-size:11px;color:var(--muted);margin-top:2px">Converse com seus clientes</div>
            </div>
          </div>
          <button class="btn-icon" title="Configurar WhatsApp" onclick="Modals.openWhatsAppConfig()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
        </div>
        <div class="wpp-body" id="wpp-chat">
          <div class="msg received" id="wpp-welcome">
            <div class="msg-avatar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="msg-content">
              <div class="msg-sender">COTTE</div>
              <div class="msg-text">Olá! Eu sou o assistente do COTTE. Posso ajudar você a criar orçamentos, enviar mensagens para clientes e muito mais. Como posso ajudar?</div>
              <div class="msg-time">Agora</div>
            </div>
          </div>
        </div>
        <div class="wpp-chips" id="wpp-chips">
          <button class="chip" onclick="this.sendQuickMessage('Criar orçamento')">Criar orçamento</button>
          <button class="chip" onclick="this.sendQuickMessage('Ver orçamentos pendentes')">Ver pendentes</button>
          <button class="chip" onclick="this.sendQuickMessage('Enviar lembrete')">Enviar lembrete</button>
        </div>
        <div class="wpp-input">
          <input type="text" id="wpp-input" placeholder="Digite sua mensagem..." onkeypress="this.handleWhatsAppKeyPress(event)">
          <button class="send-btn" onclick="this.sendWhatsAppMessage()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="m22 2-7 20-4-9-9-4Z"/>
              <path d="M22 2 11 13"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="card timeline-card">
        <div class="card-header">
          <div class="card-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 8v4l3 3"/>
              <circle cx="12" cy="12" r="10"/>
            </svg>
            <span>Atividades Recentes</span>
          </div>
          <button class="btn-icon" title="Ver todas" onclick="Modals.openTimelineModal()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="m9 18 6-6-6-6"/>
            </svg>
          </button>
        </div>
        <div class="activity-list" id="timeline-dashboard-list">
          <div class="activity-item loading">
            <div class="activity-icon">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
              </svg>
            </div>
            <div class="activity-content">
              <div class="activity-text">Carregando atividades...</div>
              <div class="activity-time">Agora</div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Configura eventos do componente
   */
  setupEvents() {
    // Configura evento de tecla Enter no input do WhatsApp
    if (this.whatsappInput) {
      this.whatsappInput.addEventListener('keypress', (e) => this.handleWhatsAppKeyPress(e));
    }
    
    // Configura botão de enviar
    const sendBtn = this.container.querySelector('.send-btn');
    if (sendBtn) {
      sendBtn.addEventListener('click', () => this.sendWhatsAppMessage());
    }
    
    // Configura chips de mensagens rápidas
    const chips = this.container.querySelectorAll('.chip');
    chips.forEach(chip => {
      chip.addEventListener('click', (e) => {
        const text = e.target.textContent;
        this.sendQuickMessage(text);
      });
    });
  }

  /**
   * Carrega dados iniciais
   */
  async loadInitialData() {
    try {
      // Carrega timeline
      await this.loadTimeline();
      
      // Carrega histórico do WhatsApp
      await this.loadWhatsAppHistory();
      
    } catch (error) {
      console.error('[RightPanel] Erro ao carregar dados iniciais:', error);
      this.showTimelineError('Erro ao carregar atividades');
    }
  }

  /**
   * Carrega eventos da timeline
   */
  async loadTimeline() {
    try {
      // Simula carregamento
      setTimeout(() => {
        this.updateTimeline([
          {
            id: 1,
            type: 'orcamento_criado',
            title: 'Novo orçamento criado',
            description: 'ORC-2026-012 para João Silva',
            time: 'há 5 minutos',
            icon: 'plus'
          },
          {
            id: 2,
            type: 'whatsapp_enviado',
            title: 'Mensagem enviada',
            description: 'Para Maria Santos (11 99999-9999)',
            time: 'há 15 minutos',
            icon: 'message-circle'
          },
          {
            id: 3,
            type: 'pagamento_recebido',
            title: 'Pagamento recebido',
            description: 'R$ 1.250,00 de Pedro Costa',
            time: 'há 1 hora',
            icon: 'dollar-sign'
          },
          {
            id: 4,
            type: 'cliente_cadastrado',
            title: 'Cliente cadastrado',
            description: 'Ana Oliveira adicionada ao sistema',
            time: 'há 2 horas',
            icon: 'user-plus'
          }
        ]);
      }, 1000);
      
    } catch (error) {
      console.error('[RightPanel] Erro ao carregar timeline:', error);
      throw error;
    }
  }

  /**
   * Atualiza a timeline com eventos
   * @param {Array} events - Lista de eventos
   */
  updateTimeline(events) {
    if (!this.timelineContainer) return;
    
    this.timelineEvents = events;
    
    if (events.length === 0) {
      this.timelineContainer.innerHTML = `
        <div class="activity-item empty">
          <div class="activity-icon">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 8v4l3 3"/>
              <circle cx="12" cy="12" r="10"/>
            </svg>
          </div>
          <div class="activity-content">
            <div class="activity-text">Nenhuma atividade recente</div>
            <div class="activity-time">-</div>
          </div>
        </div>
      `;
      return;
    }
    
    const html = events.map(event => `
      <div class="activity-item" data-type="${event.type}">
        <div class="activity-icon ${event.type}">
          ${this.getTimelineIcon(event.icon)}
        </div>
        <div class="activity-content">
          <div class="activity-text">
            <strong>${event.title}</strong>
            <div class="activity-desc">${event.description}</div>
          </div>
          <div class="activity-time">${event.time}</div>
        </div>
      </div>
    `).join('');
    
    this.timelineContainer.innerHTML = html;
  }

  /**
   * Retorna ícone SVG para a timeline
   * @param {string} iconName - Nome do ícone
   * @returns {string} SVG do ícone
   */
  getTimelineIcon(iconName) {
    const icons = {
      plus: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
      'message-circle': '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
      'dollar-sign': '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
      'user-plus': '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></svg>',
      check: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
      alert: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
    };
    
    return icons[iconName] || icons.alert;
  }

  /**
   * Mostra erro na timeline
   * @param {string} message - Mensagem de erro
   */
  showTimelineError(message) {
    if (!this.timelineContainer) return;
    
    this.timelineContainer.innerHTML = `
      <div class="activity-item error">
        <div class="activity-icon">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div class="activity-content">
          <div class="activity-text">${message}</div>
          <div class="activity-time">
            <button class="btn-text" onclick="this.loadTimeline()">Tentar novamente</button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Formata tempo relativo (há X minutos/horas)
   * @param {Date} date - Data
   * @returns {string} Tempo formatado
   */
  formatTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Agora';
    if (diffMins < 60) return `há ${diffMins} min`;
    if (diffHours < 24) return `há ${diffHours} h`;
    if (diffDays < 7) return `há ${diffDays} d`;
    return date.toLocaleDateString('pt-BR');
  }

  /**
   * Carrega histórico do WhatsApp
   */
  async loadWhatsAppHistory() {
    try {
      // Simula carregamento de histórico
      setTimeout(() => {
        this.whatsappMessages = [
          {
            id: 1,
            type: 'received',
            sender: 'COTTE',
            text: 'Olá! Eu sou o assistente do COTTE. Posso ajudar você a criar orçamentos, enviar mensagens para clientes e muito mais. Como posso ajudar?',
            time: '10:30'
          },
          {
            id: 2,
            type: 'sent',
            sender: 'Você',
            text: 'Preciso criar um orçamento para instalação de ar condicionado',
            time: '10:32'
          },
          {
            id: 3,
            type: 'received',
            sender: 'COTTE',
            text: 'Claro! Vou criar um orçamento para instalação de ar condicionado. Para qual cliente?',
            time: '10:33'
          }
        ];
        
        this.updateWhatsAppChat();
      }, 500);
      
    } catch (error) {
      console.error('[RightPanel] Erro ao carregar histórico do WhatsApp:', error);
    }
  }

  /**
   * Atualiza o chat do WhatsApp
   */
  updateWhatsAppChat() {
    if (!this.whatsappContainer) return;
    
    // Mantém a mensagem de boas-vindas
    const welcomeMsg = this.whatsappContainer.querySelector('#wpp-welcome');
    const messagesHtml = this.whatsappMessages.map(msg => `
      <div class="msg ${msg.type}" data-id="${msg.id}">
        ${msg.type === 'received' ? `
          <div class="msg-avatar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
        ` : ''}
        <div class="msg-content">
          ${msg.type === 'received' ? `<div class="msg-sender">${msg.sender}</div>` : ''}
          <div class="msg-text">${msg.text}</div>
          <div class="msg-time">${msg.time}</div>
        </div>
      </div>
    `).join('');
    
    // Remove mensagens antigas (exceto a de boas-vindas)
    const existingMessages = this.whatsappContainer.querySelectorAll('.msg:not(#wpp-welcome)');
    existingMessages.forEach(msg => msg.remove());
    
    // Adiciona novas mensagens
    this.whatsappContainer.insertAdjacentHTML('beforeend', messagesHtml);
    
    // Rola para a última mensagem
    this.whatsappContainer.scrollTop = this.whatsappContainer.scrollHeight;
  }

  /**
   * Envia mensagem pelo WhatsApp
   */
  async sendWhatsAppMessage() {
    if (!this.whatsappInput || !this.whatsappInput.value.trim()) return;
    
    const text = this.whatsappInput.value.trim();
    
    // Adiciona mensagem enviada
    const newMessage = {
      id: Date.now(),
      type: 'sent',
      sender: 'Você',
      text: text,
      time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    };
    
    this.whatsappMessages.push(newMessage);
    this.updateWhatsAppChat();
    
    // Limpa input
    this.whatsappInput.value = '';
    
    // Simula resposta do assistente
    setTimeout(() => {
      const responses = [
        'Entendi! Vou processar sua solicitação.',
        'Ótimo! Em que posso ajudar mais?',
        'Certo, vou verificar isso para você.',
        'Perfeito! Algo mais que precise?'
      ];
      
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      
      const responseMessage = {
        id: Date.now() + 1,
        type: 'received',
        sender: 'COTTE',
        text: randomResponse,
        time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
      };
      
      this.whatsappMessages.push(responseMessage);
      this.updateWhatsAppChat();
    }, 1000);
  }

  /**
   * Envia mensagem rápida (chip)
   * @param {string} text - Texto da mensagem
   */
  sendQuickMessage(text) {
    if (!this.whatsappInput) return;
    
    this.whatsappInput.value = text;
    this.sendWhatsAppMessage();
  }

  /**
   * Manipula tecla pressionada no input do WhatsApp
   * @param {KeyboardEvent} event - Evento de tecla
   */
  handleWhatsAppKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendWhatsAppMessage();
    }
  }

  /**
   * Atualiza dados do componente
   * @param {Object} data - Dados para atualização
   */
  update(data) {
    if (data.timelineEvents) {
      this.updateTimeline(data.timelineEvents);
    }
    
    if (data.whatsappMessages) {
      this.whatsappMessages = data.whatsappMessages;
      this.updateWhatsAppChat();
    }
  }

  /**
   * Destroi o componente (limpeza)
   */
  destroy() {
    // Remove event listeners
    if (this.whatsappInput) {
      this.whatsappInput.removeEventListener('keypress', this.handleWhatsAppKeyPress);
    }
    
    const sendBtn = this.container.querySelector('.send-btn');
    if (sendBtn) {
      sendBtn.removeEventListener('click', this.sendWhatsAppMessage);
    }
    
    const chips = this.container.querySelectorAll('.chip');
    chips.forEach(chip => {
      chip.removeEventListener('click', this.sendQuickMessage);
    });
    
    // Limpa referências
    this.container = null;
    this.timelineContainer = null;
    this.whatsappContainer = null;
    this.whatsappInput = null;
    this.whatsappMessages = [];
    this.timelineEvents = [];
    
    console.log('[RightPanel] Componente destruído');
  }
}

// Exporta a classe para uso global
window.RightPanel = RightPanel;
