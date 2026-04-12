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
        clienteHtml = `<div class="orc-card-v2__item-row" style="flex-direction:column;align-items:flex-start;gap:4px">
            <span class="orc-label" style="font-size:0.8rem;color:var(--ai-muted)">Cliente</span>
            <select class="orc-select" id="orc-cliente-select">
                <option value="">-- Selecionar Cliente --</option>${opts}
            </select>
        </div>`;
    } else if (dados.cliente_encontrado) {
        clienteHtml = `<div class="orc-card-v2__item-row">
            <span class="orc-label" style="font-size:0.8rem;color:var(--ai-muted)">Cliente</span>
            <span class="orc-ok" style="font-weight:600">✓ ${escapeHtml(dados.cliente_nome)}</span>
        </div>`;
    } else {
        clienteHtml = `<div class="orc-card-v2__item-row">
            <span class="orc-label" style="font-size:0.8rem;color:var(--ai-muted)">Cliente</span>
            <span class="orc-warn" style="font-weight:600">${escapeHtml(dados.cliente_nome || 'A definir')}</span>
        </div>`;
    }

    const descontoHtml = dados.desconto > 0
        ? `<div class="orc-card-v2__item-row">
            <span class="orc-label" style="font-size:0.8rem;color:var(--ai-muted)">Desconto</span>
            <span style="font-weight:600">${escapeHtml(String(dados.desconto))}${dados.desconto_tipo === 'percentual' ? '%' : ' R$'}</span>
        </div>`
        : '';

    const previewJson = JSON.stringify(dados);

    return `<div class="orc-card-v2 orc-preview-card">
        <div class="orc-card-v2__banner orc-card-v2__banner--preview">
            <span class="orc-card-v2__banner-icon" aria-hidden="true" style="background:#6366f1">📋</span>
            Prévia do Orçamento
        </div>
        <div class="orc-card-v2__body">
            ${clienteHtml}
            <div class="orc-card-v2__item-row">
                <span class="orc-label" style="font-size:0.8rem;color:var(--ai-muted)">Serviço</span>
                <span>${escapeHtml(dados.servico || '—')}</span>
            </div>
            <div class="orc-card-v2__item-row">
                <span class="orc-label" style="font-size:0.8rem;color:var(--ai-muted)">Valor</span>
                <span class="orc-valor" style="color:var(--ai-accent);font-size:1.1rem">${valorFmt}</span>
            </div>
            ${descontoHtml}
            <div class="orc-card-v2__actions" style="margin-top:16px">
                <button type="button" class="orc-card-v2__aprovar-btn" data-orc-confirm="1" style="background:var(--ai-accent);color:white;">✓ Confirmar e Criar</button>
                <button type="button" class="orc-cancel-btn" data-orc-dismiss="1" style="flex:1;min-height:42px;display:flex;align-items:center;justify-content:center;border-radius:10px;">Cancelar</button>
            </div>
            <script type="application/json" class="orc-data">${previewJson.replace(/<\/script>/g, '<\\/script>')}<\/script>
        </div>
    </div>`;
}

function renderOrcamentoCriado(dados) {
    const orcId = dados.id || '';
    const orcNum = dados.numero || '';
    const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
    const clienteNome = dados.cliente_nome || 'Cliente não informado';
    const numEnc = encodeURIComponent(orcNum);
    const aprovarEnc = encodeURIComponent('aprovar ' + numSeq);
    const totalFmt = formatValue(dados.total);
    const hora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

    // Lista de itens: usa dados.itens se disponível, senão fallback com serviço + valor
    let itensHtml = '';
    if (Array.isArray(dados.itens) && dados.itens.length > 0) {
        itensHtml = dados.itens.map(it =>
            `<div class="orc-card-v2__item-row">
                <span>${escapeHtml(it.descricao || it.nome || '—')}</span>
                <span>${formatValue(it.total ?? it.valor ?? 0)}</span>
            </div>`
        ).join('');
    } else {
        const servicoDesc = dados.servico || dados.descricao || 'Serviços gerais';
        itensHtml = `<div class="orc-card-v2__item-row">
            <span>${escapeHtml(servicoDesc)}</span>
            <span>${formatValue(dados.valor || dados.total || 0)}</span>
        </div>`;
    }

    const docBtn = orcId
        ? `<button type="button" class="orc-card-v2__doc-btn" data-editar-orc="${orcId}" title="Editar orçamento">📄</button>`
        : `<span class="orc-card-v2__doc-btn" style="cursor:default;opacity:0.4;" aria-hidden="true">📄</span>`;

    const disWhats = dados.tem_telefone === false ? 'disabled title="Cliente sem telefone"' : '';
    const disEmail = dados.tem_email === false ? 'disabled title="Cliente sem e-mail"' : '';
    const linkTokenAttr = dados.link_publico ? `data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}"` : 'disabled title="Link indisponível"';

    return `<div class="orc-card-v2">
        <div class="orc-card-v2__banner">
            <span class="orc-card-v2__banner-icon" aria-hidden="true">✓</span>
            Orçamento criado com sucesso
        </div>
        <div class="orc-card-v2__body">
            <div class="orc-card-v2__header">
                <div>
                    <div class="orc-card-v2__num-label">Orçamento ${escapeHtml(orcNum)}</div>
                    <div class="orc-card-v2__client">${escapeHtml(clienteNome)}</div>
                </div>
                ${docBtn}
            </div>
            <div class="orc-card-v2__items">${itensHtml}</div>
            <div class="orc-card-v2__total">
                <span class="orc-card-v2__total-label">Total</span>
                <div class="orc-card-v2__total-value">
                    <span class="orc-card-v2__valor-final-label">Valor Final</span>
                    <span class="orc-card-v2__valor-final">${escapeHtml(totalFmt)}</span>
                </div>
            </div>
            <div class="orc-card-v2__actions">
                <div class="orc-card-v2__icon-btns">
                    <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                </div>
                <button type="button" class="orc-card-v2__aprovar-btn btn-aprovar" data-quick-send="${aprovarEnc}">✓ Aprovar</button>
            </div>
        </div>
    </div>`;
}

