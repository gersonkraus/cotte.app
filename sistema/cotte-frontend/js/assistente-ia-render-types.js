/**
 * assistente-ia-render-types.js
 *
 * Renderização por família de resposta do assistente.
 */

function renderOrcamentoPreview(dados) {
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

function renderOrcamentoCriado(dados) {
    const orcId = dados.id || '';
    const orcNum = dados.numero || '';
    const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
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

function renderOrcamentoAtualizado(dados) {
    const orcNum = dados.numero || '';
    const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
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

function renderOperadorResultado(data, dados) {
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

        const orcId = dados.id || '';
        const orcNum = dados.numero || '';
        const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
        const numEnc = encodeURIComponent(orcNum);
        const aprovarEnc = encodeURIComponent('aprovar ' + numSeq);
        let botoesHtml = '';
        if (['rascunho', 'enviado'].includes(statusKey)) {
            const disWhats = dados.tem_telefone ? '' : 'disabled title="Cliente sem telefone"';
            const disEmail = dados.tem_email ? '' : 'disabled title="Cliente sem e-mail"';
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

function renderSaldoRapido(dados) {
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

function renderOnboarding(dados) {
    const progresso = dados.progresso_pct || 0;
    const checklist = dados.checklist || [];
    const mensagem = dados.mensagem || '';
    const acao = dados.acao_principal;
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

function renderTabelaRica(data, dados, isStreamed) {
    let content = '';
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

    if (!listaObjetos || listaObjetos.length === 0) return null;

    const headersSet = new Set();
    listaObjetos.slice(0, 10).forEach(obj => {
        if (obj) Object.keys(obj).forEach(k => headersSet.add(k));
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
        const textoPrincipal = data.resposta || dados.resposta || dados.resumo || '';
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

function renderAnaliseTexto(dados, isStreamed) {
    let content = '';

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

function formatAIResponse(data, isStreamed = false) {
    const dados = data.dados || data;
    const tipoResposta = data.tipo_resposta || dados.tipo;

    if (tipoResposta === 'orcamento_preview' && dados) {
        return renderOrcamentoPreview(dados);
    }

    if (tipoResposta === 'orcamento_criado' && dados) {
        return renderOrcamentoCriado(dados);
    }

    if (tipoResposta === 'orcamento_atualizado' && dados) {
        return renderOrcamentoAtualizado(dados);
    }

    if (tipoResposta === 'operador_resultado') {
        return renderOperadorResultado(data, dados);
    }

    if (tipoResposta === 'saldo_caixa' || dados.tipo === 'saldo_caixa') {
        return renderSaldoRapido(dados);
    }

    if (tipoResposta === 'onboarding' && dados) {
        return renderOnboarding(dados);
    }

    const tabela = renderTabelaRica(data, dados, isStreamed);
    if (tabela) return tabela;

    if (data.resposta || dados.resposta) {
        const rawTxt = data.resposta || dados.resposta;
        if (isStreamed && data.stream_has_chunks) {
            return '';
        }
        return `<div class="resposta-direta">${textToHtmlRich(rawTxt)}</div>`;
    }

    return renderAnaliseTexto(dados, isStreamed);
}
