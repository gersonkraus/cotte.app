/**
 * assistente-ia-render.js
 *
 * Facade do render do assistente: compõe a resposta final e expõe a API global.
 */

function processAIResponse(data, loadingMessage, isStreamed = false) {
    if (!isStreamed && loadingMessage && loadingMessage.remove) {
        loadingMessage.remove();
    }

    const isSuccess = data.sucesso === true || data.success === true ||
                      (data.dados && Object.keys(data.dados).length > 0);

    if (!isSuccess) {
        let errorMessage = 'Não foi possível processar sua solicitação.';
        if (data.resposta) errorMessage = data.resposta;
        if (data.message) errorMessage = data.message;
        if (data.detail) {
            errorMessage = typeof data.detail === 'string'
                ? data.detail
                : (Array.isArray(data.detail) ? data.detail.map(d => (d && d.msg) || d).join(', ') : errorMessage);
        }
        addMessage(textToHtmlPlain(String(errorMessage)), false, true);
        return;
    }

    let responseContent = formatAIResponse(data, isStreamed);
    const actionStatusMap = {
        saldo_caixa: 'Saldo consultado',
        resumo_financeiro: 'Resumo financeiro gerado',
        orcamento_preview: 'Pré-visualização pronta',
        orcamento_criado: 'Orçamento criado',
        orcamento_atualizado: 'Orçamento atualizado',
        registro_criado: 'Registro criado',
        operador_resultado: 'Ação executada',
    };
    const actionStatusLabel = actionStatusMap[data.tipo_resposta];
    // orcamento_criado e orcamento_atualizado já têm banner próprio no card
    const tiposComBannerProprio = ['orcamento_criado', 'orcamento_atualizado'];
    if (actionStatusLabel && !tiposComBannerProprio.includes(data.tipo_resposta)) {
        responseContent = `<div class="action-status-chip">✓ ${escapeHtml(actionStatusLabel)}</div>${responseContent}`;
    }
    let metaTracesHtml = '';
    const visPref = data?.dados?.visualizacao_recomendada || null;
    if (visPref && visPref.formato_preferido && visPref.formato_preferido !== 'auto') {
        metaTracesHtml += `<div class="tool-trace" style="margin-top:12px;font-size:0.75rem;color:var(--ai-muted)">🧭 Formato aplicado: <strong>${escapeHtml(String(visPref.formato_preferido))}</strong></div>`;
    }

    if (Array.isArray(data.tool_trace) && data.tool_trace.length > 0) {
        const items = data.tool_trace.map(t => {
            const ico = t.status === 'ok' ? '✅' : (t.status === 'pending' ? '⏳' : '⚠️');
            return `<span class="tool-trace-item">${ico} ${escapeHtml(String(t.tool))}</span>`;
        }).join(' ');
        metaTracesHtml += `<div class="tool-trace" style="margin-top:4px;font-size:0.75rem;color:var(--ai-muted)">🛠️ ${items}</div>`;
    }

    if (data.tipo_resposta === 'registro_criado' && data.dados) {
        const dados = data.dados;
        const registroTipo = dados.tipo_registro || 'Registro';
        const registroId = dados.id || '';
        const registroNumero = dados.numero || '';

        responseContent += `
            <div class="confirmation-card">
                <div class="confirmation-card-banner">
                    <span class="confirmation-card-banner__icon" aria-hidden="true">✓</span>
                    ${escapeHtml(registroTipo)} Criado
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
            <div class="orc-card-v2 pending-action-card" role="dialog" aria-labelledby="pa-title-${token.slice(0,8)}" data-token="${tokAttr}">
                <div class="orc-card-v2__banner orc-card-v2__banner--warning" id="pa-title-${token.slice(0,8)}">
                    <span class="orc-card-v2__banner-icon" aria-hidden="true" style="background:#f59e0b">⚠</span>
                    Confirmação necessária
                </div>
                <div class="orc-card-v2__body">
                    <div class="pending-action-tool">${humanizeToolName(pa.tool)}</div>
                    <div class="pending-action-summary">${resumo}</div>
                    <div class="orc-card-v2__actions" style="margin-top:16px;flex-wrap:wrap">
                        <button type="button" class="orc-card-v2__aprovar-btn" data-confirm-ia="${tokAttr}" style="background:var(--ai-green);color:white;min-height:42px">✅ Confirmar</button>
                        ${temMateriaisNovos ? `<button type="button" class="orc-card-v2__aprovar-btn pa-btn-cadastrar" data-confirm-ia="${tokAttr}" data-cadastrar="1" style="min-height:42px;flex:1 1 100%">✅ ✏️ Cadastrar material</button>` : ''}
                        <button type="button" class="orc-cancel-btn pa-cancel-btn" data-cancel-ia="1" style="flex:1;min-height:42px;display:flex;align-items:center;justify-content:center;border-radius:10px;">✕ Cancelar</button>
                    </div>
                </div>
            </div>`;
    }

    let sugestoes = [];
    try {
        if (data.acao_sugerida) {
            sugestoes = JSON.parse(data.acao_sugerida);
        }
    } catch (e) { /* ignorar parse error */ }
    if ((!Array.isArray(sugestoes) || sugestoes.length === 0) && Array.isArray(data.sugestoes)) {
        sugestoes = data.sugestoes;
    }

    const tipoResp = (data.tipo_resposta && data.tipo_resposta !== 'geral') ? data.tipo_resposta : ((data.dados && data.dados.tipo) || 'geral');
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

    // Se o backend não mandou texto e também não é um dos cards ricos estruturados:
    const ehCardRico = ['orcamento_criado', 'orcamento_atualizado', 'orcamento_preview', 'onboarding', 'registro_criado', 'saldo_caixa', 'resumo_financeiro'].includes(tipoResp) || data.pending_action || (responseContent && responseContent.includes('opr-card'));
    const responseHasText = (responseContent && responseContent.replace(/<[^>]*>/g, '').trim().length > 0) || (isStreamed && data.stream_has_chunks);

    if (!responseHasText && !ehCardRico) {
        responseContent = `<div class="resposta-direta">Não consegui montar a resposta completa agora. Tente novamente em alguns segundos.</div>`;
    }

    // Injeta os metas (tool_trace e formato) apenas na bolha de resposta e NÃO acima dos cards de bloco.
    if (metaTracesHtml) {
        responseContent += metaTracesHtml;
    }

    const tipoSemFeedback = ['onboarding', 'orcamento_preview', 'operador_resultado', 'registro_criado'];
    if (!tipoSemFeedback.includes(tipoResp) && !data.pending_action && (responseHasText || ehCardRico)) {
        const fbId = 'fb_' + Date.now();
        responseContent += `
            <div class="feedback-bar" id="${fbId}">
                <span class="feedback-label">Útil?</span>
                <button type="button" class="feedback-btn" data-feedback-id="${fbId}" data-feedback-val="positivo" title="Sim, ajudou">👍</button>
                <button type="button" class="feedback-btn" data-feedback-id="${fbId}" data-feedback-val="negativo" title="Não ajudou">👎</button>
            </div>`;
        window._feedbackData = window._feedbackData || {};
        window._feedbackData[fbId] = {
            pergunta: _ultimaPergunta,
            resposta: data.resposta || '',
            modulo_origem: data.modulo_origem || tipoResp || 'geral',
        };
    }

    const tiposV2Card = ['orcamento_criado', 'orcamento_atualizado', 'orcamento_preview', 'orcamento_aprovado', 'orcamento_recusado'];

    let msgEl;
    if (!isStreamed) {
        msgEl = addMessage(responseContent, false);
    } else {
        msgEl = loadingMessage;
        if (responseContent) {
            const bubble = loadingMessage.querySelector('.message-bubble');
            if (bubble) {
                // Para cards v2, limpa texto streamed anterior (evita duplicação do status)
                if (tiposV2Card.includes(tipoResp) || data.pending_action) {
                    bubble.innerHTML = '';
                }
                bubble.insertAdjacentHTML('beforeend', responseContent);
            }
        }
        if (data.grafico && window.Chart) {
            setTimeout(() => renderChart(msgEl.querySelector('.message-bubble'), data.grafico), 100);
        }
    }

    if (msgEl) msgEl.dataset.pergunta = '';

    // Bubble transparente para cards v2 (sem "card dentro de card")
    if ((tiposV2Card.includes(tipoResp) || data.pending_action) && msgEl) {
        const bubble = msgEl.querySelector('.message-bubble');
        if (bubble) bubble.classList.add('message-bubble--v2card');
    }

    setTimeout(() => {
        const chips = msgEl?.querySelectorAll('.sugestao-chip');
        chips?.forEach((chip, i) => {
            setTimeout(() => chip.classList.add('visible'), i * 100);
        });
    }, 150);

    if (window.innerWidth <= 768 && Array.isArray(sugestoes) && sugestoes.length > 0) {
        _showQuickReplyChips(sugestoes.slice(0, 3));
    }

    if (typeof captureAssistenteResponseContext === 'function') {
        captureAssistenteResponseContext(data);
    }
    if (typeof updateAssistenteMessageDensity === 'function') {
        updateAssistenteMessageDensity();
    }

    if (isStreamed) {
        setTimeout(saveChatHistory, 500);
    }
}