function renderOrcamentoAprovado(dados) {
    const orcId = dados.id || '';
    const orcNum = dados.numero || '';
    const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
    const clienteNome = dados.cliente_nome || 'Cliente não informado';
    const numEnc = encodeURIComponent(orcNum);
    const totalFmt = formatValue(dados.total);

    let itensHtml = '';
    if (Array.isArray(dados.itens) && dados.itens.length > 0) {
        itensHtml = dados.itens.map(it =>
            `<div class="orc-card-v2__item-row">
                <span>${escapeHtml(it.descricao || it.nome || '—')}</span>
                <span>${formatValue(it.total ?? it.valor ?? 0)}</span>
            </div>`
        ).join('');
    } else {
        const servicoDesc = dados.servico || dados.descricao || 'Serviços gerais';
        itensHtml = `<div class="orc-card-v2__item-row">
            <span>${escapeHtml(servicoDesc)}</span>
            <span>${formatValue(dados.valor || dados.total || 0)}</span>
        </div>`;
    }

    const docBtn = orcId
        ? `<button type="button" class="orc-card-v2__doc-btn" data-editar-orc="${orcId}" title="Editar orçamento">📄</button>`
        : `<span class="orc-card-v2__doc-btn" style="cursor:default;opacity:0.4;" aria-hidden="true">📄</span>`;

    const disWhats = dados.tem_telefone === false ? 'disabled title="Cliente sem telefone"' : '';
    const disEmail = dados.tem_email === false ? 'disabled title="Cliente sem e-mail"' : '';
    const linkTokenAttr = dados.link_publico ? `data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}"` : 'disabled title="Link indisponível"';

    return `<div class="orc-card-v2">
        <div class="orc-card-v2__banner orc-card-v2__banner--update">
            <span class="orc-card-v2__banner-icon" aria-hidden="true">✓</span>
            Orçamento aprovado com sucesso
        </div>
        <div class="orc-card-v2__body">
            <div class="orc-card-v2__header">
                <div>
                    <div class="orc-card-v2__num-label">Orçamento ${escapeHtml(orcNum)}</div>
                    <div class="orc-card-v2__client">${escapeHtml(clienteNome)}</div>
                </div>
                ${docBtn}
            </div>
            <div class="orc-card-v2__items">${itensHtml}</div>
            <div class="orc-card-v2__total">
                <span class="orc-card-v2__total-label">Total</span>
                <div class="orc-card-v2__total-value">
                    <span class="orc-card-v2__valor-final-label">Valor Final</span>
                    <span class="orc-card-v2__valor-final">${escapeHtml(totalFmt)}</span>
                </div>
            </div>
            <div class="orc-card-v2__actions">
                <div class="orc-card-v2__icon-btns">
                    <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                </div>
            </div>
        </div>
    </div>`;
}

