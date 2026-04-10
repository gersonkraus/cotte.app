/**
 * assistente-ia.js - Lógica do Assistente COTTE
 *
 * HTTP: usa ApiService com fallback para cliente legado `api`.
 */

let isLoading = false;
let sessaoId = null; // UUID de sessão para histórico de conversa
let _ultimaPergunta = ''; // Última mensagem enviada, para associar ao feedback
let _assistenteWelcomeHTML = ''; // HTML do card inicial (para Nova conversa)
const httpClient = window.ApiService || window.api;
let currentAbortController = null; // Para o botão de parar geração
let speechRecognition = null; // Para entrada por voz
let isRecording = false;
let slashCommandIndex = -1; // Índice atual da lista de slash commands
let _assistentePrefsCache = null;

const SLASH_COMMANDS = [
    { cmd: '/caixa', desc: 'Ver saldo atual disponível', icon: '💰' },
    { cmd: '/faturamento', desc: 'Total faturado em orçamentos', icon: '📈' },
    { cmd: '/receber', desc: 'Valores em aberto a receber', icon: '📥' },
    { cmd: '/pagar', desc: 'Valores em aberto a pagar', icon: '📤' },
    { cmd: '/resumo', desc: 'Visão geral (Dashboard)', icon: '📊' },
    { cmd: '/devendo', desc: 'Lista de clientes em atraso', icon: '🚨' },
    { cmd: '/previsao', desc: 'Projeção de caixa futuro', icon: '🔮' },
    { cmd: '/orcamento', desc: 'Criar um novo orçamento', icon: '📝' },
    { cmd: '/agendar', desc: 'Fazer novo agendamento', icon: '📅' },
    { cmd: '/agenda', desc: 'Ver agendamentos do dia', icon: '📆' },
    { cmd: '/ajuda', desc: 'Dúvidas sobre como usar o sistema', icon: '❓' }
];

const MOBILE_BREAKPOINT = 768;
const INPUT_MIN_HEIGHT_MOBILE = 40;
const INPUT_MIN_HEIGHT_DESKTOP = 44;
const DEFAULT_MESSAGE_PLACEHOLDER = 'Pergunte algo ou dê um comando...';
const MOBILE_MESSAGE_PLACEHOLDER = 'Digite sua mensagem...';

function hasHttpClient() {
    return !!httpClient && typeof httpClient.get === 'function' && typeof httpClient.post === 'function';
}

function showAssistentePrefNotice(msg, isError = false) {
    const el = document.getElementById('assistenteInstrucoesPermissaoHint');
    if (!el) return;
    el.textContent = msg || '';
    el.style.color = isError ? '#ef4444' : '';
}

/** Atualiza o ponto verde nas engrenagens quando há preferências personalizadas salvas no servidor. */
function syncAssistenteGearSavedBadge(prefData) {
    const pref = prefData?.preferencia_visualizacao || {};
    const formato = pref?.formato_preferido || 'auto';
    const instr = String(prefData?.instrucoes_empresa ?? '').trim();
    const showPersonalizado = formato !== 'auto' || instr.length > 0;

    const desktopBadge = document.getElementById('assistenteGearSavedBadgeDesktop');
    const mobileBadge = document.getElementById('assistenteGearSavedBadgeMobile');
    [desktopBadge, mobileBadge].forEach((el) => {
        if (el) el.classList.toggle('is-visible', showPersonalizado);
    });

    const baseLabel = 'Abrir preferências';
    const label = showPersonalizado
        ? `${baseLabel}. Há preferências personalizadas salvas.`
        : baseLabel;
    const desktopBtn = document.getElementById('btnPreferenciasGearDesktop');
    const mobileBtn = document.getElementById('btnPreferenciasGear');
    if (desktopBtn) desktopBtn.setAttribute('aria-label', label);
    if (mobileBtn) mobileBtn.setAttribute('aria-label', label);
}

function renderAssistentePreferencesCard(prefData) {
    const resumo = document.getElementById('assistentePreferenciasResumo');
    const setorTag = document.getElementById('assistenteSetorTag');
    const select = document.getElementById('assistenteFormatoSelect');
    const txt = document.getElementById('assistenteInstrucoesInput');
    const btn = document.getElementById('btnSalvarPreferenciasAssistente');
    if (!resumo || !setorTag || !select || !txt || !btn) return;

    const pref = prefData?.preferencia_visualizacao || {};
    const playbook = prefData?.playbook_setor || {};
    const podeEditar = !!prefData?.pode_editar_instrucoes;
    const setor = playbook?.setor || 'geral';
    const formato = pref?.formato_preferido || 'auto';

    _assistentePrefsCache = prefData || null;
    setorTag.textContent = `Setor: ${setor}`;
    resumo.textContent = `Formato atual: ${formato}. Playbook ativo com janelas 7/30/90 dias.`;

    select.value = ['auto', 'resumo', 'tabela'].includes(formato) ? formato : 'auto';
    txt.value = prefData?.instrucoes_empresa || '';
    txt.disabled = !podeEditar;
    btn.disabled = false;
    showAssistentePrefNotice(
        podeEditar
            ? 'Você pode editar as instruções da empresa.'
            : 'Somente gestor/admin pode editar instruções da empresa.'
    );
    syncAssistenteGearSavedBadge(prefData || {});
}

async function loadAssistentePreferences() {
    if (!hasHttpClient() || typeof httpClient.get !== 'function') return;
    try {
        const data = await httpClient.get('/ai/assistente/preferencias');
        renderAssistentePreferencesCard(data || {});
    } catch (e) {
        showAssistentePrefNotice('Não foi possível carregar preferências agora.', true);
    }
}

