---
title: Plano Assistente V2
tags:
  - roadmap
prioridade: media
status: documentado
---
---
title: Plano Assistente V2
tags:
  - roadmap
prioridade: media
status: documentado
---
# Plano — Assistente COTTE com Tool Use (Function Calling)

## Contexto

Hoje o assistente IA (`cotte_ai_hub.py`) usa **roteamento hardcoded por intent**: um classificador (regex + Haiku) decide entre `CRIAR_ORCAMENTO`, `SALDO_RAPIDO`, `OPERADOR`, `CONVERSACAO`, etc., e o backend chama o service certo manualmente. Isso limita o assistente a fluxos pré-codificados e cria fricção a cada nova capacidade.

O objetivo do Gerson é ter um assistente **verdadeiramente autônomo**, que entenda o sistema inteiro e execute tarefas (cadastrar material, lançar movimentação financeira, criar orçamento, aprovar, listar clientes, agendar etc.) sem precisar de intent hardcoded para cada caso. A solução natural é **Tool Use / Function Calling** nativo do LLM.

> **Modelo escolhido**: **GPT‑4o‑mini** (decisão do Gerson). Isso implica:
> - Adicionar dependência `openai>=1.40` em `requirements.txt` e `OPENAI_API_KEY` em `.env.example` / Railway.
> - Criar `app/services/openai_service.py` paralelo ao `ia_service.py` (não substituir — Claude continua ativo em outros fluxos como `cotte_ai_hub` conversacional, PDF IA, etc.).
> - Usar formato OpenAI de tools: `{"type":"function","function":{"name","description","parameters":JSONSchema}}` e loop de `tool_calls` na resposta.
> - Atualizar `memory/decisions.md` registrando a exceção à stack oficial (IA conversacional agora é dual: Claude + OpenAI).
> - Cuidado: respostas de GPT‑4o‑mini com tool use têm formato diferente (`choices[0].message.tool_calls`) — encapsular bem no executor para isolar do resto do sistema.

## Análise do plano original do Gerson

| Item proposto | Avaliação | Melhoria sugerida |
|---|---|---|
| Definir tools JSON mapeando services existentes | ✅ correto | Centralizar em **`app/services/ai_tools/`** (um arquivo por domínio: financeiro, orcamento, catalogo, cliente, agendamento). Cada tool = `{schema, handler, permission, idempotent}`. |
| Expandir `ai_hub.py` para tool calls + permissões | ✅ correto | Não inflar o router. Criar **`tool_executor.py`** (service) que recebe `tool_call`, valida permissão via `exigir_permissao`, valida ownership, executa, retorna resultado serializável. Router só orquestra. |
| Atualizar `manual_sistema.md` com tools e regras | ⚠️ parcial | Com Tool Use, o LLM já recebe os schemas via API — não precisa repetir tudo no prompt. O manual deve focar em **regras de negócio, tom, exemplos de uso e limites** (ex: "nunca aprove orçamento sem ID explícito"). Schemas ficam no código. |
| Streaming + "executando…" + botões de confirmação | ✅ excelente | Adicionar **dois níveis de tool**: `safe` (executa direto: listar, consultar, calcular) e `confirmacao_obrigatoria` (retorna proposta + botão; só executa após callback do usuário). Padronizar resposta do backend com `pending_action: {tool, args, descricao}`. |
| Migrar para GPT‑4o‑mini | ❌ não recomendado | Manter Anthropic Claude (ver nota acima). |

## O que está faltando no plano original

