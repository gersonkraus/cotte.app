# Analise detalhada de consumo de tokens no assistente IA

## Contexto do problema

O assistente vem registrando consumo muito alto de tokens em perguntas que deveriam ser relativamente baratas, por exemplo:

- "Resumo financeiro do mes"
- "Clientes devendo"

Casos observados chegam em ~25k de `input_tokens` por resposta, o que aumenta custo, latencia e risco de comportamento inconsistente.

## Resumo executivo

O custo elevado nao vem de um unico erro isolado. Ele ocorre por **combinacao de arquitetura de prompt + loop de tool-calling + payloads grandes de tools + retries**.

Em termos praticos:

1. perguntas financeiras geralmente caem em estrategia `standard` (nao `minimal`);
2. isso ativa contexto grande e conjunto amplo de tools;
3. cada iteracao do loop reenvia `messages` inteiras + schemas das tools;
4. os resultados de tools entram como JSON completo (`role: tool`);
5. em alguns casos ocorre retry com `full_tools_payload`, somando nova chamada cara.

Resultado: crescimento cumulativo de tokens dentro da mesma requisicao.

---

## Evidencias tecnicas no codigo

### 1) Estrategia de prompt para "resumo financeiro"

No classificador, "resumo financeiro" e mapeado para dominio financeiro/dashboard. No fluxo v2, a estrategia `minimal` so ocorre para intencoes especificas e mensagens curtas. Fora disso, entra `standard`.

Arquivo:
- `sistema/app/services/cotte_ai_hub.py`
- `sistema/app/services/ai_intention_classifier.py`

Impacto:
- `standard` tende a carregar mais contexto, historico maior e perfil de tools mais amplo.

### 2) Selecao de tools ainda cara fora do `minimal`

No metodo `_v2_selected_tool_names_for_message`, quando `prompt_strategy != "minimal"` retorna perfil `full`.

Arquivo:
- `sistema/app/services/cotte_ai_hub.py`

Impacto:
- para varias perguntas operacionais, o LLM recebe catalogo grande de tools (schema de funcoes) mesmo quando poucas seriam necessarias.

### 3) Multiplicacao de contexto no loop

No loop v2 (`_V2_MAX_ITER = 5`), cada chamada de `ia_service.chat(...)` reenvia:

- mensagens `system`;
- historico;
- mensagens anteriores `assistant`;
- mensagens `tool`;
- parametro `tools`.

Arquivo:
- `sistema/app/services/cotte_ai_hub.py`

Impacto:
- custo de prompt cresce a cada iteracao, nao de forma linear simples.

### 4) Payload completo de tool volta para o LLM

`ToolResult.to_llm_payload()` retorna `self.data` integral para status `ok`, e isso e serializado em JSON no `messages.append({"role":"tool", ...})`.

Arquivos:
- `sistema/app/services/tool_executor.py`
- `sistema/app/services/cotte_ai_hub.py`

Impacto:
- listagens com muitos itens (movimentacoes, orcamentos, etc.) aumentam fortemente o tamanho de prompt da iteracao seguinte.

### 5) Retry com tools completas

Quando ha perfil reduzido e a resposta sinaliza incapacidade, o fluxo pode fazer nova chamada com `full_tools_payload`.

Arquivo:
- `sistema/app/services/cotte_ai_hub.py`

Impacto:
- dobra (ou quase dobra) custo daquela decisao dentro da mesma requisicao.

### 6) Acumulo de tokens por iteracao

`total_in` e `total_out` sao acumulados por chamada de `chat` ao longo do loop. Logo, 20k+ pode refletir soma de varias chamadas internas no mesmo turno.

Arquivo:
- `sistema/app/services/cotte_ai_hub.py`

### 7) Catalogo operacional e amplo por definicao

A policy da engine operacional inclui muitas tools de leitura e escrita. Mesmo filtrado por engine, o baseline permanece grande quando se usa perfil `full`.

Arquivo:
- `sistema/app/services/assistant_engine_registry.py`

---

## O que foi feito errado (raiz de desenho)

1. **Acoplamento forte entre estrategia de prompt e tamanho de contexto**  
   Perguntas de resumo financeiro acabam no caminho pesado, sem uma versao enxuta dedicada.

2. **Foco de otimizacao concentrado no `minimal`**  
   A reducao dinamica de tools ajudou conversa simples, mas o problema principal aparece em perguntas de negocio (`standard`).

3. **Transporte de dados de tool sem compactacao para o LLM**  
   O LLM recebe mais dados brutos do que precisa para raciocinar.

4. **Retry caro sem budget explicito de tokens**  
   O fallback prioriza robustez, mas sem teto de custo por fase/turno.

5. **Ausencia de fast-path deterministico para intents recorrentes de resumo**  
   Casos de alta frequencia continuam passando por orquestracao generica de tools.

---

## Melhor forma de ajustar sem perder desempenho e funcionalidades

A estrategia recomendada e **incremental**, preservando contratos e comportamento da UI.

## Principios