async function saveAssistentePreferences() {
    if (!hasHttpClient() || typeof httpClient.patch !== 'function') return;
    const select = document.getElementById('assistenteFormatoSelect');
    const txt = document.getElementById('assistenteInstrucoesInput');
    const btn = document.getElementById('btnSalvarPreferenciasAssistente');
    if (!select || !txt || !btn) return;
    const podeEditar = !!(_assistentePrefsCache && _assistentePrefsCache.pode_editar_instrucoes);
    const payload = {
        formato_preferido: select.value || 'auto',
        dominio: 'geral',
    };
    if (podeEditar) {
        payload.instrucoes_empresa = txt.value || '';
    }
    btn.disabled = true;
    showAssistentePrefNotice('Salvando preferências...');
    try {
        const out = await httpClient.patch('/ai/assistente/preferencias', payload);
        renderAssistentePreferencesCard(out || {});
        showAssistentePrefNotice('Preferências salvas com sucesso.');
    } catch (e) {
        showAssistentePrefNotice('Falha ao salvar preferências.', true);
    } finally {
        btn.disabled = false;
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/** Escapa texto para inserção segura em HTML (mitiga XSS). */
function escapeHtml(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/** Escapa valor de atributo HTML. */
function escapeHtmlAttr(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;');
}

/** Texto plano: escape + quebras (erros, conteúdo sem Markdown). */
function textToHtmlPlain(text) {
    return escapeHtml(String(text ?? '')).replace(/\n/g, '<br>');
}

const _mdPh = (kind, i) => `\uE000${kind}${i}\uE001`;

/**
 * Subconjunto seguro de Markdown para respostas da IA: `código`, **negrito**,
 * links [rótulo](https://...). Apenas URLs http/https. Sem HTML bruto.
 */
function textToHtmlRich(raw) {
    const codes = [];
    const links = [];
    let s = String(raw ?? '');
    s = s.replace(/`([^`]+)`/g, (_, inner) => {
        const i = codes.length;
        codes.push(inner);
        return _mdPh('C', i);
    });
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_, label, url) => {
        const i = links.length;
        links.push({ label, url: url.trim() });
        return _mdPh('L', i);
    });
    s = escapeHtml(s);
    codes.forEach((inner, i) => {
        s = s.replace(_mdPh('C', i), '<code class="assistente-md-code">' + escapeHtml(inner) + '</code>');
    });
    links.forEach((L, i) => {
        const u = L.url.trim();
        if (!/^https?:\/\//i.test(u)) {
            s = s.replace(_mdPh('L', i), escapeHtml(`[${L.label}](${L.url})`));
            return;
        }
        s = s.replace(
            _mdPh('L', i),
            '<a href="' + escapeHtmlAttr(u) + '" class="assistente-md-link" target="_blank" rel="noopener noreferrer">' +
            escapeHtml(L.label) +
            '</a>'
        );
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return s.replace(/\n/g, '<br>');
}

function isRetryableAssistenteError(err) {
    const m = (err && err.message) ? err.message : '';
    if (/Erro (502|503|504)\b/.test(m)) return true;
    if (m.includes('conexão') || m.includes('internet')) return true;
    if (m.includes('servidor')) return true;
    if (m.includes('Failed to fetch')) return true;
    return false;
}

/**
 * Obtém hora atual formatada
 */
function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

const SUGGESTION_ICONS = {
    'cliente': '👤', 'clientes': '👥', 'novo': '🆕', 'venda': '💰',
    'orcamento': '📋', 'orçamento': '📋', 'faturamento': '📊',
    'receita': '📈', 'despesa': '💸', 'caixa': '🏦', 'saldo': '💵',
    'negócio': '🚀', 'negocio': '🚀', 'vendas': '📈', 'meta': '🎯',
    'lead': '🎣', 'leads': '🎣', 'prospec': '🔍', 'contrato': '✍️',
    'pagamento': '💳', 'receber': '📬', 'pagar': '📤',
    'ticket': '🎟️', 'médio': '📏', 'conversão': '🔄', 'conversao': '🔄',
    'índice': '📐', 'indice': '📐', 'análise': '🔬', 'analise': '🔬',
    'inadimpl': '⚠️', 'devendo': '🚨', 'bloqueado': '🔒',
    'sazonal': '📅', 'feriado': '🎉', 'campanha': '📢',
    'promo': '🔥', 'desconto': '🏷️', 'bonus': '🎁',
    'default': '💡'
};

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

/**
 * Remove o card de boas-vindas na primeira interação com o chat.
 */
function dismissWelcome() {
    const w = document.getElementById('welcomeState');
    if (w) w.remove();
}

/**
 * Ajusta altura do textarea de mensagem de forma suave.
 */
function resizeMessageInput() {
    const ta = document.getElementById('messageInput');
    if (!ta || ta.tagName !== 'TEXTAREA') return;
    const minHeight = window.innerWidth <= MOBILE_BREAKPOINT ? INPUT_MIN_HEIGHT_MOBILE : INPUT_MIN_HEIGHT_DESKTOP;
    
    const currentHeight = ta.style.height;
    ta.style.transition = 'none';
    ta.style.height = `${minHeight}px`;
    const scrollH = ta.scrollHeight;
    ta.style.height = currentHeight;
    
    // Force reflow before restoring transition
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

/** Exibe quick-reply chips acima do input no mobile */
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

/** Esconde a área de quick-reply chips */
function _hideQuickReplyChips() {
    const area = document.getElementById('quickReplyArea');
    if (area) area.style.display = 'none';
}

/**
 * Alterna visibilidade mic ↔ enviar no mobile (estilo WhatsApp/Telegram).
 * Chamado a cada evento input no textarea.
 */
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

/** Atualiza badge de status (desktop e mobile). */
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

/**
 * Limpa o histórico, reinicia sessão e restaura o card inicial.
 */
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

/**
 * Delegação de cliques no chat (atalhos, chips, cópia, feedback, confirmações).
 */
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

// --- SPEECH TO TEXT ---
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('Speech Recognition API não suportada neste navegador.');
        const btn = document.getElementById('voiceButton');
        if (btn) {
            btn.style.opacity = '0.5';
            btn.title = 'Entrada por voz não suportada nativamente neste navegador';
        }
        return;
    }
    
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = false;
    speechRecognition.interimResults = false;
    speechRecognition.lang = 'pt-BR';

    speechRecognition.onstart = function() {
        isRecording = true;
        const btn = document.getElementById('voiceButton');
        if (btn) {
            btn.setAttribute('aria-pressed', 'true');
            btn.title = 'Gravando... Clique para parar.';
        }
        const ta = document.getElementById('messageInput');
        if (ta && !ta.value.trim()) {
            ta.placeholder = 'Ouvindo...';
        }
    };

    speechRecognition.onresult = function(event) {
        let transcript = '';
        let isFinal = false;
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                isFinal = true;
            }
        }
        
        const ta = document.getElementById('messageInput');
        if (ta) {
            const currentVal = ta.value;
            if (currentVal && !currentVal.endsWith(' ')) {
                ta.value = currentVal + ' ' + transcript;
            } else {
                ta.value = currentVal + transcript;
            }
            resizeMessageInput();
            _updateVoiceSendToggle(ta);
            ta.focus();

            // Envia automaticamente após receber o áudio transcrito final
            if (isFinal) {
                // Pequeno delay para garantir que a UI atualizou o textarea e transição
                setTimeout(() => {
                    if (ta.value.trim() !== '') {
                        sendMessage();
                    }
                }, 300);
            }
        }
    };

    speechRecognition.onerror = function(event) {
        console.error('Erro no Speech Recognition:', event.error);
        stopSpeechRecognition();
    };

    speechRecognition.onend = function() {
        stopSpeechRecognition();
    };
}

function toggleSpeechRecognition() {
    if (!speechRecognition) {
        if (typeof showNotif === 'function') {
            showNotif('⚠️', 'Sem Suporte', 'Navegador não possui recurso nativo de voz. Tente Chrome ou Edge.', 'error');
        } else {
            alert('Seu navegador não suporta reconhecimento de voz nativo. Tente usar o Google Chrome ou Edge.');
        }
        return;
    }
    
    if (isRecording) {
        speechRecognition.stop();
    } else {
        try {
            speechRecognition.start();
        } catch (e) {
            console.error('Erro ao iniciar gravação:', e);
        }
    }
}

function stopSpeechRecognition() {
    isRecording = false;
    const btn = document.getElementById('voiceButton');
    if (btn) {
        btn.setAttribute('aria-pressed', 'false');
        btn.title = 'Ditar por voz';
    }
    const ta = document.getElementById('messageInput');
    if (ta) {
        ta.placeholder = getAdaptiveMessagePlaceholder();
    }
}

// --- SLASH COMMANDS ---
function initSlashCommands() {
    const ta = document.getElementById('messageInput');
    const menu = document.getElementById('slashCommandsMenu');
    if (!ta || !menu) return;

    ta.addEventListener('input', function(e) {
        const val = ta.value;
        const cursorPosition = ta.selectionStart;
        
        // Verifica se o texto até o cursor termina com '/' ou '/algo'
        // Só ativa se o '/' for o primeiro caractere ou estiver precedido por espaço
        const textBeforeCursor = val.substring(0, cursorPosition);
        // O regex verifica do final pra trás (match a partir do final)
        const match = textBeforeCursor.match(/(?:^|\s)(\/[^\s]*)$/);
        
        if (match) {
            const query = match[1].toLowerCase(); // ex: "/", "/cai"
            showSlashCommands(query);
        } else {
            hideSlashCommands();
        }
    });

    ta.addEventListener('keydown', function(e) {
        const menu = document.getElementById('slashCommandsMenu');
        if (menu.style.display !== 'none') {
            const items = menu.querySelectorAll('.slash-item');
            if (items.length === 0) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                slashCommandIndex = (slashCommandIndex + 1) % items.length;
                updateSlashCommandSelection(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                slashCommandIndex = (slashCommandIndex - 1 + items.length) % items.length;
                updateSlashCommandSelection(items);
            } else if (e.key === 'Enter' || e.key === 'Tab') {
                e.preventDefault();
                if (slashCommandIndex >= 0 && slashCommandIndex < items.length) {
                    items[slashCommandIndex].click();
                } else if (items.length > 0) {
                    items[0].click();
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideSlashCommands();
            }
        }
    });
}

function showSlashCommands(query) {
    const menu = document.getElementById('slashCommandsMenu');
    const list = document.getElementById('slashCommandsList');
    if (!menu || !list) return;

    // Filtrar
    const filtered = SLASH_COMMANDS.filter(cmd => cmd.cmd.toLowerCase().startsWith(query));
    
    if (filtered.length === 0) {
        hideSlashCommands();
        return;
    }

    list.innerHTML = '';
    filtered.forEach((cmd, idx) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'slash-item';
        btn.innerHTML = `
            <span class="slash-item-icon">${cmd.icon}</span>
            <div class="slash-item-content">
                <span class="slash-item-cmd">${cmd.cmd}</span>
                <span class="slash-item-desc">${cmd.desc}</span>
            </div>
        `;
        
        btn.addEventListener('click', () => {
            applySlashCommand(cmd.cmd);
        });
        
        list.appendChild(btn);
    });

    slashCommandIndex = 0;
    updateSlashCommandSelection(list.querySelectorAll('.slash-item'));
    menu.style.display = 'block';
}

function hideSlashCommands() {
    const menu = document.getElementById('slashCommandsMenu');
    if (menu) menu.style.display = 'none';
    slashCommandIndex = -1;
}

function updateSlashCommandSelection(items) {
    items.forEach((item, idx) => {
        if (idx === slashCommandIndex) {
            item.classList.add('active');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('active');
        }
    });
}

function applySlashCommand(command) {
    const ta = document.getElementById('messageInput');
    if (!ta) return;

    const val = ta.value;
    const cursorPosition = ta.selectionStart;
    const textBeforeCursor = val.substring(0, cursorPosition);
    const textAfterCursor = val.substring(cursorPosition);
    
    const match = textBeforeCursor.match(/(?:^|\s)(\/[^\s]*)$/);
    if (match) {
        const replaceStart = cursorPosition - match[1].length;
        ta.value = val.substring(0, replaceStart) + command + ' ' + textAfterCursor;
        // Colocar o cursor logo após o comando adicionando um espaço extra no fim
        const newCursorPos = replaceStart + command.length + 1;
        ta.setSelectionRange(newCursorPos, newCursorPos);
    }
    
    hideSlashCommands();
    resizeMessageInput();
    ta.focus();
}

/**
 * Inicialização ao carregar a página
 */
document.addEventListener('DOMContentLoaded', function() {
    const welcomeEl = document.getElementById('welcomeState');
    if (welcomeEl) {
        _assistenteWelcomeHTML = welcomeEl.outerHTML;
    }

    // Restaurar histórico se existir
    const historico = localStorage.getItem('ai_chat_history');
    if (historico) {
        const box = document.getElementById('chatMessages');
        if (box) {
            box.innerHTML = historico;
            sessaoId = localStorage.getItem('ai_sessao_id') || sessaoId;
            box.querySelectorAll('.sugestao-chip').forEach(c => c.classList.add('visible'));
            box.querySelectorAll('.loading').forEach(b => b.remove());
            setTimeout(() => scrollChatToBottom(), 100);
        }
    }

    const input = document.getElementById('messageInput');
    if (input) {
        input.focus();
        input.addEventListener('keydown', handleMessageKeydown);
        input.addEventListener('input', () => {
            resizeMessageInput();
            _updateVoiceSendToggle(input);
            if (input.value.trim().length > 0) _hideQuickReplyChips();
        });
        applyAdaptiveMessagePlaceholder();
        resizeMessageInput();
    }

    window.addEventListener('resize', () => {
        applyAdaptiveMessagePlaceholder();
        resizeMessageInput();
    }, { passive: true });

    window.addEventListener('orientationchange', () => {
        applyAdaptiveMessagePlaceholder();
        resizeMessageInput();
    }, { passive: true });

    const sendBtn = document.getElementById('sendButton');
    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            if (isLoading) {
                // Aborta a requisição
                if (currentAbortController) {
                    currentAbortController.abort();
                    currentAbortController = null;
                }
            } else {
                sendMessage();
            }
        });
    }

    const voiceBtn = document.getElementById('voiceButton');
    if (voiceBtn) {
        voiceBtn.addEventListener('click', () => {
            toggleSpeechRecognition();
        });
    }

    initSpeechRecognition();
    initSlashCommands();
    loadAssistentePreferences();

    const topNew = document.getElementById('btnNovaConversaTop');
    if (topNew) topNew.addEventListener('click', () => novaConversaAssistente());

    const mobNew = document.getElementById('btnNovaConversaMobile');
    if (mobNew) mobNew.addEventListener('click', () => novaConversaAssistente());

    // Gear: abre/fecha preferências como bottom sheet no mobile
    const gearBtns = [
        document.getElementById('btnPreferenciasGear'),
        document.getElementById('btnPreferenciasGearDesktop')
    ].filter(Boolean);
    const prefCard = document.getElementById('assistentePreferenciasCard');
    const prefBackdrop = document.getElementById('prefBackdrop');
    function _closePrefSheet() {
        if (prefCard) prefCard.classList.remove('is-open');
        if (prefBackdrop) prefBackdrop.classList.remove('is-open');
    }
    if (gearBtns.length && prefCard) {
        gearBtns.forEach((gearBtn) => gearBtn.addEventListener('click', () => {
            const open = prefCard.classList.toggle('is-open');
            if (prefBackdrop) prefBackdrop.classList.toggle('is-open', open);
        }));
    }
    if (prefBackdrop) {
        prefBackdrop.addEventListener('click', _closePrefSheet);
    }

    // Inovação 1 — Swipe down para fechar bottom sheet de preferências
    if (prefCard) {
        let _swipeStartY = 0;
        prefCard.addEventListener('touchstart', (e) => {
            _swipeStartY = e.touches[0].clientY;
        }, { passive: true });
        prefCard.addEventListener('touchmove', (e) => {
            if (e.touches[0].clientY - _swipeStartY > 60) {
                _closePrefSheet();
            }
        }, { passive: true });
    }

    // Inovação 2 — Header compacto quando teclado virtual abre
    if (window.visualViewport) {
        const _chatHeader = document.querySelector('.chat-header');
        window.visualViewport.addEventListener('resize', () => {
            if (!_chatHeader) return;
            const isKeyboard = window.visualViewport.height < window.screen.height * 0.72;
            _chatHeader.classList.toggle('chat-header--compact', isKeyboard);
        }, { passive: true });
    }

    // Sidebar mobile: hamburguer no chat-header usa o mesmo toggle de api.js
    const sidebarHamburger = document.getElementById('btnSidebarMobile');
    if (sidebarHamburger) {
        sidebarHamburger.addEventListener('click', () => {
            const sidebar = document.querySelector('.sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            if (sidebar) sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('open');
        });
    }

    const savePrefsBtn = document.getElementById('btnSalvarPreferenciasAssistente');
    if (savePrefsBtn) {
        savePrefsBtn.addEventListener('click', () => {
            saveAssistentePreferences();
        });
    }

    const scrollBtn = document.getElementById('chatScrollBottomBtn');
    if (scrollBtn) {
        scrollBtn.addEventListener('click', () => scrollChatToBottom());
    }

    const chatBox = document.getElementById('chatMessages');
    if (chatBox) {
        chatBox.addEventListener('scroll', () => updateScrollBottomButtonVisibility(), { passive: true });
        
        // Esconder menu de slash commands se clicar fora
        chatBox.addEventListener('click', () => {
            hideSlashCommands();
        });
    }

    initAssistenteChatDelegation();
    updateScrollBottomButtonVisibility();

    // Auto-trigger de onboarding: disparado quando setup está incompleto
    if (localStorage.getItem('onboarding_pending') === '1') {
        setTimeout(() => sendQuickMessage('começar'), 800);
    }
});

/**
 * Enter envia; Shift+Enter quebra linha (textarea).
 */
function handleMessageKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * Envia mensagem rápida ao clicar em um botão de ação
 */
function sendQuickMessage(message) {
    const el = document.getElementById('messageInput');
    if (el) {
        el.value = message;
        resizeMessageInput();
    }
    sendMessage();
}

/**
 * Adiciona uma mensagem ao chat
 */
function addMessage(content, isUser = false, isError = false, isLoadingState = false) {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return null;

    const time = getCurrentTime();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + (isUser ? 'user' : 'ai') + (isError ? ' error' : '') + (isLoadingState ? ' loading' : '');

    if (isLoadingState) {
        messageDiv.innerHTML = `
            <div class="message-bubble ai-loading-bubble" data-time="${time}">
                <div class="ai-loading-row">
                    <div class="loading-dots">
                        <span></span><span></span><span></span>
                    </div>
                    <span class="typing-indicator-text">Processando...</span>
                </div>
            </div>
        `;
    } else {
        const copyBtn = (!isUser && !isError)
            ? '<button type="button" class="message-copy-btn" aria-label="Copiar resposta" title="Copiar">📋</button>'
            : '';
        messageDiv.innerHTML = `<div class="message-bubble" data-time="${time}">${copyBtn}${content}</div>`;
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    updateScrollBottomButtonVisibility();

    if (!isLoadingState) {
        setTimeout(saveChatHistory, 500);
    }

    return messageDiv;
}

/**
 * Envia mensagem para o assistente
 */
async function sendMessage() {
    if (!hasHttpClient()) {
        addMessage('Serviço de API indisponível. Recarregue a página e tente novamente.', false, true);
        return;
    }

    if (isLoading) return;

    const token = localStorage.getItem('cotte_token');
    if (!token) {
        addMessage('Você precisa estar logado para usar o assistente. Redirecionando...', false, true);
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 2000);
        return;
    }

    const input = document.getElementById('messageInput');
    const message = (input && input.value) ? input.value.trim() : '';

    if (!message) return;

    dismissWelcome();
    input.value = '';
    resizeMessageInput();
    _updateVoiceSendToggle(input);
    _hideQuickReplyChips();
    _ultimaPergunta = message;

    addMessage(escapeHtml(message).replace(/\n/g, '<br>'), true);

    const loadingMessage = addMessage('', false, false, true);
    isLoading = true;

    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.classList.add('is-loading');
        sendButton.title = 'Parar Geração';
    }
    setAiStatus('loading');

    let lastError = null;
    currentAbortController = new AbortController();

    try {
        if (!sessaoId) {
            sessaoId = (typeof crypto !== 'undefined' && crypto.randomUUID)
                ? crypto.randomUUID()
                : Math.random().toString(36).substring(2) + Date.now().toString(36);
        }

        const requestBody = { mensagem: message, sessao_id: sessaoId };
        if (window._pendingConfirmationToken) {
            requestBody.confirmation_token = window._pendingConfirmationToken;
            window._pendingConfirmationToken = null;
        }
        if (window._pendingOverrideArgs) {
            requestBody.override_args = window._pendingOverrideArgs;
            window._pendingOverrideArgs = null;
        }

        const baseUrl = typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : (window.location.origin + '/api/v1');
        const fetchUrl = baseUrl + '/ai/assistente/stream';
        
        const response = await fetch(fetchUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify(requestBody),
            signal: currentAbortController.signal
        });

        if (!response.ok) {
            let errText = await response.text();
            throw new Error(`Falha no servidor: ${response.status} ${errText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;
        let responseText = '';
        let metadata = null;
        let bubbleNode = null;
        let toolBadge = null;   // Badge temporário de "executando tool"
        let _bubbleReady = false; // true após limpar dots e preparar bubble p/ conteúdo

        // Guarda referência mas NÃO limpa ainda — dots ficam visíveis até 1º conteúdo
        if (loadingMessage) {
            bubbleNode = loadingMessage.querySelector('.message-bubble');
        }

        function _prepareBubble() {
            if (_bubbleReady) return;
            _bubbleReady = true;
            if (loadingMessage) loadingMessage.classList.remove('loading');
            if (bubbleNode) bubbleNode.innerHTML = '';
        }

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            if (value) {
                const chunkStr = decoder.decode(value, { stream: true });
                const lines = chunkStr.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6).trim();
                        if (!dataStr) continue;
                        try {
                            const dataObj = JSON.parse(dataStr);
                            if (dataObj.error) throw new Error(dataObj.error);

                            // ── Evento de fase (thinking / tool_running) ──────
                            if (dataObj.phase === 'tool_running' && dataObj.tool) {
                                _prepareBubble(); // limpa dots ao primeiro evento real
                                // Criar/atualizar badge animado no bubble
                                if (bubbleNode) {
                                    if (!toolBadge) {
                                        toolBadge = document.createElement('div');
                                        toolBadge.className = 'tool-running-badge';
                                        bubbleNode.appendChild(toolBadge);
                                    }
                                    const toolLabel = dataObj.tool.replace(/_/g, ' ');
                                    toolBadge.innerHTML = `<span class="tool-running-spinner">⚙️</span> Executando: <em>${escapeHtml(toolLabel)}</em>`;
                                }
                            }

                            // ── Chunk de texto ────────────────────────────────
                            if (dataObj.chunk) {
                                _prepareBubble(); // limpa dots ao primeiro chunk de texto
                                // Remover badge de tool quando começa o texto
                                if (toolBadge) { toolBadge.remove(); toolBadge = null; }
                                responseText += dataObj.chunk;
                                if (bubbleNode && window.marked) {
                                    bubbleNode.innerHTML = marked.parse(responseText);
                                    const tables = bubbleNode.querySelectorAll('table');
                                    tables.forEach(t => {
                                        if(!t.parentElement.classList.contains('ai-table-wrapper')){
                                            t.classList.add('ai-table');
                                            const wrap = document.createElement('div');
                                            wrap.className = 'ai-table-wrapper';
                                            t.parentNode.insertBefore(wrap, t);
                                            wrap.appendChild(t);
                                        }
                                    });
                                } else if (bubbleNode) {
                                    bubbleNode.textContent = responseText;
                                }
                                scrollChatToBottom();
                            }

                            // ── Evento final ──────────────────────────────────
                            if (dataObj.is_final) {
                                _prepareBubble(); // garante que dots são removidos
                                if (toolBadge) { toolBadge.remove(); toolBadge = null; }
                                metadata = dataObj.metadata || {};
                            }
                        } catch (e) {
                            if (e.message && e.message.includes('JSON')) {} else { throw e; }
                        }
                    }
                }
            }
            done = readerDone;
        }

        setAiStatus('ready');

        const finalData = {
           sucesso: true,
           resposta: responseText
                || (metadata && typeof metadata.final_text === 'string' ? metadata.final_text : '')
                || (metadata && typeof metadata.resposta === 'string' ? metadata.resposta : '')
                || (metadata && metadata.dados && typeof metadata.dados.resposta === 'string' ? metadata.dados.resposta : ''),
           stream_has_chunks: !!(responseText && responseText.trim()),
           tipo_resposta: (metadata && metadata.tipo) ? metadata.tipo : 'geral',
           dados: metadata ? (metadata.dados || null) : null,
           grafico: metadata ? (metadata.grafico || null) : null,
           sugestoes: metadata ? (metadata.sugestoes || null) : null,
           pending_action: metadata ? (metadata.pending_action || null) : null,
           tool_trace: metadata ? (metadata.tool_trace || null) : null,
        };

        processAIResponse(finalData, loadingMessage, true);

    } catch (error) {
        console.error('Error:', error);
        
        if (error.name === 'AbortError') {
            console.log('Geração de resposta interrompida pelo usuário.');
            if (loadingMessage && loadingMessage.querySelector('.loading-dots')) {
                loadingMessage.remove(); // Remove apenas se não gerou nada ainda
            } else if (loadingMessage) {
                loadingMessage.classList.remove('loading');
                const bubble = loadingMessage.querySelector('.message-bubble');
                if (bubble && !bubble.textContent.trim() && !bubble.innerHTML.includes('<br>')) {
                    loadingMessage.remove();
                } else if (bubble) {
                    bubble.innerHTML += '<br><br><em><small>[Geração interrompida]</small></em>';
                }
            }
            setAiStatus('ready');
            return;
        }

        if (loadingMessage && loadingMessage.remove) {
            loadingMessage.remove();
        }

        let errorMessage = 'Não foi possível processar sua solicitação.';
        if (error.message && error.message.includes('Sessão expirada')) {
            errorMessage = 'Sessão expirada. Redirecionando...';
            setTimeout(() => { window.location.href = 'login.html'; }, 2000);
        } else if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('conexão'))) {
            errorMessage = 'Erro de conexão. Verifique sua internet.';
            setAiStatus('offline');
        } else {
            setAiStatus('error');
        }

        addMessage(errorMessage, false, true);
        setTimeout(() => setAiStatus('ready'), 4500);
    } finally {
        isLoading = false;
        currentAbortController = null;
        if (sendButton) {
            sendButton.classList.remove('is-loading');
            sendButton.title = 'Enviar';
        }
    }
}