1. **Loop multi-turno de tool calls** — Claude pode chamar várias tools em sequência ("liste clientes em atraso → para cada um, calcule saldo → resuma"). O executor precisa rodar em loop até `stop_reason != tool_use`, com **limite máximo (ex: 5 iterações)** para evitar runaway cost.
2. **Cache de resultados de tools read-only** — `listar_clientes`, `saldo_caixa`, etc. podem reusar `SimpleCache` existente (TTL 60s) por `(empresa_id, tool, args_hash)`. Reduz custo significativamente.
3. **Auditoria** — toda execução de tool deve gerar log estruturado (`tool_calls_log`) com `usuario_id, empresa_id, tool, args, resultado, latencia_ms`. Essencial para debug e billing.
4. **Telemetria de custo** — registrar `input_tokens + output_tokens + tool_calls_count` por sessão. Já temos campo similar — estender.
5. **Confirmação de ações destrutivas no frontend** — não basta retornar `pending_action`; o `assistente-ia.js` precisa renderizar **card com botões "Confirmar / Cancelar"** que reenviam mensagem com `confirmation_token`. Aproveitar padrão de cards interativos já implementado (memória `project_assistente_interatividade.md`).
6. **Fallback gracioso** — se uma tool falha, não vazar stack trace para o LLM. Retornar `{error: "mensagem amigável", code}` para Claude reformular.
7. **Coexistência com fluxo atual** — não jogar fora `cotte_ai_hub.py`. Adicionar Tool Use como **caminho preferencial** com feature flag (`USE_TOOL_CALLING=true` em `.env`), mantendo fallback ao roteamento por intent enquanto valida em produção.
8. **Schemas auto-gerados de Pydantic** — vários services já têm schemas Pydantic. Usar `model_json_schema()` para gerar tool definitions automaticamente — evita drift entre schema da API e schema da tool.

## Arquitetura proposta

```
Frontend (assistente-ia.js)
   │ POST /ai/assistente {mensagem, sessao_id, confirmation_token?}
   ▼
ai_hub.py (router fino)
   │
   ▼
cotte_ai_hub.assistente_unificado_v2()
   │   ├─ Carrega histórico (SessionStore)
   │   ├─ Carrega tools registradas (ai_tools/__init__.py)
   │   └─ Loop:
   │        ├─ Claude.messages.create(messages, tools=...)
   │        ├─ se stop_reason == "tool_use":
   │        │     ├─ tool_executor.execute(tool_call, usuario_atual)
   │        │     │     ├─ valida permissão
   │        │     │     ├─ valida ownership
   │        │     │     ├─ se destrutivo + sem token → retorna pending_action
   │        │     │     └─ executa service real
   │        │     └─ append tool_result ao histórico
   │        └─ se stop_reason == "end_turn": retorna texto final
   │
   ▼
AIResponse {resposta, pending_action?, tool_trace[]}
```

## Tools mínimas para o MVP (Fase 1)

Foco em **leitura ampla + 3 escritas seguras**, valida o loop antes de expandir:

- `listar_orcamentos(status?, cliente_id?, periodo?)`
- `obter_orcamento(id)`
- `listar_clientes(busca?)`
- `obter_saldo_caixa(periodo?)`
- `listar_movimentacoes_financeiras(tipo?, periodo?)`
- `listar_materiais(busca?)`
- `criar_movimentacao_financeira(tipo, valor, descricao, ...)` — **destrutiva, exige confirmação**
- `criar_cliente(nome, telefone, email?)` — destrutiva, exige confirmação
- `criar_orcamento(cliente, itens[])` — destrutiva, exige confirmação

Fase 2 (após validação): aprovar/recusar orçamento, enviar WhatsApp, criar agendamento, cadastrar material, gerar PDF.

## Arquivos a criar / modificar

**Novos:**
- `sistema/app/services/ai_tools/__init__.py` — registry central
- `sistema/app/services/ai_tools/financeiro_tools.py`
- `sistema/app/services/ai_tools/orcamento_tools.py`
- `sistema/app/services/ai_tools/cliente_tools.py`
- `sistema/app/services/ai_tools/catalogo_tools.py`
- `sistema/app/services/tool_executor.py` — execução + permissões + auditoria
- `sistema/app/models/tool_call_log.py` + migration Alembic
- `docs/tecnico/assistente-tool-use.md` — documentação técnica

