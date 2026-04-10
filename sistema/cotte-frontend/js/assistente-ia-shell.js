/**
 * assistente-ia-shell.js
 *
 * Camada de shell/UX do chat: layout dinâmico, quick replies, histórico
 * local, status e delegação de eventos. Mantém os contratos globais atuais.
 */

function getSuggestionIcon(text) {
    const lower = text.toLowerCase();
    for (const [key, icon] of Object.entries(SUGGESTION_ICONS)) {
        if (lower.includes(key)) return `<span class="sugestao-chip-icon">${icon}</span>`;
    }
    return `<span class="sugestao-chip-icon">${SUGGESTION_ICONS.default}</span>`;
}

function getOrcamentoFollowupSuggestions(data, parsedSuggestions, tipo) {
    const base = Array.isArray(parsedSuggestions) ? parsedSuggestions : [];
    const dados = data?.dados || data || {};
    const numero = String(dados.numero || '').trim();
    const numeroLabel = numero || 'este orçamento';
    const extra = tipo === 'orcamento_atualizado'
        ? [
            `Ver detalhes do ${numeroLabel}`,
            `Enviar ${numeroLabel} por WhatsApp`,
            `Enviar ${numeroLabel} por e-mail`,
            `Aprovar ${numeroLabel}`,
            `Duplicar ${numeroLabel}`,
            'Mostrar próximos passos deste orçamento',
        ]
        : [
            `Ver detalhes do ${numeroLabel}`,
            `Duplicar ${numeroLabel}`,
            `Simular desconto de 5% no ${numeroLabel}`,
            `Gerar versão premium do ${numeroLabel}`,
            'Criar mensagem de follow-up para aprovação',
            'Mostrar próximos passos deste orçamento',
        ];
    const merged = [...base, ...extra]
        .map((s) => String(s || '').trim())
        .filter(Boolean);
    return Array.from(new Set(merged)).slice(0, 8);
}

function dismissWelcome() {
    const w = document.getElementById('welcomeState');
    if (w) w.remove();
}

function resizeMessageInput() {
    const ta = document.getElementById('messageInput');
    if (!ta || ta.tagName !== 'TEXTAREA') return;
    const minHeight = window.innerWidth <= MOBILE_BREAKPOINT ? INPUT_MIN_HEIGHT_MOBILE : INPUT_MIN_HEIGHT_DESKTOP;

    const currentHeight = ta.style.height;
    ta.style.transition = 'none';
    ta.style.height = `${minHeight}px`;
    const scrollH = ta.scrollHeight;
    ta.style.height = currentHeight;

    void ta.offsetHeight;
    ta.style.transition = '';

    const max = window.innerWidth <= MOBILE_BREAKPOINT ? 100 : 140;
    const newHeight = Math.max(minHeight, Math.min(scrollH, max)) + 'px';

    if (ta.style.height !== newHeight) {
        ta.style.height = newHeight;
    }
}

function getAdaptiveMessagePlaceholder() {
    return window.innerWidth <= MOBILE_BREAKPOINT
        ? MOBILE_MESSAGE_PLACEHOLDER
        : DEFAULT_MESSAGE_PLACEHOLDER;
}

function _showQuickReplyChips(sugestoes) {
    const area = document.getElementById('quickReplyArea');
    if (!area) return;
    area.innerHTML = sugestoes.map(s => {
        const icon = (typeof getSuggestionIcon === 'function') ? getSuggestionIcon(s) : '💬';
        return `<button type="button" class="quick-reply-chip" data-qr="${encodeURIComponent(s)}">${icon} ${escapeHtml(s)}</button>`;
    }).join('');
    area.style.display = 'flex';
    area.querySelectorAll('.quick-reply-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            const msg = decodeURIComponent(btn.dataset.qr);
            const ta = document.getElementById('messageInput');
            if (ta) {
                ta.value = msg;
                resizeMessageInput();
                _updateVoiceSendToggle(ta);
            }
            _hideQuickReplyChips();
            sendMessage();
        });
    });
}

function _hideQuickReplyChips() {
    const area = document.getElementById('quickReplyArea');
    if (area) area.style.display = 'none';
}

function _updateVoiceSendToggle(ta) {
    if (window.innerWidth > 768) return;
    const group = ta ? ta.closest('.input-group') : document.querySelector('.input-group');
    if (!group) return;
    if (ta && ta.value.trim().length > 0) {
        group.classList.add('has-content');
    } else {
        group.classList.remove('has-content');
    }
}