/**
 * Processa resposta da IA
 * Passa dados completos incluindo tipo_resposta e resposta
 */
function processAIResponse(data, loadingMessage, isStreamed = false) {
    if (!isStreamed && loadingMessage && loadingMessage.remove) {
        loadingMessage.remove();
    }

    const isSuccess = data.sucesso === true || data.success === true ||
                      (data.dados && Object.keys(data.dados).length > 0);

    if (isSuccess) {
        let responseContent = formatAIResponse(data, isStreamed);
        const visPref = data?.dados?.visualizacao_recomendada || null;
        if (visPref && visPref.formato_preferido && visPref.formato_preferido !== 'auto') {
            responseContent += `<div class="tool-trace">🧭 Formato aplicado: <strong>${escapeHtml(String(visPref.formato_preferido))}</strong></div>`;
        }

        // Tool Use v2: indicador de ferramentas executadas
        if (Array.isArray(data.tool_trace) && data.tool_trace.length > 0) {
            const items = data.tool_trace.map(t => {
                const ico = t.status === 'ok' ? '✅' : (t.status === 'pending' ? '⏳' : '⚠️');
                return `<span class="tool-trace-item">${ico} ${escapeHtml(String(t.tool))}</span>`;
            }).join(' ');
            responseContent += `<div class="tool-trace">🛠️ ${items}</div>`;
        }

        // Compact Confirmation Card for new records (e.g., orçamento ID)
        if (data.tipo_resposta === 'registro_criado' && data.dados) {
            const dados = data.dados;
            const registroTipo = dados.tipo_registro || 'Registro';
            const registroId = dados.id || '';
            const registroNumero = dados.numero || '';
            
            responseContent += `
                <div class="confirmation-card">
                    <div class="confirmation-card-header">
                        <div class="confirmation-card-icon">✓</div>
                        <span>${escapeHtml(registroTipo)} Criado</span>
                    </div>
                    <div class="confirmation-card-body">
                        <div class="confirmation-card-field">
                            <span class="confirmation-card-label">ID</span>
                            <span class="confirmation-card-value">${escapeHtml(String(registroId))}</span>
                        </div>
                        ${registroNumero ? `
                        <div class="confirmation-card-field">
                            <span class="confirmation-card-label">Número</span>
                            <span class="confirmation-card-value">${escapeHtml(registroNumero)}</span>
                        </div>` : ''}
                    </div>
                </div>`;
        }

        // Tool Use v2: card de confirmação para ação destrutiva pendente
        if (data.pending_action && data.pending_action.confirmation_token) {
            const pa = data.pending_action;
            const token = pa.confirmation_token;
            const extras = pa.extras || {};
            const resumo = formatPendingArgs(pa.tool, pa.args || {}, extras);
            const temMateriaisNovos = Array.isArray(extras.materiais_novos) && extras.materiais_novos.length > 0;
            const tokAttr = escapeHtmlAttr(token);
            const btnCadastrar = temMateriaisNovos
                ? `<button type="button" class="btn btn-confirm-alt" data-confirm-ia="${tokAttr}" data-cadastrar="1">Confirmar e cadastrar produto</button>`
                : '';
            responseContent += `
                <div class="pending-action-card" role="dialog" aria-labelledby="pa-title-${token.slice(0,8)}" data-token="${tokAttr}">
                    <div class="pending-action-header" id="pa-title-${token.slice(0,8)}">⚠️ Confirmação necessária</div>
                    <div class="pending-action-tool"><strong>${humanizeToolName(pa.tool)}</strong></div>
                    <div class="pending-action-summary">${resumo}</div>
                    <div class="pending-action-guidance">Revise os dados abaixo antes de confirmar.</div>
                    <div class="pending-action-buttons">
                        <button type="button" class="btn btn-primary" data-confirm-ia="${tokAttr}">Confirmar</button>
                        ${btnCadastrar}
                        <button type="button" class="btn btn-secondary" data-cancel-ia="1">Cancelar</button>
                    </div>
                </div>`;
        }

        // Renderizar sugestões de follow-up se disponíveis
        let sugestoes = [];
        try {
            if (data.acao_sugerida) {
                sugestoes = JSON.parse(data.acao_sugerida);
            }
        } catch (e) { /* ignorar parse error */ }

        const tipoResp = data.tipo_resposta || (data.dados && data.dados.tipo) || '';
        if (tipoResp === 'orcamento_criado' || tipoResp === 'orcamento_atualizado') {
            sugestoes = getOrcamentoFollowupSuggestions(data, sugestoes, tipoResp);
        }

        if (Array.isArray(sugestoes) && sugestoes.length > 0) {
            const chips = sugestoes
                .map((s, i) => {
                    const icon = getSuggestionIcon(s);
                    const enc = encodeURIComponent(s);
                    return `<button type="button" class="sugestao-chip" data-suggestion="${enc}" data-index="${i}" title="Clique para explorar">${icon}<span>${escapeHtml(s)}</span></button>`;
                })
                .join('');
            responseContent += `<div class="sugestoes-container"><div class="sugestoes-header"><span class="sug-icon">✨</span> Próximos passos sugeridos</div>${chips}</div>`;
        }

        const responseHasText = String(responseContent || '')
            .replace(/<[^>]*>/g, '')
            .replace(/&nbsp;/g, ' ')
            .trim()
            .length > 0;
        if (!responseHasText) {
            responseContent = `<div class="resposta-direta">Não consegui montar a resposta completa agora. Tente novamente em alguns segundos.</div>`;
        }

        // Botões de feedback (👍/👎) — não exibir para onboarding ou erros
        const tipoSemFeedback = ['onboarding', 'orcamento_preview', 'orcamento_criado', 'orcamento_atualizado', 'operador_resultado', 'registro_criado'];
        if (!tipoSemFeedback.includes(data.tipo_resposta) && responseHasText) {
            const fbId = 'fb_' + Date.now();
            responseContent += `
                <div class="feedback-bar" id="${fbId}">
                    <span class="feedback-label">Útil?</span>
                    <button type="button" class="feedback-btn" data-feedback-id="${fbId}" data-feedback-val="positivo" title="Sim, ajudou">👍</button>
                    <button type="button" class="feedback-btn" data-feedback-id="${fbId}" data-feedback-val="negativo" title="Não ajudou">👎</button>
                </div>`;
            // Guardar dados da resposta no elemento para envio do feedback
            window._feedbackData = window._feedbackData || {};
            window._feedbackData[fbId] = {
                pergunta: _ultimaPergunta,
                resposta: data.resposta || '',
                modulo_origem: data.modulo_origem || data.tipo_resposta || 'geral',
            };
        }

        let msgEl;
        if (!isStreamed) {
            msgEl = addMessage(responseContent, false);
        } else {
            msgEl = loadingMessage;
            if (responseContent) {
                const bubble = loadingMessage.querySelector('.message-bubble');
                if (bubble) bubble.insertAdjacentHTML('beforeend', responseContent);
            }
            if (data.grafico && window.Chart) {
                setTimeout(() => renderChart(msgEl.querySelector('.message-bubble'), data.grafico), 100);
            }
        }

        // Guardar última pergunta enviada para associar ao feedback
        if (msgEl) msgEl.dataset.pergunta = '';
        
        // Stagger chips após DOM inserido para garantir transição CSS
        setTimeout(() => {
            const chips = msgEl?.querySelectorAll('.sugestao-chip');
            chips?.forEach((chip, i) => {
                setTimeout(() => chip.classList.add('visible'), i * 100);
            });
        }, 150);

        // Inovação 3 — Quick Reply Chips no mobile (acima do input)
        if (window.innerWidth <= 768 && Array.isArray(sugestoes) && sugestoes.length > 0) {
            _showQuickReplyChips(sugestoes.slice(0, 3));
        }

        if (isStreamed) {
             setTimeout(saveChatHistory, 500);
        }

    } else {
        let errorMessage = 'Não foi possível processar sua solicitação.';
        if (data.resposta) errorMessage = data.resposta;  // campo principal do COTTE
        if (data.message)  errorMessage = data.message;
        if (data.detail) {
            errorMessage = typeof data.detail === 'string'
                ? data.detail
                : (Array.isArray(data.detail) ? data.detail.map(d => (d && d.msg) || d).join(', ') : errorMessage);
        }
        addMessage(textToHtmlPlain(String(errorMessage)), false, true);
    }
}


