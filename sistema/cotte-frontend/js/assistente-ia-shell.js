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

function _decodeSemanticPrintablePayload(raw) {
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch (_) {
        return null;
    }
}

function _sanitizePrintableColor(value, fallback) {
    const raw = String(value || '').trim();
    return /^#[0-9a-fA-F]{6}$/.test(raw) ? raw : fallback;
}

function _base64ToUint8Array(base64Value) {
    const binary = atob(String(base64Value || ''));
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i += 1) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

function _buildSemanticPrintableHtml(payload) {
    const theme = payload?.theme && typeof payload.theme === 'object' ? payload.theme : {};
    const accentColor = _sanitizePrintableColor(theme.accent_color, '#0f766e');
    const accentSoft = _sanitizePrintableColor(theme.accent_soft, '#ecfdf5');
    const textColor = _sanitizePrintableColor(theme.text_color, '#111827');
    const mutedColor = _sanitizePrintableColor(theme.muted_color, '#4b5563');
    const borderColor = _sanitizePrintableColor(theme.border_color, '#d1d5db');
    const brandName = escapeHtml(String(theme.brand_name || payload?.brand?.name || 'Assistente COTTE'));
    const safeTitle = escapeHtml(String(payload?.title || 'Relatório do Assistente'));
    const safeSummary = textToHtmlRich(String(payload?.summary || ''));
    const rows = Array.isArray(payload?.rows) ? payload.rows : [];
    const period = payload?.period_days ? `${escapeHtml(String(payload.period_days))} dias` : 'Não informado';
    const filters = payload?.filters && typeof payload.filters === 'object'
        ? escapeHtml(JSON.stringify(payload.filters))
        : 'Sem filtros';
    const generatedAt = payload?.generated_at
        ? escapeHtml(String(payload.generated_at))
        : new Date().toISOString();
    let tableHtml = '';
    if (rows.length > 0) {
        tableHtml = renderSemanticTableRows(rows);
    }
    return `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>${safeTitle}</title>
  <style>
    body { font-family: "Segoe UI", Arial, sans-serif; margin: 28px; color: ${textColor}; }
    .cover { border: 1px solid ${borderColor}; border-left: 8px solid ${accentColor}; border-radius: 18px; padding: 22px 24px; background: linear-gradient(135deg, ${accentSoft}, #fff 72%); margin-bottom: 18px; }
    .brand { display:inline-block; margin-bottom:10px; padding:6px 10px; border-radius:999px; background:${accentSoft}; color:${accentColor}; font-size:12px; font-weight:700; }
    h1 { margin: 0 0 8px; font-size: 24px; }
    .meta { color: ${mutedColor}; font-size: 12px; margin-bottom: 12px; }
    .summary { margin: 12px 0 18px; line-height: 1.6; border:1px solid ${borderColor}; border-radius:14px; padding:16px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { border: 1px solid ${borderColor}; padding: 6px 8px; text-align: left; vertical-align: top; }
    thead { background: ${accentSoft}; color:${accentColor}; }
  </style>
</head>
<body>
  <div class="cover">
    <div class="brand">${brandName}</div>
    <h1>${safeTitle}</h1>
  </div>
  <div class="meta">Gerado em: ${new Date().toLocaleString('pt-BR')} | Período: ${period}</div>
  <div class="meta">Filtros: ${filters}</div>
  <div class="meta">Timestamp fonte: ${generatedAt}</div>
  <div class="summary">${safeSummary || 'Sem resumo disponível.'}</div>
  ${tableHtml || '<p>Sem dados tabulares para impressão.</p>'}
</body>
</html>`;
}

function _openSemanticPrintPreview(payload, printNow = false) {
    const html = _buildSemanticPrintableHtml(payload || {});
    const printWin = window.open('', '_blank', 'noopener,noreferrer');
    if (printWin) {
        printWin.document.open();
        printWin.document.write(html);
        printWin.document.close();
        if (printNow) {
            printWin.focus();
            setTimeout(() => {
                try { printWin.print(); } catch (_) { /* noop */ }
            }, 250);
        }
        return;
    }

    // Fallback para popup bloqueado: usa iframe oculto para preview/impressão.
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    document.body.appendChild(iframe);
    const doc = iframe.contentDocument || iframe.contentWindow?.document;
    if (!doc) {
        iframe.remove();
        return;
    }
    doc.open();
    doc.write(html);
    doc.close();
    if (printNow && iframe.contentWindow) {
        setTimeout(() => {
            try { iframe.contentWindow.print(); } catch (_) { /* noop */ }
            setTimeout(() => iframe.remove(), 1200);
        }, 250);
    } else {
        setTimeout(() => iframe.remove(), 8000);
    }
}

