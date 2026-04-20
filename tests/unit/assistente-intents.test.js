const assert = require('assert');

const {
  getAssistenteSlashCommands,
  getAssistenteShortcutGroups,
  getAssistenteQuickActions,
  getAssistenteOrcamentoFollowups,
  getAssistenteResponseUiPolicy,
  buildAssistenteApprovalCommand,
  buildAssistenteDebugIntentMeta,
  normalizeAssistenteResponseType,
  matchAssistenteIntent,
  parseAssistenteDraftInput,
} = require('../../sistema/cotte-frontend/js/assistente-ia-intents.js');

const slashCommands = getAssistenteSlashCommands();
assert.ok(Array.isArray(slashCommands), 'Slash commands devem ser retornados em lista');
assert.ok(slashCommands.some((item) => item.cmd === '/caixa'), 'Deve expor /caixa');
assert.ok(slashCommands.some((item) => item.cmd === '/resumo'), 'Deve expor /resumo');
assert.ok(slashCommands.some((item) => item.cmd === '/orcamento'), 'Deve expor /orcamento');

const shortcutGroups = getAssistenteShortcutGroups();
assert.ok(Array.isArray(shortcutGroups), 'Os grupos de atalhos devem vir em lista');
assert.ok(shortcutGroups.some((group) => group.title === 'Financeiro'), 'Deve expor o grupo Financeiro');
assert.ok(shortcutGroups.some((group) => group.title === 'Relatórios'), 'Deve expor o grupo Relatórios');
assert.ok(
  shortcutGroups.some((group) => group.items.some((item) => item.message === 'Resumo financeiro do mês')),
  'Deve manter o atalho de resumo financeiro do mês'
);

const quickActions = getAssistenteQuickActions();
assert.ok(Array.isArray(quickActions), 'Quick actions devem vir em lista');
assert.ok(quickActions.some((item) => item.message === 'Qual meu saldo atual?'), 'Deve manter quick action de saldo');
assert.ok(quickActions.some((item) => item.message === 'Listar meus clientes'), 'Deve manter quick action de clientes');

const policySaldo = getAssistenteResponseUiPolicy('saldo_caixa');
assert.strictEqual(policySaldo.actionStatusLabel, 'Saldo consultado', 'Deve centralizar o chip de status de saldo');
assert.strictEqual(policySaldo.hasOwnBanner, false, 'Saldo não deve marcar banner próprio');
assert.strictEqual(policySaldo.skipFeedback, false, 'Saldo deve manter feedback');
assert.strictEqual(policySaldo.isRichResponse, true, 'Saldo deve ser tratado como resposta rica');

const policyOrcamentoCriado = getAssistenteResponseUiPolicy('orcamento_criado');
assert.strictEqual(policyOrcamentoCriado.actionStatusLabel, 'Orçamento criado', 'Deve centralizar o chip de status de orçamento criado');
assert.strictEqual(policyOrcamentoCriado.hasOwnBanner, true, 'Orçamento criado deve marcar banner próprio');
assert.strictEqual(policyOrcamentoCriado.skipFeedback, true, 'Orçamento criado deve pular barra de feedback');
assert.strictEqual(policyOrcamentoCriado.isRichResponse, true, 'Orçamento criado deve ser tratado como resposta rica');

const policyRegistroCriado = getAssistenteResponseUiPolicy('registro_criado');
assert.strictEqual(policyRegistroCriado.actionStatusLabel, 'Registro criado', 'Deve centralizar o chip de status de registro criado');
assert.strictEqual(policyRegistroCriado.extraCardRenderer, 'renderRegistroCriadoCard', 'Registro criado deve centralizar o renderer do card de confirmação no policy');

const policyAjuda = getAssistenteResponseUiPolicy('geral');
assert.strictEqual(policyAjuda.actionStatusLabel, '', 'Tipo geral não deve inventar status');
assert.strictEqual(policyAjuda.skipFeedback, false, 'Tipo geral não deve bloquear feedback sozinho');