/**
 * Formata a resposta da IA
 * Renderização diferenciada baseada no tipo de resposta
 */
function formatAIResponse(data, isStreamed = false) {
    let content = '';
    
    // Extrair dados da resposta (pode ser resposta completa ou apenas dados)
    const dados = data.dados || data;
    
    const tipoResposta = data.tipo_resposta || dados.tipo;

    // ─── PRÉVIA DE ORÇAMENTO ───────────────────────────────────────────
    if (tipoResposta === 'orcamento_preview' && dados) {
        const valorFmt = formatValue(dados.valor || 0);

        let clienteHtml = '';
        if (dados.cliente_ambiguo && dados.clientes_sugeridos && dados.clientes_sugeridos.length > 0) {
            const opts = dados.clientes_sugeridos.map(c =>
                `<option value="${escapeHtmlAttr(String(c.id))}">${escapeHtml(c.nome)}</option>`
            ).join('');
            clienteHtml = `<div class="orc-field orc-field-col"><span class="orc-label">Cliente</span>
                <select class="orc-select" id="orc-cliente-select">
                    <option value="">-- Selecionar Cliente --</option>${opts}
                </select></div>`;
        } else if (dados.cliente_encontrado) {
            clienteHtml = `<div class="orc-field"><span class="orc-label">Cliente</span><span class="orc-value orc-ok">✓ ${escapeHtml(dados.cliente_nome)}</span></div>`;
        } else {
            clienteHtml = `<div class="orc-field"><span class="orc-label">Cliente</span><span class="orc-value orc-warn">${escapeHtml(dados.cliente_nome || 'A definir')}</span></div>`;
        }

        const descontoHtml = dados.desconto > 0
            ? `<div class="orc-field"><span class="orc-label">Desconto</span><span class="orc-value">${escapeHtml(String(dados.desconto))}${dados.desconto_tipo === 'percentual' ? '%' : ' R$'}</span></div>`
            : '';

        const previewJson = JSON.stringify(dados);

        return `<div class="orc-preview-card">
            <div class="orc-preview-header">Prévia do Orçamento</div>
            ${clienteHtml}
            <div class="orc-field"><span class="orc-label">Serviço</span><span class="orc-value">${escapeHtml(dados.servico || '—')}</span></div>
            <div class="orc-field"><span class="orc-label">Valor</span><span class="orc-value orc-valor">${valorFmt}</span></div>
            ${descontoHtml}
            <div class="orc-actions">
                <button type="button" class="orc-confirm-btn" data-orc-confirm="1">Confirmar e Criar</button>
                <button type="button" class="orc-cancel-btn" data-orc-dismiss="1">Cancelar</button>
            </div>
            <script type="application/json" class="orc-data">${previewJson.replace(/<\/script>/g, '<\\/script>')}<\/script>
        </div>`;
    }

    // ─── ORÇAMENTO CRIADO ─────────────────────────────────────────────
    if (tipoResposta === 'orcamento_criado' && dados) {
        const orcId   = dados.id || '';
        const orcNum  = dados.numero || '';
        const numSeq  = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
        const clienteNome = dados.cliente_nome || 'Cliente não informado';
        const servicoDesc = dados.servico || dados.descricao || 'Serviços gerais';
        
        const copiarBtn = dados.link_publico
            ? `<button type="button" class="orc-action-btn btn-link" data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}">🔗 Copiar link público</button>`
            : '';
        const numEnc = encodeURIComponent(orcNum);
        const aprovarEnc = encodeURIComponent('aprovar ' + numSeq);
        const totalFmt = formatValue(dados.total);
        
        let metaTags = `<span class="orc-success-meta-item">👤 ${escapeHtml(clienteNome)}</span>`;
        if (dados.desconto && dados.desconto > 0) {
            metaTags += `<span class="orc-success-meta-item highlight-meta">🏷️ Desconto: ${formatValue(dados.desconto)}</span>`;
        }
        if (dados.validade_dias) {
            metaTags += `<span class="orc-success-meta-item">⏱️ Validade: ${dados.validade_dias} dias</span>`;
        }

        return `<div class="orc-success-card">
            <div class="orc-success-topline">
                <span class="orc-success-icon" aria-hidden="true">✓</span>
                <span class="orc-success-kicker">Orçamento Gerado com Sucesso</span>
            </div>
            <div class="orc-success-num">${escapeHtml(orcNum || 'Orçamento')}</div>
            <div class="orc-success-details">
                <strong>Serviço/Produto:</strong> ${escapeHtml(servicoDesc)}<br>
                <div style="margin-top: 8px; font-size: 1.1rem; color: var(--ai-text);"><strong>Total:</strong> ${escapeHtml(totalFmt)}</div>
            </div>
            <div class="orc-success-meta">
                ${metaTags}
            </div>
            <div class="orc-action-btns orc-action-btns--success">
                <button type="button" class="orc-action-btn btn-whats" data-enviar-wa="${orcId}" data-orc-numero="${numEnc}">📱 Enviar WhatsApp</button>
                <button type="button" class="orc-action-btn btn-email" data-enviar-email="${orcId}" data-orc-numero="${numEnc}">📧 Enviar E-mail</button>
                <button type="button" class="orc-action-btn btn-aprovar" data-quick-send="${aprovarEnc}">✅ Aprovar Agora</button>
                ${copiarBtn}
            </div>
        </div>`;
    }

    // ─── ORÇAMENTO ATUALIZADO ─────────────────────────────────────────
    if (tipoResposta === 'orcamento_atualizado' && dados) {
        const orcNum  = dados.numero || '';
        const numSeq  = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
        const clienteNome = dados.cliente_nome || '';
        const totalFmt = formatValue(dados.total);
        const numEnc = encodeURIComponent(orcNum);
        const verEnc = encodeURIComponent('ver ' + numSeq);

        return `<div class="orc-success-card">
            <div class="orc-success-topline">
                <span class="orc-success-icon" aria-hidden="true">✓</span>
                <span class="orc-success-kicker">Orçamento Atualizado com Sucesso</span>
            </div>
            <div class="orc-success-num">${escapeHtml(orcNum || 'Orçamento')}</div>
            <div class="orc-success-details">
                ${clienteNome ? `<strong>Cliente:</strong> ${escapeHtml(clienteNome)}<br>` : ''}
                <div style="margin-top: 8px; font-size: 1.1rem; color: var(--ai-text);"><strong>Novo total:</strong> ${escapeHtml(totalFmt)}</div>
            </div>
            <div class="orc-action-btns orc-action-btns--success">
                <button type="button" class="orc-action-btn btn-whats" data-enviar-wa="${dados.id || ''}" data-orc-numero="${numEnc}">📱 Enviar WhatsApp</button>
                <button type="button" class="orc-action-btn btn-email" data-enviar-email="${dados.id || ''}" data-orc-numero="${numEnc}">📧 Enviar E-mail</button>
                <button type="button" class="orc-action-btn" data-quick-send="${verEnc}">🔍 Ver orçamento</button>
            </div>
        </div>`;
    }

    // ─── RESULTADO DE COMANDO OPERADOR ────────────────────────────────
    if (tipoResposta === 'operador_resultado') {
        const acaoIcones = { 'VER': '🔍', 'APROVADO': '✅', 'RECUSADO': '❌', 'ENVIADO': '📤', 'DESCONTO': '💰', 'ADICIONADO': '➕', 'REMOVIDO': '➖' };
        const acao = dados && dados.acao ? dados.acao : '';
        const icone = acaoIcones[acao] || '⚡';
        const linkHtml = dados && dados.id ? `<a href="orcamentos.html" class="opr-link">Ver orçamento →</a>` : '';

        if (acao === 'VER' && dados) {
            const itensHtml = (dados.itens || []).map((it, i) =>
                `<div class="opr-field"><span>${i + 1}. ${escapeHtml(it.descricao)}</span><span>R$ ${Number(it.total).toFixed(2)}</span></div>`
            ).join('');

            // Badge de status colorido
            const statusMap = { rascunho:'badge-rascunho', enviado:'badge-enviado', aprovado:'badge-aprovado', em_execucao:'badge-em-execucao', aguardando_pagamento:'badge-aguardando-pagamento', recusado:'badge-recusado', expirado:'badge-expirado' };
            const statusKey = (dados.status || '').toLowerCase();
            const badgeClass = statusMap[statusKey] || 'badge-rascunho';
            const statusBadge = `<span class="opr-status-badge ${badgeClass}">${escapeHtml(dados.status || '')}</span>`;

            // Campos extras opcionais
            const pagFmt = { a_vista:'À vista', pix:'PIX', '2x':'2×', '3x':'3×', '4x':'4×' };
            const formaHtml = dados.forma_pagamento
                ? `<div class="opr-field"><span>Pagamento</span><span>${escapeHtml(pagFmt[dados.forma_pagamento] || String(dados.forma_pagamento))}</span></div>` : '';
            const validadeHtml = dados.validade_dias
                ? `<div class="opr-field"><span>Validade</span><span>${escapeHtml(String(dados.validade_dias))} dias</span></div>` : '';
            const obsHtml = dados.observacoes
                ? `<div class="opr-field" style="flex-direction:column;align-items:flex-start;gap:3px;"><span style="font-size:0.75em;color:var(--ai-muted)">Observações</span><span class="operador-md" style="font-size:0.82em;">${textToHtmlRich(dados.observacoes)}</span></div>` : '';
            const linkPublicoHtml = dados.link_publico
                ? `<div class="opr-field"><span>Link público</span><button type="button" class="orc-action-btn" style="flex:unset;padding:3px 8px;font-size:0.74em;" data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}">📋 Copiar link</button></div>` : '';

            // Botões de ação contextuais por status
            const orcId  = dados.id || '';
            const orcNum = dados.numero || '';
            const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
            const numEnc = encodeURIComponent(orcNum);
            const aprovarEnc = encodeURIComponent('aprovar ' + numSeq);
            let botoesHtml = '';
            if (['rascunho','enviado'].includes(statusKey)) {
                const disWhats = dados.tem_telefone ? '' : 'disabled title="Cliente sem telefone"';
                const disEmail = dados.tem_email    ? '' : 'disabled title="Cliente sem e-mail"';
                botoesHtml = `
                    <div class="orc-action-btns">
                        <button type="button" class="orc-action-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}">📱 WhatsApp</button>
                        <button type="button" class="orc-action-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}">📧 E-mail</button>
                        <button type="button" class="orc-action-btn btn-aprovar" data-quick-send="${aprovarEnc}">✅ Aprovar</button>
                    </div>`;
            } else if (statusKey === 'aprovado') {
                const disWhats = dados.tem_telefone ? '' : 'disabled title="Cliente sem telefone"';
                botoesHtml = `
                    <div class="orc-action-btns">
                        <button type="button" class="orc-action-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}">📱 Reenviar WhatsApp</button>
                    </div>`;
            }

            return `<div class="opr-card">
                <div class="opr-numero">${escapeHtml(orcNum)} &nbsp;${statusBadge}</div>
                <div class="opr-field"><span>Cliente</span><span>${escapeHtml(dados.cliente || '—')}</span></div>
                ${itensHtml}
                <div class="opr-field"><span>Total</span><span><strong>${formatValue(dados.total || 0)}</strong></span></div>
                ${formaHtml}${validadeHtml}${obsHtml}${linkPublicoHtml}
                ${botoesHtml}
            </div>`;
        }

        const respText = data.resposta || (dados && dados.resposta) || '';
        return `<div class="opr-result operador-md ${data.sucesso !== false ? 'opr-ok' : 'opr-err'}">
            <span class="opr-icon">${icone}</span>
            <span>${textToHtmlRich(respText)}</span>
            ${linkHtml}
        </div>`;
    }

    // ─── SALDO RÁPIDO ─────────────────────────────────────────────────
    if (tipoResposta === 'saldo_caixa' || dados.tipo === 'saldo_caixa') {
        const saldoAtual = dados.saldo_atual || dados.valor || 0;
        const saldoFormatado = formatValue(saldoAtual);
        
        return `
            <div class="saldo-rapido-resposta">
                <div class="saldo-label">Saldo em Caixa</div>
                <div class="saldo-valor ${saldoAtual >= 0 ? 'positivo' : 'negativo'}">${saldoFormatado}</div>
                <div class="saldo-data">Atualizado em ${new Date().toLocaleDateString('pt-BR')}</div>
            </div>
        `;
    }
    
    // ─── ONBOARDING GUIADO ────────────────────────────────────────────
    if (tipoResposta === 'onboarding' && dados) {
        const progresso = dados.progresso_pct || 0;
        const checklist = dados.checklist || [];
        const mensagem  = dados.mensagem || '';
        const acao      = dados.acao_principal;
        const concluido = dados.concluido || false;

        const itensHtml = checklist.map(item =>
            `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;${item.concluida ? '' : 'color:var(--muted)'}">
                <span style="flex-shrink:0">${item.concluida ? '✅' : '⬜'}</span>
                <span style="font-size:13px">${escapeHtml(item.titulo)}</span>
            </div>`
        ).join('');

        const btnHtml = (!concluido && acao)
            ? `<button type="button" class="btn btn-primary" style="width:100%;margin-top:14px;justify-content:center"
                onclick="window.location.href='${escapeHtmlAttr(acao.destino)}'">${escapeHtml(acao.label)} →</button>`
            : '';

        const mensagemHtml = mensagem
            ? `<p class="onboarding-md" style="font-size:13px;color:var(--text);margin:12px 0 0;white-space:pre-line">${textToHtmlRich(mensagem)}</p>`
            : '';

        return `<div style="background:var(--accent-dim);border:1px solid rgba(6,182,212,0.3);border-radius:12px;padding:18px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                <span style="font-weight:700;font-size:14px">🚀 Configuração inicial</span>
                <span style="background:var(--accent);color:#fff;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:700">${progresso}%</span>
            </div>
            <div style="height:6px;background:rgba(6,182,212,0.15);border-radius:3px;overflow:hidden;margin-bottom:12px">
                <div style="height:100%;width:${progresso}%;background:var(--accent);border-radius:3px;transition:width .4s"></div>
            </div>
            <div>${itensHtml}</div>
            ${mensagemHtml}
            ${btnHtml}
        </div>`;
    }

    // ─── LISTAS DE DADOS GENÉRICAS (TABELA RICA) ──────────────────────
    let listaObjetos = Array.isArray(dados) ? dados : null;
    if (!listaObjetos && dados && typeof dados === 'object') {
        const skipKeys = ['insights', 'checklist'];
        for (const key in dados) {
            if (!skipKeys.includes(key) && Array.isArray(dados[key]) && dados[key].length > 0 && typeof dados[key][0] === 'object' && dados[key][0] !== null) {
                listaObjetos = dados[key];
                break;
            }
        }
    }

    if (listaObjetos && listaObjetos.length > 0) {
        const headersSet = new Set();
        listaObjetos.slice(0, 10).forEach(obj => {
            if(obj) Object.keys(obj).forEach(k => headersSet.add(k));
        });
        const headers = Array.from(headersSet)
            .filter(k => !k.toLowerCase().includes('id') && typeof listaObjetos[0][k] !== 'object')
            .slice(0, 6);
            
        const ths = headers.map(h => `<th>${escapeHtml(String(h).replace(/_/g, ' ').replace(/^[a-z]/, l => l.toUpperCase()))}</th>`).join('');

        const trs = listaObjetos.map(obj => {
            const tds = headers.map(h => {
                let val = obj[h];
                if (typeof val === 'number') {
                    if (h.toLowerCase().match(/valor|total|preco|preço|saldo|despesa|receita/)) {
                        val = formatValue(val);
                    } else if (val % 1 !== 0) {
                        val = val.toLocaleString('pt-BR');
                    }
                } else if (typeof val === 'boolean') {
                    val = val ? 'Sim' : 'Não';
                }
                return `<td><span class="ai-td-content">${escapeHtml(String(val ?? '—'))}</span></td>`;
            }).join('');
            return `<tr>${tds}</tr>`;
        }).join('');

        if (!isStreamed) {
            let textoPrincipal = data.resposta || dados.resposta || dados.resumo || '';
            if (textoPrincipal) {
                content += `<div class="resposta-direta">${textToHtmlRich(textoPrincipal)}</div>`;
            }

            content += `
                <div class="ai-table-wrapper">
                    <table class="ai-table">
                        <thead><tr>${ths}</tr></thead>
                        <tbody>${trs}</tbody>
                    </table>
                </div>`;
        }
            
        if (dados.kpi_principal) {
            content += `<br>🎯 <strong>${escapeHtml(dados.kpi_principal.nome)}:</strong> ${formatValue(dados.kpi_principal.valor)}<br>`;
        }
            
        return content;
    }

    // ─── RESPOSTA COM TEXTO PRONTO (resposta direta da IA) ────────────
    if (data.resposta || dados.resposta) {
        const rawTxt = data.resposta || dados.resposta;
        if (isStreamed && data.stream_has_chunks) {
            return '';
        }
        return `<div class="resposta-direta">${textToHtmlRich(rawTxt)}</div>`;
    }

    // ─── DASHBOARD E ANÁLISES DETALHADAS ──────────────────────────────
    // Todas as propriedades devem ser lidas de 'dados'
    if (dados.resumo) {
        content += textToHtmlRich(dados.resumo) + '<br><br>';
    }

    if (dados.kpi_principal) {
        content += `🎯 <strong>${escapeHtml(dados.kpi_principal.nome)}:</strong> ${formatValue(dados.kpi_principal.valor)}<br>`;
        if (dados.kpi_principal.comparacao) {
            content += `📈 ${textToHtmlRich(dados.kpi_principal.comparacao)}<br>`;
        }
        content += '<br>';
    }

    if (dados.valor !== undefined && dados.valor !== null && dados.tipo !== 'saldo') {
        content += `💰 <strong>Valor:</strong> ${formatValue(dados.valor)}<br><br>`;
    }

    if (dados.taxa_conversao !== undefined) {
        content += `📊 <strong>Taxa de Conversão:</strong> ${(dados.taxa_conversao * 100).toFixed(1)}%<br>`;
        content += `📋 <strong>Enviados:</strong> ${escapeHtml(String(dados.orcamentos_enviados ?? '—'))} | `;
        content += `✅ <strong>Aprovados:</strong> ${escapeHtml(String(dados.orcamentos_aprovados ?? '—'))}<br>`;
        if (dados.ticket_medio) {
            content += `💰 <strong>Ticket Médio:</strong> ${formatValue(dados.ticket_medio)}<br>`;
        }
        if (dados.servico_mais_vendido) {
            content += `🔥 <strong>Serviço:</strong> ${escapeHtml(dados.servico_mais_vendido)}<br>`;
        }
        content += '<br>';
    }

    if (dados.sugestao) {
        content += `💡 ${textToHtmlRich(dados.sugestao)}<br>`;
        if (dados.impacto_estimado) {
            content += `📈 <strong>Impacto:</strong> ${textToHtmlRich(dados.impacto_estimado)}<br>`;
        }
        if (dados.acao_imediata) {
            content += `⚡ <strong>Ação:</strong> ${textToHtmlRich(dados.acao_imediata)}<br>`;
        }
        content += '<br>';
    }

    if (dados.insights && dados.insights.length > 0) {
        content += '🔍 <strong>Insights:</strong><br>';
        dados.insights.forEach(insight => {
            content += `• ${textToHtmlRich(insight)}<br>`;
        });
        content += '<br>';
    }

    return content || (isStreamed ? '' : 'Resposta recebida.');
}

