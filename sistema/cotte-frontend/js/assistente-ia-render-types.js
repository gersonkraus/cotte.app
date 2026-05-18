/**
 * assistente-ia-render-types.js
 *
 * Renderização por família de resposta do assistente.
 */
function renderOrcamentoCardUnificado(dados) {
    const orcId = dados.id || '';
    const orcNum = dados.numero || '';
    const clienteNome = dados.cliente_nome || (dados.cliente && dados.cliente.nome) || dados.cliente || 'Cliente não informado';
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
    let bannerClass = 'orc-card-v2__banner';
    if (statusKey === 'aprovado') {
        bannerIcon = '✅';
        bannerText = 'Orçamento Aprovado';
        bannerColor = 'background:var(--ai-green, #10b981);color:white;';
        bannerClass += ' st-current';
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
        bannerText = !orcId ? 'Prévia do Orçamento' : 'Orçamento Rascunho';
    }
    const docBtn = orcId
        ? `<button type="button" class="orc-card-v2__doc-btn" data-editar-orc="${orcId}" title="Ver orçamento">📄</button>`
        : `<span class="orc-card-v2__doc-btn" style="cursor:default;opacity:0.4;" aria-hidden="true">📄</span>`;
    const disWhats = dados.tem_telefone === false ? 'disabled title="Cliente sem telefone"' : '';
    const disEmail = dados.tem_email === false ? 'disabled title="Cliente sem e-mail"' : '';
    const linkTokenAttr = dados.link_publico ? `data-copy-public-token="${escapeHtmlAttr(dados.link_publico)}"` : 'disabled title="Link indisponível"';
    // Botões
    let botoesHtml = '';
    let extraDataHtml = '';
    let previewBtnHtml = '';
    
    if (!orcId) {
        const previewJson = JSON.stringify(dados);
        const materiaisNovos = Array.isArray(dados.materiais_novos) ? dados.materiais_novos : [];
        const showCadastrarMaterial = materiaisNovos.length > 0;
        botoesHtml = `
            <div class="orc-card-v2__action-row">
                <button type="button" class="orc-card-v2__aprovar-btn orc-card-v2__aprovar-btn--compact btn-aprovar" data-orc-confirm="1">✅ Criar</button>
                ${showCadastrarMaterial ? '<button type="button" class="orc-card-v2__aprovar-btn orc-card-v2__aprovar-btn--compact btn-aprovar" data-orc-confirm="1" data-cadastrar="1">📦 Criar + mat.</button>' : ''}
                <button type="button" class="orc-card-v2__compact-btn orc-card-v2__compact-btn--ghost" data-orc-dismiss="1">✖ Cancelar</button>
            </div>
        `;
        extraDataHtml = `<script type="application/json" class="orc-data">${previewJson.replace(/<\/script>/g, '<\\/script>')}</script>`;
    } else {
        // Preview só para rascunho/enviado: aprovado já tem o botão 📄 no header
        if (statusKey !== 'aprovado') {
            previewBtnHtml = `
                <button type="button" class="orc-card-v2__preview-btn" onclick="abrirDetalhesOrcamento(${orcId})">
                    🔍 Preview
                </button>
            `;
        }

        if (['rascunho', 'enviado'].includes(statusKey)) {
            botoesHtml = `
                <div class="orc-card-v2__action-row">
                    <div class="orc-card-v2__icon-btns orc-card-v2__icon-btns--compact">
                        <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬 <span>Whats</span></button>
                        <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗 <span>Link</span></button>
                        <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️ <span>E-mail</span></button>
                    </div>
                    <button type="button" class="orc-card-v2__aprovar-btn orc-card-v2__aprovar-btn--compact btn-aprovar" data-quick-send="${aprovarEnc}" data-silent-send="true">✅ Aprovar</button>
                </div>
            `;
        } else if (statusKey === 'aprovado') {
            botoesHtml = `
                <div class="orc-card-v2__icon-btns orc-card-v2__icon-btns--compact orc-card-v2__icon-btns--center">
                    <button type="button" class="orc-card-v2__icon-btn btn-calendar" onclick="abrirModalAgendamentoRapido(${orcId}, '${escapeHtml(orcNum)}', '${(clienteNome || '').replace(/'/g, "\\'")}')" title="Agendar">📅 <span>Agenda</span></button>
                    <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬 <span>Whats</span></button>
                    <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗 <span>Link</span></button>
                    <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️ <span>E-mail</span></button>
                </div>
            `;
        } else {
             botoesHtml = `
                <div class="orc-card-v2__icon-btns orc-card-v2__icon-btns--compact orc-card-v2__icon-btns--center">
                     <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Reenviar WhatsApp">💬 <span>Whats</span></button>
                     <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗 <span>Link</span></button>
                </div>
             `;
        }
    }
    return `<div class="orc-card-v2${!orcId ? ' orc-preview-card' : ''}">
        <div class="${bannerClass}" style="${bannerColor}">
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
            <div class="orc-card-v2__actions">
                ${previewBtnHtml}
                ${botoesHtml}
            </div>
            ${extraDataHtml}
        </div>
    </div>`;
}
function renderOrcamentoSimulacao(dados) {
    if (!dados) return '<div class="opr-result opr-err">Dados da simulação indisponíveis.</div>';
    const num = escapeHtml(dados.numero || ('#' + (dados.id || '?')));
    const clienteNome = escapeHtml(
        (dados.cliente && dados.cliente.nome) || dados.cliente_nome || ''
    );
    const orcId = dados.id || null;
    const pct = Number(dados.desconto_pct || 0);
    const origFmt = escapeHtml(dados.total_original_fmt || '—');
    const novoFmt = escapeHtml(dados.total_com_desconto_fmt || '—');
    const econFmt = escapeHtml(dados.economia_fmt || '—');
    const applyBtn = orcId
        ? `<button type="button" class="orc-card-v2__aprovar-btn orc-card-v2__aprovar-btn--compact" data-apply-discount="${orcId}" data-desconto-pct="${pct}" style="margin-top:8px;">✅ Aplicar desconto</button>`
        : '';
    return `<div class="orc-card-v2">
        <div class="orc-card-v2__banner" style="background:var(--ai-warning,#f59e0b);color:#1e293b;">
            <span class="orc-card-v2__banner-icon" aria-hidden="true">🏷️</span>
            Simulação de Desconto — ${num}
        </div>
        <div class="orc-card-v2__body">
            ${clienteNome ? `<div class="orc-card-v2__client" style="margin-bottom:8px;">${clienteNome}</div>` : ''}
            <div class="orc-card-v2__item-row">
                <span>Total original</span><span>${origFmt}</span>
            </div>
            <div class="orc-card-v2__item-row" style="color:var(--ai-warning,#f59e0b);">
                <span>Desconto (${pct}%)</span><span>− ${econFmt}</span>
            </div>
            <div class="orc-card-v2__total">
                <span class="orc-card-v2__total-label">Novo total</span>
                <div class="orc-card-v2__total-value">
                    <span class="orc-card-v2__valor-final">${novoFmt}</span>
                </div>
            </div>
            <div class="orc-card-v2__actions">${applyBtn}</div>
        </div>
    </div>`;
}