(function assistenteHealthCheck() {
    const CRITICAL = [
        'sendMessage', 'sendQuickMessage', 'processAIResponse', 'addMessage',
        'confirmarAcaoIA', 'cancelarAcaoIA', 'confirmarOrcamento',
        'enviarPorWhatsapp', 'enviarPorEmail', 'enviarFeedback',
        'formatPendingArgs', 'humanizeToolName', 'escapeHtml',
        'initAssistenteChatDelegation', 'setAiStatus', 'resizeMessageInput',
        'formatAIResponse', 'renderChart',
    ];
    const reallyMissing = CRITICAL.filter(fn => {
        try { return typeof eval(fn) !== 'function'; } catch (_) { return true; }
    });
    if (reallyMissing.length > 0) {
        console.warn('[Assistente HealthCheck] Funções críticas ausentes:', reallyMissing.join(', '));
    } else {
        console.debug('[Assistente HealthCheck] OK — todas as funções críticas presentes.');
    }
})();

window.processAIResponse = processAIResponse;
window.formatAIResponse = formatAIResponse;
window.confirmarOrcamento = confirmarOrcamento;
window.enviarPorWhatsapp = enviarPorWhatsapp;
window.enviarPorEmail = enviarPorEmail;
window.enviarFeedback = enviarFeedback;
window.humanizeToolName = humanizeToolName;
window.formatPendingArgs = formatPendingArgs;
window.confirmarAcaoIA = confirmarAcaoIA;
window.cancelarAcaoIA = cancelarAcaoIA;
window.renderChart = renderChart;
