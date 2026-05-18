# Handoff: Autonomia Real do Assistente IA — Pipeline Analítico + Renderização Rica

**Data:** 2026-05-18  
**Status:** Em andamento — fase de validação em produção

---

## 1. Objetivo

Tornar o assistente IA do COTTE capaz de responder perguntas analíticas (rankings, cruzamentos, relatórios complexos, extratos de clientes) de forma autônoma, sem precisar que o usuário saiba IDs ou formatos exatos. O assistente deve buscar dados diretamente no banco via SQL read-only, formatar a resposta em tabelas ricas no frontend e manter contexto conversacional entre turnos.

---

## 2. Contexto essencial

**Stack:** FastAPI + SQLAlchemy + PostgreSQL | Vanilla JS + Tailwind CDN | LiteLLM (Claude) | Railway deploy | Root dir = `sistema/`

**Variáveis de ambiente críticas (Railway — já configuradas):**
```
V2_SQL_AGENT=true
V2_LANGGRAPH_ORCHESTRATION=true
V2_LANGGRAPH_DIRECT_AGENTS=true
```

**Restrições arquiteturais:**
- Frontend é 100% Vanilla JS — sem React, sem frameworks
- Hub principal: `app/services/cotte_ai_hub.py` (~6.300 linhas) — tocar cirurgicamente
- LangGraph mantido (não substituir)
- SQL é sempre read-only, sempre filtrado por `empresa_id = :empresa_id`

**Decisões tomadas:**
- Abordagem "B+C combinado": pipeline analítico dedicado + módulos isolados que preparam refatoração futura do hub
- `AnalyticalClassifier` é heurístico (zero LLM, zero latência) — não substituir por LLM-based
- `semantic_contract` é o contrato de dados entre backend e frontend — toda resposta rica passa por ele
- Ferramentas de edição (`editar_cliente`, `excluir_cliente`, `criar_cliente`) são excluídas do tool set quando `intent_str = "ANALISE_SQL"`

---

## 3. O que já foi feito

### Sessão de hoje (2026-05-18) — commits em `main`

**1. Análise dos 7 gargalos originais** (sem código)
- DataAgent sem schema, SQL Guard bloqueava UNION/subqueries, fast-paths interceptavam antes do LLM, `executar_sql_analitico` ausente na engine, LangGraph sem db/current_user, limite de iterações insuficiente, Supervisor sem schema

**2. Schema Registry** — `app/ai/rag/schema_registry.py` (novo)
- Indexa schema do banco no startup via pgvector/SemanticRAGService
- `SchemaRegistry.get_relevant_tables(query, top_k=5)` retorna tabelas relevantes por similaridade
- Tabelas excluídas: `alembic_*`, `ai_database_schema_index`, `ai_documentos_conhecimento`
- Colunas sensíveis de `usuarios` omitidas (senha_hash, reset_token, api_key)
- Inicializado em `app/main.py` lifespan event — tolerante a falha

**3. SQL Guard v2** — `app/services/analytics_sql_guard.py` (reescrita)
- Era: whitelist de 10 tabelas, UNION bloqueado, score de complexidade
- Agora: blacklist de DML apenas (INSERT/UPDATE/DELETE/DROP etc.), UNION/subqueries livres
- Obriga `:empresa_id` como parâmetro no SQL (tenant isolation)
- Semicolon e tenant check feitos sobre `cleaned` (após strip de literais/comentários)

**4. Session Registry** — `app/ai/graph/session_registry.py` (novo)
- TTL dict thread-safe para passar `db`/`current_user` para agentes LangGraph sem serializar
- `register(thread_id, db=db, current_user=user, ttl_seconds=300)`
- `get(thread_id) -> tuple[Session, Usuario] | None`
- Registrado em `app/routers/ai_hub.py` em ambos os endpoints (streaming e não-streaming)
- Consultado em `app/ai/graph/assistant.py` → `specialist_agent_node`

**5. DataAgent schema-aware** — `app/ai/agents/data_agent.py` (reescrita)
- `set_db_context(db=db)` chamado pelo tool_runner antes de executar
- Injeta schema relevante no system prompt via `SchemaRegistry.get_relevant_tables(query)`
- Graceful degradation: funciona sem schema se Registry falhar

**6. `executar_sql_analitico` na engine operacional**
- `app/services/assistant_engine_registry.py` — adicionado em `ENGINE_OPERATIONAL.allowed_tools`
- Protegido pela flag `V2_SQL_AGENT=true`