function renderOperadorResultado(data, dados) {
    const acaoIcones = { 'VER': '🔍', 'APROVADO': '✅', 'RECUSADO': '❌', 'ENVIADO': '📤', 'DESCONTO': '💰', 'ADICIONADO': '➕', 'REMOVIDO': '➖' };
    const acao = dados && dados.acao ? dados.acao : '';
    const icone = acaoIcones[acao] || '⚡';
    const respText = data.resposta || (dados && dados.resposta) || '';
    const linkHtml = dados && dados.id ? `<a href="orcamentos.html" class="opr-link">Ver orçamento →</a>` : '';
    if (acao === 'VER' && dados && dados.id && !respText.trim()) {
        // Abre o modal de detalhes diretamente para evitar duplicar o card já visível
        const orcNum = dados.numero || ('#' + dados.id);
        setTimeout(function () {
            if (typeof abrirDetalhesOrcamento === 'function') abrirDetalhesOrcamento(dados.id);
        }, 80);
        return `<div class="opr-result opr-ok" style="gap:6px;">
            <span class="opr-icon">🔍</span>
            <span>Abrindo detalhes do <strong>${escapeHtml(orcNum)}</strong>…</span>
        </div>`;
    }
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
function renderListaClientes(dados) {
    const itens = Array.isArray(dados.clientes) ? dados.clientes : [];
    const total = Number(dados.total || 0);
    const hasMore = !!dados.has_more;
    const nextCursor = dados.next_cursor || '';
    const filtros = dados.filtros || {};
    const buscaFiltro = filtros.busca || '';
    const limitLista = Number(dados.limit || 10);
    const titulo = buscaFiltro
        ? `Clientes (Busca: "${escapeHtml(buscaFiltro)}")`
        : 'Meus Clientes';

    if (itens.length === 0) {
        return `<div class="orc-list-empty">Nenhum cliente encontrado para os filtros selecionados.</div>`;
    }

    const buildItemData = (item) => {
        const id = item.id || '—';
        const nome = escapeHtml(item.nome || 'Sem nome');
        const telefone = escapeHtml(item.telefone || '—');
        const telefoneRaw = item.telefone || '';
        const email = escapeHtml(item.email || '—');
        
        let dataExibicao = '—';
        if (item.criado_em) {
            const dateObj = new Date(item.criado_em);
            const dia = String(dateObj.getDate()).padStart(2, '0');
            const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
            const ano = dateObj.getFullYear();
            dataExibicao = `${dia}/${mes}/${ano}`;
        }

        return { id, nome, telefone, telefoneRaw, email, dataExibicao };
    };

    // ── Layout tabela (desktop) ───────────────────────────────────────────
    const trsDaTabela = itens.map((item) => {
        const d = buildItemData(item);

        const waLink = d.telefoneRaw 
            ? `<a href="https://wa.me/55${d.telefoneRaw.replace(/\D/g, '')}" target="_blank" class="btn-acao-tabela" title="Chamar no WhatsApp">💬</a>`
            : '';

        const actionBtn = item.id
            ? `<button type="button" class="btn-acao-tabela" onclick="if(typeof abrirDetalhesCliente === 'function') abrirDetalhesCliente(${item.id})" title="Ver detalhes">🔍</button>`
            : '';

        return `<tr>
            <td><strong>${d.id}</strong></td>
            <td><span class="td-truncate">${d.nome}</span></td>
            <td><span class="td-truncate">${d.telefone}</span></td>
            <td><span class="td-truncate">${d.email}</span></td>
            <td>${d.dataExibicao}</td>
            <td><div class="acoes-tabela">${actionBtn}${waLink}</div></td>
        </tr>`;
    }).join('');

    // ── Layout cards (mobile) ─────────────────────────────────────────────
    const cardsMobile = itens.map((item) => {
        const d = buildItemData(item);

        const waLink = d.telefoneRaw 
            ? `<a href="https://wa.me/55${d.telefoneRaw.replace(/\D/g, '')}" target="_blank" class="cliente-card-action" title="WhatsApp"><span aria-hidden="true">💬</span></a>`
            : '';

        const actionBtn = item.id
            ? `<button type="button" class="cliente-card-action" onclick="if(typeof abrirDetalhesCliente === 'function') abrirDetalhesCliente(${item.id})" title="Ver detalhes"><span aria-hidden="true">🔍</span></button>`
            : '';

        return `<div class="cliente-card-mobile">
            <div class="cliente-card-mobile__header">
                <span class="cliente-card-mobile__id">#${d.id}</span>
                <span class="cliente-card-mobile__nome">${d.nome}</span>
            </div>
            <div class="cliente-card-mobile__body">
                <div class="cliente-card-mobile__row">
                    <span class="cliente-card-mobile__label">Telefone</span>
                    <span class="cliente-card-mobile__value">${d.telefone}</span>
                </div>
                <div class="cliente-card-mobile__row">
                    <span class="cliente-card-mobile__label">Email</span>
                    <span class="cliente-card-mobile__value cliente-card-mobile__value--truncate">${d.email}</span>
                </div>
                <div class="cliente-card-mobile__row">
                    <span class="cliente-card-mobile__label">Cadastro</span>
                    <span class="cliente-card-mobile__value">${d.dataExibicao}</span>
                </div>
            </div>
            <div class="cliente-card-mobile__actions">
                ${actionBtn}
                ${waLink}
            </div>
        </div>`;
    }).join('');

    const printableRows = itens.map(item => ({
        "ID": item.id || '',
        "Nome": item.nome || '—',
        "Telefone": item.telefone || '—',
        "Email": item.email || '—',
        "Cadastro": item.criado_em ? new Date(item.criado_em).toLocaleDateString('pt-BR') : '—'
    }));

    const resumoImpresso = `Foram encontrados ${total} clientes. Exibindo ${itens.length} itens.`;
    const printableObj = {
        title: titulo,
        summary: resumoImpresso,
        rows: printableRows,
        theme: { variant: 'professional' }
    };
    const printablePayloadEscaped = escapeHtmlAttr(JSON.stringify(printableObj));

    const printableHtml = `
        <div class="semantic-printable-card" data-testid="semantic-printable-card" style="margin-bottom: 12px; margin-top: 12px;">
            <div class="semantic-printable-card__head">
                <span class="semantic-printable-card__icon" aria-hidden="true">🖨️</span>
                <div>
                    <div class="semantic-printable-card__title">${escapeHtml(titulo)}</div>
                    <div class="semantic-printable-card__sub">${escapeHtml(resumoImpresso)}</div>
                </div>
            </div>
            <div class="semantic-printable-card__actions">
                <button type="button" class="btn btn-primary" data-semantic-print-now="${printablePayloadEscaped}">Imprimir</button>
                <button type="button" class="btn btn-secondary" data-semantic-export-report="${printablePayloadEscaped}" data-export-format="csv">Exportar CSV</button>
                <button type="button" class="btn btn-secondary" data-semantic-export-report="${printablePayloadEscaped}" data-export-format="pdf">Exportar PDF</button>
            </div>
        </div>`;

    const loadMoreBtn = hasMore && nextCursor
        ? `<div style="margin-top: 12px; display: flex; justify-content: center;">
              <button type="button"
                class="orc-list-card__load-more"
                data-clientes-load-more="1"
                data-cursor="${escapeHtmlAttr(nextCursor)}"
                data-busca="${escapeHtmlAttr(String(buscaFiltro || ''))}"
                data-limit="${escapeHtmlAttr(String(limitLista || 10))}"
              >Carregar mais clientes</button>
           </div>`
        : '';

    return `<div class="orc-list-card" data-testid="assistente-clientes-list-card" style="padding: 0; background: transparent; border: none;">
        <div class="orc-list-card__header" style="margin-bottom: 8px;">
            <h4 class="orc-list-card__title" style="font-size: 1.1rem;">${escapeHtml(titulo)}</h4>
        </div>

        <!-- Tabela para desktop -->
        <div class="ai-table-wrapper cliente-lista-desktop">
            <table class="ai-table">
                <thead>
                    <tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Email</th><th>Cadastro</th><th>Ações</th></tr>
                </thead>
                <tbody>${trsDaTabela}</tbody>
            </table>
        </div>

        <!-- Cards para mobile -->
        <div class="cliente-lista-mobile">
            ${cardsMobile}
        </div>

        ${printableHtml}
        ${loadMoreBtn}
    </div>`;
}


function renderListaOrcamentos(dados) {
    const itens = Array.isArray(dados.orcamentos) ? dados.orcamentos : [];
    const total = Number(dados.total || 0);
    const itensRetornados = Number(dados.itens_retornados || itens.length || 0);
    const hasMore = !!dados.has_more;
    const nextCursor = dados.next_cursor || '';
    const filtros = dados.filtros || {};
    const statusFiltro = filtros.status || '';
    const clienteId = filtros.cliente_id || '';
    const dias = Number(filtros.dias || 30);
    const limitLista = Number(dados.limit || 10);
    const aprovadoEmDe = filtros.aprovado_em_de || '';
    const aprovadoEmAte = filtros.aprovado_em_ate || '';
    const titulo = statusFiltro
        ? `Orçamentos (${escapeHtml(String(statusFiltro).toUpperCase())})`
        : 'Orçamentos listados';

    const badgeMap = {
        'rascunho': 'badge-rascunho',
        'enviado': 'badge-enviado',
        'aprovado': 'badge-aprovado',
        'recusado': 'badge-recusado',
        'expirado': 'badge-expirado'
    };

    if (itens.length === 0) {
        return `<div class="orc-list-empty">Nenhum orçamento encontrado para os filtros selecionados.</div>`;
    }

    const trsDaTabela = itens.map((item) => {
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

        const valor = formatValue(item.total || 0);

        const actionBtn = item.id
            ? `<button type="button" class="btn btn-ghost" style="padding: 2px 8px; font-size: 11px;" onclick="if(typeof abrirDetalhesOrcamento === 'function') abrirDetalhesOrcamento(${item.id})" title="Ver detalhes do orçamento">🔍 Ver</button>`
            : '';

        return `<tr>
            <td data-label="Num"><strong>${numero}</strong></td>
            <td data-label="Cliente">${cliente}</td>
            <td data-label="${colunaDataLabel}">${dataExibicao}</td>
            <td data-label="Status"><span class="opr-status-badge ${badgeClass}" style="font-size:0.7em; padding:2px 6px;">${escapeHtml(statusStr)}</span></td>
            <td data-label="Total"><strong>${escapeHtml(valor)}</strong></td>
            <td data-label="Ações">${actionBtn}</td>
        </tr>`;
    }).join('');

    const itensImpressao = Array.isArray(dados.orcamentos_impressao) ? dados.orcamentos_impressao : itens;
    const printableRows = itensImpressao.map(item => {
        let dataExport = '—';
        if (filtros.aprovado_em_de || filtros.aprovado_em_ate) {
            if (item.aprovado_em) {
                const dateObj = new Date(item.aprovado_em);
                const dia = String(dateObj.getDate()).padStart(2, '0');
                const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
                const ano = dateObj.getFullYear();
                const hora = String(dateObj.getHours()).padStart(2, '0');
                const min = String(dateObj.getMinutes()).padStart(2, '0');
                dataExport = `${dia}/${mes}/${ano} ${hora}:${min}`;
            }
        } else if (item.criado_em) {
            const dateObj = new Date(item.criado_em);
            const dia = String(dateObj.getDate()).padStart(2, '0');
            const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
            const ano = dateObj.getFullYear();
            dataExport = `${dia}/${mes}/${ano}`;
        }
        
        const rowData = {
            "Orçamento": item.numero || String(item.id || ''),
            "Cliente": item.cliente_nome || '—',
            "Status": item.status || '—',
            "Total": formatValue(item.total || 0)
        };

        if (filtros.aprovado_em_de || filtros.aprovado_em_ate) {
            rowData["Aprovado em"] = dataExport;
        } else {
            rowData["Emissão"] = dataExport;
        }
        
        return rowData;
    });

    const resumoImpresso = `Foram encontrados ${total} orçamentos. Exibindo ${itensImpressao.length} itens.`;
    const printableObj = {
        title: titulo,
        summary: resumoImpresso,
        rows: printableRows,
        theme: { variant: 'professional' }
    };
    const printablePayloadEscaped = escapeHtmlAttr(JSON.stringify(printableObj));

    const printableHtml = `
        <div class="semantic-printable-card" data-testid="semantic-printable-card" style="margin-bottom: 12px; margin-top: 12px;">
            <div class="semantic-printable-card__head">
                <span class="semantic-printable-card__icon" aria-hidden="true">🖨️</span>
                <div>
                    <div class="semantic-printable-card__title">${escapeHtml(titulo)}</div>
                    <div class="semantic-printable-card__sub">${escapeHtml(resumoImpresso)}</div>
                </div>
            </div>
            <div class="semantic-printable-card__actions">
                <button type="button" class="btn btn-primary" data-semantic-print-now="${printablePayloadEscaped}">Imprimir</button>
                <button type="button" class="btn btn-secondary" data-semantic-export-report="${printablePayloadEscaped}" data-export-format="csv">Exportar CSV</button>
                <button type="button" class="btn btn-secondary" data-semantic-export-report="${printablePayloadEscaped}" data-export-format="pdf">Exportar PDF</button>
            </div>
        </div>`;

    const totaisPorStatus = dados.totais_por_status && typeof dados.totais_por_status === 'object'
        ? Object.entries(dados.totais_por_status)
        : [];
    const pillsHtml = totaisPorStatus
        .slice(0, 5)
        .map(([status, quantidade]) =>
            `<span class="orc-list-card__status-pill">${escapeHtml(status)}: ${escapeHtml(String(quantidade || 0))}</span>`,
        )
        .join('');

    const loadMoreBtn = hasMore && nextCursor
        ? `<div style="margin-top: 12px; display: flex; justify-content: center;">
              <button type="button"
                class="orc-list-card__load-more"
                data-orcamentos-load-more="1"
                data-cursor="${escapeHtmlAttr(nextCursor)}"
                data-status="${escapeHtmlAttr(String(statusFiltro || ''))}"
                data-cliente-id="${escapeHtmlAttr(String(clienteId || ''))}"
                data-dias="${escapeHtmlAttr(String(dias || 30))}"
                data-limit="${escapeHtmlAttr(String(limitLista || 10))}"
                data-aprovado-em-de="${escapeHtmlAttr(String(aprovadoEmDe || ''))}"
                data-aprovado-em-ate="${escapeHtmlAttr(String(aprovadoEmAte || ''))}"
              >Carregar mais resultados</button>
           </div>`
        : '';

    const tituloColData = (filtros.aprovado_em_de || filtros.aprovado_em_ate) ? 'Aprovado em' : 'Data';

    return `<div class="orc-list-card" data-testid="assistente-orc-list-card" style="padding: 0; background: transparent; border: none;">
        <div class="orc-list-card__header" style="margin-bottom: 8px;">
            <h4 class="orc-list-card__title" style="font-size: 1.1rem;">${escapeHtml(titulo)}</h4>
            <div class="orc-list-card__status-pills" style="margin-top: 6px;">${pillsHtml}</div>
        </div>

        <div class="ai-table-wrapper">
            <table class="ai-table">
                <thead>
                    <tr><th>Num</th><th>Cliente</th><th>${tituloColData}</th><th>Status</th><th>Total</th><th>Ações</th></tr>
                </thead>
                <tbody>${trsDaTabela}</tbody>
            </table>
        </div>

        ${printableHtml}
        ${loadMoreBtn}
    </div>`;
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
            } else if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
                // Formatting ISO dates like 2024-05-18T10:30:00
                const dateObj = new Date(val);
                const dia = String(dateObj.getDate()).padStart(2, '0');
                const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
                const ano = dateObj.getFullYear();
                const hora = String(dateObj.getHours()).padStart(2, '0');
                const min = String(dateObj.getMinutes()).padStart(2, '0');
                
                if (hora !== '00' || min !== '00') {
                    val = `${dia}/${mes}/${ano} ${hora}:${min}`;
                } else {
                    val = `${dia}/${mes}/${ano}`;
                }
            } else if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}$/)) {
                // Formatting ISO dates like 2024-05-18
                const [ano, mes, dia] = val.split('-');
                val = `${dia}/${mes}/${ano}`;
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
function renderSemanticTableRows(rows) {
    if (!Array.isArray(rows) || rows.length === 0) return '';
    const headersSet = new Set();
    rows.slice(0, 20).forEach((obj) => {
        if (obj && typeof obj === 'object') {
            Object.keys(obj).forEach((k) => headersSet.add(k));
        }
    });
    const headers = Array.from(headersSet)
        .filter((k) => typeof rows[0][k] !== 'object')
        .slice(0, 8);
    if (!headers.length) return '';
    const ths = headers
        .map((h) => `<th>${escapeHtml(String(h).replace(/_/g, ' ').replace(/^[a-z]/, (l) => l.toUpperCase()))}</th>`)
        .join('');
    const trs = rows.slice(0, 100).map((obj) => {
        const tds = headers.map((h) => {
            let val = obj[h];
            if (typeof val === 'number') {
                if (h.toLowerCase().match(/valor|total|preco|preço|saldo|despesa|receita|ticket/)) {
                    val = formatValue(val);
                } else if (val % 1 !== 0) {
                    val = val.toLocaleString('pt-BR');
                }
            } else if (typeof val === 'boolean') {
                val = val ? 'Sim' : 'Não';
            } else if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
                // Formatting ISO dates like 2024-05-18T10:30:00
                const dateObj = new Date(val);
                const dia = String(dateObj.getDate()).padStart(2, '0');
                const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
                const ano = dateObj.getFullYear();
                const hora = String(dateObj.getHours()).padStart(2, '0');
                const min = String(dateObj.getMinutes()).padStart(2, '0');
                
                // Show time only if it's not midnight exactly (indicative of date-only field converted to datetime)
                if (hora !== '00' || min !== '00') {
                    val = `${dia}/${mes}/${ano} ${hora}:${min}`;
                } else {
                    val = `${dia}/${mes}/${ano}`;
                }
            } else if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}$/)) {
                // Formatting ISO dates like 2024-05-18
                const [ano, mes, dia] = val.split('-');
                val = `${dia}/${mes}/${ano}`;
            }
            return `<td><span class="ai-td-content">${escapeHtml(String(val ?? '—'))}</span></td>`;
        }).join('');
        return `<tr>${tds}</tr>`;
    }).join('');
    return `<div class="ai-table-wrapper">
        <table class="ai-table">
            <thead><tr>${ths}</tr></thead>
            <tbody>${trs}</tbody>
        </table>
    </div>`;
}
function renderSemanticContract(data, semanticContract, isStreamed) {
    const sc = semanticContract || {};
    let content = '';
    const summary = (sc.summary || data.resposta || '').trim();
    if (summary && !(isStreamed && data.stream_has_chunks)) {
        content += `<div class="resposta-direta">${textToHtmlRich(summary)}</div>`;
    }
    const tableHtml = renderSemanticTableRows(sc.table || []);
    if (tableHtml) {
        content += tableHtml;
    }
    const meta = sc.metadata || {};
    const proveniencia = [];
    if (meta.capability && meta.capability !== 'UnknownCapability') proveniencia.push(`Capability: ${String(meta.capability)}`);
    if (meta.domain && meta.domain !== 'unknown') proveniencia.push(`Domínio: ${String(meta.domain)}`);
    if (meta.period_days) proveniencia.push(`Período: ${String(meta.period_days)} dias`);
    if (Array.isArray(meta.data_sources) && meta.data_sources.length) {
        proveniencia.push(`Fontes: ${meta.data_sources.join(', ')}`);
    }
    if (meta.truncated) {
        proveniencia.push(`Dados truncados (${meta.rows_returned || 0}/${meta.rows_total || 0})`);
    }
    if (proveniencia.length) {
        content += `<div class="semantic-provenance" style="margin-top:10px;font-size:12px;color:var(--ai-muted)">
            ${proveniencia.map((item) => `<div>• ${escapeHtml(String(item))}</div>`).join('')}
        </div>`;
    }
    if (Array.isArray(sc.insights) && sc.insights.length > 0) {
        const insightsHtml = sc.insights
            .map((insight) => `<li>${escapeHtml(String(insight.title || 'Insight'))}: ${escapeHtml(String(insight.detail || ''))}</li>`)
            .join('');
        content += `<div class="semantic-insights-card" style="margin-top:10px">
            <strong>Insights</strong>
            <ul style="margin:6px 0 0 16px">${insightsHtml}</ul>
        </div>`;
    }
    if (Array.isArray(sc.suggested_actions) && sc.suggested_actions.length > 0) {
        const actionsHtml = sc.suggested_actions
            .map((action) => `<button type="button" class="btn btn-ghost" data-semantic-suggested-action="${escapeHtmlAttr(JSON.stringify(action))}">${escapeHtml(String(action.label || 'Ação'))}</button>`)
            .join('');
        content += `<div class="semantic-actions" style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">${actionsHtml}</div>`;
    }
    // Cria o slot onde o gráfico será ancorado (antes do card de impressão)
    if (sc.chart) {
        content += `<div class="semantic-chart-slot" style="margin-top:12px;width:100%;min-height:10px;"></div>`;
    }

    const printableObj = sc.printable && typeof sc.printable === 'object' ? sc.printable : null;
    const printableRows = Array.isArray(printableObj?.rows) ? printableObj.rows : [];
    const printableSummary = String(printableObj?.summary || summary || '');
    const printableHint = `${String(data?.resposta || '')} ${String(sc?.summary || '')}`.toLowerCase();
    const shouldShowPrintable = !!(
        printableObj
        && (
            printableRows.length > 0
            || printableObj.force_printable === true
            || /\b(imprimir|impress[aã]o|pdf|exportar)\b/.test(printableHint)
        )
    );
    if (shouldShowPrintable) {
        const title = sc.printable.title || 'Versão imprimível disponível';
        const printSummary = printableSummary;
        const theme = sc.printable.theme && typeof sc.printable.theme === 'object' ? sc.printable.theme : {};
        const variant = String(theme.variant || 'professional');
        const printablePayloadEscaped = escapeHtmlAttr(JSON.stringify(sc.printable));
        content += `<div class="semantic-printable-card" data-testid="semantic-printable-card">
            <div class="semantic-printable-card__head">
                <span class="semantic-printable-card__icon" aria-hidden="true">🖨️</span>
                <div>
                    <div class="semantic-printable-card__title">${escapeHtml(String(title))}</div>
                    <div class="semantic-printable-card__sub">${textToHtmlRich(String(printSummary || ''))}</div>
                    <div class="semantic-printable-card__sub" style="margin-top:6px;font-size:12px;color:var(--ai-muted)">Tema: ${escapeHtml(variant)}</div>
                </div>
            </div>
            <div class="semantic-printable-card__actions">
                <button type="button" class="btn btn-primary" data-semantic-print-now="${printablePayloadEscaped}">Imprimir</button>
                <button type="button" class="btn btn-secondary" data-semantic-export-report="${printablePayloadEscaped}" data-export-format="csv">Exportar CSV</button>
                <button type="button" class="btn btn-secondary" data-semantic-export-report="${printablePayloadEscaped}" data-export-format="pdf">Exportar PDF</button>
                <button type="button" class="btn btn-ghost" data-semantic-copy-summary="${escapeHtmlAttr(String(printSummary || summary || ''))}">Copiar resumo</button>
            </div>
        </div>`;
    }
    return content || (isStreamed ? '' : '<div class="resposta-direta">Resposta semântica recebida.</div>');
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
    if (Array.isArray(dados.insights) && dados.insights.length > 0) {
        const insightsHtml = dados.insights
            .map((insight) => {
                if (typeof insight === 'string') return textToHtmlRich(insight);
                if (!insight || typeof insight !== 'object') return '';
                const titulo = String(insight.titulo || '').trim();
                const descricao = String(insight.descricao || '').trim();
                if (!titulo && !descricao) return '';
                if (titulo && descricao) return `<strong>${escapeHtml(titulo)}:</strong> ${textToHtmlRich(descricao)}`;
                return titulo ? escapeHtml(titulo) : textToHtmlRich(descricao);
            })
            .filter(Boolean);
        if (insightsHtml.length > 0) {
            content += '🔍 <strong>Insights:</strong><br>';
            insightsHtml.forEach(insightHtml => {
                content += `• ${insightHtml}<br>`;
            });
            content += '<br>';
        }
    }
    return content || (isStreamed ? '' : 'Resposta recebida.');
}
function resolveAssistenteRenderResult(data, isStreamed = false) {
    let dados = data.dados || data;
    let tipoResposta = (data.tipo_resposta && data.tipo_resposta !== 'geral') ? data.tipo_resposta : (dados.tipo || 'geral');

    // O backend pode retornar `orcamento_criado`, `orcamento_atualizado` ou `operador_resultado`.
    const isApproval = typeof _ultimaPergunta !== 'undefined' && _ultimaPergunta && _ultimaPergunta.toLowerCase().startsWith('aprovar');
    if (isApproval && ['orcamento_criado', 'orcamento_atualizado', 'operador_resultado'].includes(tipoResposta)) {
        const orcamentoData = data.orcamento || data.dados || data;
        if (orcamentoData && orcamentoData.id && orcamentoData.numero) {
            tipoResposta = 'orcamento_aprovado';
            dados = orcamentoData;
            dados.status = 'aprovado';
        }
    }

    // FIX: Unificação da renderização do card
    const cardTypes = ['orcamento_preview', 'orcamento_criado', 'orcamento_aprovado', 'orcamento_recusado', 'orcamento_atualizado', 'orcamento_card_unificado'];
    if (cardTypes.includes(tipoResposta) && dados) {
        return { html: renderOrcamentoCardUnificado(dados), rendererId: 'renderOrcamentoCardUnificado', tipoResposta, dados };
    }

    if (tipoResposta === 'catalogo_sugestao' && dados) {
        return { html: renderCatalogoSugestao(dados), rendererId: 'renderCatalogoSugestao', tipoResposta, dados };
    }

    const semanticContract = (dados && dados.semantic_contract) || data.semantic_contract || null;
    if (semanticContract && typeof semanticContract === 'object') {
        return { html: renderSemanticContract(data, semanticContract, isStreamed), rendererId: 'renderSemanticContract', tipoResposta, dados };
    }
    if (dados && Array.isArray(dados.orcamentos) && typeof dados.total !== 'undefined') {
        return { html: renderListaOrcamentos(dados), rendererId: 'renderListaOrcamentos', tipoResposta, dados };
    }
    if (dados && Array.isArray(dados.clientes) && (typeof dados.total !== 'undefined' || ['clientes_lista', 'listar_clientes'].includes(tipoResposta))) {
        return { html: renderListaClientes(dados), rendererId: 'renderListaClientes', tipoResposta, dados };
    }
    if (tipoResposta === 'operador_resultado') {
        return { html: renderOperadorResultado(data, dados), rendererId: 'renderOperadorResultado', tipoResposta, dados };
    }
    if (tipoResposta === 'orcamento_simulacao') {
        return { html: renderOrcamentoSimulacao(dados), rendererId: 'renderOrcamentoSimulacao', tipoResposta, dados };
    }
    if (tipoResposta === 'saldo_caixa' || dados.tipo === 'saldo_caixa') {
        return { html: renderSaldoRapido(dados), rendererId: 'renderSaldoRapido', tipoResposta, dados };
    }
    if (tipoResposta === 'onboarding' && dados) {
        return { html: renderOnboarding(dados), rendererId: 'renderOnboarding', tipoResposta, dados };
    }
    const tabela = renderTabelaRica(data, dados, isStreamed);
    if (tabela) return { html: tabela, rendererId: 'renderTabelaRica', tipoResposta, dados };
    if (data.resposta || dados.resposta) {
        const rawTxt = data.resposta || dados.resposta;
        if (isStreamed && data.stream_has_chunks) {
            var metaFe = dados._meta_frontend_data || dados;
            if (metaFe.is_list && typeof renderGenericDataList === 'function') {
                var html = renderGenericDataList(metaFe);
                if (html) {
                    return { html: html, rendererId: 'renderGenericDataList_streamed', tipoResposta, dados };
                }
            }
            return { html: '', rendererId: 'streaming_chunks', tipoResposta, dados };
        }
        return { html: `<div class="resposta-direta">${textToHtmlRich(rawTxt)}</div>`, rendererId: 'resposta-direta', tipoResposta, dados };
    }
    
    if (dados && dados.is_list && typeof renderGenericDataList === 'function') {
        var _entityKeys = Object.keys(_GENERIC_LIST_ENTITY_CONFIGS || {});
        var _hasKnownEntity = false;
        for (var _ei = 0; _ei < _entityKeys.length; _ei++) {
            if (Array.isArray(dados[_entityKeys[_ei]])) { _hasKnownEntity = true; break; }
        }
        if (!_hasKnownEntity) {
            for (var _dk in dados) {
                if (dados.hasOwnProperty(_dk) && Array.isArray(dados[_dk]) && dados[_dk].length > 0 && typeof dados[_dk][0] === 'object') {
                    _hasKnownEntity = true;
                    break;
                }
            }
        }
        if (_hasKnownEntity) {
            return { html: renderGenericDataList(dados), rendererId: 'renderGenericDataList', tipoResposta, dados };
        }
        return { html: '<div class="orc-list-empty">Nenhum dado disponível para exibição. Tente refinar sua consulta.</div>', rendererId: 'emptyListFallback', tipoResposta, dados };
    }

    const analiseHtml = renderAnaliseTexto(dados, isStreamed);
    const hasText = analiseHtml && String(analiseHtml).replace(/<[^>]*>/g, '').trim().length > 0;
    
    if (hasText) {
        return { html: analiseHtml, rendererId: 'renderAnaliseTexto', tipoResposta, dados };
    }

    if (isStreamed && data.stream_has_chunks) {
        return { html: '', rendererId: 'streaming_chunks_fallback', tipoResposta, dados };
    }

    const isSemanticResponse = !!((data && data.semantic_contract) || (dados && dados.semantic_contract));
    const uiPolicy = typeof window.getAssistenteResponseUiPolicy === 'function'
        ? window.getAssistenteResponseUiPolicy(tipoResposta)
        : { isRichResponse: false };
        
    const ehCardRico = isSemanticResponse || !!uiPolicy.isRichResponse || data.pending_action || tipoResposta === 'operador_resultado';

    if (!ehCardRico) {
        return { html: `<div class="resposta-direta">Não consegui montar a resposta completa agora. Tente novamente em alguns segundos.</div>`, rendererId: 'fallback_erro', tipoResposta, dados };
    }

    return { html: analiseHtml, rendererId: 'renderAnaliseTexto', tipoResposta, dados };
}

