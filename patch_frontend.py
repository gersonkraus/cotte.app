import re

with open('sistema/cotte-frontend/js/assistente-ia-render-types.js', 'r') as f:
    content = f.read()

# Add renderOrcamentoRecusado
new_func = """
function renderOrcamentoRecusado(dados) {
    const orcId = dados.id || '';
    const orcNum = dados.numero || '';
    const numSeq = orcNum.replace(/^ORC-/, '').split('-')[0] || orcNum;
    const clienteNome = dados.cliente_nome || dados.cliente || 'Cliente não informado';
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
        ? `<button type="button" class="orc-card-v2__doc-btn" data-editar-orc="${orcId}" title="Ver orçamento">📄</button>`
        : `<span class="orc-card-v2__doc-btn" style="cursor:default;opacity:0.4;" aria-hidden="true">📄</span>`;

    return `<div class="orc-card-v2">
        <div class="orc-card-v2__banner" style="background:var(--ai-error);color:white;">
            <span class="orc-card-v2__banner-icon" aria-hidden="true">❌</span>
            Orçamento recusado com sucesso
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
        </div>
    </div>`;
}
"""

if "function renderOrcamentoRecusado" not in content:
    content = content.replace("function renderOrcamentoAtualizado", new_func + "\nfunction renderOrcamentoAtualizado")

# Add to formatAIResponse
if "if (tipoResposta === 'orcamento_recusado'" not in content:
    content = content.replace(
        "if (tipoResposta === 'orcamento_atualizado' && dados) {",
        "if (tipoResposta === 'orcamento_recusado' && dados) {\n        return renderOrcamentoRecusado(dados);\n    }\n\n    if (tipoResposta === 'orcamento_atualizado' && dados) {"
    )

with open('sistema/cotte-frontend/js/assistente-ia-render-types.js', 'w') as f:
    f.write(content)
