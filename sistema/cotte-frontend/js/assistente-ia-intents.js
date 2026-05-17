(function (globalScope) {
    const DRAFT_RE = /or[cç]amento\s+para\s+(?<cliente>[\wÀ-ÿ][\wÀ-ÿ\s]{1,40}?)\s+de\s+(?<servico>[\wÀ-ÿ][\wÀ-ÿ\s]{1,40}?)\s+(?:por|a)\s+R?\$?\s*(?<preco>\d+(?:[.,]\d{1,2})?)/i;

    const ASSISTENTE_INTENT_REGISTRY = [
        {
            id: 'caixa',
            label: 'Caixa',
            response_type: 'saldo_caixa',
            response_types: ['saldo_caixa'],
            renderer: 'renderSaldoRapido',
            data_minimos: [],
            quick_messages: ['Quanto tenho em caixa hoje?'],
            welcome_shortcuts: [
                { group: 'Financeiro', label: 'Quanto tenho em caixa hoje?', icon: '💰', message: 'Quanto tenho em caixa hoje?' },
            ],
            quick_actions: ['Qual meu saldo atual?'],
            quick_action_items: [
                { label: 'Consultar Saldo', description: 'Ver saldo atualizado agora', icon: '💰', message: 'Qual meu saldo atual?' },
            ],
            slash_commands: [
                { cmd: '/caixa', desc: 'Ver saldo atual disponível', icon: '💰' },
            ],
            patterns: [/\bcaixa\b|\bsaldo\b/i],
        },
        {
            id: 'resumo_financeiro',
            label: 'Resumo financeiro',
            response_type: 'resumo_financeiro',
            response_types: ['resumo_financeiro'],
            renderer: 'renderAnaliseTexto',
            data_minimos: [],
            quick_messages: ['Resumo financeiro do mês'],
            welcome_shortcuts: [
                { group: 'Financeiro', label: 'Resumo financeiro do mês', icon: '📊', message: 'Resumo financeiro do mês' },
            ],
            quick_actions: ['Resumo financeiro do mes'],
            quick_action_items: [
                { label: 'Resumo Financeiro', description: 'Acompanhar resultados do mês', icon: '📊', message: 'Resumo financeiro do mes' },
            ],
            slash_commands: [
                { cmd: '/faturamento', desc: 'Total faturado em orçamentos', icon: '📈' },
                { cmd: '/resumo', desc: 'Visão geral (Dashboard)', icon: '📊' },
            ],
            patterns: [/\bresumo financeiro\b|\bfaturamento\b/i],
        },
        {
            id: 'contas_receber',
            label: 'Contas a receber',
            response_type: 'analise_financeira',
            response_types: ['analise_financeira'],
            renderer: 'renderAnaliseTexto',
            data_minimos: [],
            slash_commands: [
                { cmd: '/receber', desc: 'Valores em aberto a receber', icon: '📥' },
            ],
            patterns: [/\breceber\b|\bem aberto\b/i],
        },
        {
            id: 'contas_pagar',
            label: 'Contas a pagar',
            response_type: 'analise_financeira',
            response_types: ['analise_financeira'],
            renderer: 'renderAnaliseTexto',
            data_minimos: [],
            slash_commands: [
                { cmd: '/pagar', desc: 'Valores em aberto a pagar', icon: '📤' },
            ],
            patterns: [/\bpagar\b/i],
        },
        {
            id: 'clientes_atraso',
            label: 'Clientes em atraso',
            response_type: 'analise_financeira',
            response_types: ['analise_financeira'],
            renderer: 'renderAnaliseTexto',
            data_minimos: [],
            quick_messages: ['Quem está devendo?'],
            welcome_shortcuts: [
                { group: 'Financeiro', label: 'Quem está devendo?', icon: '💸', message: 'Quem está devendo?' },
            ],
            slash_commands: [
                { cmd: '/devendo', desc: 'Lista de clientes em atraso', icon: '🚨' },
            ],
            patterns: [/\bdevendo\b|\batraso\b|\binadimpl|\bdevedores\b/i],
        },
        {
            id: 'previsao_caixa',
            label: 'Previsão de caixa',
            response_type: 'analise_financeira',
            response_types: ['analise_financeira'],
            renderer: 'renderAnaliseTexto',
            data_minimos: ['periodo'],
            slash_commands: [
                { cmd: '/previsao', desc: 'Projeção de caixa futuro', icon: '🔮' },
            ],
            patterns: [/\bprevis[aã]o\b/i],
        },
        {
            id: 'novo_orcamento',
            label: 'Novo orçamento',
            response_type: 'orcamento_preview',
            response_types: ['orcamento_preview', 'orcamento_criado', 'orcamento_atualizado'],
            renderer: 'renderOrcamentoCardUnificado',
            data_minimos: ['cliente', 'servico', 'preco'],
            quick_messages: ['Gerar orçamento para cliente'],
            welcome_shortcuts: [
                { group: 'Vendas & Serviços', label: 'Gerar novo orçamento', icon: '📝', message: 'Gerar orçamento para cliente' },
            ],
            quick_actions: ['Gerar orcamento para cliente'],
            quick_action_items: [
                { label: 'Novo Orçamento', description: 'Criar orçamento para cliente', icon: '📝', message: 'Gerar orcamento para cliente' },
            ],
            slash_commands: [
                { cmd: '/orcamento', desc: 'Criar um novo orçamento', icon: '📝' },
            ],
            patterns: [/\bgerar\b.*\bor[çc]amento\b|\bcriar\b.*\bor[çc]amento\b/i],
        },
        {
            id: 'consultar_orcamento',
            label: 'Consultar orçamento',
            response_type: 'orcamento_card_unificado',
            response_types: ['orcamento_card_unificado', 'orcamento_aprovado', 'orcamento_recusado'],
            renderer: 'renderOrcamentoCardUnificado',
            data_minimos: ['orcamento_numero'],
            patterns: [/\bver\b.*\bor[çc]amento\b|\bdetalhes?\b.*\bor[çc]amento\b/i],
        },
        {
            id: 'orcamentos_pendentes',
            label: 'Orçamentos pendentes',
            response_type: 'orcamentos',
            response_types: ['orcamentos'],
            renderer: 'renderListaOrcamentos',
            data_minimos: [],
            quick_messages: ['Quais orçamentos pendentes?'],
            welcome_shortcuts: [
                { group: 'Vendas & Serviços', label: 'Orçamentos pendentes', icon: '⏳', message: 'Quais orçamentos pendentes?' },
            ],
            patterns: [/\bor[çc]amentos?\b.*\bpendentes?\b/i],
        },
        {
            id: 'listar_orcamentos',
            label: 'Orçamentos',
            response_type: 'lista_orcamentos',
            response_types: ['lista_orcamentos', 'orcamentos'],
            renderer: 'renderListaOrcamentos',
            data_minimos: [],
            quick_action_items: [
                { label: 'Listar Orçamentos', description: 'Ver orçamentos recentes', icon: '📝', message: 'Listar meus orçamentos' },
            ],
            patterns: [/\blistar\b.*\bor[çc]amentos?\b|\blista\b.*\bor[çc]amentos?\b/i],
        },
        {
            id: 'listar_clientes',
            label: 'Clientes',
            response_type: 'clientes_lista',
            response_types: ['clientes_lista'],
            renderer: 'renderListaClientes',
            data_minimos: [],
            quick_action_items: [
                { label: 'Listar Clientes', description: 'Consultar base de clientes', icon: '👥', message: 'Listar meus clientes' },
            ],
            patterns: [/\blistar\b.*\bclientes\b|\blista\b.*\bclientes\b|\bmeus clientes\b/i],
        },
        {
            id: 'taxa_conversao',
            label: 'Taxa de conversão',
            response_type: 'analise_conversao',
            response_types: ['analise_conversao'],
            renderer: 'renderAnaliseTexto',
            data_minimos: ['periodo'],
            quick_messages: ['Taxa de conversão de orçamentos este mês'],
            welcome_shortcuts: [
                { group: 'Relatórios', label: 'Taxa de conversão', icon: '📈', message: 'Taxa de conversão de orçamentos este mês' },
            ],
            patterns: [/\bconvers[aã]o\b/i],
        },
        {
            id: 'faturamento_cliente',
            label: 'Faturamento por cliente',
            response_type: 'analise_financeira',
            response_types: ['analise_financeira'],
            renderer: 'renderAnaliseTexto',
            data_minimos: ['periodo'],
            quick_messages: ['Faturamento dos últimos 30 dias por cliente'],
            welcome_shortcuts: [
                { group: 'Relatórios', label: 'Faturamento por cliente', icon: '💰', message: 'Faturamento dos últimos 30 dias por cliente' },
            ],
            patterns: [/\bfaturamento\b.*\bcliente\b/i],
        },
        {
            id: 'servicos_mais_vendidos',
            label: 'Serviços mais vendidos',
            response_type: 'analise_financeira',
            response_types: ['analise_financeira'],
            renderer: 'renderAnaliseTexto',
            data_minimos: ['periodo'],
            quick_messages: ['Serviços mais vendidos nos últimos 90 dias'],
            welcome_shortcuts: [
                { group: 'Relatórios', label: 'Serviços mais vendidos', icon: '🏆', message: 'Serviços mais vendidos nos últimos 90 dias' },
            ],
            patterns: [/\bservi[cç]os?\b.*\bmais vendidos\b/i],
        },
        {
            id: 'relatorio_orcamentos_mes',
            label: 'Visão geral de orçamentos',
            response_type: 'orcamentos',
            response_types: ['orcamentos'],
            renderer: 'renderListaOrcamentos',
            data_minimos: ['periodo'],
            quick_messages: ['Relatório geral de orçamentos do mês'],
            welcome_shortcuts: [
                { group: 'Relatórios', label: 'Visão geral de orçamentos', icon: '📊', message: 'Relatório geral de orçamentos do mês' },
            ],
            patterns: [/\brelat[oó]rio\b.*\bor[çc]amentos?\b/i],
        },
        {
            id: 'agendamentos',
            label: 'Agendamentos',
            response_type: 'geral',
            response_types: ['geral'],
            renderer: 'resposta-direta',
            data_minimos: [],
            slash_commands: [
                { cmd: '/agendar', desc: 'Fazer novo agendamento', icon: '📅' },
                { cmd: '/agenda', desc: 'Ver agendamentos do dia', icon: '📆' },
            ],
            patterns: [/\bagenda(r|mentos?)\b/i],
        },
        {
            id: 'ajuda',
            label: 'Ajuda',
            response_type: 'geral',
            response_types: ['geral'],
            renderer: 'resposta-direta',
            data_minimos: [],
            slash_commands: [
                { cmd: '/ajuda', desc: 'Dúvidas sobre como usar o sistema', icon: '❓' },
            ],
            patterns: [/\bajuda\b|\bcomo usar\b/i],
        },
    ];

    const ASSISTENTE_ORCAMENTO_FOLLOWUPS = {
        orcamento_atualizado: [
            'Ver detalhes do {numero}',
            'Enviar {numero} por WhatsApp',
            'Enviar {numero} por e-mail',
            'Aprovar {numero}',
            'Duplicar {numero}',
            'Status do {numero}',
        ],
        default: [
            'Ver detalhes do {numero}',
            'Duplicar {numero}',
            'Simular desconto de 5% no {numero}',
            'Status do {numero}',
        ],
    };

    const ASSISTENTE_RESPONSE_UI_POLICY = {
        saldo_caixa: {
            actionStatusLabel: 'Saldo consultado',
            hasOwnBanner: false,
            skipFeedback: false,
            isRichResponse: true,
        },
        resumo_financeiro: {
            actionStatusLabel: 'Resumo financeiro gerado',
            hasOwnBanner: false,
            skipFeedback: false,
            isRichResponse: true,
        },
        orcamento_preview: {
            actionStatusLabel: 'Pré-visualização pronta',
            hasOwnBanner: false,
            skipFeedback: true,
            isRichResponse: true,
            isV2Card: true,
        },
        orcamento_criado: {
            actionStatusLabel: 'Orçamento criado',
            hasOwnBanner: true,
            skipFeedback: true,
            isRichResponse: true,
            isV2Card: true,
        },
        orcamento_atualizado: {
            actionStatusLabel: 'Orçamento atualizado',
            hasOwnBanner: true,
            skipFeedback: false,
            isRichResponse: true,
            isV2Card: true,
        },
        orcamento_card_unificado: {
            actionStatusLabel: '',
            hasOwnBanner: false,
            skipFeedback: false,
            isRichResponse: true,
            isV2Card: true,
        },
        registro_criado: {
            actionStatusLabel: 'Registro criado',
            hasOwnBanner: false,
            skipFeedback: true,
            isRichResponse: true,
            extraCardRenderer: 'renderRegistroCriadoCard',
        },
        operador_resultado: {
            actionStatusLabel: 'Ação executada',
            hasOwnBanner: false,
            skipFeedback: true,
            isRichResponse: false,
        },
        onboarding: {
            actionStatusLabel: '',
            hasOwnBanner: false,
            skipFeedback: true,
            isRichResponse: true,
        },
        analise_financeira: {
            actionStatusLabel: '',
            hasOwnBanner: false,
            skipFeedback: false,
            isRichResponse: true,
        },
        analise_conversao: {
            actionStatusLabel: '',
            hasOwnBanner: false,
            skipFeedback: false,
            isRichResponse: true,
        },
        sugestao_negocio: {
            actionStatusLabel: '',
            hasOwnBanner: false,
            skipFeedback: false,
            isRichResponse: true,
        },
        geral: {
            actionStatusLabel: '',
            hasOwnBanner: false,
            skipFeedback: false,
            isRichResponse: false,
        },
    };

    function cloneIntent(intent) {
        return {
            ...intent,
            data_minimos: Array.isArray(intent.data_minimos) ? [...intent.data_minimos] : [],
            response_types: Array.isArray(intent.response_types) ? [...intent.response_types] : [],
            quick_messages: Array.isArray(intent.quick_messages) ? [...intent.quick_messages] : [],
            quick_actions: Array.isArray(intent.quick_actions) ? [...intent.quick_actions] : [],
            slash_commands: Array.isArray(intent.slash_commands) ? intent.slash_commands.map((item) => ({ ...item })) : [],
            patterns: Array.isArray(intent.patterns) ? [...intent.patterns] : [],
        };
    }

    function getAssistenteIntentRegistry() {
        return ASSISTENTE_INTENT_REGISTRY.map(cloneIntent);
    }

    function getAssistenteSlashCommands() {
        return ASSISTENTE_INTENT_REGISTRY.flatMap((intent) => (
            Array.isArray(intent.slash_commands)
                ? intent.slash_commands.map((item) => ({ ...item, intent_id: intent.id, label: intent.label }))
                : []
        ));
    }

    function getAssistenteShortcutGroups() {
        const groups = [];
        ASSISTENTE_INTENT_REGISTRY.forEach((intent) => {
            (intent.welcome_shortcuts || []).forEach((item) => {
                let group = groups.find((entry) => entry.title === item.group);
                if (!group) {
                    group = { title: item.group, items: [] };
                    groups.push(group);
                }
                group.items.push({ ...item, intent_id: intent.id, label: intent.label });
            });
        });
        return groups;
    }

    function getAssistenteQuickActions() {
        return ASSISTENTE_INTENT_REGISTRY.flatMap((intent) => (
            Array.isArray(intent.quick_action_items)
                ? intent.quick_action_items.map((item) => ({ ...item, intent_id: intent.id, label: intent.label }))
                : []
        ));
    }

    function getAssistenteResponseUiPolicy(responseType) {
        const normalized = String(responseType || '').trim() || 'geral';
        const policy = ASSISTENTE_RESPONSE_UI_POLICY[normalized] || ASSISTENTE_RESPONSE_UI_POLICY.geral;
        return { ...policy };
    }

    function findAssistenteIntentByResponseType(responseType) {
        const normalized = String(responseType || '').trim();
        if (!normalized) return null;
        const matched = ASSISTENTE_INTENT_REGISTRY.find((intent) => (
            intent.response_type === normalized
            || (Array.isArray(intent.response_types) && intent.response_types.includes(normalized))
        ));
        return matched ? cloneIntent(matched) : null;
    }

    function findAssistenteIntentByLabel(label) {
        const normalized = String(label || '').trim().toLowerCase();
        if (!normalized) return null;
        const matched = ASSISTENTE_INTENT_REGISTRY.find((intent) => (
            String(intent.label || '').trim().toLowerCase() === normalized
            || String(intent.id || '').trim().toLowerCase() === normalized
        ));
        return matched ? cloneIntent(matched) : null;
    }

    function normalizeAssistenteResponseType({ responseType, intentDetected, dadosType } = {}) {
        const explicit = String(responseType || '').trim();
        const dados = String(dadosType || '').trim();
        const isGeneric = !explicit || explicit === 'geral' || explicit === 'analise_financeira';

        if (!isGeneric) {
            return explicit;
        }

        const intent = findAssistenteIntentByLabel(intentDetected);
        if (intent && intent.id) {
            return intent.id;
        }

        if (dados && dados !== 'geral') {
            return dados;
        }

        return explicit || dados || 'geral';
    }

    function getAssistenteOrcamentoFollowups(tipo, numero) {
        const numeroLabel = String(numero || '').trim() || 'este orçamento';
        const templates = ASSISTENTE_ORCAMENTO_FOLLOWUPS[tipo] || ASSISTENTE_ORCAMENTO_FOLLOWUPS.default;
        return templates.map((item) => item.replaceAll('{numero}', numeroLabel));
    }

    function buildAssistenteApprovalCommand(numero) {
        const numeroLimpo = String(numero || '').trim();
        return numeroLimpo ? `aprovar ${numeroLimpo}` : 'aprovar';
    }

    function buildAssistenteDebugIntentMeta({ userMessage, responseType, intentDetected = '', followups = [], rendererId = '' } = {}) {
        const requestIntent = matchAssistenteIntent(userMessage);
        const normalizedResponseType = normalizeAssistenteResponseType({ responseType, intentDetected });
        const responseIntent = findAssistenteIntentByResponseType(normalizedResponseType) || findAssistenteIntentByLabel(normalizedResponseType);
        const resolvedRenderer = String(rendererId || responseIntent?.renderer || '').trim() || 'desconhecido';
        return {
            request_intent: requestIntent ? {
                id: requestIntent.id,
                label: requestIntent.label,
            } : null,
            response_intent: responseIntent ? {
                id: responseIntent.id,
                label: responseIntent.label,
            } : null,
            response_type_normalized: normalizedResponseType || 'geral',
            renderer: {
                id: resolvedRenderer,
            },
            followups: Array.isArray(followups) ? [...followups] : [],
        };
    }

    function matchAssistenteIntent(text) {
        const source = String(text || '').trim();
        if (!source) return null;

        const slashMatch = source.toLowerCase().match(/(?:^|\s)(\/[^\s]+)/);
        if (slashMatch) {
            const slash = slashMatch[1];
            const slashIntent = ASSISTENTE_INTENT_REGISTRY.find((intent) => (
                Array.isArray(intent.slash_commands)
                && intent.slash_commands.some((item) => String(item.cmd || '').toLowerCase() === slash)
            ));
            return slashIntent ? cloneIntent(slashIntent) : null;
        }

        const matched = ASSISTENTE_INTENT_REGISTRY.find((intent) => (
            Array.isArray(intent.patterns)
            && intent.patterns.some((pattern) => pattern.test(source))
        ));
        return matched ? cloneIntent(matched) : null;
    }

    function parseAssistenteDraftInput(text) {
        const match = String(text || '').match(DRAFT_RE);
        if (!match || !match.groups) return null;
        return {
            cliente: match.groups.cliente.trim(),
            servico: match.groups.servico.trim(),
            preco: parseFloat(match.groups.preco.replace(',', '.')),
        };
    }

    const api = {
        getAssistenteIntentRegistry,
        getAssistenteSlashCommands,
        getAssistenteShortcutGroups,
        getAssistenteQuickActions,
        getAssistenteResponseUiPolicy,
        getAssistenteOrcamentoFollowups,
        buildAssistenteApprovalCommand,
        findAssistenteIntentByResponseType,
        normalizeAssistenteResponseType,
        buildAssistenteDebugIntentMeta,
        matchAssistenteIntent,
        parseAssistenteDraftInput,
        ASSISTENTE_INTENT_REGISTRY,
    };

    globalScope.getAssistenteIntentRegistry = getAssistenteIntentRegistry;
    globalScope.getAssistenteSlashCommands = getAssistenteSlashCommands;
    globalScope.getAssistenteShortcutGroups = getAssistenteShortcutGroups;
    globalScope.getAssistenteQuickActions = getAssistenteQuickActions;
    globalScope.getAssistenteResponseUiPolicy = getAssistenteResponseUiPolicy;
    globalScope.getAssistenteOrcamentoFollowups = getAssistenteOrcamentoFollowups;
    globalScope.buildAssistenteApprovalCommand = buildAssistenteApprovalCommand;
    globalScope.findAssistenteIntentByResponseType = findAssistenteIntentByResponseType;
    globalScope.normalizeAssistenteResponseType = normalizeAssistenteResponseType;
    globalScope.buildAssistenteDebugIntentMeta = buildAssistenteDebugIntentMeta;
    globalScope.matchAssistenteIntent = matchAssistenteIntent;
    globalScope.parseAssistenteDraftInput = parseAssistenteDraftInput;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
}(typeof window !== 'undefined' ? window : globalThis));