function formatAIResponse(data, isStreamed = false) {
    return resolveAssistenteRenderResult(data, isStreamed).html;
}
window.resolveAssistenteRenderResult = resolveAssistenteRenderResult;
function formatAssistenteMetaTraces(data) {
    let metaTracesHtml = '';
    const visPref = data?.dados?.visualizacao_recomendada || null;
    if (visPref && visPref.formato_preferido && visPref.formato_preferido !== 'auto') {
        metaTracesHtml += `<div class="tool-trace" style="margin-top:12px;font-size:0.75rem;color:var(--ai-muted)">🧭 Formato aplicado: <strong>${escapeHtml(String(visPref.formato_preferido))}</strong></div>`;
    }

    const intentDetectada = data?.dados?.intent_detectada || data?.metadata?.dados?.intent_detectada;
    if (intentDetectada) {
        metaTracesHtml += `<div class="tool-trace" style="margin-top:4px;font-size:0.75rem;color:var(--ai-muted)">🎯 Intenção detectada: <strong>${escapeHtml(intentDetectada)}</strong></div>`;
    }

    if (Array.isArray(data.tool_trace) && data.tool_trace.length > 0) {
        const items = data.tool_trace.map(t => {
            const ico = t.status === 'ok' ? '✅' : (t.status === 'pending' ? '⏳' : '⚠️');
            const rawReason = (typeof t.reason === 'string' && t.reason.trim())
                ? t.reason.trim()
                : ((typeof t.code === 'string' && t.code.trim()) ? t.code.trim() : '');
            const reasonHtml = rawReason
                ? ` <code class="tool-trace-reason">${escapeHtml(rawReason)}</code>`
                : '';
            return `<span class="tool-trace-item">${ico} ${escapeHtml(String(t.tool))}${reasonHtml}</span>`;
        }).join(' ');
        metaTracesHtml += `<div class="tool-trace" style="margin-top:4px;font-size:0.75rem;color:var(--ai-muted)">🛠️ ${items}</div>`;
    }

    const tIn = data.input_tokens;
    const tOut = data.output_tokens;
    if ((tIn != null && tIn > 0) || (tOut != null && tOut > 0)) {
        const tin = tIn || 0;
        const tout = tOut || 0;
        metaTracesHtml += `<div class="token-usage-badge" title="Tokens consumidos nesta resposta">🔢 ${tin + tout} tokens (↑${tin} ↓${tout})</div>`;
    }
    return metaTracesHtml;
}
window.formatAssistenteMetaTraces = formatAssistenteMetaTraces;
window.abrirModalAgendamentoRapido = function(orcamentoId, numero, clienteNome) {
    window.location.href = `agendamentos.html?novo=true&orcamento_id=${orcamentoId}&cliente=${encodeURIComponent(clienteNome)}`;
};

