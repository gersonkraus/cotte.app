---
title: Assistente Tool Use
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Assistente Tool Use
tags:
  - tecnico
prioridade: media
status: documentado
---
# Assistente IA — Tool Use v2

Documentação técnica do assistente do COTTE em modo Tool Use / Function Calling. Cobre arquitetura, fluxo de execução, ferramentas disponíveis, regras de segurança e operação.

## Visão geral

O assistente v2 substitui o roteamento por intent hardcoded por **function calling nativo do LLM**. O modelo recebe um catálogo de ferramentas (`tools=`) junto com a mensagem do usuário e decide sozinho quais chamar, em qual ordem, com quais argumentos. O backend valida, executa e devolve o resultado para o LLM continuar o raciocínio.

Ativado por feature flag: `USE_TOOL_CALLING=true` no `.env` ou nas Variables do Railway. Quando desligado, o sistema cai no `assistente_unificado` v1 (intent-based) — rollback instantâneo, sem redeploy.

**Decisão de stack**: continua usando Anthropic Claude (via LiteLLM) — não houve migração para GPT-4o-mini. LiteLLM permite trocar de provider futuramente sem mexer no resto.

## Arquitetura

```
Frontend (assistente-ia.js)
   │ POST /ai/assistente {mensagem, sessao_id, confirmation_token?}
   ▼
ai_hub.py (router fino — feature flag USE_TOOL_CALLING)
   │
   ▼
cotte_ai_hub.assistente_unificado_v2()
   │   ├─ Fast-path se confirmation_token: tool_executor.execute_pending()
   │   │     └─ Executa direto pelos args travados no token (sem LLM)
   │   │
   │   ├─ Carrega histórico (SessionStore) e tools (openai_tools_payload)
   │   └─ Loop (máx 5 iterações):
   │        ├─ ia_service.chat(messages, tools=...)
   │        ├─ se tool_calls != None:
   │        │     ├─ tool_executor.execute(tool_call, db, current_user)
   │        │     │     ├─ rate limit por empresa
   │        │     │     ├─ lookup REGISTRY
   │        │     │     ├─ valida args (Pydantic)
   │        │     │     ├─ valida permissão (exigir_permissao)
   │        │     │     ├─ cache hit? retorna sem executar handler
   │        │     │     ├─ destrutiva sem token? emite confirmation_token
   │        │     │     │      e retorna pending
   │        │     │     ├─ executa handler real (service de domínio)
   │        │     │     ├─ guarda em cache se ok + cacheable_ttl
   │        │     │     └─ persiste em ToolCallLog
   │        │     └─ append tool_result ao histórico, próxima iteração
   │        └─ se sem tool_calls: usa o conteúdo como texto final
   │
   ▼
AIResponse {sucesso, resposta, pending_action?, tool_trace[], dados}
```

## Componentes

| Arquivo | Papel |
|---|---|
| `sistema/app/routers/ai_hub.py` | Router fino. Feature flag, valida request, chama o serviço apropriado. |
| `sistema/app/services/cotte_ai_hub.py` (`assistente_unificado_v2`) | Loop de tool calling, monta histórico, gerencia fast-path de confirmação. |
| `sistema/app/services/ia_service.py` (`ia_service.chat`) | Wrapper LiteLLM com suporte a `tools=`. |
| `sistema/app/services/tool_executor.py` | **Único ponto autorizado** a invocar handlers do REGISTRY. RBAC, gating destrutivas, cache, rate limit, log. |
| `sistema/app/services/ai_tools/__init__.py` | REGISTRY central + `openai_tools_payload()` para o LLM. |
| `sistema/app/services/ai_tools/_base.py` | `ToolSpec` (dataclass): nome, schema Pydantic, handler, flags, permissão, TTL de cache. |
| `sistema/app/services/ai_tools/{cliente,catalogo,financeiro,orcamento}_tools.py` | Specs por domínio. Handlers chamam services existentes. |
| `sistema/app/models/models.py` (`ToolCallLog`) | Auditoria de cada chamada. Migration `tc001_tool_call_log`. |
| `sistema/cotte-frontend/js/assistente-ia.js` | Renderiza tool_trace, card de pending_action, reenvia com confirmation_token. |
| `sistema/app/services/prompts/manual_sistema.md` | Regras de negócio do assistente (não duplica schemas — schemas vêm via API). |