- manter mesmas capacidades funcionais (consulta, listagem, acao com confirmacao);
- reduzir custo de prompt antes de reduzir capacidade;
- aplicar fallback apenas quando necessario e com limites claros;
- instrumentar tudo por fase para evitar regressao silenciosa.

## Ajustes recomendados (ordem de prioridade)

### A) Scoped tools tambem para `standard`

Expandir selecao dinamica para perguntas de negocio frequentes, em vez de usar `full` por padrao.

Exemplo para "resumo financeiro do mes":
- permitir inicialmente: `obter_saldo_caixa`, `listar_movimentacoes_financeiras`, `listar_despesas`;
- incluir `listar_orcamentos` somente se a resposta realmente exigir esse bloco.

Beneficio:
- corta grande parte do custo fixo dos schemas de tools.

### B) Compactacao do payload de tools para o LLM

Antes de inserir `role: tool`, transformar `result.data` em payload de raciocinio:

- `summary`: agregados principais;
- `rows_preview`: top-N (ex. 10);
- `counts` e `totals`;
- manter payload completo apenas para renderer/UI, nao para a proxima chamada do LLM.

Beneficio:
- reduz drasticamente crescimento de `messages` por iteracao.

### C) Fast-path deterministico para resumos financeiros e inadimplencia

Adicionar caminho de baixa latencia para intents recorrentes:

- "resumo financeiro do mes";
- "clientes devendo";
- "contas vencidas".

Fluxo:
- backend agrega dados diretamente;
- opcionalmente uma unica chamada LLM curta para "narrativa";
- sem loop de tool-calling para casos previsiveis.

Beneficio:
- maior previsibilidade de custo e tempo de resposta.

### D) Budget de tokens por turno e por fase

Definir limites operacionais:

- budget fase `tool_loop`;
- budget total da requisicao;
- bloqueio de retry para `full_tools_payload` quando budget estiver perto do limite.

Beneficio:
- evita picos de 20k+ em cenarios repetitivos.

### E) Gating de contexto extra

Condicionar memoria semantica, RAG e blocos adaptativos por tipo de pergunta:

- perguntas factuais simples: contexto minimo;
- perguntas analiticas amplas: contexto progressivo.

Beneficio:
- remove custo fixo desnecessario sem perder cobertura quando realmente precisa.

---

## Riscos e como mitigar

1. **Risco:** resposta perder abrangencia por toolset reduzido.  
   **Mitigacao:** fallback controlado por regra + testes de regressao por intent.

2. **Risco:** sumario de tool ocultar detalhe importante.  
   **Mitigacao:** manter campos criticos obrigatorios no `summary` e preservar payload completo para UI/auditoria.

3. **Risco:** fast-path ficar divergente do fluxo principal.  
   **Mitigacao:** shared helpers de agregacao e contrato unico de resposta.

4. **Risco:** cortar contexto em excesso para perguntas ambiguas.  
   **Mitigacao:** escalonamento progressivo (contexto aumenta por necessidade, nao por default).

---

## Plano de rollout recomendado

## Fase 1 - Observabilidade e baseline (baixo risco)

- adicionar metricas por fase:
  - `tokens_prompt_pre_tools`
  - `tokens_tool_loop`
  - `tokens_retry_full_tools`
  - `tokens_final_stream`
- registrar `tool_count`, `tool_profile`, `iterations_count`.

Objetivo:
- medir onde o token explode com precisao por intent.

## Fase 2 - Scoped tools para `standard`

- ativar feature flag para 10% dos tenants;
- aplicar apenas em intents financeiras e inadimplencia.

Criterios:
- queda relevante de `input_tokens`;
- sem aumento de erro funcional.

## Fase 3 - Compactacao de payload de tool

- enviar ao LLM apenas sumario estruturado + top-N;
- manter dados completos no renderer/backend.

Criterios:
- reducao adicional de tokens;
- mesma qualidade das respostas.

## Fase 4 - Fast-path deterministico

- implementar para:
  - resumo financeiro do mes;
  - clientes devendo.

Criterios:
- latencia menor;
- custo mais previsivel;
- qualidade igual ou melhor.

---

## Metricas de aceite

- `input_tokens` p95 para intents de resumo financeiro reduzido em pelo menos 40-60%;
- `iterations_count` medio reduzido para <= 2 nesses intents;
- taxa de fallback para `full_tools_payload` controlada (ex.: < 10%);
- regressao funcional zero nos fluxos criticos:
  - saldo;
  - listar orcamentos;
  - clientes devendo;
  - acoes com confirmacao.

---

## Conclusao

O consumo alto de tokens e consequencia de um desenho que combina:

- estrategia `standard` pesada para perguntas frequentes de negocio;
- orquestracao de tools com payloads grandes e cumulativos;
- retries caros.

A melhor correcao **sem perder desempenho e funcionalidades** e:

1. expandir scoped tools para `standard`,
2. compactar payload de tool para raciocinio do LLM,
3. criar fast-path deterministico para resumos financeiros/inadimplencia,
4. controlar custo com budget e observabilidade por fase.

Esse caminho preserva comportamento atual, reduz custo de forma robusta e melhora latencia/estabilidade do assistente.