async function _exportSemanticReport(payload, format = 'csv') {
    try {
        const response = await httpClient.post('/ai/assistente/report/export', {
            format,
            printable_payload: payload || {},
        });
        const normalized = normalizeAssistenteApiEnvelope(response);
        const data = normalized?.data || {};
        const content = data.content || '';
        const fileName = data.file_name || `relatorio.${format}`;
        const mime = data.content_type || 'text/plain;charset=utf-8';
        let blob;
        if (data.content_base64) {
            blob = new Blob([_base64ToUint8Array(data.content_base64)], { type: mime });
        } else {
            if (!content) return;
            blob = new Blob([content], { type: mime });
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (err) {
        console.error('Falha ao exportar relatório semântico', err);
    }
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

const ASSISTENTE_CHAT_META_KEY = 'ai_chat_meta';
const ASSISTENTE_COMPACT_THRESHOLD = 8;
const ASSISTENTE_COMPACT_RECENT_COUNT = 4;
const ASSISTENTE_SCROLL_FOLLOW_THRESHOLD = 96;
const _assistenteChatUiState = {
    autoFollow: true,
    userDetached: false,
    context: { command: '', entity: '', summary: '', secondary: '' },
    pendingUserContext: null,
    programmaticScroll: false,
};

function isAssistenteEmbedMode() {
    return document.body.classList.contains('embed-mode');
}

function _normalizeContextText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
}

function _buildAssistenteContext(command = '', entity = '') {
    const normalizedCommand = _normalizeContextText(command);
    const normalizedEntity = _normalizeContextText(entity);
    return {
        command: normalizedCommand,
        entity: normalizedEntity,
        summary: normalizedCommand || normalizedEntity,
        secondary: normalizedCommand && normalizedEntity ? normalizedEntity : '',
    };
}

function _extractAssistenteCommand(text) {
    const source = _normalizeContextText(text).toLowerCase();
    if (!source) return '';

    const slashMatch = source.match(/(?:^|\s)(\/[^\s]+)/);
    if (slashMatch) {
        return slashMatch[1];
    }

    const intentMatchers = [
        { label: 'Caixa', pattern: /\bcaixa\b|\bsaldo\b/ },
        { label: 'Resumo financeiro', pattern: /\bresumo financeiro\b|\bfaturamento\b/ },
        { label: 'Contas a receber', pattern: /\breceber\b|\bem aberto\b/ },
        { label: 'Contas a pagar', pattern: /\bpagar\b/ },
        { label: 'Clientes em atraso', pattern: /\bdevendo\b|\batraso\b|\binadimpl/i },
        { label: 'Previsão de caixa', pattern: /\bprevis[aã]o\b/ },
        { label: 'Novo orçamento', pattern: /\bgerar\b.*\bor[çc]amento\b|\bcriar\b.*\bor[çc]amento\b/ },
        { label: 'Consultar orçamento', pattern: /\bver\b.*\bor[çc]amento\b|\bdetalhes?\b.*\bor[çc]amento\b/ },
        { label: 'Orçamentos pendentes', pattern: /\bor[çc]amentos?\b.*\bpendentes?\b/ },
        { label: 'Agendamentos', pattern: /\bagenda(r|mentos?)\b/ },
        { label: 'Ajuda', pattern: /\bajuda\b|\bcomo usar\b/ },
    ];

    const match = intentMatchers.find((item) => item.pattern.test(source));
    return match ? match.label : '';
}

function _extractAssistenteEntityFromText(text) {
    const source = _normalizeContextText(text);
    if (!source) return '';

    const orcNumero = source.match(/\bORC[-\s]?\d[\w-]*/i);
    if (orcNumero) {
        return `Orçamento ${orcNumero[0].toUpperCase().replace(/\s+/g, '-')}`;
    }

    const orcId = source.match(/\bor[çc]amento\s+#?(\d{1,6}(?:-\d{2})?)/i);
    if (orcId) {
        return `Orçamento ${orcId[1]}`;
    }

    const cliente = source.match(/\bcliente\s+([A-ZÀ-ÿ][\wÀ-ÿ'-]*(?:\s+[A-ZÀ-ÿ][\wÀ-ÿ'-]*){0,2})/);
    if (cliente) {
        return `Cliente ${cliente[1]}`;
    }

    return '';
}

function _extractAssistenteEntityFromResponse(data) {
    const pending = data?.pending_action || {};
    const extras = pending?.extras || {};
    const args = pending?.args || {};
    const dados = data?.dados || data || {};

    const numero = _normalizeContextText(dados.numero || dados.orcamento_numero || extras.orcamento_numero);
    if (numero) return `Orçamento ${numero}`;

    const clienteNome = _normalizeContextText(
        dados.cliente_nome
        || dados.cliente
        || extras.cliente_nome_resolvido
        || args.cliente_nome
    );
    if (clienteNome) return `Cliente ${clienteNome}`;

    const servico = _normalizeContextText(dados.servico || dados.titulo || args.servico);
    if (servico) return `Serviço ${servico}`;

    const genericId = _normalizeContextText(dados.id);
    if (genericId && /orcamento/i.test(String(data?.tipo_resposta || data?.tipo || ''))) {
        return `Orçamento #${genericId}`;
    }

    return '';
}

function _persistAssistenteChatMeta() {
    try {
        localStorage.setItem(ASSISTENTE_CHAT_META_KEY, JSON.stringify({
            context: _assistenteChatUiState.context,
        }));
    } catch (_) {
        /* noop */
    }
}

function renderAssistenteContextBar() {
    const bar = document.getElementById('embedContextBar');
    const primary = document.getElementById('embedContextBarPrimary');
    const secondary = document.getElementById('embedContextBarSecondary');
    if (!bar || !primary || !secondary) return;

    const context = _assistenteChatUiState.context || {};
    const hasSummary = !!_normalizeContextText(context.summary);
    if (!hasSummary) {
        bar.hidden = true;
        primary.textContent = '';
        secondary.textContent = '';
        return;
    }

    const primaryText = context.command
        ? `Último comando: ${context.command}`
        : `Última entidade: ${context.entity}`;
    primary.textContent = primaryText;
    secondary.textContent = context.secondary || '';
    bar.hidden = false;
}

function setAssistenteContext(command = '', entity = '', options = {}) {
    _assistenteChatUiState.context = _buildAssistenteContext(command, entity);
    renderAssistenteContextBar();
    if (options.persist !== false) {
        _persistAssistenteChatMeta();
    }
}

function trackAssistenteUserIntent(message) {
    const nextContext = _buildAssistenteContext(
        _extractAssistenteCommand(message),
        _extractAssistenteEntityFromText(message)
    );
    _assistenteChatUiState.pendingUserContext = nextContext;
    setAssistenteContext(nextContext.command, nextContext.entity);
}

function captureAssistenteResponseContext(data) {
    const pending = _assistenteChatUiState.pendingUserContext || {};
    const responseEntity = _extractAssistenteEntityFromResponse(data);
    const nextContext = _buildAssistenteContext(
        pending.command || '',
        responseEntity || pending.entity || ''
    );
    _assistenteChatUiState.pendingUserContext = null;
    setAssistenteContext(nextContext.command, nextContext.entity);
}

function restoreAssistenteChatMeta() {
    let restored = null;
    try {
        restored = JSON.parse(localStorage.getItem(ASSISTENTE_CHAT_META_KEY) || 'null');
    } catch (_) {
        restored = null;
    }

    const savedContext = restored?.context || null;
    if (savedContext && (savedContext.command || savedContext.entity || savedContext.summary)) {
        _assistenteChatUiState.context = _buildAssistenteContext(savedContext.command, savedContext.entity);
        renderAssistenteContextBar();
        return;
    }

    const box = document.getElementById('chatMessages');
    if (!box) return;
    const userMessages = Array.from(box.children)
        .filter((node) => node.classList && node.classList.contains('message') && node.classList.contains('user'));
    const lastUserBubble = userMessages.length
        ? userMessages[userMessages.length - 1].querySelector('.message-bubble')
        : null;
    const fallbackText = _normalizeContextText(lastUserBubble?.innerText || '');
    if (!fallbackText) return;
    setAssistenteContext(_extractAssistenteCommand(fallbackText), _extractAssistenteEntityFromText(fallbackText));
}

function _isAssistenteMessageProtectedFromCompact(messageEl) {
    if (!messageEl || messageEl.id === 'welcomeState' || messageEl.classList.contains('loading')) {
        return true;
    }
    return !!messageEl.querySelector('.pending-action-card, .orc-preview-card, .orc-success-card, .opr-card, .chart-container, table');
}

function updateAssistenteMessageDensity() {
    const box = document.getElementById('chatMessages');
    if (!box) return;

    const messages = Array.from(box.children)
        .filter((node) => node.classList && node.classList.contains('message'));

    messages.forEach((messageEl) => messageEl.classList.remove('message--compact'));
    box.classList.remove('chat-messages--dense');

    if (!isAssistenteEmbedMode()) return;

    const meaningfulMessages = messages.filter((messageEl) => messageEl.id !== 'welcomeState');
    if (meaningfulMessages.length <= ASSISTENTE_COMPACT_THRESHOLD) return;

    const preservedMessages = new Set(meaningfulMessages.slice(-ASSISTENTE_COMPACT_RECENT_COUNT));
    let compactedCount = 0;

    meaningfulMessages.forEach((messageEl) => {
        if (preservedMessages.has(messageEl) || _isAssistenteMessageProtectedFromCompact(messageEl)) {
            return;
        }
        messageEl.classList.add('message--compact');
        compactedCount += 1;
    });

    if (compactedCount > 0) {
        box.classList.add('chat-messages--dense');
    }
}

function _isChatNearBottom(threshold = ASSISTENTE_SCROLL_FOLLOW_THRESHOLD) {
    const box = document.getElementById('chatMessages');
    if (!box) return true;
    return (box.scrollHeight - box.scrollTop - box.clientHeight) < threshold;
}

function shouldAutoFollowChat(force = false) {
    return force || !isAssistenteEmbedMode() || _assistenteChatUiState.autoFollow;
}

function handleAssistenteChatScroll() {
    const box = document.getElementById('chatMessages');
    if (!box) return;

    if (_assistenteChatUiState.programmaticScroll) {
        updateScrollBottomButtonVisibility();
        return;
    }

    const nearBottom = _isChatNearBottom();
    _assistenteChatUiState.autoFollow = nearBottom;
    _assistenteChatUiState.userDetached = !nearBottom;
    updateScrollBottomButtonVisibility();
}

function setChatAutoFollow(enabled, options = {}) {
    _assistenteChatUiState.autoFollow = !!enabled;
    _assistenteChatUiState.userDetached = !enabled;
    if (enabled && options.scroll !== false) {
        scrollChatToBottom({
            force: true,
            behavior: options.behavior || 'auto',
        });
        return;
    }
    updateScrollBottomButtonVisibility();
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

function scrollChatToBottom(options = {}) {
    const el = document.getElementById('chatMessages');
    if (!el) return;

    const force = !!options.force;
    if (force) {
        _assistenteChatUiState.autoFollow = true;
        _assistenteChatUiState.userDetached = false;
    }
    if (!shouldAutoFollowChat(force)) {
        updateScrollBottomButtonVisibility();
        return;
    }

    _assistenteChatUiState.programmaticScroll = true;
    const nextTop = el.scrollHeight;
    if (typeof el.scrollTo === 'function') {
        el.scrollTo({ top: nextTop, behavior: options.behavior || 'auto' });
    } else {
        el.scrollTop = nextTop;
    }
    window.setTimeout(() => {
        _assistenteChatUiState.programmaticScroll = false;
        updateScrollBottomButtonVisibility();
    }, options.behavior === 'smooth' ? 220 : 32);
    updateScrollBottomButtonVisibility();
}

function updateScrollBottomButtonVisibility() {
    const box = document.getElementById('chatMessages');
    const btn = document.getElementById('chatScrollBottomBtn');
    if (!box || !btn) return;
    const threshold = 120;
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < threshold;
    const paused = isAssistenteEmbedMode() && !_assistenteChatUiState.autoFollow;
    btn.classList.toggle('is-visible', (!nearBottom || paused) && box.scrollHeight > box.clientHeight + 40);
    btn.classList.toggle('is-paused', paused);
    btn.title = paused ? 'Retomar acompanhamento da resposta' : 'Últimas mensagens';
    btn.setAttribute('aria-label', paused ? 'Retomar acompanhamento da resposta' : 'Ir para a mensagem mais recente');
}

function novaConversaAssistente() {
    if (isLoading) return;
    const box = document.getElementById('chatMessages');
    if (!box) return;
    sessaoId = null;
    localStorage.removeItem('ai_sessao_id');
    localStorage.removeItem('ai_chat_history');
    localStorage.removeItem(ASSISTENTE_CHAT_META_KEY);
    window._pendingConfirmationToken = null;
    window._pendingOverrideArgs = null;
    window._feedbackData = {};
    box.innerHTML = _assistenteWelcomeHTML || '';
    _assistenteChatUiState.pendingUserContext = null;
    setAssistenteContext('', '', { persist: false });
    setChatAutoFollow(true, { scroll: false });
    updateAssistenteMessageDensity();
    setAiStatus('ready');
    const ta = document.getElementById('messageInput');
    if (ta) {
        ta.value = '';
        resizeMessageInput();
        _updateVoiceSendToggle(ta);
        ta.focus();
    }
    _persistAssistenteChatMeta();
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

        const retryBtn = t.closest('[data-assistente-retry]');
        if (retryBtn) {
            e.preventDefault();
            if (!_ultimaPergunta) return;
            const ta = document.getElementById('messageInput');
            if (ta) {
                ta.value = _ultimaPergunta;
                resizeMessageInput();
                _updateVoiceSendToggle(ta);
            }
            sendMessage();
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
            if (qs.hasAttribute('data-silent-send')) {
                window._silentNextMessage = true;
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

        const loadMoreBtn = t.closest('[data-orcamentos-load-more]');
        if (loadMoreBtn) {
            e.preventDefault();
            const cursor = loadMoreBtn.getAttribute('data-cursor') || '';
            const status = loadMoreBtn.getAttribute('data-status') || '';
            const clienteId = loadMoreBtn.getAttribute('data-cliente-id') || '';
            const dias = loadMoreBtn.getAttribute('data-dias') || '30';
            const lim = loadMoreBtn.getAttribute('data-limit') || '10';
            const aprovadoDe = loadMoreBtn.getAttribute('data-aprovado-em-de') || '';
            const aprovadoAte = loadMoreBtn.getAttribute('data-aprovado-em-ate') || '';
            if (!cursor) return;
            let command;
            if (aprovadoDe || aprovadoAte) {
                command = `Liste mais orçamentos com cursor "${cursor}", limite ${lim}`;
                if (aprovadoDe) command += `, aprovado_em_de ${aprovadoDe}`;
                if (aprovadoAte) command += `, aprovado_em_ate ${aprovadoAte}`;
                command += '.';
            } else {
                command = `Liste mais orçamentos com cursor "${cursor}", dias ${dias}, limite ${lim}.`;
            }
            if (status) {
                command += ` Status ${status}.`;
            }
            if (clienteId) {
                command += ` Cliente ${clienteId}.`;
            }
            window._silentNextMessage = true;
            sendQuickMessage(command);
            return;
        }

        const semanticPreviewBtn = t.closest('[data-semantic-print-preview]');
        if (semanticPreviewBtn) {
            e.preventDefault();
            const payload = _decodeSemanticPrintablePayload(semanticPreviewBtn.getAttribute('data-semantic-print-preview'));
            if (payload) _openSemanticPrintPreview(payload, false);
            return;
        }

        const semanticPrintBtn = t.closest('[data-semantic-print-now]');
        if (semanticPrintBtn) {
            e.preventDefault();
            const payload = _decodeSemanticPrintablePayload(semanticPrintBtn.getAttribute('data-semantic-print-now'));
            if (payload) _openSemanticPrintPreview(payload, true);
            return;
        }

        const semanticCopySummaryBtn = t.closest('[data-semantic-copy-summary]');
        if (semanticCopySummaryBtn) {
            e.preventDefault();
            const summary = semanticCopySummaryBtn.getAttribute('data-semantic-copy-summary') || '';
            const setFeedback = () => {
                const original = semanticCopySummaryBtn.textContent;
                semanticCopySummaryBtn.textContent = 'Resumo copiado';
                setTimeout(() => { semanticCopySummaryBtn.textContent = original || 'Copiar resumo'; }, 1400);
            };
            const fallbackCopy = () => {
                try {
                    const ta = document.createElement('textarea');
                    ta.value = summary;
                    ta.setAttribute('readonly', '');
                    ta.style.position = 'fixed';
                    ta.style.opacity = '0';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    ta.remove();
                    setFeedback();
                } catch (_) {
                    // noop
                }
            };
            if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                navigator.clipboard.writeText(summary).then(setFeedback).catch(fallbackCopy);
            } else {
                fallbackCopy();
            }
            return;
        }

        const semanticExportBtn = t.closest('[data-semantic-export-report]');
        if (semanticExportBtn) {
            e.preventDefault();
            const payload = _decodeSemanticPrintablePayload(semanticExportBtn.getAttribute('data-semantic-export-report'));
            const fmt = semanticExportBtn.getAttribute('data-export-format') || 'csv';
            if (payload) {
                _exportSemanticReport(payload, fmt);
            }
            return;
        }

        const semanticSuggestedActionBtn = t.closest('[data-semantic-suggested-action]');
        if (semanticSuggestedActionBtn) {
            e.preventDefault();
            const raw = semanticSuggestedActionBtn.getAttribute('data-semantic-suggested-action');
            try {
                const parsed = JSON.parse(raw || '{}');
                const label = String(parsed.label || '').trim();
                if (label) {
                    sendQuickMessage(label);
                }
            } catch (_) {
                // noop
            }
            return;
        }

        const editBtn = t.closest('[data-editar-orc]');
        if (editBtn) {
            e.preventDefault();
            const orcId = editBtn.getAttribute('data-editar-orc');
            if (orcId) {
                window.location.href = `orcamentos.html?editar=${encodeURIComponent(orcId)}`;
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
    clone.classList.remove('chat-messages--dense');
    clone.querySelectorAll('.message--compact').forEach((el) => el.classList.remove('message--compact'));
    localStorage.setItem('ai_chat_history', clone.innerHTML);
    if (sessaoId) localStorage.setItem('ai_sessao_id', sessaoId);
    _persistAssistenteChatMeta();
}

function _toggleQuickActions(open) {
    const sheet = document.getElementById('quickActionsSheet');
    const backdrop = document.getElementById('quickActionsBackdrop');
    if (!sheet || !backdrop) return;
    const shouldOpen = typeof open === 'boolean' ? open : !sheet.classList.contains('is-open');
    sheet.classList.toggle('is-open', shouldOpen);
    backdrop.classList.toggle('is-open', shouldOpen);
}

function _initQuickActionsSheet() {
    const button = document.getElementById('quickActionsBtn');
    const sheet = document.getElementById('quickActionsSheet');
    const backdrop = document.getElementById('quickActionsBackdrop');
    if (!button || !sheet || !backdrop) return;

    button.addEventListener('click', () => _toggleQuickActions(true));
    backdrop.addEventListener('click', () => _toggleQuickActions(false));

    sheet.querySelectorAll('[data-quick-action]').forEach((item) => {
        item.addEventListener('click', () => {
            const message = item.getAttribute('data-quick-action') || '';
            if (message && typeof sendQuickMessage === 'function') {
                sendQuickMessage(message);
            }
            _toggleQuickActions(false);
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            _toggleQuickActions(false);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    _initQuickActionsSheet();
});

window.getSuggestionIcon = getSuggestionIcon;
window.getOrcamentoFollowupSuggestions = getOrcamentoFollowupSuggestions;
window.dismissWelcome = dismissWelcome;
window.resizeMessageInput = resizeMessageInput;
window._showQuickReplyChips = _showQuickReplyChips;
window._hideQuickReplyChips = _hideQuickReplyChips;
window._updateVoiceSendToggle = _updateVoiceSendToggle;
window.applyAdaptiveMessagePlaceholder = applyAdaptiveMessagePlaceholder;
window.setAiStatus = setAiStatus;
window.isAssistenteEmbedMode = isAssistenteEmbedMode;
window.trackAssistenteUserIntent = trackAssistenteUserIntent;
window.captureAssistenteResponseContext = captureAssistenteResponseContext;
window.restoreAssistenteChatMeta = restoreAssistenteChatMeta;
window.renderAssistenteContextBar = renderAssistenteContextBar;
window.updateAssistenteMessageDensity = updateAssistenteMessageDensity;
window.shouldAutoFollowChat = shouldAutoFollowChat;
window.handleAssistenteChatScroll = handleAssistenteChatScroll;
window.setChatAutoFollow = setChatAutoFollow;
window.scrollChatToBottom = scrollChatToBottom;
window.updateScrollBottomButtonVisibility = updateScrollBottomButtonVisibility;
window.novaConversaAssistente = novaConversaAssistente;
window.initAssistenteChatDelegation = initAssistenteChatDelegation;
window.saveChatHistory = saveChatHistory;
window._toggleQuickActions = _toggleQuickActions;