## Fluxo de uma tool call

1. **Usuário** manda mensagem no frontend.
2. **`assistente_unificado_v2`** monta `messages` com system prompt + histórico + nova mensagem, e chama `ia_service.chat(messages, tools=openai_tools_payload())`.
3. **LLM** retorna `tool_calls` com `{name, arguments}`.
4. **`tool_executor.execute()`** processa cada tool call:
   - **0. Rate limit** — `_check_rate_limit()` consulta `ToolCallLog` por empresa nos últimos 60s e 60min. Configurável via `TOOL_RATE_LIMIT_PER_MIN` (default 30) e `TOOL_RATE_LIMIT_PER_HOUR` (default 300). Se estourar, retorna `status="rate_limited"`.
   - **1. Lookup** — `REGISTRY.get(name)`. Se não existir, `status="unknown_tool"`.
   - **2. Validação Pydantic** — `spec.input_model(**args_dict)`. Se inválido, `status="invalid_input"`.
   - **3. Permissão** — `exigir_permissao(spec.permissao_recurso, spec.permissao_acao)(usuario=current_user)`. Se negada, `status="forbidden"`.
   - **4a. Cache** — só para tools não destrutivas com `cacheable_ttl > 0`. Lookup `(empresa_id, tool_name, args_hash)`. Hit retorna em ms.
   - **4b. Gating destrutiva** — se `spec.destrutiva` e sem `confirmation_token` válido, gera token (TTL 5min) e retorna `status="pending"` + `pending_action={tool, args, description, confirmation_token}`. Os args são persistidos no `_PENDING_TOKENS` server-side para que a confirmação execute exatamente a mesma ação.
   - **5. Handler** — `await spec.handler(validated, db=db, current_user=current_user)`. Captura `HTTPException` (forbidden / http_error) e `Exception` (com `db.rollback()` defensivo).
   - **6. Persistência** — `_log()` grava `ToolCallLog` (sempre, mesmo em erro), com `latencia_ms`, `args_json`, `resultado_json`, `status`.
5. **Resultado** vira mensagem `{role: "tool"}` no histórico.
6. **Loop** volta ao passo 2 (até 5 iterações ou até o LLM responder texto puro).
7. **Resposta final** sai como `AIResponse` para o frontend, incluindo `tool_trace` (lista das tools executadas) e `pending_action` se houver alguma destrutiva pendente.

## Confirmação de ações destrutivas (fast-path)

Problema clássico do Tool Use: quando o usuário clica "Confirmar", o frontend reenvia a mensagem original junto com o `confirmation_token`. Se o backend reinvocar o LLM, o modelo pode chamar a tool com **args diferentes** (chutar outro ID, mudar o nome) — o token validaria por hash e rejeitaria, ou pior, executaria algo diferente do que o usuário viu no card.

**Solução implementada**: ao emitir o `confirmation_token`, o `tool_executor` persiste no `_PENDING_TOKENS` server-side os `args_dict` exatos, o `tool_name`, e o `empresa_id` (isolamento por tenant). Quando a confirmação chega, `assistente_unificado_v2` faz **fast-path**: chama `tool_executor.execute_pending(token)` que recupera os args travados, **revalida RBAC e rate limit**, executa o handler e retorna direto — sem passar pelo LLM. Custo zero de tokens, garantia de que executa exatamente o que o usuário viu.

Token TTL: 5 minutos. Uso único (`pop_pending`).

## Cache de read-only

Cada `ToolSpec` declara `cacheable_ttl` em segundos. O `tool_executor._TOOL_CACHE` é um `dict` em memória keyed por `(empresa_id, tool_name, args_hash)`:

| Tool | TTL |
|---|---|
| `listar_materiais` | 60s |
| `listar_clientes`, `obter_saldo_caixa` | 30s |
| `listar_orcamentos`, `obter_orcamento`, `listar_movimentacoes_financeiras` | 15s |

Regras:
- Lookup acontece **depois** da validação RBAC — cache não fura permissão.
- Só cacheia `status="ok"` de tools **não destrutivas**.
- Isolado por `empresa_id` (nunca vaza dados entre tenants).
- Poda automática de expirados + soft cap de 512 entradas (descarta mais antigas).
- Não persiste entre restarts do worker (cache local — aceito como simplicidade).