**Modificar:**
- `sistema/app/routers/ai_hub.py` — adicionar suporte a `confirmation_token`, branch via feature flag
- `sistema/app/services/cotte_ai_hub.py` — nova função `assistente_unificado_v2()` paralela à atual
- `sistema/app/services/ia_service.py` — wrapper para `messages.create` com `tools=`
- `sistema/app/services/prompts/manual_sistema.md` — adicionar seção "Como o assistente age" + regras de negócio (NÃO duplicar schemas)
- `sistema/cotte-frontend/assistente-ia.html` + `js/assistente-ia.js` — renderização de cards de confirmação, indicador "executando ferramenta…", suporte a `pending_action`
- `sistema/.env.example` — `USE_TOOL_CALLING=true`

## Funções/utilitários existentes a reusar

- `app/services/cotte_context_builder.py` — `SessionStore` (histórico de conversa)
- `app/services/ai_intention_classifier.py` — pode virar fallback quando feature flag desligada
- `app/core/permissions.py` — `exigir_permissao`, `verificar_ownership`
- `app/services/cache_service.py` (ou `SimpleCache`) — cache de tools read-only
- Schemas Pydantic existentes em `app/schemas/` — gerar tool definitions via `model_json_schema()`
- Padrão de cards interativos existente (memória `project_assistente_interatividade.md`)

## Verificação end-to-end

1. **Unitário**: pytest em `tool_executor.py` cobrindo: permissão negada, ownership falho, tool inexistente, idempotência, ação destrutiva sem token retorna pending.
2. **Integração**: pytest disparando `assistente_unificado_v2()` com mock do Claude retornando tool_use → tool_result → end_turn. Validar histórico final.
3. **Manual no sistema** (Playwright ou navegador):
   - "Quanto tenho em caixa?" → deve chamar `obter_saldo_caixa`, sem confirmação.
   - "Liste meus 5 últimos orçamentos" → `listar_orcamentos(limit=5)`.
   - "Crie um cliente João, telefone 4999..." → retorna card de confirmação → confirmar → cliente criado.
   - "Aprovar orçamento" (sem ID) → assistente pergunta o ID (não executa).
4. **Logs**: verificar `tool_call_log` populado e `ai_costs` somando tokens.
5. **Rollback**: setar `USE_TOOL_CALLING=false` deve reverter ao fluxo antigo sem regressão.

## Riscos principais

- **Custo**: tool use multiplica chamadas (~2-4x). Mitigação: cache + Haiku para classificação inicial + limite de iterações.
- **Latência**: cada tool call adiciona ~1-2s. Mitigação: streaming na resposta final + indicador visual "executando…".
- **Permissões mal validadas**: maior risco de segurança. Mitigação: **toda tool obrigatoriamente passa por `tool_executor`** — proibir chamada direta. Test coverage alto nesse módulo.
- **LLM inventando tools / parâmetros** ("hallucination"): Claude é robusto, mas validar args com Pydantic antes de executar. Erros voltam para o LLM corrigir.






# Plano — Assistente COTTE com Tool Use (Function Calling)

## Contexto

Hoje `assistente_unificado()` em `sistema/app/services/cotte_ai_hub.py:1488` roteia mensagens via classificador de intenção (`ai_intention_classifier`) para handlers hardcoded (`CRIAR_ORCAMENTO`, `SALDO_RAPIDO`, `OPERADOR`, `ONBOARDING`, `CONVERSACAO`). Cada nova capacidade exige código novo no roteador. O objetivo é permitir que o LLM decida e execute ações via **Tool Use nativo do Claude**, mantendo guardrails (permissões, ownership, confirmação de ações destrutivas, auditoria).

