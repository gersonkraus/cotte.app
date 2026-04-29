# QA - Sugestões proativas no Assistente IA

## Objetivo

Validar o frontend mínimo de insights proativos no Assistente COTTE sem alterar backend.

## Cenários manuais

1. Abrir `assistente-ia.html` com usuário autenticado e permissão de IA.
2. Confirmar que a página chama `GET /api/v1/ai/insights?limit=5` sem travar o chat em caso de erro.
3. Quando a API retornar insights, verificar que os cards aparecem dentro do welcome, abaixo dos atalhos.
4. Enviar uma pergunta cuja resposta tenha `dados.insights` e confirmar que os cards aparecem junto da resposta.
5. Clicar em `Usar` em um card e verificar que o texto da ação preenche `#messageInput` e recebe foco, sem envio automático.
6. Clicar em `Dispensar` e verificar que o card some sem remover a conversa.
7. Confirmar no Network que cliques enviam `POST /api/v1/ai/insights/feedback` com `insight_id`, `acao` e `sessao_id` quando disponível.
8. Reduzir a tela para largura mobile e confirmar que cards e CTAs ficam em coluna única sem quebrar o layout.

## Validações automatizadas usadas nesta task

- `node cotte-frontend/js/assistente-ia-insights.test.js`
- `node --check cotte-frontend/js/assistente-ia-insights.js`
- `node --check cotte-frontend/js/assistente-ia.js`
- `node --check cotte-frontend/js/assistente-ia-render.js`
- `rtk pytest tests/test_assistente_unificado_v2.py -q -k 'insight or insights'`
- `rtk pytest tests/test_ai_assistente_contract.py -q -k 'insights'`

## Observações

- O CTA apenas preenche o input por segurança operacional.
- Falhas de busca, renderização ou feedback devem aparecer apenas como `console.warn` discreto.
- Os cards usam borda completa de `1px`; não há barra lateral de destaque.