/**
 * Formata valores monetários
 */
function formatValue(value) {
    if (typeof value === 'number') {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }
    return value;
}

/**
 * Confirma e cria o orçamento a partir da prévia exibida no chat.
 * Lê os dados do elemento <script type="application/json"> dentro do card.
 */
async function confirmarOrcamento(btn) {
    if (!hasHttpClient()) return;

    const card = btn.closest('.orc-preview-card');
    const scriptEl = card ? card.querySelector('.orc-data') : null;
    if (!scriptEl) return;

    let dados;
    try { dados = JSON.parse(scriptEl.textContent); } catch (e) { return; }

    const select = card.querySelector('#orc-cliente-select');
    const clienteId = select ? (parseInt(select.value) || null) : (dados.cliente_id || null);

    const body = {
        cliente_id: clienteId,
        cliente_nome: dados.cliente_nome || 'A definir',
        servico: dados.servico || 'Serviço',
        valor: dados.valor || 0,
        desconto: dados.desconto || 0,
        desconto_tipo: dados.desconto_tipo || 'percentual',
        observacoes: dados.observacoes || null
    };

    // Desabilitar botão para evitar duplo clique
    btn.disabled = true;
    btn.textContent = 'Criando...';

    const loadingMsg = addMessage('', false, false, true);
    try {
        const data = await httpClient.post('/ai/orcamento/confirmar', body, { bypassAutoLogout: true });
        if (loadingMsg) loadingMsg.remove();
        if (card) card.remove(); // Remove card de prévia após criação
        processAIResponse(data, null);
    } catch (e) {
        if (loadingMsg) loadingMsg.remove();
        btn.disabled = false;
        btn.textContent = 'Confirmar e Criar';
        addMessage('Erro ao criar o orçamento. Tente novamente.', false, true);
    }
}

