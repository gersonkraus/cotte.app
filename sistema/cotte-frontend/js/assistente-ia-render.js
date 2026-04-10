/**
 * assistente-ia-render.js
 *
 * Renderização rica das respostas, cards de ação e confirmações.
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

        if (isStreamed) {
             setTimeout(saveChatHistory, 500);
        }

    } else {
        let errorMessage = 'Não foi possível processar sua solicitação.';
        if (data.resposta) errorMessage = data.resposta;
        if (data.message)  errorMessage = data.message;
        if (data.detail) {
            errorMessage = typeof data.detail === 'string'
                ? data.detail
                : (Array.isArray(data.detail) ? data.detail.map(d => (d && d.msg) || d).join(', ') : errorMessage);
        }
        addMessage(textToHtmlPlain(String(errorMessage)), false, true);
    }
}

function formatAIResponse(data, isStreamed = false) {
    let content = '';
    const dados = data.dados || data;
    const tipoResposta = data.tipo_resposta || dados.tipo;

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

    if (tipoResposta === 'operador_resultado') {
        const acaoIcones = { 'VER': '🔍', 'APROVADO': '✅', 'RECUSADO': '❌', 'ENVIADO': '📤', 'DESCONTO': '💰', 'ADICIONADO': '➕', 'REMOVIDO': '➖' };
        const acao = dados && dados.acao ? dados.acao : '';
        const icone = acaoIcones[acao] || '⚡';
        const linkHtml = dados && dados.id ? `<a href="orcamentos.html" class="opr-link">Ver orçamento →</a>` : '';

        if (acao === 'VER' && dados) {
            const itensHtml = (dados.itens || []).map((it, i) =>
                `<div class="opr-field"><span>${i + 1}. ${escapeHtml(it.descricao)}</span><span>R$ ${Number(it.total).toFixed(2)}</span></div>`
            ).join('');

            const statusMap = { rascunho:'badge-rascunho', enviado:'badge-enviado', aprovado:'badge-aprovado', em_execucao:'badge-em-execucao', aguardando_pagamento:'badge-aguardando-pagamento', recusado:'badge-recusado', expirado:'badge-expirado' };
            const statusKey = (dados.status || '').toLowerCase();
            const badgeClass = statusMap[statusKey] || 'badge-rascunho';
            const statusBadge = `<span class="opr-status-badge ${badgeClass}">${escapeHtml(dados.status || '')}</span>`;

            const pagFmt = { a_vista:'À vista', pix:'PIX', '2x':'2×', '3x':'3×', '4x':'4×' };
            const formaHtml = dados.forma_pagamento
                ? `<div class="opr-field"><span>Pagamento</span><span>${escapeHtml(pagFmt[dados.forma_pagamento] || String(dados.forma_pagamento))}</span></div>` : '';
            const validadeHtml = dados.validade_dias
                ? `<div class="opr-field"><span>Validade</span><span>${escapeHtml(String(dados.validade_dias))} dias</span></div>` : '';
            const obsHtml = dados.observacoes
                ? `<div class="opr-field" style="flex-direction:column;align-items:flex-start;gap:3px;"><span style="font-size:0.75em;color:var(--ai-muted)">Observações</span><span class="operador-md" style="font-size:0.82em;">${textToHtmlRich(dados.observacoes)}</span></div>` : '';
            const linkPublicoHtml = dados.link_publico
                ? `<div class="opr-field"><span>Link público</span><button type="button" class="orc-action-btn" style="flex:unset;padding:3px 8px;font-size:0.74em;" data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}">📋 Copiar link</button></div>` : '';

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

    if (data.resposta || dados.resposta) {
        const rawTxt = data.resposta || dados.resposta;
        if (isStreamed && data.stream_has_chunks) {
            return '';
        }
        return `<div class="resposta-direta">${textToHtmlRich(rawTxt)}</div>`;
    }

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

function formatValue(value) {
    if (typeof value === 'number') {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }
    return value;
}

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

    btn.disabled = true;
    btn.textContent = 'Criando...';

    const loadingMsg = addMessage('', false, false, true);
    try {
        const data = await httpClient.post('/ai/orcamento/confirmar', body, { bypassAutoLogout: true });
        if (loadingMsg) loadingMsg.remove();
        if (card) card.remove();
        processAIResponse(data, null);
    } catch (e) {
        if (loadingMsg) loadingMsg.remove();
        btn.disabled = false;
        btn.textContent = 'Confirmar e Criar';
        addMessage('Erro ao criar o orçamento. Tente novamente.', false, true);
    }
}

function mockAIResponse(endpoint, body) {
    return new Promise(resolve => {
        setTimeout(() => {
            let response;
            const message = body?.mensagem || '';

            if (endpoint.includes('/financeiro/') || message.toLowerCase().includes('finança')) {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: '💰 Análise Financeira (Demonstração)',
                        kpi_principal: {
                            nome: 'Saldo Disponível',
                            valor: 12500.75,
                            comparacao: '↑ 12% este mês'
                        },
                        insights: [
                            'Maior receita no período da tarde',
                            'Cliente João Silva é o mais lucrativo',
                            'Aumento de 15% em manutenção'
                        ]
                    }
                };
            } else if (endpoint.includes('/conversao/') || message.toLowerCase().includes('ticket')) {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: '📊 Análise de Conversão (Demonstração)',
                        taxa_conversao: 0.72,
                        orcamentos_enviados: 38,
                        orcamentos_aprovados: 27,
                        ticket_medio: 920.00,
                        servico_mais_vendido: 'Instalação Elétrica',
                        insights: [
                            'Taxa de conversão acima da média',
                            'WhatsApp é o canal mais eficiente',
                            'Orçamentos com fotos têm 40% mais aprovação'
                        ]
                    }
                };
            } else if (endpoint.includes('/negocio/') || message.toLowerCase().includes('sugest')) {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: '💡 Sugestões de Negócio (Demonstração)',
                        sugestao: 'Aumente seu ticket médio oferecendo pacotes de serviços',
                        impacto_estimado: 'Aumento de R$ 2.500/mês em receita',
                        acao_imediata: 'Crie 3 pacotes de serviços',
                        insights: [
                            'Pacote "Manutenção Completa" tem maior aceitação',
                            'Clientes empresariais preferem contratos mensais'
                        ]
                    }
                };
            } else {
                response = {
                    sucesso: true,
                    dados: {
                        resumo: '🤖 Assistente COTTE (Demonstração)',
                        insights: [
                            'Modo demonstração ativo',
                            'Dados apresentados são simulados'
                        ]
                    }
                };
            }
            resolve(response);
        }, 800);
    });
}

async function enviarFeedback(fbId, avaliacao) {
    const barEl = document.getElementById(fbId);
    if (!barEl) return;

    const fbData = (window._feedbackData || {})[fbId] || {};

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
        // Silencioso.
    }
}

window._pendingConfirmationToken = null;
window._pendingOverrideArgs = null;

function humanizeToolName(tool) {
    if (!tool) return 'Ação';
    return tool
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase())
        .replace(/Orcamento/g, 'Orçamento')
        .replace(/Movimentacao/g, 'Movimentação')
        .replace(/Recebivel/g, 'Recebível');
}

function _brl(v) {
    const n = Number(v);
    if (isNaN(n)) return String(v);
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

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
    const input = document.getElementById('messageInput');
    if (input) input.focus();
}

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

(function assistenteHealthCheck() {
    const CRITICAL = [
        'sendMessage', 'sendQuickMessage', 'processAIResponse', 'addMessage',
        'confirmarAcaoIA', 'cancelarAcaoIA', 'confirmarOrcamento',
        'enviarPorWhatsapp', 'enviarPorEmail', 'enviarFeedback',
        'formatPendingArgs', 'humanizeToolName', 'escapeHtml',
        'initAssistenteChatDelegation', 'setAiStatus', 'resizeMessageInput',
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