**7. Configurações de limite**
- `_V2_MAX_ITER`: 5 → 8
- `max_steps` (tool_runner): 4 → 6
- Token budget: 15k operacional / 20k analítico

**8. AnalyticalClassifier com contexto histórico** — `app/ai/analytical_classifier.py` (expandido)
- Adicionado `HistoryContext` + `build_history_context(messages)`
- Detecta se último turno do assistente retornou dados (indicadores: "foram encontrados", "exibindo", "r$", etc.)
- Follow-ups curtos em contexto de dados disparam `is_analytical=True`
- Exemplo fixado: `"id 1"` após lista de clientes → analítico (não mais `editar_cliente`)
- ~30 novas keywords: `tabela`, `contas de/da/do`, `todas as contas`, `detalhar`, `vencidas`, `em aberto`, etc.

**9. Hub: histórico passado ao classifier**
- `_pre_clf_hist = SessionStore.get_or_create(sessao_id)` antes da chamada ao classifier
- `_history_ctx = build_history_context(_pre_clf_hist)` passado para `classify_analytical_intent`

**10. Ferramentas de edição excluídas em modo analítico**
- Quando `_analytical_intent.is_analytical`, filtra `editar_cliente`, `excluir_cliente`, `criar_cliente` do tool set
- `tool_profile = "analytical_readonly"`

**11. Supervisor atualizado** — `app/ai/agents/supervisor.py`
- DataAgent preferido para qualquer consulta de dados (incluindo follow-ups com ID)
- OperadorAgent restrito a verbos imperativos + ID (aprovar, enviar, excluir)
- Regra antiga "prefira OperadorAgent quando há ID" — removida

**12. Renderização rica de resultados SQL** — backend + frontend + CSS
- **Backend** (`cotte_ai_hub.py`): detecta `rows` em `tool_data_collector` → auto-constrói `semantic_contract` com table, printable, metadata (rows_returned, rows_total, truncated)
- **Frontend** (`assistente-ia-render-types.js`): `renderSemanticTableRows` melhorado:
  - Aceita `meta` (rows_returned, rows_total, truncated)
  - Cabeçalho "X resultados" / "Exibindo X de Y"
  - `data-raw` nos `<td>` para sort preciso
  - `data-sort-col` + `data-col-idx` nos `<th>`
  - Colunas numéricas à direita (`ai-th-numeric`, `ai-td-numeric`)
  - Linhas zebra (`ai-tr-alt`)
  - Helpers `_isNumericColumn()` e `_formatCellValue()`
- **CSS** (`assistente-ia.css`): `.ai-table-wrapper--analytic` com scroll limitado e header sticky, `.ai-table-meta-header`, `.ai-table-count`, `.ai-th-sortable`, `.ai-th-sorted`, `.ai-sort-arrow`

**13. Ordenação de colunas por clique**
- Event delegation no `document` — cobre todas as tabelas passadas e futuras
- Sort numérico automático via `data-raw`, sort de datas ISO, sort de texto
- Toggle asc/desc com seta ▲/▼ no header
- Reindexação das classes zebra após reordenação
- Inicializado em IIFE no fim de `assistente-ia-render-types.js`

**14. Novas ferramentas de orçamento** — `app/ai/tools/orcamento_tools.py`
- `adicionar_item_orcamento`: adiciona item com descrição, valor, quantidade; recalcula total
- `remover_item_orcamento`: remove por posição (1 = primeiro); recalcula total
- `aplicar_desconto_orcamento`: desconto fixo ou percentual com validação
- Todas: destrutivas (requer confirmação), exigem status RASCUNHO, registram evento de auditoria

### Descartado / não implementado
- Wrapper automático de tenant no SQL Guard (descartado — obrigar `:empresa_id` como parâmetro é mais robusto)
- Classifier baseado em LLM (descartado — zero latência é requisito)

---

## 4. Estado atual

**O que funciona:**
- Pipeline analítico completo: classifier → bypass fast-paths → DataAgent + schema → SQL Guard → semantic_contract → tabela rica no frontend
- Follow-ups em contexto analítico detectados corretamente (`"id 1"` após lista → analítico)
- Tabelas com ordenação por clique, contador, zebra, colunas monetárias formatadas
- Export CSV/PDF via botão no card printable (já existia no semantic_contract)
- 85/85 testes passando

