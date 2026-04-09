/**
 * chat-virtualization.js - Virtualização da lista de mensagens
 * Otimiza performance para conversas longas (100+ mensagens)
 */

class ChatVirtualizer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.bufferSize = options.bufferSize || 5; // Mensagens extras acima/abaixo da viewport
        this.messageHeights = new Map(); // Cache de alturas
        this.visibleRange = { start: 0, end: 0 };
        this.allMessages = [];
        this.isEnabled = false;
        this.totalHeight = 0;
        
        this.init();
    }

    init() {
        // Observer para detectar mudanças no DOM
        this.observer = new MutationObserver(() => {
            this.updateMessageList();
        });
        
        this.observer.observe(this.container, {
            childList: true,
            subtree: false
        });

        // Scroll com debounce
        this.scrollHandler = this.debounce(() => {
            this.renderVisibleMessages();
        }, 16); // ~60fps

        this.container.addEventListener('scroll', this.scrollHandler, { passive: true });
    }

    updateMessageList() {
        const messages = Array.from(this.container.querySelectorAll('.message'));
        if (messages.length < 20) {
            // Desativa virtualização para poucas mensagens
            this.disable();
            return;
        }

        if (!this.isEnabled) {
            this.enable(messages);
        }

        this.allMessages = messages;
        this.calculateTotalHeight();
        this.renderVisibleMessages();
    }

    enable(messages) {
        this.isEnabled = true;
        
        // Cria spacer para manter scroll height correto
        this.spacerTop = document.createElement('div');
        this.spacerTop.className = 'virtual-spacer';
        this.spacerTop.style.position = 'absolute';
        this.spacerTop.style.top = '0';
        this.spacerTop.style.left = '0';
        this.spacerTop.style.right = '0';
        this.spacerTop.style.pointerEvents = 'none';
        
        // Wrapper para mensagens visíveis
        this.visibleWrapper = document.createElement('div');
        this.visibleWrapper.className = 'virtual-visible-wrapper';
        this.visibleWrapper.style.position = 'absolute';
        this.visibleWrapper.style.left = '0';
        this.visibleWrapper.style.right = '0';
        this.visibleWrapper.style.willChange = 'transform';

        // Spacer inferior
        this.spacerBottom = document.createElement('div');
        this.spacerBottom.className = 'virtual-spacer';
        this.spacerBottom.style.position = 'absolute';
        this.spacerBottom.style.left = '0';
        this.spacerBottom.style.right = '0';
        this.spacerBottom.style.bottom = '0';
        this.spacerBottom.style.pointerEvents = 'none';

        // Limpa container e adiciona estrutura virtual
        const scrollTop = this.container.scrollTop;
        this.container.innerHTML = '';
        this.container.appendChild(this.spacerTop);
        this.container.appendChild(this.visibleWrapper);
        this.container.appendChild(this.spacerBottom);
        this.container.scrollTop = scrollTop;
        
        // Define position relative no container
        this.container.style.position = 'relative';
        this.container.style.overflowY = 'auto';
    }

    disable() {
        if (!this.isEnabled) return;
        this.isEnabled = false;
        
        // Restaura conteúdo original
        const allMsgs = [...this.storedMessages || []];
        this.container.innerHTML = '';
        allMsgs.forEach(msg => this.container.appendChild(msg));
        this.container.style.position = '';
        
        this.spacerTop = null;
        this.spacerBottom = null;
        this.visibleWrapper = null;
        this.storedMessages = null;
    }

    calculateTotalHeight() {
        let height = 0;
        this.allMessages.forEach((msg, idx) => {
            const h = this.messageHeights.get(idx) || msg.offsetHeight || 80;
            this.messageHeights.set(idx, h);
            height += h;
        });
        this.totalHeight = height;
    }

    renderVisibleMessages() {
        if (!this.isEnabled || !this.visibleWrapper) return;

        const scrollTop = this.container.scrollTop;
        const viewportHeight = this.container.clientHeight;
        
        // Calcula range visível + buffer
        let accumulatedHeight = 0;
        let startIndex = 0;
        let endIndex = this.allMessages.length - 1;

        // Encontra mensagem inicial
        for (let i = 0; i < this.allMessages.length; i++) {
            const h = this.messageHeights.get(i) || 80;
            if (accumulatedHeight + h >= scrollTop - viewportHeight) {
                startIndex = Math.max(0, i - this.bufferSize);
                break;
            }
            accumulatedHeight += h;
        }

        // Encontra mensagem final
        accumulatedHeight = 0;
        for (let i = 0; i < this.allMessages.length; i++) {
            const h = this.messageHeights.get(i) || 80;
            accumulatedHeight += h;
            if (accumulatedHeight >= scrollTop + viewportHeight * 2) {
                endIndex = Math.min(this.allMessages.length - 1, i + this.bufferSize);
                break;
            }
        }

        // Evita re-render se range não mudou
        if (startIndex === this.visibleRange.start && endIndex === this.visibleRange.end) {
            return;
        }

        this.visibleRange = { start: startIndex, end: endIndex };

        // Atualiza spacers
        let topHeight = 0;
        for (let i = 0; i < startIndex; i++) {
            topHeight += this.messageHeights.get(i) || 80;
        }

        let bottomHeight = 0;
        for (let i = endIndex + 1; i < this.allMessages.length; i++) {
            bottomHeight += this.messageHeights.get(i) || 80;
        }

        this.spacerTop.style.height = topHeight + 'px';
        this.spacerBottom.style.height = bottomHeight + 'px';
        this.visibleWrapper.style.transform = `translateY(${topHeight}px)`;

        // Renderiza mensagens visíveis
        this.visibleWrapper.innerHTML = '';
        for (let i = startIndex; i <= endIndex; i++) {
            const msg = this.allMessages[i].cloneNode(true);
            msg.style.position = 'absolute';
            msg.style.width = '100%';
            
            // Calcula posição Y relativa ao wrapper
            let yPos = 0;
            for (let j = startIndex; j < i; j++) {
                yPos += this.messageHeights.get(j) || 80;
            }
            msg.style.transform = `translateY(${yPos}px)`;
            
            this.visibleWrapper.appendChild(msg);
        }

        // Armazena referências
        this.storedMessages = this.allMessages;
    }

    addMessage(messageEl) {
        this.allMessages.push(messageEl);
        const idx = this.allMessages.length - 1;
        this.messageHeights.set(idx, messageEl.offsetHeight || 80);
        this.calculateTotalHeight();
        this.renderVisibleMessages();
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }
        this.container.removeEventListener('scroll', this.scrollHandler);
        this.disable();
    }
}

// Exporta para uso global
window.ChatVirtualizer = ChatVirtualizer;
