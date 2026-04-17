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

> **Estado atual do código (2026):** as chamadas de IA estão centralizadas em **`ia_service` + LiteLLM**; modelos e autenticação vêm de `AI_MODEL`, `AI_TECHNICAL_MODEL`, `AI_MODEL_FALLBACK`, `AI_PROVIDER`, `OPENROUTER_API_KEY` / `AI_API_KEY`, etc. O texto abaixo mistura **proposta, histórico de migração e decisões antigas** — não assuma um único provedor (Anthropic vs OpenAI) como verdade absoluta.

## Contexto

Hoje o assistente IA (`cotte_ai_hub.py`) usa **roteamento hardcoded por intent**: um classificador (regex + fallback) decide entre `CRIAR_ORCAMENTO`, `SALDO_RAPIDO`, `OPERADOR`, `CONVERSACAO`, etc., e o backend chama o service certo manualmente. Isso limita o assistente a fluxos pré-codificados e cria fricção a cada nova capacidade.

O objetivo do Gerson é ter um assistente **verdadeiramente autônomo**, que entenda o sistema inteiro e execute tarefas (cadastrar material, lançar movimentação financeira, criar orçamento, aprovar, listar clientes, agendar etc.) sem precisar de intent hardcoded para cada caso. A solução natural é **Tool Use / Function Calling** nativo do LLM.

> **Nota (legado deste plano):** havia discussão de **GPT‑4o‑mini** como modelo econômico e de um segundo wrapper OpenAI. Na implementação consolidada, **um único gateway LiteLLM** cobre os providers; o formato de tools segue o que o `ia_service.chat` expõe ao modelo configurado.

## Análise do plano original do Gerson

| Item proposto | Avaliação | Melhoria sugerida |
|---|---|---|
| Definir tools JSON mapeando services existentes | ✅ correto | Centralizar em **`app/services/ai_tools/`** (um arquivo por domínio: financeiro, orcamento, catalogo, cliente, agendamento). Cada tool = `{schema, handler, permission, idempotent}`. |
| Expandir `ai_hub.py` para tool calls + permissões | ✅ correto | Não inflar o router. Criar **`tool_executor.py`** (service) que recebe `tool_call`, valida permissão via `exigir_permissao`, valida ownership, executa, retorna resultado serializável. Router só orquestra. |
| Atualizar `manual_sistema.md` com tools e regras | ⚠️ parcial | Com Tool Use, o LLM já recebe os schemas via API — não precisa repetir tudo no prompt. O manual deve focar em **regras de negócio, tom, exemplos de uso e limites** (ex: "nunca aprove orçamento sem ID explícito"). Schemas ficam no código. |
| Streaming + "executando…" + botões de confirmação | ✅ excelente | Adicionar **dois níveis de tool**: `safe` (executa direto: listar, consultar, calcular) e `confirmacao_obrigatoria` (retorna proposta + botão; só executa após callback do usuário). Padronizar resposta do backend com `pending_action: {tool, args, descricao}`. |
| Migrar para GPT‑4o‑mini | ⚠️ obsoleto como decisão fixa | Escolher modelo via `AI_MODEL` / rota LiteLLM (custo x qualidade). |

## O que está faltando no plano original

1. **Loop multi-turno de tool calls** — o LLM pode chamar várias tools em sequência ("liste clientes em atraso → para cada um, calcule saldo → resuma"). O executor precisa rodar em loop até `stop_reason != tool_use`, com **limite máximo (ex: 5 iterações)** para evitar runaway cost.
2. **Cache de resultados de tools read-only** — `listar_clientes`, `saldo_caixa`, etc. podem reusar `SimpleCache` existente (TTL 60s) por `(empresa_id, tool, args_hash)`. Reduz custo significativamente.
3. **Auditoria** — toda execução de tool deve gerar log estruturado (`tool_calls_log`) com `usuario_id, empresa_id, tool, args, resultado, latencia_ms`. Essencial para debug e billing.
4. **Telemetria de custo** — registrar `input_tokens + output_tokens + tool_calls_count` por sessão. Já temos campo similar — estender.
5. **Confirmação de ações destrutivas no frontend** — não basta retornar `pending_action`; o `assistente-ia.js` precisa renderizar **card com botões "Confirmar / Cancelar"** que reenviam mensagem com `confirmation_token`. Aproveitar padrão de cards interativos já implementado (memória `project_assistente_interatividade.md`).
6. **Fallback gracioso** — se uma tool falha, não vazar stack trace para o LLM. Retornar `{error: "mensagem amigável", code}` para o modelo reformular.
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
   │        ├─ ia_service.chat / LiteLLM (messages, tools=...)
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
- `sistema/app/services/ia_service.py` — `chat()` via LiteLLM com suporte a `tools=`
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
2. **Integração**: pytest disparando `assistente_unificado_v2()` com mock do LLM retornando tool_use → tool_result → end_turn. Validar histórico final.
3. **Manual no sistema** (Playwright ou navegador):
   - "Quanto tenho em caixa?" → deve chamar `obter_saldo_caixa`, sem confirmação.
   - "Liste meus 5 últimos orçamentos" → `listar_orcamentos(limit=5)`.
   - "Crie um cliente João, telefone 4999..." → retorna card de confirmação → confirmar → cliente criado.
   - "Aprovar orçamento" (sem ID) → assistente pergunta o ID (não executa).
4. **Logs**: verificar `tool_call_log` populado e `ai_costs` somando tokens.
5. **Rollback**: setar `USE_TOOL_CALLING=false` deve reverter ao fluxo antigo sem regressão.

## Riscos principais

- **Custo**: tool use multiplica chamadas (~2-4x). Mitigação: cache + classificação barata (regex) + limite de iterações.
- **Latência**: cada tool call adiciona ~1-2s. Mitigação: streaming na resposta final + indicador visual "executando…".
- **Permissões mal validadas**: maior risco de segurança. Mitigação: **toda tool obrigatoriamente passa por `tool_executor`** — proibir chamada direta. Test coverage alto nesse módulo.
- **LLM inventando tools / parâmetros** ("hallucination"): validar args com Pydantic antes de executar. Erros voltam para o LLM corrigir.

## Documentação canônica (preferir estes arquivos)

| Documento | Conteúdo |
|-----------|----------|
| `docs/tecnico/plano-tool-use-v2.md` | Fases do Tool Use, registry, pendências e estado real do código |
| `docs/tecnico/assistente-tool-use.md` | Contrato técnico: variáveis de ambiente, fluxo, auditoria |
| `docs/tecnico/assistente-ia-arquitetura.md` | Fast-paths, arquivos críticos, checklist de regressão |
| `docs/tecnico/assistente-ia.md` | Mapa de endpoints e serviços |

Trechos antigos deste plano falavam em **inventário Anthropic (Sonnet/Haiku)**, **`ai_provider.py`** e **SDK `client.messages.create`**. Isso foi **substituído** na implementação por **`ia_service` + LiteLLM** e modelos configuráveis (`AI_MODEL`, chaves por rota). Use os documentos da tabela acima e o código em `sistema/app/services/` como fonte da verdade.