> **Decisão de modelo**: introduzir **OpenAI (GPT‑4o‑mini)** como provider alternativo, atrás de feature flag `AI_PROVIDER=openai|anthropic` (default `anthropic`). Migração faseada por caso de uso, com testes de regressão comparando respostas entre os dois providers nos prompts reais do sistema. Claude permanece como fallback até validação completa.

## Inventário de chamadas Anthropic (estado atual)

| Arquivo:linha | Função | Modelo | Uso | Fase migração |
|---|---|---|---|---|
| `app/services/ia_service.py:70` | `interpretar_mensagem` | Sonnet | extrai dados de orçamento de texto livre | Fase 2 |
| `app/services/ia_service.py:99` | `interpretar_comando_operador` | Haiku | classifica comando | Fase 2 |
| `app/services/ia_service.py:117` | `gerar_resposta_bot` | Sonnet | resposta WhatsApp bot | Fase 3 |
| `app/services/ia_service.py:140` | `interpretar_tabela_catalogo` | Sonnet | parse de planilha | Fase 3 |
| `app/services/ia_service.py:190` | `analisar_leads` | Sonnet | qualificação de leads | Fase 3 |
| `app/services/ai_intention_classifier.py:641` | classificador Haiku | Haiku | fallback de intenção | Fase 2 |
| `app/services/cotte_ai_hub.py:830` | `processar` | Sonnet | resposta estruturada por módulo | Fase 2 |
| `app/services/cotte_ai_hub.py:970` | `conversar` | Sonnet | conversação genérica | Fase 2 |
| `app/services/cotte_ai_hub.py:1619` | `assistente_unificado` | Sonnet | endpoint principal `/ai/assistente` | **Fase 1 (este PR)** |
| `tests/test_ia_orcamentos.py` | mocks | — | atualizar para `ai_provider` |
| `requirements.txt` | dep `anthropic` | — | manter, adicionar `openai>=1.40` | Fase 1 |
| `.env.example` | `ANTHROPIC_API_KEY` | — | adicionar `OPENAI_API_KEY` e `AI_PROVIDER` | Fase 1 |

## Tabela de equivalência por caso de uso

| Caso de uso | Hoje | Alvo | Justificativa |
|---|---|---|---|
| Tool use no /assistente | Sonnet | `gpt-4o-mini` | custo ~5x menor, function calling maduro |
| Classificação de intenção | Haiku | `gpt-4o-mini` | unificar provider |
| Extração JSON estruturado | Sonnet | `gpt-4o-mini` + `response_format=json_schema` | structured outputs garantidos |
| Resposta livre WhatsApp | Sonnet | `gpt-4o-mini` | qualidade equivalente em PT-BR |
| Tarefas pesadas (PDF IA) | Sonnet | **manter Sonnet** | qualidade superior em raciocínio longo |

## Estratégia de migração faseada

Fase 1 (este PR): abstração de provider + tool use no /assistente atrás de flag.
Fase 2: migrar ia_service + classifier + cotte_ai_hub conversacional.
Fase 3: migrar bot WhatsApp, extrações JSON, leads.
Fase 4: remover Sonnet onde regressão validar.

Rollback a qualquer momento: `AI_PROVIDER=anthropic` e/ou `USE_TOOL_CALLING=false`.

**Checkpoints entre fases**: suite de regressão verde; custo/latência medidos em produção por 7 dias; aprovação do Gerson.

## Camada de abstração de provider

Novo módulo `sistema/app/services/ai_provider.py`:

- `class AIProvider(Protocol)` com `chat(messages, system, tools=None, max_tokens=...) -> AIProviderResponse` e `stream_chat(...)` (stub).
- `AIProviderResponse` normaliza: `text`, `tool_calls: list[{id,name,arguments}]`, `stop_reason: Literal["end_turn","tool_use","max_tokens","error"]`, `usage: {input_tokens,output_tokens}`.
- `AnthropicProvider` — wrapper sobre `client.messages.create` (reusa `client` global de `cotte_ai_hub.py:46`).
- `OpenAIProvider` — wrapper sobre `openai.OpenAI().chat.completions.create`. Converte tools Claude → OpenAI automaticamente.
- `get_provider(override: str|None = None) -> AIProvider` lê `AI_PROVIDER` do env.

