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
        const hasRetry = typeof isRetryableAssistenteError === 'function'
            ? isRetryableAssistenteError({ message: String(errorMessage) })
            : true;
        const errorHtml = typeof buildAssistenteErrorCard === 'function'
            ? buildAssistenteErrorCard(String(errorMessage), hasRetry)
            : textToHtmlPlain(String(errorMessage));
        addMessage(errorHtml, false, true);
        return;
    }

    const isSilentLoadMore = window._isSilentLoadMoreOrcamentos || window._isSilentLoadMoreClientes;
    console.log('[load more] isSilentLoadMore:', isSilentLoadMore, '_isSilentLoadMoreOrcamentos:', window._isSilentLoadMoreOrcamentos);
    if (isSilentLoadMore) {
        const dados = data.dados || data;
        const isOrcamentos = window._isSilentLoadMoreOrcamentos && Array.isArray(dados.orcamentos) && dados.orcamentos.length > 0;
        const isClientes = window._isSilentLoadMoreClientes && Array.isArray(dados.clientes) && dados.clientes.length > 0;
        console.log('[load more] isOrcamentos:', isOrcamentos, 'isClientes:', isClientes, 'dados:', dados);
        
        window._isSilentLoadMoreOrcamentos = false;
        window._isSilentLoadMoreClientes = false;
        
        if (isOrcamentos) {
            if (!isStreamed && loadingMessage && loadingMessage.remove) {
                loadingMessage.remove();
            } else if (isStreamed && loadingMessage && loadingMessage.remove) {
                loadingMessage.remove();
            }
            _appendOrcamentosToExistingTable(dados);
            return;
        }
        if (isClientes) {
            if (!isStreamed && loadingMessage && loadingMessage.remove) {
                loadingMessage.remove();
            } else if (isStreamed && loadingMessage && loadingMessage.remove) {
                loadingMessage.remove();
            }
            _appendClientesToExistingTable(dados);
            return;
        }
    }

    const renderResult = typeof window.resolveAssistenteRenderResult === 'function'
        ? window.resolveAssistenteRenderResult(data, isStreamed)
        : {
            html: formatAIResponse(data, isStreamed),
            rendererId: 'desconhecido',
            tipoResposta: (data.tipo_resposta && data.tipo_resposta !== 'geral') ? data.tipo_resposta : ((data.dados && data.dados.tipo) || 'geral'),
        };
    let responseContent = renderResult.html;
    const isSemanticResponse = !!(
        (data && data.semantic_contract)
        || (data && data.dados && data.dados.semantic_contract)
    );
    const tipoResp = renderResult.tipoResposta || ((data.tipo_resposta && data.tipo_resposta !== 'geral') ? data.tipo_resposta : ((data.dados && data.dados.tipo) || 'geral'));
    const uiPolicy = typeof window.getAssistenteResponseUiPolicy === 'function'
        ? window.getAssistenteResponseUiPolicy(tipoResp)
        : { actionStatusLabel: '', hasOwnBanner: false, skipFeedback: false, isRichResponse: false };
        
    // Definir flags para controlar feedback e renderização de cards ricos
    const responseHasText = (data.resposta && data.resposta.trim().length > 0) || (data.message && data.message.trim().length > 0);
    const ehCardRico = uiPolicy.isRichResponse && data.dados;

    if (!isSemanticResponse && uiPolicy.actionStatusLabel && !uiPolicy.hasOwnBanner) {
        responseContent = `<div class="action-status-chip">✓ ${escapeHtml(uiPolicy.actionStatusLabel)}</div>${responseContent}`;
    }
    const metaTracesHtml = typeof window.formatAssistenteMetaTraces === 'function'
        ? window.formatAssistenteMetaTraces(data)
        : '';

    if (uiPolicy.extraCardRenderer && typeof window[uiPolicy.extraCardRenderer] === 'function' && data.dados) {
        responseContent += window[uiPolicy.extraCardRenderer](data.dados);
    }

    if (data.pending_action && data.pending_action.confirmation_token && typeof window.renderPendingActionCard === 'function') {
        responseContent += window.renderPendingActionCard(data.pending_action);
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

    if (!isSemanticResponse && (tipoResp === 'orcamento_criado' || tipoResp === 'orcamento_atualizado')) {
        sugestoes = getOrcamentoFollowupSuggestions(data, sugestoes, tipoResp);
    }

    if (data.debug_ui && typeof data.debug_ui === 'object' && typeof window.buildAssistenteDebugIntentMeta === 'function') {
        data.debug_ui.intent_resolution = window.buildAssistenteDebugIntentMeta({
            userMessage: data.debug_ui.mensagem_debug_intent || data.debug_ui.mensagem_preview || '',
            responseType: data.debug_ui.tipo_resposta_normalizado || tipoResp,
            intentDetected: data?.dados?.intent_detectada || data?.debug_ui?.metadata?.intent_detectada || '',
            followups: sugestoes,
            rendererId: renderResult.rendererId,
        });
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

    // Injeta os metas (tool_trace e formato) apenas na bolha de resposta e NÃO acima dos cards de bloco.
    if (metaTracesHtml) {
        responseContent += metaTracesHtml;
    }

    // Painel provisório de debug (ativado por ?debug_ui=1 ou enableAssistenteDebugUi)
    if (data.debug_ui && typeof data.debug_ui === 'object') {
        const redactDeep = (o) => {
            if (!o || typeof o !== 'object') return;
            if (Array.isArray(o)) {
                o.forEach(redactDeep);
                return;
            }
            for (const k of Object.keys(o)) {
                const lk = String(k).toLowerCase();
                if (
                    lk.includes('token')
                    || lk.includes('authorization')
                    || lk.includes('cookie')
                    || lk === 'password'
                    || lk === 'senha'
                ) {
                    o[k] = '[omitido]';
                } else {
                    redactDeep(o[k]);
                }
            }
        };
        let safe;
        try {
            safe = JSON.parse(JSON.stringify(data.debug_ui));
            redactDeep(safe);
        } catch (_) {
            safe = { erro: 'não foi possível clonar debug_ui' };
        }
        const intentResolution = safe.intent_resolution && typeof safe.intent_resolution === 'object'
            ? safe.intent_resolution
            : null;
        let debugSummaryHtml = '';
        if (intentResolution) {
            const requestLabel = intentResolution?.request_intent?.label || 'não identificada';
            const responseLabel = intentResolution?.response_intent?.label || 'não identificada';
            const normalizedTypeLabel = intentResolution?.response_type_normalized || 'geral';
            const rendererLabel = intentResolution?.renderer?.id || 'desconhecido';
            const followups = Array.isArray(intentResolution?.followups) ? intentResolution.followups : [];
            const followupsHtml = followups.length > 0
                ? followups.map((item) => `<span class="tool-trace-item">${escapeHtml(String(item))}</span>`).join(' ')
                : '<span class="tool-trace-item">nenhum follow-up gerado</span>';
            debugSummaryHtml = `
                <div style="margin:10px 0 12px;display:grid;gap:8px;">
                    <div class="tool-trace" style="margin-top:0;font-size:0.75rem;color:var(--ai-muted)">🧭 Intent da pergunta: <strong>${escapeHtml(requestLabel)}</strong></div>
                    <div class="tool-trace" style="margin-top:0;font-size:0.75rem;color:var(--ai-muted)">🧩 Intent da resposta: <strong>${escapeHtml(responseLabel)}</strong></div>
                    <div class="tool-trace" style="margin-top:0;font-size:0.75rem;color:var(--ai-muted)">🏷️ Tipo normalizado: <strong>${escapeHtml(normalizedTypeLabel)}</strong></div>
                    <div class="tool-trace" style="margin-top:0;font-size:0.75rem;color:var(--ai-muted)">🖼️ Renderer: <strong>${escapeHtml(rendererLabel)}</strong></div>
                    <div class="tool-trace" style="margin-top:0;font-size:0.75rem;color:var(--ai-muted)">✨ Follow-ups: ${followupsHtml}</div>
                </div>`;
        }
        let preJson;
        try {
            preJson = JSON.stringify(safe, null, 2);
        } catch (_) {
            preJson = '{"erro":"serialização falhou"}';
        }
        const pre = escapeHtml(preJson);
        responseContent += `<details class="ai-debug-ui"><summary class="ai-debug-ui__summary">Debug UI (stream / metadata)</summary>${debugSummaryHtml}<pre class="ai-debug-ui__pre" tabindex="0">${pre}</pre><p class="ai-debug-ui__hint">Desative com <code>disableAssistenteDebugUi()</code> no console ou remova <code>?debug_ui=1</code> da URL.</p></details>`;
    }

    if (!uiPolicy.skipFeedback && !data.pending_action && (responseHasText || ehCardRico)) {
        const fbId = 'fb_' + Date.now();
        responseContent += `
            <div class="feedback-bar" id="${fbId}">
                <span class="feedback-label">Útil?</span>
                <button type="button" class="feedback-btn" data-feedback-id="${fbId}" data-feedback-val="positivo" title="Sim, ajudou">👍</button>
                <button type="button" class="feedback-btn" data-feedback-id="${fbId}" data-feedback-val="negativo" title="Não ajudou">👎</button>
            </div>`;
        window._feedbackData = window._feedbackData || {};
        window._feedbackData[fbId] = {
            pergunta: (typeof _ultimaPergunta !== 'undefined') ? _ultimaPergunta : '',
            resposta: data.resposta || '',
            modulo_origem: data.modulo_origem || tipoResp || 'geral',
        };
    }

    let msgEl;
    if (!isStreamed) {
        msgEl = addMessage(responseContent, false);
    } else {
        msgEl = loadingMessage;
        if (responseContent) {
            const bubble = loadingMessage.querySelector('.message-bubble');
            if (bubble) {
                // Para cards v2, limpa texto streamed anterior (evita duplicação do status)
                if (uiPolicy.isV2Card || data.pending_action) {
                    bubble.innerHTML = '';
                }
                bubble.insertAdjacentHTML('beforeend', responseContent);
            }
        }
    }
    const chartPayload = data.grafico
        || (data.semantic_contract && data.semantic_contract.chart)
        || (data.dados && data.dados.semantic_contract && data.dados.semantic_contract.chart)
        || null;
    if (chartPayload && window.Chart && msgEl) {
        setTimeout(() => {
            // Tenta achar o slot específico para o gráfico, se não encontrar joga no final do chat (fallback)
            const chartSlot = msgEl.querySelector('.semantic-chart-slot');
            renderChart(chartSlot || msgEl.querySelector('.message-bubble'), chartPayload);
        }, 100);
    }

    if (msgEl) msgEl.dataset.pergunta = '';

    if (window.AssistenteInsights && typeof window.AssistenteInsights.renderFromResponse === 'function') {
        window.AssistenteInsights.renderFromResponse(data, { messageEl: msgEl, placement: 'response' });
    }

    // Bubble transparente para cards v2 (sem "card dentro de card")
    if ((uiPolicy.isV2Card || data.pending_action) && msgEl) {
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

function _appendOrcamentosToExistingTable(dados) {
    console.log('[load more] dados recebidos:', dados);
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.log('[load more] chatMessages não encontrado');
        return;
    }
    
    const lastOrcamentosCard = chatMessages.querySelector('.orc-list-card[data-testid="assistente-orc-list-card"]');
    if (!lastOrcamentosCard) {
        console.log('[load more] tabela de orçamentos não encontrada');
        return;
    }
    
    const tbody = lastOrcamentosCard.querySelector('.ai-table tbody');
    if (!tbody) {
        console.log('[load more] tbody não encontrado');
        return;
    }
    
    const itens = Array.isArray(dados.orcamentos) ? dados.orcamentos : [];
    console.log('[load more] itens para adicionar:', itens.length);
    const filtros = dados.filtros || {};
    const badgeMap = {
        'rascunho': 'badge-rascunho',
        'enviado': 'badge-enviado',
        'aprovado': 'badge-aprovado',
        'recusado': 'badge-recusado',
        'expirado': 'badge-expirado'
    };
    
    itens.forEach((item) => {
        const numero = escapeHtml(item.numero || `#${item.id || '—'}`);
        const cliente = escapeHtml(item.cliente_nome || 'Cliente não informado');
        const statusStr = item.status || '—';
        const statusKey = statusStr.toLowerCase();
        const badgeClass = badgeMap[statusKey] || 'badge-rascunho';
        
        let dataExibicao = '—';
        let colunaDataLabel = 'Emissão';
        
        if (filtros.aprovado_em_de || filtros.aprovado_em_ate) {
            colunaDataLabel = 'Aprovado em';
            if (item.aprovado_em) {
                const dateObj = new Date(item.aprovado_em);
                const dia = String(dateObj.getDate()).padStart(2, '0');
                const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
                const ano = dateObj.getFullYear();
                const hora = String(dateObj.getHours()).padStart(2, '0');
                const min = String(dateObj.getMinutes()).padStart(2, '0');
                dataExibicao = `${dia}/${mes}/${ano} ${hora}:${min}`;
            }
        } else if (item.criado_em) {
            const dateObj = new Date(item.criado_em);
            const dia = String(dateObj.getDate()).padStart(2, '0');
            const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
            const ano = dateObj.getFullYear();
            dataExibicao = `${dia}/${mes}/${ano}`;
        }
        
        const valor = typeof formatValue === 'function' ? formatValue(item.total || 0) : (item.total || 0);
        
        const actionBtn = item.id
            ? `<button type="button" class="btn btn-ghost" style="padding: 2px 8px; font-size: 11px;" onclick="if(typeof abrirDetalhesOrcamento === 'function') abrirDetalhesOrcamento(${item.id})" title="Ver detalhes do orçamento">🔍 Ver</button>`
            : '';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td data-label="Num"><strong>${numero}</strong></td>
            <td data-label="Cliente">${cliente}</td>
            <td data-label="${colunaDataLabel}">${dataExibicao}</td>
            <td data-label="Status"><span class="opr-status-badge ${badgeClass}" style="font-size:0.7em; padding:2px 6px;">${escapeHtml(statusStr)}</span></td>
            <td data-label="Total"><strong>${escapeHtml(valor)}</strong></td>
            <td data-label="Ações">${actionBtn}</td>
        `;
        tbody.appendChild(tr);
    });
    
    const existingLoadMore = lastOrcamentosCard.querySelector('[data-orcamentos-load-more]');
    if (existingLoadMore) {
        const hasMore = !!dados.has_more;
        const nextCursor = dados.next_cursor || '';
        if (!hasMore || !nextCursor) {
            existingLoadMore.parentElement.remove();
        } else {
            const status = filtros.status || '';
            const clienteId = filtros.cliente_id || '';
            const dias = Number(filtros.dias || 30);
            const limitLista = Number(dados.limit || 10);
            const aprovadoDe = filtros.aprovado_em_de || '';
            const aprovadoAte = filtros.aprovado_em_ate || '';
            
            existingLoadMore.setAttribute('data-cursor', nextCursor);
            existingLoadMore.setAttribute('data-status', String(status));
            existingLoadMore.setAttribute('data-cliente-id', String(clienteId));
            existingLoadMore.setAttribute('data-dias', String(dias));
            existingLoadMore.setAttribute('data-limit', String(limitLista));
            existingLoadMore.setAttribute('data-aprovado-em-de', String(aprovadoDe));
            existingLoadMore.setAttribute('data-aprovado-em-ate', String(aprovadoAte));
            existingLoadMore.textContent = 'Carregar mais resultados';
        }
    }
    
    if (typeof saveChatHistory === 'function') {
        setTimeout(saveChatHistory, 500);
    }
}

function _appendClientesToExistingTable(dados) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const lastClientesCard = chatMessages.querySelector('.orc-list-card[data-testid="assistente-clientes-list-card"]');
    if (!lastClientesCard) return;
    
    const tbody = lastClientesCard.querySelector('.ai-table tbody');
    const cardsMobile = lastClientesCard.querySelector('.cliente-lista-mobile');
    
    const itens = Array.isArray(dados.clientes) ? dados.clientes : [];
    
    itens.forEach((item) => {
        const id = escapeHtml(item.id || '—');
        const nome = escapeHtml(item.nome || '—');
        const telefone = escapeHtml(item.telefone || '—');
        const email = escapeHtml(item.email || '—');
        const criadoEm = item.criado_em ? new Date(item.criado_em).toLocaleDateString('pt-BR') : '—';
        
        if (tbody) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td data-label="ID">${id}</td>
                <td data-label="Nome">${nome}</td>
                <td data-label="Telefone">${telefone}</td>
                <td data-label="Email">${email}</td>
                <td data-label="Cadastro">${criadoEm}</td>
            `;
            tbody.appendChild(tr);
        }
        
        if (cardsMobile) {
            const card = document.createElement('div');
            card.className = 'cliente-card-mobile';
            card.innerHTML = `
                <div class="cliente-card-mobile__header">
                    <span class="cliente-card-mobile__nome">${nome}</span>
                </div>
                <div class="cliente-card-mobile__info">
                    <span>📞 ${telefone}</span>
                    <span>✉️ ${email}</span>
                </div>
            `;
            cardsMobile.appendChild(card);
        }
    });
    
    const existingLoadMore = lastClientesCard.querySelector('[data-clientes-load-more]');
    if (existingLoadMore) {
        const hasMore = !!dados.has_more;
        const nextCursor = dados.next_cursor || '';
        if (!hasMore || !nextCursor) {
            existingLoadMore.parentElement.remove();
        } else {
            existingLoadMore.setAttribute('data-cursor', nextCursor);
            existingLoadMore.textContent = 'Carregar mais clientes';
        }
    }
    
    if (typeof saveChatHistory === 'function') {
        setTimeout(saveChatHistory, 500);
    }
}

window._appendOrcamentosToExistingTable = _appendOrcamentosToExistingTable;
window._appendClientesToExistingTable = _appendClientesToExistingTable;
