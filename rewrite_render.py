import re
import sys

filepath = "sistema/cotte-frontend/js/assistente-ia-render-types.js"

with open(filepath, "r") as f:
    content = f.read()

# Replace all old render functions with a single one
# We find the start of renderOrcamentoPreview and the end of renderOrcamentoAtualizado

start_idx = content.find("function renderOrcamentoPreview(dados)")
end_idx = content.find("function renderOperadorResultado(data, dados)")

if start_idx == -1 or end_idx == -1:
    print("Could not find start or end index.")
    sys.exit(1)

unified_fn = """function renderOrcamentoCardUnificado(dados) {
    const orcId = dados.id || '';
    const orcNum = dados.numero || '';
    const clienteNome = dados.cliente_nome || dados.cliente || 'Cliente não informado';
    const numEnc = encodeURIComponent(orcNum);
    const aprovarEnc = encodeURIComponent('aprovar ' + orcNum);
    const totalFmt = formatValue(dados.total);
    const statusKey = (dados.status || 'rascunho').toLowerCase();

    // Itens
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

    // Configurações por status
    let bannerIcon = '📋';
    let bannerText = 'Detalhes do Orçamento';
    let bannerColor = ''; // default

    if (statusKey === 'aprovado') {
        bannerIcon = '✅';
        bannerText = 'Orçamento Aprovado';
        bannerColor = 'background:var(--ai-accent);color:white;';
    } else if (statusKey === 'recusado') {
        bannerIcon = '❌';
        bannerText = 'Orçamento Recusado';
        bannerColor = 'background:var(--ai-error);color:white;';
    } else if (statusKey === 'enviado') {
        bannerIcon = '📤';
        bannerText = 'Orçamento Enviado';
        bannerColor = 'background:var(--ai-warning);color:#1e293b;';
    } else if (statusKey === 'rascunho') {
        bannerIcon = '📝';
        bannerText = 'Orçamento Rascunho';
    }

    const docBtn = orcId
        ? `<button type="button" class="orc-card-v2__doc-btn" data-editar-orc="${orcId}" title="Ver orçamento">📄</button>`
        : `<span class="orc-card-v2__doc-btn" style="cursor:default;opacity:0.4;" aria-hidden="true">📄</span>`;

    const disWhats = dados.tem_telefone === false ? 'disabled title="Cliente sem telefone"' : '';
    const disEmail = dados.tem_email === false ? 'disabled title="Cliente sem e-mail"' : '';
    const linkTokenAttr = dados.link_publico ? `data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}"` : 'disabled title="Link indisponível"';

    // Botões
    let botoesHtml = '';
    if (['rascunho', 'enviado'].includes(statusKey)) {
        botoesHtml = `
            <div style="display: flex; gap: 8px; width: 100%;">
                <div class="orc-card-v2__icon-btns" style="flex: 1; justify-content: flex-start;">
                    <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                </div>
                <button type="button" class="orc-card-v2__aprovar-btn btn-aprovar" data-quick-send="${aprovarEnc}" data-silent-send="true" style="flex: 1; padding:0 8px;">✓ Aprovar</button>
            </div>
        `;
    } else if (statusKey === 'aprovado') {
        botoesHtml = `
            <div class="orc-card-v2__icon-btns" style="justify-content: center; gap: 12px; width: 100%;">
                <button type="button" class="orc-card-v2__icon-btn btn-calendar" onclick="abrirModalAgendamentoRapido(${orcId}, '${escapeHtml(orcNum)}', '${(clienteNome || '').replace(/'/g, "\\\\'")}')" title="Agendar">📅</button>
                <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
            </div>
        `;
    } else {
         botoesHtml = `
            <div class="orc-card-v2__icon-btns" style="justify-content: center; gap: 12px; width: 100%;">
                 <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Reenviar WhatsApp">💬</button>
                 <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
            </div>
         `;
    }

    return `<div class="orc-card-v2">
        <div class="orc-card-v2__banner" style="${bannerColor}">
            <span class="orc-card-v2__banner-icon" aria-hidden="true">${bannerIcon}</span>
            ${bannerText}
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
                    <span class="orc-card-v2__valor-final">${escapeHtml(totalFmt)}</span>
                </div>
            </div>
            <div class="orc-card-v2__actions" style="display:flex;flex-direction:column;gap:8px">
                <button type="button" class="btn btn-primary" onclick="abrirDetalhesOrcamento(${orcId})" style="width: 100%; margin-bottom: 4px; font-size: 14px; font-weight: 600; justify-content: center; padding: 10px;">
                    🔍 Ver Preview Completo
                </button>
                ${botoesHtml}
            </div>
        </div>
    </div>`;
}

"""

content = content[:start_idx] + unified_fn + content[end_idx:]

# Now replace inside formatAIResponse
formatAI_start = content.find("function formatAIResponse(data, isStreamed = false) {")
if formatAI_start != -1:
    format_content = content[formatAI_start:]

    replacements = [
        (
            "if (tipoResposta === 'orcamento_preview' && dados) {\n        return renderOrcamentoPreview(dados);\n    }",
            "",
        ),
        (
            "if (tipoResposta === 'orcamento_criado' && dados) {\n        return renderOrcamentoCriado(dados);\n    }",
            "",
        ),
        (
            "if (tipoResposta === 'orcamento_aprovado' && dados) {\n        return renderOrcamentoAprovado(dados);\n    }",
            "",
        ),
        (
            "if (tipoResposta === 'orcamento_recusado' && dados) {\n        return renderOrcamentoRecusado(dados);\n    }",
            "",
        ),
        (
            "if (tipoResposta === 'orcamento_atualizado' && dados) {\n        return renderOrcamentoAtualizado(dados);\n    }",
            "",
        ),
        (
            "if (tipoResposta === 'orcamento_card_unificado' && dados) {\n        return renderOrcamentoCardUnificado(dados);\n    }",
            "",
        ),
    ]

    for old, new in replacements:
        format_content = format_content.replace(old, new)

    format_content = format_content.replace(
        "// FIX: Corrige a renderização para respostas de aprovação de orçamento.",
        """// FIX: Unificação da renderização do card
    const cardTypes = ['orcamento_preview', 'orcamento_criado', 'orcamento_aprovado', 'orcamento_recusado', 'orcamento_atualizado', 'orcamento_card_unificado'];
    if (cardTypes.includes(tipoResposta) && dados) {
        return renderOrcamentoCardUnificado(dados);
    }""",
    )

    content = content[:formatAI_start] + format_content

with open(filepath, "w") as f:
    f.write(content)

print("Rewrite successful")