// ── Inovação 2: Sugestão por catálogo ────────────────────────────────────
function renderPendingActionCard(pa) {
    if (!pa || !pa.confirmation_token) return '';
    const token = pa.confirmation_token;
    const extras = pa.extras || {};
    const resumo = formatPendingArgs(pa.tool, pa.args || {}, extras);
    const temMateriaisNovos = Array.isArray(extras.materiais_novos) && extras.materiais_novos.length > 0;
    const tokAttr = escapeHtmlAttr(token);
    const btnCadastrar = temMateriaisNovos
        ? `<button type="button" class="btn btn-confirm-alt" data-confirm-ia="${tokAttr}" data-cadastrar="1">Confirmar e cadastrar produto</button>`
        : '';
    return `
        <div class="orc-card-v2 pending-action-card" role="dialog" aria-labelledby="pa-title-${token.slice(0,8)}" data-token="${tokAttr}">
            <div class="orc-card-v2__banner orc-card-v2__banner--warning" id="pa-title-${token.slice(0,8)}">
                <span class="orc-card-v2__banner-icon" aria-hidden="true" style="background:#f59e0b">⚠</span>
                Confirmação necessária
            </div>
            <div class="orc-card-v2__body">
                <div class="pending-action-tool">${humanizeToolName(pa.tool)}</div>
                <div class="pending-action-summary">${resumo}</div>
                <div class="orc-card-v2__action-row" style="margin-top:14px;">
                    <button type="button" class="orc-card-v2__aprovar-btn orc-card-v2__aprovar-btn--compact" data-confirm-ia="${tokAttr}" style="background:var(--ai-green);color:white;">✅ Confirmar</button>
                    ${btnCadastrar}
                    <button type="button" class="orc-card-v2__compact-btn orc-card-v2__compact-btn--ghost pa-cancel-btn" data-cancel-ia="1">✕ Cancelar</button>
                </div>
            </div>
        </div>`;
}
window.renderPendingActionCard = renderPendingActionCard;