function renderOrcamentoAtualizado(dados) {
    const orcId = dados.id || '';
    const orcNum = dados.numero || '';
    const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
    const clienteNome = dados.cliente_nome || 'Cliente';
    const totalFmt = formatValue(dados.total);
    const numEnc = encodeURIComponent(orcNum);
    const aprovarEnc = encodeURIComponent('aprovar ' + numSeq);
    const hora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

    let itensHtml = '';
    if (Array.isArray(dados.itens) && dados.itens.length > 0) {
        itensHtml = dados.itens.map(it =>
            `<div class="orc-card-v2__item-row">
                <span>${escapeHtml(it.descricao || it.nome || '—')}</span>
                <span>${formatValue(it.total ?? it.valor ?? 0)}</span>
            </div>`
        ).join('');
    } else {
        const servicoDesc = dados.servico || dados.descricao || 'Serviços gerais';
        itensHtml = `<div class="orc-card-v2__item-row">
            <span>${escapeHtml(servicoDesc)}</span>
            <span>${formatValue(dados.valor || dados.total || 0)}</span>
        </div>`;
    }

    const linkTokenAttr = dados.link_publico ? `data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}"` : 'disabled title="Link indisponível"';
    const disWhats = dados.tem_telefone === false ? 'disabled title="Cliente sem telefone"' : '';
    const disEmail = dados.tem_email === false ? 'disabled title="Cliente sem e-mail"' : '';

    return `<div class="orc-card-v2">
        <div class="orc-card-v2__banner orc-card-v2__banner--update">
            <span class="orc-card-v2__banner-icon" aria-hidden="true">✓</span>
            Orçamento atualizado com sucesso
        </div>
        <div class="orc-card-v2__body">
            <div class="orc-card-v2__header">
                <div>
                    <div class="orc-card-v2__num-label">Orçamento ${escapeHtml(orcNum)}</div>
                    <div class="orc-card-v2__client">${escapeHtml(clienteNome)}</div>
                </div>
                <span class="orc-card-v2__doc-btn" style="cursor:default;" aria-hidden="true">📄</span>
            </div>
            <div class="orc-card-v2__items">${itensHtml}</div>
            <div class="orc-card-v2__total">
                <span class="orc-card-v2__total-label">Total</span>
                <div class="orc-card-v2__total-value">
                    <span class="orc-card-v2__valor-final-label">Novo Total</span>
                    <span class="orc-card-v2__valor-final">${escapeHtml(totalFmt)}</span>
                </div>
            </div>
            <div class="orc-card-v2__actions">
                <div class="orc-card-v2__icon-btns">
                    <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                </div>
                <button type="button" class="orc-card-v2__aprovar-btn btn-aprovar" data-quick-send="${aprovarEnc}">✓ Aprovar</button>
            </div>
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
            const linkTokenAttr = dados.link_publico ? `data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}"` : 'disabled title="Link indisponível"';
            botoesHtml = `
                <div class="orc-card-v2__actions" style="margin-top:14px;margin-bottom:0">
                    <div class="orc-card-v2__icon-btns">
                        <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                        <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                        <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                    </div>
                    <button type="button" class="orc-card-v2__aprovar-btn btn-aprovar" data-quick-send="${aprovarEnc}">✓ Aprovar</button>
                </div>`;
        } else if (statusKey === 'aprovado') {
            const disWhats = dados.tem_telefone ? '' : 'disabled title="Cliente sem telefone"';
            botoesHtml = `
                <div class="orc-card-v2__actions" style="margin-top:14px;margin-bottom:0">
                    <div class="orc-card-v2__icon-btns">
                        <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Reenviar WhatsApp">💬</button>
                    </div>
                </div>`;
        }

        return `<div class="opr-card">
            <div class="opr-numero">${escapeHtml(orcNum)} &nbsp;${statusBadge}</div>
            <div class="opr-body">
                <div class="opr-field"><span>Cliente</span><span>${escapeHtml(dados.cliente || '—')}</span></div>
                ${itensHtml}
                <div class="opr-field"><span>Total</span><span><strong>${formatValue(dados.total || 0)}</strong></span></div>
                ${formaHtml}${validadeHtml}${obsHtml}${linkPublicoHtml}
                ${botoesHtml}
            </div>
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
    const hora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    return `
        <div class="saldo-rapido-resposta">
            <div class="saldo-banner">
                <span class="saldo-banner__icon" aria-hidden="true">💰</span>
                Saldo em Caixa
            </div>
            <div class="saldo-body">
                <div class="saldo-valor ${saldoAtual >= 0 ? 'positivo' : 'negativo'}">${saldoFormatado}</div>
                <div class="saldo-data">${new Date().toLocaleDateString('pt-BR')} • ${hora}</div>
            </div>
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
    let dados = data.dados || data;
    let tipoResposta = (data.tipo_resposta && data.tipo_resposta !== 'geral') ? data.tipo_resposta : (dados.tipo || 'geral');

    // FIX: Corrige a renderização para respostas de aprovação de orçamento.
    // O backend pode retornar `tipo_resposta: 'orcamento_criado'` mesmo para uma aprovação.
    // Também, os dados do orçamento podem estar no nível raiz em vez de em `data.dados`.
    const isApproval = typeof _ultimaPergunta !== 'undefined' && _ultimaPergunta && _ultimaPergunta.toLowerCase().startsWith('aprovar');
    if (tipoResposta === 'orcamento_criado' && isApproval) {
        tipoResposta = 'orcamento_aprovado';
        // Se os dados do orçamento (ex: `data.id`) estiverem no nível raiz, use o objeto `data` como `dados`.
        if (data.id) {
            dados = data;
        }
    }

    if (tipoResposta === 'orcamento_preview' && dados) {
        return renderOrcamentoPreview(dados);
    }

    if (tipoResposta === 'orcamento_criado' && dados) {
        return renderOrcamentoCriado(dados);
    }

    if (tipoResposta === 'orcamento_aprovado' && dados) {
        return renderOrcamentoAprovado(dados);
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