/**
 * Resposta simulada para modo demonstração
 */
function mockAIResponse(endpoint, body) {
    return new Promise(resolve => {
        setTimeout(() => {
            let response;
            const message = body?.mensagem || '';
            
            if (endpoint.includes('/financeiro/') || message.toLowerCase().includes('finança')) {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: "💰 Análise Financeira (Demonstração)",
                        kpi_principal: {
                            nome: "Saldo Disponível",
                            valor: 12500.75,
                            comparacao: "↑ 12% este mês"
                        },
                        insights: [
                            "Maior receita no período da tarde",
                            "Cliente João Silva é o mais lucrativo",
                            "Aumento de 15% em manutenção"
                        ]
                    }
                };
            } else if (endpoint.includes('/conversao/') || message.toLowerCase().includes('ticket')) {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: "📊 Análise de Conversão (Demonstração)",
                        taxa_conversao: 0.72,
                        orcamentos_enviados: 38,
                        orcamentos_aprovados: 27,
                        ticket_medio: 920.00,
                        servico_mais_vendido: "Instalação Elétrica",
                        insights: [
                            "Taxa de conversão acima da média",
                            "WhatsApp é o canal mais eficiente",
                            "Orçamentos com fotos têm 40% mais aprovação"
                        ]
                    }
                };
            } else if (endpoint.includes('/negocio/') || message.toLowerCase().includes('sugest')) {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: "💡 Sugestões de Negócio (Demonstração)",
                        sugestao: "Aumente seu ticket médio oferecendo pacotes de serviços",
                        impacto_estimado: "Aumento de R$ 2.500/mês em receita",
                        acao_imediata: "Crie 3 pacotes de serviços",
                        insights: [
                            "Pacote 'Manutenção Completa' tem maior aceitação",
                            "Clientes empresariais preferem contratos mensais"
                        ]
                    }
                };
            } else {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: "🤖 Assistente COTTE (Demonstração)",
                        insights: [
                            "Modo demonstração ativo",
                            "Dados apresentados são simulados"
                        ]
                    }
                };
            }
            resolve(response);
        }, 800);
    });
}