## Tools disponíveis

### Leitura (cacheable, sem confirmação)

| Tool | Permissão | TTL | Uso |
|---|---|---|---|
| `listar_clientes(busca?, limit?)` | clientes:leitura | 30s | Lista clientes da empresa, com busca opcional. Retorna `id` real do banco em cada item. |
| `listar_materiais(busca?, limit?)` | catalogo:leitura | 60s | Catálogo de serviços/materiais. |
| `listar_orcamentos(status?, periodo?)` | orcamentos:leitura | 15s | Orçamentos filtrados. |
| `obter_orcamento(id)` | orcamentos:leitura | 15s | Detalhe completo de um orçamento. |
| `obter_saldo_caixa(periodo?)` | financeiro:leitura | 30s | Saldo operacional consolidado. |
| `listar_movimentacoes_financeiras(tipo?, periodo?)` | financeiro:leitura | 15s | Entradas/saídas confirmadas. |

### Destrutivas (exigem confirmation_token)

| Tool | Permissão | Uso |
|---|---|---|
| `criar_cliente(nome, telefone?, email?)` | clientes:escrita | Apenas `nome` é obrigatório. |
| `excluir_cliente(cliente_id)` | clientes:escrita | Por ID — nunca por nome. LLM deve buscar com `listar_clientes(busca='...')` antes. |
| `criar_orcamento(...)` | orcamentos:escrita | Cria orçamento manual. |
| `criar_movimentacao_financeira(tipo, valor, descricao, ...)` | financeiro:escrita | Lança entrada/saída avulsa. |

## Configuração (env vars)

| Variável | Default | Descrição |
|---|---|---|
| `USE_TOOL_CALLING` | `false` | Ativa o assistente v2. Sem isso, usa o v1 antigo. |
| `TOOL_RATE_LIMIT_PER_MIN` | `30` | Máximo de tool calls (status `ok` ou `erro`) por empresa por minuto. `0` desativa. |
| `TOOL_RATE_LIMIT_PER_HOUR` | `300` | Idem, por hora. `0` desativa. |
| `ANTHROPIC_API_KEY` | — | Necessária pelo LiteLLM. |

## Auditoria — `tool_call_log`

Migration `tc001_tool_call_log` cria a tabela. Campos:

| Coluna | Tipo | Uso |
|---|---|---|
| `id` | int PK | |
| `empresa_id` | FK empresas, indexed | Filtro por tenant. |
| `usuario_id` | FK usuarios, indexed | Quem disparou. |
| `sessao_id` | str(64), indexed | Agrupar por conversa. |
| `tool` | str(100), indexed | Nome da tool. |
| `args_json` | JSON | Args validados (depois do Pydantic). |
| `resultado_json` | JSON | Payload retornado para o LLM (`to_llm_payload()`). |
| `status` | str(20), indexed | `ok` / `erro` / `forbidden` / `pending` / `invalid_input` / `unknown_tool` / `rate_limited`. |
| `latencia_ms` | int | Tempo total da execução. |
| `input_tokens` / `output_tokens` | int | Para futura agregação de custo. |
| `criado_em` | timestamptz, indexed | Para rate limit e relatórios. |

Falha ao gravar log **nunca quebra o assistente** (`logger.warning` + `db.rollback()` defensivo).

## Regras críticas para o LLM (system prompt)

Definidas em `_V2_SYSTEM_PROMPT` em `cotte_ai_hub.py` e reforçadas em `manual_sistema.md`:

1. **Nunca inventar valores numéricos** (saldo, totais, IDs) — sempre obter via tool de leitura.
2. **Ações destrutivas** — chamar a tool DIRETAMENTE; o sistema mostra automaticamente o card de confirmação. NUNCA perguntar "deseja prosseguir?" antes.
3. **Nunca executar ação sem ID/dado explícito** vindo do usuário.
4. **IDs sempre via tool** — para excluir/editar por nome, chamar `listar_clientes(busca='...')` primeiro e usar o `id` retornado. NUNCA usar a posição na lista.
5. **Sem tool correspondente** — se o usuário pedir uma ação para a qual não há tool, dizer claramente. NUNCA chamar outra no lugar.
6. **Campos opcionais** — não pedir ao usuário se a tool não exigir.
7. **Erros de tool** — virar resposta clara, não retry cego.
8. **`rate_limited`** — avisar o usuário, não retry automático.