function renderRegistroCriadoCard(dados) {
    if (!dados) return '';
    const registroTipo = dados.tipo_registro || 'Registro';
    const registroId = dados.id || '';
    const registroNumero = dados.numero || '';

    return `
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
window.renderRegistroCriadoCard = renderRegistroCriadoCard;

function renderCatalogoSugestao(dados) {
    const { sugestoes = [], termo_buscado = '', contexto_orcamento = {} } = dados;
    const clienteNome = contexto_orcamento.cliente_nome || '';

    const itemsHtml = sugestoes.map(s => {
        const precoFmt = s.preco != null ? `R$ ${Number(s.preco).toFixed(2).replace('.', ',')}` : 'Sem preço';
        const meta = [s.categoria, s.unidade].filter(Boolean).join(' · ');
        const dataAttr = JSON.stringify({ nome: s.nome, preco: s.preco, cliente: clienteNome }).replace(/'/g, '&#39;');
        return `
            <div class="cat-sug__item">
                <div class="cat-sug__info">
                    <div class="cat-sug__nome">${s.nome}</div>
                    ${meta ? `<div class="cat-sug__meta">${meta}</div>` : ''}
                </div>
                <div class="cat-sug__preco">${precoFmt}</div>
                <button class="cat-sug__btn-usar" onclick="usarSugestaoCatalogo(this)" data-item='${dataAttr}'>Usar este</button>
            </div>`;
    }).join('');

    return `
        <div class="cat-sug__card">
            <div class="cat-sug__header">📦 Catálogo — ${sugestoes.length} opção(ões) para "${termo_buscado}"</div>
            <div class="cat-sug__items">${itemsHtml}</div>
            <button class="cat-sug__btn-outro" onclick="informarOutroValorCatalogo(this)" data-termo="${termo_buscado}" data-cliente="${clienteNome}">Informar outro valor</button>
        </div>`;
}

window.usarSugestaoCatalogo = function(btn) {
    const item = JSON.parse(btn.dataset.item || '{}');
    if (!item.nome) return;
    const preco = item.preco != null ? ` por R$${Number(item.preco).toFixed(2)}` : '';
    const cliente = item.cliente ? ` para ${item.cliente}` : '';
    if (typeof sendQuickMessage === 'function') {
        sendQuickMessage(`orçamento de ${item.nome}${preco}${cliente}`);
    }
};

var _GENERIC_LIST_ENTITY_CONFIGS = {
    orcamentos: {
        titleDefault: 'Orçamentos listados',
        titleKey: 'numero',
        titleFn: function(item) { return item.numero || ('#' + (item.id || '—')); },
        badgeField: 'status',
        badgeMap: { rascunho: 'badge-rascunho', enviado: 'badge-enviado', aprovado: 'badge-aprovado', recusado: 'badge-recusado', expirado: 'badge-expirado' },
        actionFn: function(item) {
            if (!item.id) return '';
            return '<button type="button" class="btn btn-ghost" style="padding:2px 8px;font-size:11px;" onclick="if(typeof abrirDetalhesOrcamento===\'function\')abrirDetalhesOrcamento(' + item.id + ')" title="Ver detalhes">🔍 Ver</button>';
        },
        loadMoreAttr: 'data-orcamentos-load-more',
        loadMoreLabel: 'Carregar mais resultados',
        loadMoreCommandFn: function(attrs) {
            var cmd = 'Liste mais orçamentos com cursor "' + attrs.cursor + '", limite ' + attrs.limit;
            if (attrs.aprovado_em_de) cmd += ', aprovado_em_de ' + attrs.aprovado_em_de;
            if (attrs.aprovado_em_ate) cmd += ', aprovado_em_ate ' + attrs.aprovado_em_ate;
            cmd += '.';
            if (attrs.status) cmd += ' Status ' + attrs.status + '.';
            if (attrs.cliente_id) cmd += ' Cliente ' + attrs.cliente_id + '.';
            return cmd;
        }
    },
    clientes: {
        titleDefault: 'Meus Clientes',
        titleKey: 'nome',
        actionFn: function(item) {
            var btns = '';
            if (item.id) btns += '<button type="button" class="btn-acao-tabela" onclick="if(typeof abrirDetalhesCliente===\'function\')abrirDetalhesCliente(' + item.id + ')" title="Ver detalhes"><span aria-hidden="true">🔍</span></button>';
            if (item.telefone) btns += '<a href="https://wa.me/55' + String(item.telefone).replace(/\D/g, '') + '" target="_blank" class="btn-acao-tabela" title="WhatsApp"><span aria-hidden="true">💬</span></a>';
            return btns ? '<div class="acoes-tabela">' + btns + '</div>' : '';
        },
        mobileCardFn: function(item) {
            var html = '<div class="cliente-card-mobile">';
            html += '<div class="cliente-card-mobile__header">';
            html += '<span class="cliente-card-mobile__id">#' + escapeHtml(String(item.id || '—')) + '</span>';
            html += '<span class="cliente-card-mobile__nome">' + escapeHtml(item.nome || '—') + '</span>';
            html += '</div><div class="cliente-card-mobile__body">';
            var fields = _genericExtractDisplayFields(item);
            fields.forEach(function(f) {
                if (f.key === 'id' || f.key === 'nome') return;
                html += '<div class="cliente-card-mobile__row"><span class="cliente-card-mobile__label">' + escapeHtml(f.label) + '</span><span class="cliente-card-mobile__value">' + escapeHtml(String(f.value)) + '</span></div>';
            });
            html += '</div></div>';
            return html;
        },
        loadMoreAttr: 'data-clientes-load-more',
        loadMoreLabel: 'Carregar mais clientes',
        loadMoreCommandFn: function(attrs) {
            var cmd = 'Liste mais clientes com cursor "' + attrs.cursor + '", limite ' + attrs.limit;
            if (attrs.busca) cmd += ', buscar "' + attrs.busca + '"';
            return cmd + '.';
        }
    }
};

function _genericExtractDisplayFields(item) {
    var skipKeys = ['id', '_meta', 'empresa_id', 'usuario_id'];
    var fields = [];
    for (var key in item) {
        if (!item.hasOwnProperty(key) || skipKeys.indexOf(key) >= 0) continue;
        var val = item[key];
        if (val === null || val === undefined) continue;
        if (typeof val === 'object') continue;
        var label = key.replace(/_/g, ' ').replace(/^[a-z]/, function(l) { return l.toUpperCase(); });
        var display = val;
        if (typeof val === 'number') {
            if (/valor|total|preco|preço|saldo|despesa|receita|ticket/i.test(key)) {
                display = typeof formatValue === 'function' ? formatValue(val) : 'R$ ' + val.toFixed(2).replace('.', ',');
            } else if (val % 1 !== 0) {
                display = val.toLocaleString('pt-BR');
            }
        } else if (typeof val === 'boolean') {
            display = val ? 'Sim' : 'Não';
        } else if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(val)) {
            var d = new Date(val);
            var dia = String(d.getDate()).padStart(2, '0');
            var mes = String(d.getMonth() + 1).padStart(2, '0');
            var ano = d.getFullYear();
            var hora = String(d.getHours()).padStart(2, '0');
            var min = String(d.getMinutes()).padStart(2, '0');
            display = (hora === '00' && min === '00') ? dia + '/' + mes + '/' + ano : dia + '/' + mes + '/' + ano + ' ' + hora + ':' + min;
        } else if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
            var parts = val.split('-');
            display = parts[2] + '/' + parts[1] + '/' + parts[0];
        }
        fields.push({ key: key, label: label, value: display });
    }
    return fields;
}

function _entityConfigToGenericConfig(entityConfig, entityKey) {
    var config = {};
    if (entityConfig.title) config.titleDefault = entityConfig.title;
    if (entityConfig.title_key) config.titleKey = entityConfig.title_key;
    if (entityConfig.badge_field) config.badgeField = entityConfig.badge_field;
    if (entityConfig.badge_map) config.badgeMap = entityConfig.badge_map;
    if (entityConfig.load_more_label) config.loadMoreLabel = entityConfig.load_more_label;
    if (entityConfig.load_more_command) {
        var cmdTemplate = entityConfig.load_more_command;
        config.loadMoreCommandFn = function(attrs) {
            var result = cmdTemplate;
            for (var ak in attrs) {
                if (attrs.hasOwnProperty(ak)) {
                    result = result.replace(new RegExp('\\{\\{' + ak + '\\}\\}', 'g'), String(attrs[ak] || ''));
                }
            }
            return result;
        };
    }
    if (Array.isArray(entityConfig.columns) && entityConfig.columns.length > 0) {
        config.columnSchema = entityConfig.columns.map(function(col) {
            if (typeof col === 'string') return { key: col };
            return {
                key: col.key || col.name || '',
                label: col.label || col.title || '',
                format: col.format || col.type || '',
                align: col.align || ''
            };
        }).filter(function(col) { return !!col.key; });
    }
    return config;
}

function renderGenericDataList(dados) {
    var entityKey = null;
    var items = [];
    var entityKeys = Object.keys(_GENERIC_LIST_ENTITY_CONFIGS);
    for (var i = 0; i < entityKeys.length; i++) {
        var ek = entityKeys[i];
        if (Array.isArray(dados[ek]) && dados[ek].length >= 0) {
            entityKey = ek;
            items = dados[ek];
            break;
        }
    }

    if (!entityKey) {
        for (var dk in dados) {
            if (dados.hasOwnProperty(dk) && Array.isArray(dados[dk]) && dados[dk].length > 0 && typeof dados[dk][0] === 'object' && dados[dk][0] !== null) {
                entityKey = dk;
                items = dados[dk];
                break;
            }
        }
    }

    if (!entityKey) {
        return '<div class="orc-list-empty">Nenhum dado disponível para exibição.</div>';
    }

    var config = _GENERIC_LIST_ENTITY_CONFIGS[entityKey] || {};

    if (dados.entity_config && typeof dados.entity_config === 'object') {
        var ecConfig = _entityConfigToGenericConfig(dados.entity_config, entityKey);
        for (var ecKey in ecConfig) {
            if (ecConfig.hasOwnProperty(ecKey) && !(ecKey in config)) {
                config[ecKey] = ecConfig[ecKey];
            }
        }
        if (typeof registerGenericEntityConfig === 'function') {
            registerGenericEntityConfig(entityKey, config);
        }
    }

    var _metaFrontend = dados._meta_frontend_data;
    if (_metaFrontend && _metaFrontend.entity_config && typeof _metaFrontend.entity_config === 'object') {
        var ecMetaConfig = _entityConfigToGenericConfig(_metaFrontend.entity_config, entityKey);
        for (var ecMetaKey in ecMetaConfig) {
            if (ecMetaConfig.hasOwnProperty(ecMetaKey) && !(ecMetaKey in config)) {
                config[ecMetaKey] = ecMetaConfig[ecMetaKey];
            }
        }
        if (typeof registerGenericEntityConfig === 'function') {
            registerGenericEntityConfig(entityKey, config);
        }
    }

    var total = Number(dados.total || items.length || 0);
    var hasMore = !!dados.has_more;
    var nextCursor = dados.next_cursor || '';
    var filtros = dados.filtros || {};
    var limitLista = Number(dados.limit || 10);
    var titulo = dados.titulo || config.titleDefault || (entityKey.charAt(0).toUpperCase() + entityKey.slice(1));

    if (items.length === 0) {
        var emptyMsg = 'Nenhum registro encontrado';
        if (filtros.status) emptyMsg += ' com status "' + escapeHtml(filtros.status) + '"';
        if (filtros.busca) emptyMsg += ' para a busca "' + escapeHtml(filtros.busca) + '"';
        if (filtros.dias) emptyMsg += ' nos últimos ' + filtros.dias + ' dias';
        return '<div class="orc-list-empty">' + emptyMsg + '. Tente ajustar os filtros ou refazer a consulta.</div>';
    }

    var hasSchema = Array.isArray(config.columnSchema) && config.columnSchema.length > 0;
    var columnDefs = [];
    var columnSchemas = [];

    if (hasSchema) {
        config.columnSchema.forEach(function(col) {
            if (!col || !col.key) return;
            if (config.badgeField && col.key === config.badgeField) return;
            columnDefs.push(col.key);
            columnSchemas.push(col);
        });
    } else if (items.length > 0) {
        var seen = {};
        var sampleKeys = [];
        items.slice(0, 10).forEach(function(item) {
            for (var k in item) {
                if (item.hasOwnProperty(k) && !seen[k] && typeof item[k] !== 'object') {
                    seen[k] = true;
                    sampleKeys.push(k);
                }
            }
        });
        var skipColKeys = ['id', 'empresa_id', 'usuario_id', '_meta'];
        sampleKeys.forEach(function(k) {
            if (skipColKeys.indexOf(k) >= 0) return;
            if (k === 'status' && config.badgeField === 'status') return;
            if (k === entityKey.replace(/s$/, '') + '_id' || k === 'cliente_id') {
                if (k === 'cliente_id') return;
            }
            columnDefs.push(k);
            columnSchemas.push({ key: k, label: k.replace(/_/g, ' ').replace(/^[a-z]/, function(l) { return l.toUpperCase(); }) });
        });
    }

    if (!hasSchema && config.badgeField) {
        var bfIdx = columnDefs.indexOf(config.badgeField);
        if (bfIdx >= 0) { columnDefs.splice(bfIdx, 1); columnSchemas.splice(bfIdx, 1); }
    }

    var hasActions = typeof config.actionFn === 'function';

    function _schemaLabel(col) {
        return col.label || col.key.replace(/_/g, ' ').replace(/^[a-z]/, function(l) { return l.toUpperCase(); });
    }

    function _schemaAlign(col) {
        return col.align ? ' style="text-align:' + escapeHtml(col.align) + ';"' : '';
    }

    var ths = columnSchemas.map(function(col) {
        return '<th' + _schemaAlign(col) + '>' + escapeHtml(_schemaLabel(col)) + '</th>';
    }).join('');
    if (config.badgeField) {
        var bfLabel = config.badgeField.replace(/_/g, ' ').replace(/^[a-z]/, function(l) { return l.toUpperCase(); });
        ths += '<th>' + escapeHtml(bfLabel) + '</th>';
    }
    if (hasActions) ths += '<th>Ações</th>';

    function _formatValueBySchema(raw, col) {
        if (raw === null || raw === undefined) return '—';
        var fmt = (col.format || '').toLowerCase();
        if (fmt === 'currency' || /valor|total|preco|preço|saldo|despesa|receita|ticket/i.test(col.key)) {
            return typeof formatValue === 'function' ? formatValue(Number(raw)) : 'R$ ' + Number(raw).toFixed(2).replace('.', ',');
        }
        if (fmt === 'date' || (typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(raw))) {
            var d = new Date(raw);
            var dia = String(d.getDate()).padStart(2, '0');
            var mes = String(d.getMonth() + 1).padStart(2, '0');
            var ano = d.getFullYear();
            var hora = String(d.getHours()).padStart(2, '0');
            var min = String(d.getMinutes()).padStart(2, '0');
            return (hora === '00' && min === '00') ? dia + '/' + mes + '/' + ano : dia + '/' + mes + '/' + ano + ' ' + hora + ':' + min;
        }
        if (fmt === 'date_short' || (typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(raw))) {
            var p = String(raw).split('-');
            return p[2] + '/' + p[1] + '/' + p[0];
        }
        if (fmt === 'boolean' || typeof raw === 'boolean') {
            return raw ? 'Sim' : 'Não';
        }
        if (fmt === 'percent') {
            return Number(raw).toFixed(1).replace('.', ',') + '%';
        }
        if (fmt === 'cnpj') {
            var s = String(raw).replace(/\D/g, '');
            return s.length === 14 ? s.slice(0,2)+'.'+s.slice(2,5)+'.'+s.slice(5,8)+'/'+s.slice(8,12)+'-'+s.slice(12) : String(raw);
        }
        if (fmt === 'cpf') {
            var c = String(raw).replace(/\D/g, '');
            return c.length === 11 ? c.slice(0,3)+'.'+c.slice(3,6)+'.'+c.slice(6,9)+'-'+c.slice(9) : String(raw);
        }
        if (fmt === 'phone' || fmt === 'telefone') {
            var t = String(raw).replace(/\D/g, '');
            if (t.length === 11) return '('+t.slice(0,2)+') '+t.slice(2,7)+'-'+t.slice(7);
            if (t.length === 10) return '('+t.slice(0,2)+') '+t.slice(2,6)+'-'+t.slice(6);
            return String(raw);
        }
        if (typeof raw === 'number') {
            if (raw % 1 !== 0) return raw.toLocaleString('pt-BR');
            return String(raw);
        }
        return String(raw);
    }

    var trs = items.map(function(item) {
        var tds = columnSchemas.map(function(col) {
            var raw = item[col.key];
            var display = hasSchema ? _formatValueBySchema(raw, col) : _formatValueBySchema(raw, { key: col.key, format: '' });
            var isTitle = (col.key === config.titleKey);
            return '<td data-label="' + escapeHtml(col.key) + '"' + _schemaAlign(col) + '>' + (isTitle ? '<strong>' : '<span class="ai-td-content">') + escapeHtml(String(display != null ? display : '—')) + (isTitle ? '</strong>' : '</span>') + '</td>';
        }).join('');

        if (config.badgeField) {
            var statusVal = item[config.badgeField] || '—';
            var statusKey = String(statusVal).toLowerCase();
            var badgeClass = (config.badgeMap && config.badgeMap[statusKey]) || '';
            if (badgeClass) {
                tds += '<td data-label="' + escapeHtml(config.badgeField) + '"><span class="opr-status-badge ' + badgeClass + '" style="font-size:0.7em;padding:2px 6px;">' + escapeHtml(String(statusVal)) + '</span></td>';
            } else {
                tds += '<td data-label="' + escapeHtml(config.badgeField) + '">' + escapeHtml(String(statusVal)) + '</td>';
            }
        }

        if (hasActions) {
            tds += '<td data-label="Ações">' + config.actionFn(item) + '</td>';
        }

        return '<tr>' + tds + '</tr>';
    }).join('');

    var mobileCards = '';
    if (typeof config.mobileCardFn === 'function') {
        mobileCards = items.map(config.mobileCardFn).join('');
    }

    var printableRows = items.map(function(item) {
        var row = {};
        columnSchemas.forEach(function(col) {
            row[_schemaLabel(col)] = item[col.key] != null ? item[col.key] : '—';
        });
        if (config.badgeField && item[config.badgeField]) {
            row[config.badgeField] = item[config.badgeField];
        }
        return row;
    });
    var resumoImpresso = 'Foram encontrados ' + total + ' registros. Exibindo ' + items.length + ' itens.';
    var printableObj = { title: titulo, summary: resumoImpresso, rows: printableRows, theme: { variant: 'professional'     },
    detalhes: {
        titleDefault: 'Resultados',
        titleKey: 'agrupador',
    },
    movimentacoes: {
        titleDefault: 'Movimentações de Caixa',
        titleKey: 'descricao',
    },
    despesas: {
        titleDefault: 'Contas a Pagar',
        titleKey: 'descricao',
    }
};
    var printablePayloadEscaped = escapeHtmlAttr(JSON.stringify(printableObj));

    var printableHtml = '<div class="semantic-printable-card" data-testid="semantic-printable-card" style="margin-bottom:12px;margin-top:12px;">' +
        '<div class="semantic-printable-card__head">' +
        '<span class="semantic-printable-card__icon" aria-hidden="true">🖨️</span>' +
        '<div><div class="semantic-printable-card__title">' + escapeHtml(titulo) + '</div>' +
        '<div class="semantic-printable-card__sub">' + escapeHtml(resumoImpresso) + '</div></div></div>' +
        '<div class="semantic-printable-card__actions">' +
        '<button type="button" class="btn btn-primary" data-semantic-print-now="' + printablePayloadEscaped + '">Imprimir</button>' +
        '<button type="button" class="btn btn-secondary" data-semantic-export-report="' + printablePayloadEscaped + '" data-export-format="csv">Exportar CSV</button>' +
        '<button type="button" class="btn btn-secondary" data-semantic-export-report="' + printablePayloadEscaped + '" data-export-format="pdf">Exportar PDF</button>' +
        '</div></div>';

    var loadMoreDataAttrs = '';
    if (config.loadMoreAttr) {
        loadMoreDataAttrs = ' ' + config.loadMoreAttr + '="1"';
    }
    loadMoreDataAttrs += ' data-generic-load-more="1" data-entity-key="' + escapeHtmlAttr(entityKey) + '"';
    loadMoreDataAttrs += ' data-cursor="' + escapeHtmlAttr(nextCursor) + '"';
    loadMoreDataAttrs += ' data-limit="' + escapeHtmlAttr(String(limitLista)) + '"';
    if (filtros) {
        for (var fk in filtros) {
            if (filtros.hasOwnProperty(fk) && filtros[fk]) {
                loadMoreDataAttrs += ' data-filter-' + fk + '="' + escapeHtmlAttr(String(filtros[fk])) + '"';
            }
        }
    }

    var loadMoreBtn = (hasMore && nextCursor)
        ? '<div style="margin-top:12px;display:flex;justify-content:center;"><button type="button" class="orc-list-card__load-more"' + loadMoreDataAttrs + '>' + escapeHtml(config.loadMoreLabel || 'Carregar mais') + '</button></div>'
        : '';

    var pillsHtml = '';
    var totaisPorStatus = dados.totais_por_status && typeof dados.totais_por_status === 'object' ? Object.entries(dados.totais_por_status) : [];
    if (totaisPorStatus.length > 0) {
        pillsHtml = '<div class="orc-list-card__status-pills" style="margin-top:6px;">' +
            totaisPorStatus.slice(0, 5).map(function(entry) {
                return '<span class="orc-list-card__status-pill">' + escapeHtml(entry[0]) + ': ' + escapeHtml(String(entry[1] || 0)) + '</span>';
            }).join('') + '</div>';
    }

    var mobileSection = '';
    if (mobileCards) {
        mobileSection = '<div class="cliente-lista-mobile" style="display:none;">' + mobileCards + '</div>';
    }

    return '<div class="orc-list-card" data-testid="assistente-generic-list-card" data-entity-key="' + escapeHtmlAttr(entityKey) + '" style="padding:0;background:transparent;border:none;">' +
        '<div class="orc-list-card__header" style="margin-bottom:8px;">' +
        '<h4 class="orc-list-card__title" style="font-size:1.1rem;">' + escapeHtml(titulo) + '</h4>' +
        pillsHtml +
        '</div>' +
        '<div class="ai-table-wrapper cliente-lista-desktop">' +
        '<table class="ai-table"><thead><tr>' + ths + '</tr></thead><tbody>' + trs + '</tbody></table></div>' +
        mobileSection +
        printableHtml +
        loadMoreBtn +
        '</div>';
}

window.renderGenericDataList = renderGenericDataList;

function registerGenericEntityConfig(key, config) {
    if (!key || typeof key !== 'string') {
        console.warn('[registerGenericEntityConfig] chave invalida:', key);
        return;
    }
    if (!config || typeof config !== 'object') {
        console.warn('[registerGenericEntityConfig] config invalido para chave:', key);
        return;
    }
    if (!_GENERIC_LIST_ENTITY_CONFIGS) {
        console.warn('[registerGenericEntityConfig] _GENERIC_LIST_ENTITY_CONFIGS nao inicializado');
        return;
    }
    _GENERIC_LIST_ENTITY_CONFIGS[key] = config;
}

function unregisterGenericEntityConfig(key) {
    if (_GENERIC_LIST_ENTITY_CONFIGS && key && _GENERIC_LIST_ENTITY_CONFIGS[key]) {
        delete _GENERIC_LIST_ENTITY_CONFIGS[key];
    }
}

function getRegisteredEntityConfigs() {
    return _GENERIC_LIST_ENTITY_CONFIGS ? Object.assign({}, _GENERIC_LIST_ENTITY_CONFIGS) : {};
}

window.registerGenericEntityConfig = registerGenericEntityConfig;
window.unregisterGenericEntityConfig = unregisterGenericEntityConfig;
window.getRegisteredEntityConfigs = getRegisteredEntityConfigs;
window._entityConfigToGenericConfig = _entityConfigToGenericConfig;
window._formatValueBySchema = _formatValueBySchema;

window.informarOutroValorCatalogo = function(btn) {
    const termo = btn.dataset.termo || '';
    const cliente = btn.dataset.cliente ? ` para ${btn.dataset.cliente}` : '';
    const input = document.getElementById('messageInput');
    if (input) {
        input.value = `orçamento de ${termo}${cliente} por `;
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    }
};
