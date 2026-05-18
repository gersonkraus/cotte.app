# Design: Autonomia Real do Assistente IA

**Data:** 2026-05-17  
**Status:** Aprovado  
**Escopo:** Operador (empresa) como usuário primário; prepara base para migração futura do hub monolítico  
**Abordagem:** B + C combinado — implementa pipeline analítico dedicado agora, com módulos isolados que preparam a refatoração completa futura  

---

## Problema

O assistente não consegue responder perguntas analíticas (rankings, cruzamentos, relatórios complexos) de forma autônoma porque:

1. O DataAgent não conhece o schema do banco — gera SQL incorreto ou não tenta
2. O SQL Guard bloqueia queries válidas (UNION, subqueries, whitelist pequena, regex de tenant frágil)
3. Fast-paths de regex interceptam perguntas antes do LLM ter chance de raciocinar
4. `executar_sql_analitico` não está no engine do operador
5. LangGraph não conecta `db`/`current_user` aos agentes — executam via fallback legado
6. Limite de 5 iterações e 15k tokens insuficiente para análises encadeadas
7. Supervisor não conhece o schema — roteamento para DataAgent impreciso

---

## Arquitetura

### Fluxo atual (problema)

```
User → fast-path regex → [interceptado] → resposta simples sem dados
User → LLM loop → [sem schema, sem SQL] → resposta vaga
User → LangGraph → [db não serializa] → fallback para legado
```

### Fluxo proposto

```
User
 └─→ Analytical Classifier
       ├─ analytical query ──→ Analytical Pipeline
       │                         ├─ Schema Registry (top-5 tabelas relevantes)
       │                         ├─ DataAgent (SQL-aware, schema no prompt)
       │                         ├─ SQL Guard v2 (SELECT livre, DML bloqueado)
       │                         └─ LLM formata resultado
       │
       └─ operational query ─→ fast-paths existentes (sem mudança)
                                └─ LLM loop (se não interceptado)

LangGraph (quando V2_LANGGRAPH_DIRECT_AGENTS=true):
  Session Registry (request-scoped)
  └─→ agentes executam com db/current_user reais via lookup por thread_id
```

### Princípio de isolamento (preparação para C)

Cada componente novo é um módulo com responsabilidade única. O hub legado os chama, nunca o contrário. Isso permite substituir o hub gradualmente sem quebrar os módulos já validados.

---

## Componentes

### 1. Schema Registry

**Arquivo:** `app/ai/rag/schema_registry.py`  
**Responsabilidade:** Indexar e consultar o schema do banco por similaridade semântica.

**Comportamento:**
- Chamado no startup do FastAPI (lifespan event) via `SchemaRegistry.initialize(db)`
- Itera sobre `Base.metadata.tables`, gera embedding por tabela com nome + descrição + lista de colunas
- Salva em `AIDatabaseSchemaIndex` (model já existe, nunca era populado)
- Expõe `SchemaRegistry.get_relevant_tables(query: str, top_k: int = 5) -> list[TableSchema]`
- `TableSchema`: `{table: str, columns: list[str], description: str}`
- Tabelas excluídas: `alembic_*`, `ai_database_schema_index`, `ai_documentos_conhecimento`

**Tabelas sensíveis (blacklist de exibição):** o schema de `usuarios` é fornecido sem colunas de hash/token (`senha_hash`, `reset_token`, `api_key`)

**Startup:** FastAPI lifespan event em `app/main.py` — tolerante a falha (log warning, não bloqueia startup)

---

### 2. SQL Guard v2

**Arquivo:** `app/services/analytics_sql_guard.py` (reescrita)  
**Responsabilidade:** Validar SQL garantindo read-only e tenant isolation.

**Regras (o que muda):**

| Regra anterior | Regra nova |
|---|---|
| Whitelist de 10 tabelas | Blacklist de tabelas sensíveis (`pg_*`, `alembic_*`) |
| UNION bloqueado | UNION permitido |
| Subquery IN/EXISTS bloqueada | Subqueries permitidas |
| Regex `empresa_id = :empresa_id` obrigatória | Executor injeta wrapper de tenant automaticamente |
| Score de complexidade ≤ 20 | Score removido — só bloqueia DML |

**O que permanece bloqueado:**
- INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE
- Multi-statement (`;`)
- Acesso a tabelas `pg_*`, `information_schema`, `alembic_version`