/**
 * Envia feedback 👍/👎 de uma resposta do assistente
 */
async function enviarFeedback(fbId, avaliacao, btnClicado) {
    const barEl = document.getElementById(fbId);
    if (!barEl) return;

    const fbData = (window._feedbackData || {})[fbId] || {};

    // Se negativo, mostrar campo de comentário opcional antes de enviar
    if (avaliacao === 'negativo') {
        barEl.innerHTML = `
            <div class="feedback-negativo">
                <span class="feedback-label">O que você precisava saber?</span>
                <textarea id="${fbId}_txt" class="feedback-textarea" placeholder="Opcional — ajuda a melhorar o assistente" rows="2" maxlength="500"></textarea>
                <div class="feedback-negativo-btns">
                    <button type="button" class="feedback-send-btn">Enviar</button>
                    <button type="button" class="feedback-skip-btn">Pular</button>
                </div>
            </div>`;
        barEl.querySelector('.feedback-send-btn')?.addEventListener('click', () => _confirmarFeedbackNegativo(fbId));
        barEl.querySelector('.feedback-skip-btn')?.addEventListener('click', () => _confirmarFeedbackNegativo(fbId, true));
        window._feedbackData[fbId].avaliacao = 'negativo';
        return;
    }

    // Positivo: enviar diretamente
    await _enviarFeedbackApi(fbData.pergunta, fbData.resposta, avaliacao, null, fbData.modulo_origem);
    barEl.innerHTML = '<span class="feedback-enviado">✓ Obrigado!</span>';
    delete (window._feedbackData || {})[fbId];
}

async function _confirmarFeedbackNegativo(fbId, pular = false) {
    const barEl = document.getElementById(fbId);
    const fbData = (window._feedbackData || {})[fbId] || {};
    const comentario = pular ? null : (document.getElementById(fbId + '_txt') || {}).value || null;
    await _enviarFeedbackApi(fbData.pergunta, fbData.resposta, 'negativo', comentario, fbData.modulo_origem);
    barEl.innerHTML = '<span class="feedback-enviado">✓ Obrigado pelo retorno!</span>';
    delete (window._feedbackData || {})[fbId];
}

/**
 * Envia orçamento por WhatsApp diretamente via endpoint de orcamentos
 */
async function enviarPorWhatsapp(id, numero, btnEl) {
    if (!hasHttpClient()) return;

    if (!id) return;
    let orcInfo = null;
    try {
        orcInfo = await httpClient.get(`/orcamentos/${id}`);
    } catch (_) { /* segue o fluxo */ }
    const stW = (orcInfo?.status || '').toLowerCase();
    const precisaW = !!(orcInfo && (orcInfo.enviado_em || (stW && stW !== 'rascunho')));
    if (precisaW) {
        let ok = true;
        if (typeof cotteConfirmarReenvioSeNecessario === 'function') {
            ok = await cotteConfirmarReenvioSeNecessario(orcInfo, 'whatsapp');
        } else if (!confirm('Este orçamento já foi enviado ao cliente antes. Deseja enviar novamente pelo WhatsApp?')) {
            ok = false;
        }
        if (!ok) return;
    }
    if (btnEl) { btnEl.disabled = true; btnEl.textContent = '⏳ Enviando...'; }
    try {
        await httpClient.post(`/orcamentos/${id}/enviar-whatsapp`, {});
        addMessage(`${escapeHtml(String(numero))} enviado por WhatsApp com sucesso!`, false);
        if (btnEl) { btnEl.textContent = '✓ Enviado'; }
    } catch (err) {
        const rawMsg = err?.detail || err?.message || 'Erro ao enviar por WhatsApp.';
        if (rawMsg.startsWith('cliente_sem_telefone:')) {
            const partes = rawMsg.split(':');
            const clienteId = partes[1];
            const clienteNome = partes.slice(2).join(':') || 'O cliente';
            addMessage(
                `❌ <strong>${clienteNome}</strong> não tem WhatsApp cadastrado.<br>` +
                `<a href="clientes.html" style="color:var(--blue);font-weight:600">→ Cadastrar número agora</a>`,
                false, true
            );
        } else {
            addMessage(`❌ ${rawMsg}`, false, true);
        }
        if (btnEl) { btnEl.disabled = false; btnEl.textContent = '📱 WhatsApp'; }
    }
}

/**
 * Envia orçamento por e-mail diretamente via endpoint de orcamentos
 */
async function enviarPorEmail(id, numero, btnEl) {
    if (!hasHttpClient()) return;

    if (!id) return;
    let orcInfo = null;
    try {
        orcInfo = await httpClient.get(`/orcamentos/${id}`);
    } catch (_) { /* segue o fluxo */ }
    const stE = (orcInfo?.status || '').toLowerCase();
    const precisaE = !!(orcInfo && (orcInfo.enviado_em || (stE && stE !== 'rascunho')));
    if (precisaE) {
        let ok = true;
        if (typeof cotteConfirmarReenvioSeNecessario === 'function') {
            ok = await cotteConfirmarReenvioSeNecessario(orcInfo, 'email');
        } else if (!confirm('Este orçamento já foi enviado ao cliente antes. Deseja enviar novamente por e-mail?')) {
            ok = false;
        }
        if (!ok) return;
    }
    if (btnEl) { btnEl.disabled = true; btnEl.textContent = '⏳ Enviando...'; }
    try {
        await httpClient.post(`/orcamentos/${id}/enviar-email`, {});
        addMessage(`✅ ${escapeHtml(String(numero))} enviado por e-mail com sucesso!`, false);
        if (btnEl) { btnEl.textContent = '✓ Enviado'; }
    } catch (err) {
        const msg = err?.detail || err?.message || 'Erro ao enviar por e-mail.';
        addMessage(`❌ ${msg}`, false, true);
        if (btnEl) { btnEl.disabled = false; btnEl.textContent = '📧 E-mail'; }
    }
}

async function _enviarFeedbackApi(pergunta, resposta, avaliacao, comentario, modulo_origem) {
    try {
        await httpClient.post('/ai/feedback', {
            sessao_id: sessaoId,
            pergunta: pergunta || '',
            resposta: resposta || '',
            avaliacao,
            comentario: comentario || null,
            modulo_origem: modulo_origem || null,
        }, { bypassAutoLogout: true });
    } catch (e) {
        // Silencioso — falha no feedback não deve incomodar o usuário
    }
}

// ── Tool Use v2: confirmação de ações destrutivas ─────────────────────────
window._pendingConfirmationToken = null;
window._pendingOverrideArgs = null;

// Torna o nome técnico da tool legível (ex: criar_orcamento → "Criar orçamento")
function humanizeToolName(tool) {
    if (!tool) return 'Ação';
    return tool
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase())
        .replace(/Orcamento/g, 'Orçamento')
        .replace(/Movimentacao/g, 'Movimentação')
        .replace(/Recebivel/g, 'Recebível');
}