`tool_executor` e `assistente_unificado_v2` consomem **somente** `AIProvider`.

## Fase 1 — MVP (escopo desta entrega)

Caminho Tool Use atrás de feature flag, com tools de leitura e 3 escritas confirmáveis. Fluxo legado intocado.

### Arquivos novos

- `sistema/app/services/ai_tools/__init__.py` — `REGISTRY: dict[str, ToolSpec]`, `claude_tools_payload()`.
- `sistema/app/services/ai_tools/_base.py` — `ToolSpec(name, description, input_schema, handler, destrutiva, cacheable_ttl)`.
- `sistema/app/services/ai_tools/financeiro_tools.py` — `obter_saldo_caixa`, `listar_movimentacoes_financeiras`, `criar_movimentacao_financeira` (destrutiva).
- `sistema/app/services/ai_tools/orcamento_tools.py` — `listar_orcamentos`, `obter_orcamento`.
- `sistema/app/services/ai_tools/cliente_tools.py` — `listar_clientes`, `criar_cliente` (destrutiva).
- `sistema/app/services/ai_tools/catalogo_tools.py` — `listar_materiais`.
- `sistema/app/services/tool_executor.py` — `async execute(tool_call, *, db, current_user, confirmation_token)`. Centraliza: lookup no REGISTRY, validação Pydantic dos `input`, `exigir_permissao` (real em `app/core/auth.py:227`), `verificar_ownership` (`app/core/auth.py:301`), checagem de `confirmation_token`, execução, captura de exceção → `{"error","code"}`, persistência em `ToolCallLog`.
- `sistema/app/models/tool_call_log.py` — SQLAlchemy: `id, empresa_id, usuario_id, sessao_id, tool, args_json, resultado_json, status, latencia_ms, input_tokens, output_tokens, criado_em`.
- `sistema/alembic/versions/<nova>_tool_call_log.py`.

### Arquivos modificados

- `sistema/app/services/cotte_ai_hub.py`
  - Adicionar `assistente_unificado_v2()` paralelo (não tocar no original). Reusa `SessionStore` e `client`.
  - Loop: monta `messages`, injeta data/hora no `system`, chama `client.messages.create(model=SONNET, max_tokens=1024, system=SYSTEM_PROMPT_TOOLS, tools=claude_tools_payload(), messages=messages)`. Enquanto `stop_reason == "tool_use"`: itera blocos `tool_use`, chama `tool_executor.execute`, anexa `{role:assistant,content:response.content}` e `{role:user,content:[{type:tool_result,tool_use_id,content:json.dumps(resultado)}]}`. Limite 5 iterações.
  - Se `tool_executor` devolver `PendingAction`, encerra loop e retorna `AIResponse` com `pending_action`.
  - Acumular `input_tokens/output_tokens` para telemetria.
- `AIResponse` — adicionar `pending_action: Optional[dict] = None` e `tool_trace: Optional[list[dict]] = None`.
- `sistema/app/routers/ai_hub.py:554` — aceitar `confirmation_token` no request; branch via `os.getenv("USE_TOOL_CALLING","false")=="true"`.
- `sistema/app/services/prompts/manual_sistema.md` — seção curta "Ferramentas e regras" (nunca executar ação sem ID explícito; preferir leitura antes de propor ação). **Não duplicar JSON Schemas.**
- `sistema/cotte-frontend/assistente-ia.html` + `js/assistente-ia.js` — renderizar `pending_action` como card "Confirmar / Cancelar"; indicador "executando ferramenta…".
- `sistema/.env.example` — `USE_TOOL_CALLING=false`, `AI_PROVIDER=anthropic`, `OPENAI_API_KEY=`.
- `sistema/requirements.txt` — `openai>=1.40`.