## Frontend — `assistente-ia.js`

Pontos de integração com Tool Use v2:

- **`sendMessage()`** (linhas ~136-172): se `window._pendingConfirmationToken` está setado, anexa ao requestBody.
- **`processAIResponse()`** (linhas ~178-274):
  - Renderiza `data.tool_trace` como `🛠️ ✅ tool_name` (ou `⏳`, `⚠️`).
  - Renderiza `data.pending_action` como card "⚠️ Confirmação necessária" com args formatados, botões Confirmar/Cancelar.
- **`confirmarAcaoIA(token, btnEl)`** / **`cancelarAcaoIA(btnEl)`** (linhas ~784-811): handlers dos botões. O confirm reenvia a última pergunta + token.

**Cache-buster do JS** está em `assistente-ia.html:870` — `<script src="js/assistente-ia.js?v=N">`. **Sempre que mudar o JS, bumpe o `?v=`** ou os browsers continuam servindo o antigo (problema enfrentado e corrigido em produção em `fea82ba`).

## Testes

- `sistema/tests/test_tool_executor.py` — 8 testes cobrindo: lookup, validação, permissão, gating destrutiva, token TTL, hash de args, exceção do handler, persistência em log. **Executar**: `python -m pytest tests/test_tool_executor.py -q` (rodando em ~1s sem dependência de litellm).
- `sistema/tests/test_assistente_unificado_v2.py` — testes de integração do loop completo. Requer `litellm` instalado (default no Railway).

## Operação

### Deploy

1. `git push origin main` — Railway faz auto-build.
2. `release.sh` roda `alembic upgrade head` antes de subir o uvicorn (migrations automáticas).
3. **Setar `USE_TOOL_CALLING=true`** nas Variables do Railway. Sem isso, o v2 não é ativado.
4. **Sempre que mexer em JS de frontend, bumpar o cache-buster** no HTML correspondente.

### Rollback

- **Imediato**: setar `USE_TOOL_CALLING=false` no Railway. Volta ao v1 sem redeploy.
- **Migration tc001 é aditiva** (só cria tabela `tool_call_log`) — pode permanecer sem causar problemas.

### Monitoramento

- Tabela `tool_call_log` é a fonte primária. Queries úteis:
  ```sql
  -- Tools mais chamadas nas últimas 24h
  SELECT tool, status, count(*), avg(latencia_ms)
  FROM tool_call_log
  WHERE criado_em > now() - interval '24 hours'
  GROUP BY tool, status
  ORDER BY count(*) DESC;

  -- Empresas próximas do rate limit
  SELECT empresa_id, count(*) AS calls_last_min
  FROM tool_call_log
  WHERE criado_em > now() - interval '1 minute'
    AND status IN ('ok', 'erro')
  GROUP BY empresa_id
  HAVING count(*) > 20;

  -- Taxa de erro por tool
  SELECT tool,
    sum(case when status = 'ok' then 1 else 0 end)::float / count(*) AS taxa_ok
  FROM tool_call_log
  WHERE criado_em > now() - interval '7 days'
  GROUP BY tool;
  ```

## Dívida técnica e próximos passos

- **Cache de tools é local ao worker** — em deploys multi-instance, hits são por-instância. Migrar para Redis se houver mais de 1 worker.
- **`_PENDING_TOKENS` também é local** — mesmo problema. Em multi-worker, um confirm pode cair em outro worker e não achar o token. Migrar para Redis com TTL nativo.
- **Tools de Fase 2** ainda não implementadas: `aprovar_orcamento`, `recusar_orcamento`, `enviar_orcamento_whatsapp`, `enviar_orcamento_email`, `criar_agendamento`, `cadastrar_material`, `gerar_pdf_orcamento`.
- **Telemetria de custo agregada** — `input_tokens`/`output_tokens` já estão no log; falta endpoint/tela para somar por empresa por período (futuro billing).
- **Cache-buster do JS** é manual e frágil — vale automatizar com hash de build no `release.sh`.