**Tenant isolation (novo mecanismo):**  
O guard valida que o SQL contém o token `:empresa_id` como parâmetro em algum lugar (WHERE, JOIN ON, ou CTE). O executor então faz bind de `{"empresa_id": current_user.empresa_id}` na execução. O schema injetado no DataAgent inclui a instrução explícita: *"todo SQL deve conter `empresa_id = :empresa_id` no WHERE ou JOIN — o executor vai rejeitar se não encontrar o parâmetro"*. Se o LLM esquecer, o guard retorna um erro descritivo que permite retry na próxima iteração. Essa abordagem é mais robusta que wrapper porque funciona com qualquer lista de colunas no SELECT.

---

### 3. Analytical Classifier

**Arquivo:** `app/ai/analytical_classifier.py`  
**Responsabilidade:** Detectar antes dos fast-paths se a query precisa de análise SQL/multi-tool.

**Triggers analíticos (heurística — sem LLM):**
- Palavras: `ranking`, `top N`, `mais vendido`, `por mês`, `por período`, `comparar`, `análise`, `cruzar`, `quais clientes`, `quais orçamentos`, `crescimento`, `média`, `ticket médio`, `inadimplente`, `histórico`
- Padrões: múltiplos tópicos financeiros na mesma frase, presença de número cardinal com contexto de ranking ("os 5 melhores", "top 10")

**Comportamento:**
- Retorna `AnalyticalIntent(is_analytical: bool, confidence: float, triggers: list[str])`
- Se `is_analytical=True`, o hub salta os fast-paths e vai direto para o LLM loop com `DataAgent` no contexto
- Sem chamada LLM — apenas regex/keyword matching para manter zero latência

---

### 4. Session Registry (LangGraph)

**Arquivo:** `app/ai/graph/session_registry.py`  
**Responsabilidade:** Manter `db` e `current_user` acessíveis por thread_id sem serializar no estado do LangGraph.

**Interface:**
```python
SessionRegistry.register(thread_id: str, db: Session, current_user: Usuario, ttl_seconds: int = 300)
SessionRegistry.get(thread_id: str) -> tuple[Session, Usuario] | None
SessionRegistry.cleanup()  # remove entradas expiradas
```

**Implementação:** `dict` simples com timestamp. Cleanup a cada chamada de `register`. Thread-safe com `threading.Lock`. TTL padrão: 5 minutos (cobre toda a duração de uma requisição SSE).

**Integração:**
1. Em `ai_hub.py` (router), antes de chamar o LangGraph: `SessionRegistry.register(sessao_id, db, current_user)`
2. Em `graph/assistant.py`, no `specialist_agent_node`: `db, current_user = SessionRegistry.get(state["sessao_id"])` — se `None`, cai no legacy_runner (sem regressão)

---

### 5. DataAgent com schema context

**Arquivo:** `app/ai/agents/data_agent.py` (atualização)  
**Responsabilidade:** Gerar e executar SQL com conhecimento real do schema.

**Mudanças:**
- `DataAgent.__call__()` recebe `query: str` e chama `SchemaRegistry.get_relevant_tables(query)` antes de montar o system prompt
- Schema relevante é injetado como bloco estruturado no prompt
- System prompt atualizado: inclui instrução explícita para sempre filtrar por `empresa_id` e listar as regras de negócio principais (status de orçamento, tipos de movimentação)

---

### 6. Supervisor com contexto de schema

**Arquivo:** `app/ai/agents/supervisor.py` (atualização)  
**Responsabilidade:** Rotear com informação suficiente para decidir DataAgent vs outros.

**Mudanças:**
- Prompt atualizado: `DataAgent — use para rankings, agrupamentos, cruzamento entre tabelas, contagens, médias, análises de período. Tem acesso a SQL read-only.`
- Schema top-3 tabelas injetado como contexto antes do roteamento

---

### 7. Mudanças de configuração

**`app/services/assistant_engine_registry.py`:**
- Adicionar `executar_sql_analitico` em `ENGINE_OPERATIONAL.allowed_tools`

**`app/services/cotte_ai_hub.py`:**
- `_V2_MAX_ITER`: `5 → 8`
- Token budget: `15.000 → 20.000` para queries analíticas (detectadas pelo classifier)
- Integrar `AnalyticalClassifier` antes do bloco de fast-paths