// Formata preço em BRL
function _brl(v) {
    const n = Number(v);
    if (isNaN(n)) return String(v);
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

// Resumo legível dos argumentos, por tool
function formatPendingArgs(tool, args, extras) {
    const escape = (s) => String(s ?? '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const row = (label, value) => `<div class="pa-row"><span class="pa-label">${label}:</span> <span class="pa-value">${escape(value)}</span></div>`;
    const hiddenFallbackKeys = new Set([
        'confirmation_token', 'idempotency_key', 'debug', 'tool', 'tool_name',
        'override_args', 'force', 'dry_run', 'bypass', 'internal_note'
    ]);
    const humanizeKey = (key) => String(key || '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase())
        .replace(/\bId\b/g, 'ID');
    const shouldShowFallbackKey = (key, value) => {
        if (!key || value == null || typeof value === 'object') return false;
        if (hiddenFallbackKeys.has(key)) return false;
        if (/^(debug_|internal_|_)/i.test(key)) return false;
        if (/(confirmation|token|idempot|override|trace|raw)/i.test(key)) return false;
        return true;
    };
    const lines = [];
    const a = args || {};
    const ex = extras || {};
    switch (tool) {
        case 'criar_cliente':
            lines.push(row('Nome', a.nome));
            if (a.telefone) lines.push(row('Telefone', a.telefone));
            if (a.email) lines.push(row('E-mail', a.email));
            break;
        case 'editar_cliente':
            if (ex.cliente_nome_registro) lines.push(row('👤 Cliente', ex.cliente_nome_registro));
            lines.push(row('Cliente ID', a.cliente_id));
            Object.entries(a).forEach(([k, v]) => {
                if (k !== 'cliente_id' && v != null) lines.push(row(k, v));
            });
            break;
        case 'excluir_cliente':
            if (ex.cliente_nome_registro) lines.push(row('👤 Cliente a excluir', ex.cliente_nome_registro));
            lines.push(row('Cliente ID', a.cliente_id));
            break;
        case 'criar_orcamento': {
            if (ex.cliente_nome_resolvido) {
                const tag = ex.cliente_auto_criar ? ' <span style="color:#d97706;font-size:11px;font-weight:600">(sem cadastro)</span>' : '';
                lines.push(`<div class="pa-row"><span class="pa-label">👤 Cliente:</span> <span class="pa-value">${escape(ex.cliente_nome_resolvido)}${tag}</span></div>`);
            } else if (a.cliente_id) {
                lines.push(row('👤 Cliente ID', a.cliente_id));
            } else if (a.cliente_nome) {
                lines.push(row('👤 Cliente', a.cliente_nome));
            }
            if (Array.isArray(a.itens)) {
                const total = a.itens.reduce((s, i) => s + ((Number(i.quantidade) || 1) * (Number(i.valor_unit) || 0)), 0);
                a.itens.forEach(i => {
                    const qtd = Number(i.quantidade) || 1;
                    const vu = Number(i.valor_unit) || 0;
                    const isNovo = Array.isArray(ex.materiais_novos) && ex.materiais_novos.some(m => m.descricao === i.descricao);
                    const badge = isNovo ? '<span style="color:#0d9488;font-weight:600">🆕 novo</span> ' : '';
                    lines.push(`<div class="pa-row"><span class="pa-label">•</span> <span class="pa-value">${badge}${escape(i.descricao)} — ${qtd} × ${_brl(vu)}</span></div>`);
                });
                lines.push(row('Total', _brl(total)));
            }
            if (a.observacoes) lines.push(row('Obs', a.observacoes));
            break;
        }
        case 'editar_orcamento':
        case 'duplicar_orcamento':
        case 'aprovar_orcamento':
        case 'recusar_orcamento':
        case 'enviar_orcamento_whatsapp':
        case 'enviar_orcamento_email':
        case 'anexar_documento_orcamento':
        case 'editar_item_orcamento':
            if (ex.orcamento_numero) lines.push(row('📄 Orçamento', ex.orcamento_numero));
            else if (a.orcamento_id) lines.push(row('Orçamento (ref.)', a.orcamento_id));
            if (ex.cliente_nome) lines.push(row('👤 Cliente', ex.cliente_nome));
            if (ex.total_atual != null && ex.total_atual !== '') lines.push(row('Total atual', _brl(ex.total_atual)));
            if (ex.status_orcamento) lines.push(row('Status', ex.status_orcamento));
            if (Array.isArray(ex.mudancas) && ex.mudancas.length) {
                ex.mudancas.forEach((m) => {
                    lines.push(`<div class="pa-row"><span class="pa-value">• ${escape(String(m))}</span></div>`);
                });
            }
            if (a.num_item != null) lines.push(row('Item nº', a.num_item));
            if (a.motivo) lines.push(row('Motivo', a.motivo));
            if (a.documento_id) lines.push(row('Documento ID', a.documento_id));
            if (a.observacoes) lines.push(row('Obs', a.observacoes));
            if (a.desconto != null) lines.push(row('Desconto', a.desconto));
            if (a.desconto_tipo) lines.push(row('Tipo desconto', a.desconto_tipo));
            if (a.valor_total != null) lines.push(row('Novo total', _brl(a.valor_total)));
            if (a.validade_dias != null) lines.push(row('Validade (dias)', a.validade_dias));
            if (a.descricao) lines.push(row('Nova descrição (item)', a.descricao));
            if (a.valor_unit != null) lines.push(row('Valor unitário', _brl(a.valor_unit)));
            if (a.quantidade != null) lines.push(row('Quantidade', a.quantidade));
            break;
        case 'criar_movimentacao_financeira':
            lines.push(row('Tipo', a.tipo));
            lines.push(row('Valor', _brl(a.valor)));
            lines.push(row('Descrição', a.descricao));
            if (a.categoria) lines.push(row('Categoria', a.categoria));
            break;
        case 'criar_despesa':
            lines.push(row('Descrição', a.descricao));
            lines.push(row('Valor', _brl(a.valor)));
            lines.push(row('Vencimento', a.data_vencimento));
            if (a.favorecido) lines.push(row('Favorecido', a.favorecido));
            break;
        case 'marcar_despesa_paga':
            if (ex.conta_descricao) lines.push(row('Despesa', ex.conta_descricao));
            if (ex.despesa_favorecido) lines.push(row('Favorecido', ex.despesa_favorecido));
            if (ex.conta_saldo_aberto != null && ex.conta_saldo_aberto !== '') {
                lines.push(row('Saldo em aberto', _brl(ex.conta_saldo_aberto)));
            }
            lines.push(row('Conta ID', a.conta_id));
            lines.push(row('Valor a pagar', a.valor != null ? _brl(a.valor) : 'saldo integral'));
            break;
        case 'registrar_pagamento_recebivel':
            if (ex.conta_descricao) lines.push(row('Conta a receber', ex.conta_descricao));
            if (ex.orcamento_numero) lines.push(row('📄 Orçamento', ex.orcamento_numero));
            if (ex.cliente_nome) lines.push(row('👤 Cliente', ex.cliente_nome));
            if (ex.conta_saldo_aberto != null && ex.conta_saldo_aberto !== '') {
                lines.push(row('Saldo em aberto', _brl(ex.conta_saldo_aberto)));
            }
            lines.push(row('Conta ID', a.conta_id));
            lines.push(row('Valor do recebimento', a.valor != null ? _brl(a.valor) : 'saldo integral'));
            break;
        case 'criar_parcelamento':
            if (ex.cliente_nome && (a.tipo || '').toLowerCase() === 'receber') {
                lines.push(row('👤 Cliente', ex.cliente_nome));
            }
            lines.push(row('Tipo', a.tipo));
            lines.push(row('Descrição', a.descricao));
            lines.push(row('Valor total', _brl(a.valor_total)));
            lines.push(row('Parcelas', a.parcelas));
            lines.push(row('1ª parcela', a.primeira_data));
            if (a.favorecido) lines.push(row('Favorecido', a.favorecido));
            break;
        case 'criar_agendamento':
            if (ex.cliente_nome) lines.push(row('👤 Cliente', ex.cliente_nome));
            lines.push(row('Cliente ID', a.cliente_id));
            lines.push(row('Data', a.data_agendada));
            if (a.duracao_estimada_min) lines.push(row('Duração', `${a.duracao_estimada_min} min`));
            if (a.endereco) lines.push(row('Endereço', a.endereco));
            break;
        case 'cancelar_agendamento':
            if (ex.agendamento_numero) lines.push(row('📅 Agendamento', ex.agendamento_numero));
            if (ex.cliente_nome) lines.push(row('👤 Cliente', ex.cliente_nome));
            if (ex.agendamento_data_atual) lines.push(row('Data/hora atual', ex.agendamento_data_atual));
            lines.push(row('Agendamento ID', a.agendamento_id));
            if (a.motivo) lines.push(row('Motivo', a.motivo));
            if (Array.isArray(ex.mudancas) && ex.mudancas.length) {
                ex.mudancas.forEach((m) => {
                    lines.push(`<div class="pa-row"><span class="pa-value">• ${escape(String(m))}</span></div>`);
                });
            }
            break;
        case 'remarcar_agendamento':
            if (ex.agendamento_numero) lines.push(row('📅 Agendamento', ex.agendamento_numero));
            if (ex.cliente_nome) lines.push(row('👤 Cliente', ex.cliente_nome));
            if (ex.agendamento_data_atual) lines.push(row('Data/hora atual', ex.agendamento_data_atual));
            lines.push(row('Agendamento ID', a.agendamento_id));
            lines.push(row('Nova data', a.nova_data));
            if (a.motivo) lines.push(row('Motivo', a.motivo));
            if (Array.isArray(ex.mudancas) && ex.mudancas.length) {
                ex.mudancas.forEach((m) => {
                    lines.push(`<div class="pa-row"><span class="pa-value">• ${escape(String(m))}</span></div>`);
                });
            }
            break;
        case 'cadastrar_material':
            lines.push(row('Nome', a.nome));
            if (a.preco_padrao) lines.push(row('Preço', _brl(a.preco_padrao)));
            if (a.unidade) lines.push(row('Unidade', a.unidade));
            break;
        default:
            // fallback: lista chave/valor genérica
            Object.entries(a).forEach(([k, v]) => {
                if (shouldShowFallbackKey(k, v)) lines.push(row(humanizeKey(k), v));
            });
    }
    return lines.join('') || '<div class="pa-row pa-empty">(sem detalhes adicionais)</div>';
}

function confirmarAcaoIA(token, btnEl) {
    if (!token) return;
    window._pendingConfirmationToken = token;
    if (btnEl && btnEl.dataset.cadastrar === '1') {
        window._pendingOverrideArgs = { cadastrar_materiais_novos: true };
    }
    const card = btnEl.closest('.pending-action-card');
    if (card) {
        card.querySelectorAll('button').forEach(b => b.disabled = true);
        const status = document.createElement('div');
        status.className = 'pending-action-status';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        status.textContent = '⏳ Executando ferramenta…';
        card.appendChild(status);
    }
    // Reenvia a última pergunta com o token; o backend reconhece e executa.
    const input = document.getElementById('messageInput');
    if (input && _ultimaPergunta) {
        input.value = _ultimaPergunta;
        resizeMessageInput();
        sendMessage();
    }
}

function cancelarAcaoIA(btnEl) {
    window._pendingConfirmationToken = null;
    window._pendingOverrideArgs = null;
    const card = btnEl.closest('.pending-action-card');
    if (card) {
        card.innerHTML = '<div class="pending-action-cancelled" role="status">❌ Ação cancelada.</div>';
    }
    // Foca o input — usuário decide o próximo passo sem acionar o backend
    const input = document.getElementById('messageInput');
    if (input) input.focus();
}

window.sendMessage = sendMessage;
window.sendQuickMessage = sendQuickMessage;
window.confirmarOrcamento = confirmarOrcamento;
window.enviarPorWhatsapp = enviarPorWhatsapp;
window.enviarPorEmail = enviarPorEmail;
window.confirmarAcaoIA = confirmarAcaoIA;
window.cancelarAcaoIA = cancelarAcaoIA;

// ── Health Check — detecta funções críticas ausentes ─────────────────────────
(function _assistenteHealthCheck() {
    const CRITICAL = [
        'sendMessage', 'sendQuickMessage', 'processAIResponse', 'addMessage',
        'confirmarAcaoIA', 'cancelarAcaoIA', 'confirmarOrcamento',
        'enviarPorWhatsapp', 'enviarPorEmail', 'enviarFeedback',
        'formatPendingArgs', 'humanizeToolName', 'escapeHtml',
        'initAssistenteChatDelegation', 'setAiStatus', 'resizeMessageInput',
    ];
    const missing = CRITICAL.filter(fn => typeof window[fn] !== 'function' && typeof eval('typeof ' + fn) === 'undefined');
    // Verifica no escopo local via tentativa
    const reallyMissing = CRITICAL.filter(fn => {
        try { return typeof eval(fn) !== 'function'; } catch (_) { return true; }
    });
    if (reallyMissing.length > 0) {
        console.warn('[Assistente HealthCheck] Funções críticas ausentes:', reallyMissing.join(', '));
    } else {
        console.debug('[Assistente HealthCheck] OK — todas as funções críticas presentes.');
    }
})();

function renderChart(containerOrMsgEl, grafico) {
    if (!grafico || !grafico.dados || !containerOrMsgEl) return;
    const canvasId = 'chart_' + Date.now() + Math.floor(Math.random() * 1000);
    const html = `<div class="chart-container" style="position:relative; width:100%; max-width:100%; height:300px; margin-top:16px; margin-bottom:16px; background:var(--ai-user-bg); padding:16px; border-radius:12px; border:1px solid rgba(255,255,255,0.05);"><canvas id="${canvasId}"></canvas></div>`;
    const innerBubble = containerOrMsgEl.querySelector('.message-bubble') || containerOrMsgEl;
    innerBubble.insertAdjacentHTML('beforeend', html);

    setTimeout(() => {
        const canvasEl = document.getElementById(canvasId);
        if (canvasEl && window.Chart) {
            Chart.defaults.color = '#94a3b8';
            Chart.defaults.font.family = "'Outfit', sans-serif";
            new Chart(canvasEl.getContext('2d'), {
                type: grafico.tipo || 'bar',
                data: grafico.dados,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#e2e8f0', usePointStyle: true, boxWidth: 8 } }
                    },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
            setTimeout(scrollChatToBottom, 100);
        }
    }, 200);
}
window.renderChart = renderChart;
