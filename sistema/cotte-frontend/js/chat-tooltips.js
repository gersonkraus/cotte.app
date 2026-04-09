/**
 * chat-tooltips.js - Sistema de tooltips acessíveis e responsivos
 */

class TooltipManager {
    constructor() {
        this.activeTooltip = null;
        this.hideTimeout = null;
        this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        this.init();
    }

    init() {
        // Delegação de eventos para tooltips
        document.addEventListener('DOMContentLoaded', () => {
            this.setupTooltips();
        });

        // Re-setup quando DOM muda (mensagens novas)
        const observer = new MutationObserver(() => {
            this.setupTooltips();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['data-tooltip']
        });

        // Esconde tooltip ao scrollar (mobile)
        if (this.isTouchDevice) {
            document.addEventListener('scroll', () => {
                this.hideAllTooltips();
            }, { passive: true });
        }
    }

    setupTooltips() {
        // Seleciona elementos com data-tooltip
        const elements = document.querySelectorAll('[data-tooltip]');
        
        elements.forEach(el => {
            if (el.dataset.tooltipInitialized) return;
            
            el.dataset.tooltipInitialized = 'true';
            
            if (this.isTouchDevice) {
                // Touch: tooltip no long-press
                let pressTimer;
                
                el.addEventListener('touchstart', (e) => {
                    pressTimer = setTimeout(() => {
                        this.showTooltip(el, el.dataset.tooltip);
                    }, 500);
                }, { passive: true });
                
                el.addEventListener('touchend', () => {
                    clearTimeout(pressTimer);
                    this.hideTooltip(el);
                });
                
                el.addEventListener('touchcancel', () => {
                    clearTimeout(pressTimer);
                    this.hideTooltip(el);
                });
            } else {
                // Desktop: tooltip no hover
                el.addEventListener('mouseenter', (e) => {
                    this.showTooltip(el, el.dataset.tooltip);
                });
                
                el.addEventListener('mouseleave', () => {
                    this.hideTooltip(el);
                });
                
                el.addEventListener('focus', (e) => {
                    this.showTooltip(el, el.dataset.tooltip);
                });
                
                el.addEventListener('blur', () => {
                    this.hideTooltip(el);
                });
            }
        });
    }

    showTooltip(targetEl, text) {
        if (!text || !targetEl) return;
        
        // Remove tooltip anterior
        this.hideAllTooltips();
        
        // Cria elemento do tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.setAttribute('role', 'tooltip');
        tooltip.textContent = text;
        
        // Posicionamento
        const rect = targetEl.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Estilo base
        tooltip.style.position = 'fixed';
        tooltip.style.zIndex = '10000';
        tooltip.style.pointerEvents = 'none';
        
        // Detecta se é mobile
        const isMobile = viewportWidth <= 768;
        
        if (isMobile) {
            // Mobile: tooltip abaixo do elemento, centralizado
            const tooltipWidth = Math.min(240, viewportWidth - 32);
            const leftPos = Math.max(16, Math.min(rect.left + rect.width / 2 - tooltipWidth / 2, viewportWidth - tooltipWidth - 16));
            const topPos = rect.bottom + 8;
            
            tooltip.style.width = tooltipWidth + 'px';
            tooltip.style.left = leftPos + 'px';
            tooltip.style.top = Math.min(topPos, viewportHeight - 100) + 'px';
            tooltip.classList.add('tooltip-mobile');
        } else {
            // Desktop: tooltip acima ou abaixo dependendo do espaço
            const tooltipWidth = 200;
            const spaceAbove = rect.top;
            const spaceBelow = viewportHeight - rect.bottom;
            
            tooltip.style.width = tooltipWidth + 'px';
            
            if (spaceAbove > spaceBelow && spaceAbove > 50) {
                // Acima do elemento
                tooltip.style.left = (rect.left + rect.width / 2 - tooltipWidth / 2) + 'px';
                tooltip.style.top = (rect.top - 40) + 'px';
                tooltip.classList.add('tooltip-top');
            } else {
                // Abaixo do elemento
                tooltip.style.left = (rect.left + rect.width / 2 - tooltipWidth / 2) + 'px';
                tooltip.style.top = (rect.bottom + 8) + 'px';
                tooltip.classList.add('tooltip-bottom');
            }
        }
        
        document.body.appendChild(tooltip);
        this.activeTooltip = { element: tooltip, target: targetEl };
        
        // Auto-hide após 3 segundos em mobile
        if (this.isTouchDevice) {
            setTimeout(() => {
                this.hideTooltip(targetEl);
            }, 3000);
        }
    }

    hideTooltip(targetEl) {
        if (this.activeTooltip && this.activeTooltip.target === targetEl) {
            this.activeTooltip.element.remove();
            this.activeTooltip = null;
        }
    }

    hideAllTooltips() {
        if (this.activeTooltip) {
            this.activeTooltip.element.remove();
            this.activeTooltip = null;
        }
        
        // Remove todos os tooltips restantes
        document.querySelectorAll('.custom-tooltip').forEach(t => t.remove());
    }
}

// Inicializa quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.tooltipManager = new TooltipManager();
});
