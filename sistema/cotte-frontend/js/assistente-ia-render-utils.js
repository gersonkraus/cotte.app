/**
 * assistente-ia-render-utils.js
 *
 * Utilitários de render e formatação do assistente.
 */

function formatValue(value) {
    if (typeof value === 'number') {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }
    return value;
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
