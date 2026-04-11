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
    if (actionStatusLabel) {
        responseContent = `<div class="action-status-chip">✓ ${escapeHtml(actionStatusLabel)}</div>${responseContent}`;
    }
    const visPref = data?.dados?.visualizacao_recomendada || null;
    if (visPref && visPref.formato_preferido && visPref.formato_preferido !== 'auto') {
        responseContent += `<div class="tool-trace">🧭 Formato aplicado: <strong>${escapeHtml(String(visPref.formato_preferido))}</strong></div>`;
    }

    if (Array.isArray(data.tool_trace) && data.tool_trace.length > 0) {
        const items = data.tool_trace.map(t => {
            const ico = t.status === 'ok' ? '✅' : (t.status === 'pending' ? '⏳' : '⚠️');
            return `<span class="tool-trace-item">${ico} ${escapeHtml(String(t.tool))}</span>`;
        }).join(' ');
        responseContent += `<div class="tool-trace">🛠️ ${items}</div>`;
    }

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

    let sugestoes = [];
    try {
        if (data.acao_sugerida) {
            sugestoes = JSON.parse(data.acao_sugerida);
        }
    } catch (e) { /* ignorar parse error */ }
    if ((!Array.isArray(sugestoes) || sugestoes.length === 0) && Array.isArray(data.sugestoes)) {
        sugestoes = data.sugestoes;
    }

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

    const tipoSemFeedback = ['onboarding', 'orcamento_preview', 'orcamento_criado', 'orcamento_atualizado', 'operador_resultado', 'registro_criado'];
    if (!tipoSemFeedback.includes(data.tipo_resposta) && responseHasText) {
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

    if (msgEl) msgEl.dataset.pergunta = '';

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