**O que ainda não foi validado em produção:**
- Fluxo completo end-to-end: usuário pergunta → DataAgent gera SQL → resultado aparece em tabela rica (requer testar no servidor de desenvolvimento com dados reais)
- Schema Registry inicializado corretamente no primeiro deploy após mudança
- LangGraph com SessionRegistry funcionando com `V2_LANGGRAPH_DIRECT_AGENTS=true`

**Nenhum teste quebrado:** testes pré-existentes que falhavam (`test_ai_assistente_contract.py` — 29 falhas) são pré-existentes, unrelated, causados por `AttributeError: 'AsyncSession' object has no attribute 'query'` em `app/core/auth.py`.

---

## 5. Próximos passos

1. **Testar end-to-end no servidor dev** — reproduzir a conversa da sessão anterior:
   - "quem está devendo?" → lista de inadimplentes
   - "crie uma tabela com todas as contas da Ana julia" → deve retornar tabela rica
   - "id 1" → deve retornar contas do cliente ID 1 via SQL (não `editar_cliente`)
   - Verificar se tabela aparece com ordenação, contador e botão de export

2. **Validar Schema Registry no startup** — checar nos logs do Railway se aparece:
   `"SchemaRegistry inicializado com N tabelas"` ou o warning de falha

3. **Testar queries analíticas diretas:**
   - "top 5 clientes que mais compraram esse ano"
   - "ranking de faturamento por mês"
   - "ticket médio dos últimos 60 dias"

4. **Implementar gráfico automático para resultados com 2 colunas** (INOVAÇÃO pendente)
   - Quando SQL retorna `(categoria, valor)` → popular `semantic_contract.chart` automaticamente
   - O slot `<div class="semantic-chart-slot">` já existe no frontend

5. **Cache de queries analíticas por fingerprint** (INOVAÇÃO pendente)
   - Hash do SQL gerado → Redis cache com TTL 5min
   - Evita re-execução de queries pesadas frequentes

6. **Health check do pipeline analítico** (INOVAÇÃO pendente)
   - Endpoint `/admin/ai-health` verificando: `V2_SQL_AGENT` flag, SchemaRegistry inicializado, `executar_sql_analitico` acessível
   - Retorna OK/DEGRADED/OFFLINE por componente

---

## 6. Perguntas em aberto

- **Schema Registry com pgvector**: o embedding de schema funciona bem para tabelas com nomes descritivos (clientes, orcamentos), mas pode falhar para tabelas com nomes técnicos. Precisa validar a qualidade do ranking em produção.
- **Limite de 200 linhas na tabela**: adequado? Para relatórios grandes (ex: 1000 registros), o usuário vai precisar de paginação server-side ou o frontend aguenta?
- **`_v2_is_orcamento_context_followup_message` e outros fast-paths** não respeitam `intent_str = "ANALISE_SQL"`. Baixo risco hoje, mas pode causar conflito em edge cases. Considerar adicionar `and intent_str != "ANALISE_SQL"` nas guards.
- **Novas ferramentas de orçamento** (`adicionar_item_orcamento` etc.) foram adicionadas mas ainda não testadas pelo usuário. Confirmar se a UX de confirmação funciona corretamente.

---

## 7. Artefatos relevantes

### Arquivos criados/modificados nesta sessão