const followupsAtualizado = getAssistenteOrcamentoFollowups('orcamento_atualizado', 'ORC-123');
assert.ok(followupsAtualizado.includes('Enviar ORC-123 por WhatsApp'), 'Deve expor follow-up de WhatsApp para orçamento atualizado');
assert.ok(followupsAtualizado.includes('Aprovar ORC-123'), 'Deve expor follow-up de aprovação para orçamento atualizado');

const followupsDefault = getAssistenteOrcamentoFollowups('desconhecido', 'ORC-123');
assert.ok(followupsDefault.includes('Gerar versão premium do ORC-123'), 'Deve usar fallback default de follow-up');

assert.strictEqual(buildAssistenteApprovalCommand('ORC-123'), 'aprovar ORC-123', 'Deve centralizar alias de aprovação');
assert.strictEqual(buildAssistenteApprovalCommand(''), 'aprovar', 'Deve manter fallback seguro para aprovação');

const debugMeta = buildAssistenteDebugIntentMeta({
  userMessage: 'Resumo financeiro do mês',
  responseType: 'resumo_financeiro',
  intentDetected: 'Resumo financeiro',
  followups: ['Ver detalhes do ORC-123'],
});
assert.strictEqual(debugMeta.request_intent.label, 'Resumo financeiro', 'Deve resolver intent da pergunta no debug');
assert.strictEqual(debugMeta.response_intent.label, 'Resumo financeiro', 'Deve resolver intent da resposta no debug');
assert.strictEqual(debugMeta.renderer.id, 'renderAnaliseTexto', 'Deve informar o renderer esperado no debug');
assert.deepStrictEqual(debugMeta.followups, ['Ver detalhes do ORC-123'], 'Deve preservar follow-ups gerados no debug');

const genericDebugMeta = buildAssistenteDebugIntentMeta({
  userMessage: 'Quem está devendo?',
  responseType: 'geral',
  intentDetected: 'Clientes em atraso',
  followups: [],
});
assert.strictEqual(genericDebugMeta.response_type_normalized, 'clientes_atraso', 'Deve normalizar o tipo genérico no debug');
assert.strictEqual(genericDebugMeta.response_intent.label, 'Clientes em atraso', 'Deve refletir a intent refinada no debug');

assert.strictEqual(
  normalizeAssistenteResponseType({
    responseType: 'geral',
    intentDetected: 'Clientes em atraso',
    dadosType: '',
  }),
  'clientes_atraso',
  'Deve priorizar a intent detectada quando o tipo vier genérico'
);

assert.strictEqual(
  normalizeAssistenteResponseType({
    responseType: 'analise_financeira',
    intentDetected: 'Taxa de conversão',
    dadosType: '',
  }),
  'taxa_conversao',
  'Deve refinar tipo genérico analítico usando a intent detectada'
);

assert.strictEqual(
  normalizeAssistenteResponseType({
    responseType: 'saldo_caixa',
    intentDetected: 'Resumo financeiro',
    dadosType: '',
  }),
  'saldo_caixa',
  'Não deve sobrescrever tipo específico já conhecido'
);

const inadimplencia = matchAssistenteIntent('Quem está devendo?');
assert.ok(inadimplencia, 'Deve reconhecer intenção de inadimplência');
assert.strictEqual(inadimplencia.label, 'Clientes em atraso');

const novoOrcamento = matchAssistenteIntent('Gerar orçamento para cliente');
assert.ok(novoOrcamento, 'Deve reconhecer intenção de novo orçamento');
assert.strictEqual(novoOrcamento.label, 'Novo orçamento');

const draft = parseAssistenteDraftInput('orçamento para Maria Silva de limpeza técnica por R$ 350,50');
assert.deepStrictEqual(draft, {
  cliente: 'Maria Silva',
  servico: 'limpeza técnica',
  preco: 350.5,
});

assert.strictEqual(parseAssistenteDraftInput('quero ver meu caixa'), null, 'Não deve extrair rascunho fora do padrão');

console.log('assistente-intents: ok');