function applyAdaptiveMessagePlaceholder(force = false) {
    const ta = document.getElementById('messageInput');
    if (!ta) return;
    if (isRecording && !force) return;
    if (!force && ta.value.trim()) return;
    ta.placeholder = getAdaptiveMessagePlaceholder();
}

function setAiStatus(mode) {
    const hero = document.getElementById('aiStatusBadge');
    const heroDot = document.getElementById('aiStatusDot');
    const heroLbl = document.getElementById('aiStatusLabel');
    const mobLbl = document.getElementById('aiStatusLabelMobile');
    const mobDot = document.getElementById('aiStatusDotMobile');
    const modes = {
        ready: { text: ['IA Pronta', 'Ativo agora'], cls: '' },
        loading: { text: ['Pensando…', 'Pensando…'], cls: 'ai-status-badge--loading' },
        error: { text: ['Falha na resposta', 'Erro'], cls: 'ai-status-badge--error' },
        offline: { text: ['Sem conexão', 'Sem conexão'], cls: 'ai-status-badge--offline' },
    };
    const cfg = modes[mode] || modes.ready;
    if (hero) {
        hero.classList.remove('ai-status-badge--loading', 'ai-status-badge--error', 'ai-status-badge--offline');
        if (cfg.cls) hero.classList.add(cfg.cls);
    }
    if (heroLbl) heroLbl.textContent = cfg.text[0];
    if (mobLbl) mobLbl.textContent = cfg.text[1];
    if (heroDot) {
        if (mode === 'ready') {
            heroDot.style.animation = '';
            heroDot.style.opacity = '';
        } else if (mode === 'error' || mode === 'offline') {
            heroDot.style.animation = 'none';
            heroDot.style.opacity = '1';
        }
    }
    if (mobDot) {
        if (mode === 'ready') {
            mobDot.style.background = '';
            mobDot.style.opacity = '';
        } else {
            mobDot.style.opacity = mode === 'error' ? '0.9' : '1';
            mobDot.style.background = mode === 'error' ? '#f87171' : (mode === 'offline' ? '#94a3b8' : '#4ade80');
        }
    }
}

function scrollChatToBottom() {
    const el = document.getElementById('chatMessages');
    if (el) el.scrollTop = el.scrollHeight;
    updateScrollBottomButtonVisibility();
}

function updateScrollBottomButtonVisibility() {
    const box = document.getElementById('chatMessages');
    const btn = document.getElementById('chatScrollBottomBtn');
    if (!box || !btn) return;
    const threshold = 120;
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < threshold;
    btn.classList.toggle('is-visible', !nearBottom && box.scrollHeight > box.clientHeight + 40);
}

function novaConversaAssistente() {
    if (isLoading) return;
    const box = document.getElementById('chatMessages');
    if (!box) return;
    sessaoId = null;
    localStorage.removeItem('ai_sessao_id');
    localStorage.removeItem('ai_chat_history');
    window._pendingConfirmationToken = null;
    window._pendingOverrideArgs = null;
    window._feedbackData = {};
    box.innerHTML = _assistenteWelcomeHTML || '';
    setAiStatus('ready');
    const ta = document.getElementById('messageInput');
    if (ta) {
        ta.value = '';
        resizeMessageInput();
        _updateVoiceSendToggle(ta);
        ta.focus();
    }
    updateScrollBottomButtonVisibility();
}