### Tools do MVP

| Nome | Destrutiva | Reusa |
|---|---|---|
| `obter_saldo_caixa(periodo?)` | não | `financeiro_service._calcular_estatisticas_caixa` |
| `listar_movimentacoes_financeiras(tipo?, periodo?, limit?)` | não | `financeiro_service` |
| `listar_orcamentos(status?, cliente_id?, periodo?, limit?)` | não | `orcamento_repository` |
| `obter_orcamento(id)` | não | idem |
| `listar_clientes(busca?, limit?)` | não | `cliente_service` |
| `listar_materiais(busca?, limit?)` | não | `catalogo_service` |
| `criar_movimentacao_financeira(...)` | sim | `financeiro_service` |
| `criar_cliente(nome, telefone, email?)` | sim | `cliente_service` |
| `criar_orcamento(cliente_id, itens[])` | sim | `criar_orcamento_ia` (`cotte_ai_hub.py:1016`) |

Schemas Pydantic dos `InputModel` reusam `app/schemas/` via `model_json_schema()` quando possível.

### Testes de regressão provider-vs-provider

`sistema/tests/regression/test_provider_parity.py` + `fixtures/prompts.json` (~20 prompts reais). Para cada prompt executa em `AnthropicProvider` e `OpenAIProvider`. Asserções estruturais (não textuais): mesmo conjunto de tools chamadas, mesmos args em destrutivas, `stop_reason==end_turn`, mesmos `entity_ids` na resposta. Relatório em `reports/<ts>.md`. Marcado `@pytest.mark.regression` (roda manual, custo de API).

### Fora do MVP (Fase 2)

Aprovar/recusar orçamento, WhatsApp, agendamento, cadastro de material, PDF. Cache TTL de tools read-only. Streaming SSE.

## Plano de rollback

| Cenário | Ação | Tempo |
|---|---|---|
| Tool use quebrado | `USE_TOOL_CALLING=false` | <1 min |
| OpenAI instável | `AI_PROVIDER=anthropic` | <1 min |
| Custo explode | `AI_PROVIDER=anthropic` | <1 min |
| Bug em tool | revert / desabilitar no REGISTRY | <5 min |

Flags lidas por request. SessionStore (in-memory) sobrevive ao toggle.

## Verificação

1. **Unit** (`test_tool_executor.py`): tool inexistente → `unknown_tool`; permissão negada → `forbidden`; destrutiva sem token → `PendingAction` com UUID; destrutiva com token → executa + log; handler exceção → `{error,code}`, log `status=erro`.
2. **Integração**: monkeypatch `client.messages.create` com sequência [tool_use → tool_use → end_turn]; valida iteração, histórico no `SessionStore`, limite de 5 iterações.
3. **Manual** (`USE_TOOL_CALLING=true`): "Quanto tenho em caixa hoje?" → `obter_saldo_caixa` sem confirmação; "Liste meus 5 últimos orçamentos" → `listar_orcamentos(limit=5)`; "Cadastre cliente João, 4999…" → card confirmação → confirmar → log gravado; "Aprovar orçamento" sem ID → assistente pergunta (regra crítica do `CLAUDE.md`).
4. **Rollback**: flag off → fluxo legado intacto.
5. **Logs**: `select count(*), tool from tool_call_log group by tool;`.

## Riscos

- **Custo/latência**: limite de 5 iterações + `max_tokens=1024`; cache na Fase 2.
- **Permissão mal validada**: tool_executor é o **único** ponto autorizado a invocar handlers; proibido importar handlers fora dele. Coberto por testes.
- **LLM inventando args**: validação Pydantic antes de executar; erro volta ao LLM para auto-correção.
- **Drift legado vs v2**: coexistem atrás de flag; remover legado só após validação em produção.