**`app/ai/agents/tool_runner.py`:**
- `max_steps`: `4 → 6`

---

## Fluxo de dados para uma query analítica

**Exemplo:** *"Quais são os 5 clientes que mais compraram esse ano?"*

1. `AnalyticalClassifier` detecta: `is_analytical=True` (trigger: "5 clientes", "mais compraram")
2. Hub salta fast-paths, vai para LLM loop com `DataAgent` habilitado e `executar_sql_analitico` no payload
3. LLM recebe schema: `clientes(id, empresa_id, nome)`, `orcamentos(id, cliente_id, empresa_id, valor_total, status, created_at)`
4. LLM gera SQL:
   ```sql
   SELECT c.nome, SUM(o.valor_total) as total
   FROM orcamentos o JOIN clientes c ON o.cliente_id = c.id
   WHERE o.empresa_id = :empresa_id AND o.status = 'aprovado'
     AND o.created_at >= '2026-01-01'
   GROUP BY c.nome ORDER BY total DESC LIMIT 5
   ```
5. SQL Guard v2 valida: SELECT, sem DML, sem tabelas sensíveis → OK
6. Executor aplica wrapper de tenant e executa
7. LLM recebe resultado e formata resposta estruturada com tabela

---

## Impacto em código existente

| Arquivo | Tipo de mudança | Risco |
|---|---|---|
| `app/main.py` | Adiciona lifespan event para SchemaRegistry | Baixo — tolerante a falha |
| `app/services/analytics_sql_guard.py` | Reescrita | Médio — testes obrigatórios |
| `app/services/assistant_engine_registry.py` | Adiciona 1 tool | Baixo |
| `app/services/cotte_ai_hub.py` | Adiciona classifier antes dos fast-paths, ajusta limites | Baixo — só adiciona, não remove |
| `app/ai/agents/data_agent.py` | Injeta schema no prompt | Baixo |
| `app/ai/agents/supervisor.py` | Prompt update + schema contexto | Baixo |
| `app/ai/agents/tool_runner.py` | max_steps 4→6 | Baixo |
| `app/ai/graph/session_registry.py` | **Novo arquivo** | Novo |
| `app/ai/rag/schema_registry.py` | **Novo arquivo** | Novo |
| `app/ai/analytical_classifier.py` | **Novo arquivo** | Novo |

---

## Testes recomendados

1. **Schema indexer:** após startup, verificar que `AIDatabaseSchemaIndex` tem registros; testar `get_relevant_tables("orçamentos de clientes")` retorna tabelas corretas
2. **SQL Guard v2:** testar SELECT com UNION, IN subquery, múltiplos JOINs → devem passar; testar INSERT/UPDATE → deve bloquear; testar query sem `empresa_id` → executor deve injetar filtro corretamente
3. **Analytical Classifier:** testar 10 queries analíticas e 10 operacionais — verificar classificação correta
4. **DataAgent end-to-end:** perguntar "top 5 clientes do mês" → verificar que SQL é executado e resultado retornado
5. **LangGraph com Session Registry:** habilitar `V2_LANGGRAPH_DIRECT_AGENTS=true`, verificar que `specialist_agent_node` executa sem cair em legacy_runner

---

## Variáveis de ambiente relevantes

| Variável | Valor recomendado | Descrição |
|---|---|---|
| `V2_LANGGRAPH_DIRECT_AGENTS` | `true` | Habilita agentes diretos via Session Registry |
| `V2_LANGGRAPH_ORCHESTRATION` | `true` | Habilita orquestração LangGraph |
| `V2_SQL_AGENT` | `true` | Habilita `executar_sql_analitico` na engine operacional |
| `ANALYTICS_SQL_ALLOWED_SOURCES` | (remover ou ignorar) | Substituído por blacklist no Guard v2 |

---

## Preparação para C (refatoração futura)

Cada componente novo tem interface limpa e pode ser chamado diretamente pelo hub ou por um futuro orquestrador que substitua o hub:
- `SchemaRegistry` — singleton com interface estável
- `AnalyticalClassifier` — função pura, sem estado
- `SessionRegistry` — serviço stateful com interface clara
- `DataAgent` — agente standalone, pode ser usado fora do hub

Quando a refatoração completa (C) for iniciada, esses módulos continuam válidos — apenas o hub de 6.222 linhas é decomposed ao redor deles.