function initAssistenteChatDelegation() {
    const box = document.getElementById('chatMessages');
    if (!box) return;

    box.addEventListener('click', (e) => {
        const t = e.target;
        const shortcut = t.closest('.shortcut[data-quick-message]');
        if (shortcut) {
            e.preventDefault();
            const msg = shortcut.getAttribute('data-quick-message') || '';
            sendQuickMessage(msg);
            return;
        }

        const chip = t.closest('.sugestao-chip[data-suggestion]');
        if (chip) {
            e.preventDefault();
            const raw = chip.getAttribute('data-suggestion') || '';
            let text = '';
            try {
                text = decodeURIComponent(raw);
            } catch (_) {
                text = raw;
            }
            chip.classList.add('dismissed');
            sendQuickMessage(text);
            return;
        }

        const copyBtn = t.closest('.message-copy-btn');
        if (copyBtn) {
            e.preventDefault();
            const bubble = copyBtn.closest('.message-bubble');
            if (!bubble) return;
            const txt = bubble.innerText.replace(/\s+$/m, '').trim();
            navigator.clipboard.writeText(txt).then(() => {
                const prev = copyBtn.textContent;
                copyBtn.textContent = '✓';
                setTimeout(() => { copyBtn.textContent = prev || '📋'; }, 2000);
            }).catch(() => {});
            return;
        }

        const fb = t.closest('.feedback-btn[data-feedback-id]');
        if (fb) {
            e.preventDefault();
            const id = fb.getAttribute('data-feedback-id');
            const val = fb.getAttribute('data-feedback-val');
            if (id && val) enviarFeedback(id, val, fb);
            return;
        }

        const cia = t.closest('[data-confirm-ia]');
        if (cia && t.closest('.pending-action-card')) {
            e.preventDefault();
            const token = cia.getAttribute('data-confirm-ia');
            if (token) confirmarAcaoIA(token, cia);
            return;
        }

        const canc = t.closest('[data-cancel-ia]');
        if (canc && t.closest('.pending-action-card')) {
            e.preventDefault();
            cancelarAcaoIA(canc);
            return;
        }

        const orcGo = t.closest('[data-orc-confirm]');
        if (orcGo) {
            e.preventDefault();
            confirmarOrcamento(orcGo);
            return;
        }

        const orcDismiss = t.closest('[data-orc-dismiss]');
        if (orcDismiss) {
            e.preventDefault();
            const card = orcDismiss.closest('.orc-preview-card');
            if (card) card.remove();
            return;
        }

        const wa = t.closest('[data-enviar-wa]');
        if (wa) {
            e.preventDefault();
            const id = parseInt(wa.getAttribute('data-enviar-wa'), 10);
            let num = '';
            try {
                num = decodeURIComponent(wa.getAttribute('data-orc-numero') || '');
            } catch (_) {
                num = wa.getAttribute('data-orc-numero') || '';
            }
            enviarPorWhatsapp(id, num, wa);
            return;
        }

        const em = t.closest('[data-enviar-email]');
        if (em) {
            e.preventDefault();
            const id = parseInt(em.getAttribute('data-enviar-email'), 10);
            let num = '';
            try {
                num = decodeURIComponent(em.getAttribute('data-orc-numero') || '');
            } catch (_) {
                num = em.getAttribute('data-orc-numero') || '';
            }
            enviarPorEmail(id, num, em);
            return;
        }

        const qs = t.closest('[data-quick-send]');
        if (qs) {
            e.preventDefault();
            let text = '';
            try {
                text = decodeURIComponent(qs.getAttribute('data-quick-send') || '');
            } catch (_) {
                text = qs.getAttribute('data-quick-send') || '';
            }
            sendQuickMessage(text);
            return;
        }

        const cp = t.closest('[data-copy-public-token]');
        if (cp) {
            e.preventDefault();
            const tok = cp.getAttribute('data-copy-public-token');
            if (tok) {
                const url = window.location.origin + '/app/orcamento-publico.html?token=' + encodeURIComponent(tok);
                navigator.clipboard.writeText(url).then(() => {
                    cp.textContent = '✓ Copiado';
                }).catch(() => {});
            }
        }
    });

    const obs = new MutationObserver((mutations) => {
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.nodeType !== 1) continue;
                const root = node.matches?.('.message') ? node : node.querySelector?.('.message');
                const scope = root || node;
                const btn = scope.querySelector?.('.pending-action-card [data-confirm-ia]');
                if (btn) {
                    setTimeout(() => btn.focus(), 50);
                    return;
                }
            }
        }
    });
    obs.observe(box, { childList: true, subtree: true });
}

function saveChatHistory() {
    const box = document.getElementById('chatMessages');
    if (!box || isLoading) return;
    const clone = box.cloneNode(true);
    clone.querySelectorAll('.loading').forEach(el => el.remove());
    localStorage.setItem('ai_chat_history', clone.innerHTML);
    if (sessaoId) localStorage.setItem('ai_sessao_id', sessaoId);
}

window.getSuggestionIcon = getSuggestionIcon;
window.getOrcamentoFollowupSuggestions = getOrcamentoFollowupSuggestions;
window.dismissWelcome = dismissWelcome;
window.resizeMessageInput = resizeMessageInput;
window._showQuickReplyChips = _showQuickReplyChips;
window._hideQuickReplyChips = _hideQuickReplyChips;
window._updateVoiceSendToggle = _updateVoiceSendToggle;
window.applyAdaptiveMessagePlaceholder = applyAdaptiveMessagePlaceholder;
window.setAiStatus = setAiStatus;
window.scrollChatToBottom = scrollChatToBottom;
window.updateScrollBottomButtonVisibility = updateScrollBottomButtonVisibility;
window.novaConversaAssistente = novaConversaAssistente;
window.initAssistenteChatDelegation = initAssistenteChatDelegation;
window.saveChatHistory = saveChatHistory;