| Arquivo | Tipo | O que é |
|---|---|---|
| `app/ai/rag/schema_registry.py` | Novo | Indexa e consulta schema do banco por similaridade |
| `app/ai/graph/session_registry.py` | Novo | TTL dict para db/current_user no LangGraph |
| `app/ai/analytical_classifier.py` | Modificado | Classifier com histórico + keywords expandidas |
| `app/ai/agents/data_agent.py` | Reescrito | DataAgent schema-aware com set_db_context |
| `app/ai/agents/supervisor.py` | Modificado | Regras de roteamento atualizadas |
| `app/ai/agents/tool_runner.py` | Modificado | max_steps 4→6, set_db_context |
| `app/services/analytics_sql_guard.py` | Reescrito | DML blacklist, UNION livre, tenant via :empresa_id |
| `app/services/assistant_engine_registry.py` | Modificado | executar_sql_analitico em ENGINE_OPERATIONAL |
| `app/services/cotte_ai_hub.py` | Modificado | Classifier com histórico, SQL→semantic_contract, tool filter |
| `app/routers/ai_hub.py` | Modificado | SessionRegistry.register() em ambos endpoints |
| `app/ai/graph/assistant.py` | Modificado | SessionRegistry.get() em specialist_agent_node |
| `app/main.py` | Modificado | SchemaRegistry.initialize() no lifespan |
| `app/ai/tools/orcamento_tools.py` | Modificado | +adicionar/remover item, aplicar desconto |
| `app/ai/tools/__init__.py` | Modificado | Exporta novas tools |
| `cotte-frontend/js/assistente-ia-render-types.js` | Modificado | Tabela rica, sort, helpers |
| `cotte-frontend/css/assistente-ia.css` | Modificado | CSS tabela analítica, sort, zebra |
| `docs/superpowers/specs/2026-05-17-assistente-ia-autonomia-design.md` | Novo | Design spec aprovado |
| `docs/superpowers/plans/2026-05-17-assistente-ia-autonomia.md` | Novo | Plano de implementação |
| `tests/test_analytics_sql_guard.py` | Novo | 18 testes do SQL Guard v2 |
| `tests/test_session_registry.py` | Novo | 5 testes do Session Registry |
| `tests/test_analytical_classifier.py` | Novo | 33 testes do classifier |
| `tests/test_schema_registry.py` | Novo | 6 testes do Schema Registry |

### Commits desta sessão
```
d717d45  feat(tools): adicionar/remover item e aplicar desconto em orçamentos
d47acf8  feat(ui): renderização rica de resultados SQL analíticos com tabela estruturada
179baa1  fix(ai): context-aware analytical routing + expanded keywords + read-only tool set
1208b7e  chore: ignore patch_classifier.py temp file
442b2bc  feat(ai): improve executar_sql_analitico description for better LLM routing
3dac8ce  fix(ai): implement fast router, fix langgraph silent failures...
```

### Comandos úteis para a próxima sessão
```bash
# Rodar todos os testes do pipeline analítico
python -m pytest tests/test_analytics_sql_guard.py tests/test_session_registry.py tests/test_analytical_classifier.py tests/test_schema_registry.py -v

# Ver logs do Schema Registry no startup
grep "SchemaRegistry" logs/app.log

# Testar classifier com contexto manualmente
python -c "
from app.ai.analytical_classifier import classify_analytical_intent, build_history_context
hist = [{'role':'assistant','content':'foram encontrados 103 registros. Ana Julia: R\$ 8.384'}]
ctx = build_history_context(hist)
r = classify_analytical_intent('id 1', history_context=ctx)
print(r)
"
```

### Localização dos pontos-chave no hub (cotte_ai_hub.py)
- Classifier call: linha ~4946 (`_pre_clf_hist`, `_history_ctx`, `_clf`)
- Tool filter analítico: linha ~5717 (`_ANALYTICAL_EXCLUDED`)
- SQL → semantic_contract: linha ~6058 (`_sql_rows`)
- Inferência de tipo de resposta: linha ~6083

---

## 8. Instruções para a próxima sessão

**Tom:** Direto ao ponto, sem teoria. Gerson é empreendedor com background técnico intermediário — quer ver funcionando, não explicações longas.

**Começar por:** Testar o fluxo end-to-end no servidor de desenvolvimento. Pedir ao Gerson para reproduzir a conversa de teste ("quem está devendo?" → "crie uma tabela com todas as contas da Ana julia" → "id 1"). Se funcionar, o pipeline está validado.

**Armadilhas a evitar:**
1. **Não tocar nos fast-paths existentes** sem necessidade — eles servem casos operacionais simples que já funcionam bem
2. **Não refatorar o hub** (`cotte_ai_hub.py`) além do necessário — tem 6.300 linhas e é estável
3. **`SessionStore.get_or_create(sessao_id)` sem db** funciona via compatibilidade de sufixo em `_resolve_cache_key` — não "corrigir" isso
4. **Os 29 testes que falham em `test_ai_assistente_contract.py`** são pré-existentes (AsyncSession sem `.query`) — não tentar consertar nesta sessão
5. **`V2_SQL_AGENT=true` no Railway** — já está configurado. Se o pipeline não funcionar em produção, verificar os logs do SchemaRegistry primeiro

**Nível de detalhe esperado:** Médio. Plano curto antes de editar, lista de arquivos e impacto após. Sempre incluir 3 sugestões de inovação no final de cada tarefa concluída (requisito do CLAUDE.md).
