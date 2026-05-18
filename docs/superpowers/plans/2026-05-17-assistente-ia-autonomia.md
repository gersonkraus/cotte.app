# Autonomia Real do Assistente IA — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar o assistente capaz de responder perguntas analíticas complexas (rankings, cruzamentos, relatórios) de forma autônoma, buscando dados reais no banco via SQL.

**Architecture:** SQL Guard reescrito para liberar SELECT livre com isolamento por parâmetro. Schema Registry indexa tabelas no startup e injeta contexto no DataAgent. Analytical Classifier detecta queries complexas antes dos fast-paths e força o LLM loop com SQL habilitado. Session Registry resolve o problema de serialização do LangGraph.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, LangGraph, LiteLLM, pgvector

---

## Mapa de Arquivos

| Ação | Arquivo | Responsabilidade |
|---|---|---|
| **Reescrever** | `sistema/app/services/analytics_sql_guard.py` | Guard v2: SELECT livre, DML bloqueado, sem whitelist |
| **Reescrever** | `sistema/tests/test_analytics_sql_guard.py` | Testes atualizados para guard v2 |
| **Criar** | `sistema/app/ai/graph/session_registry.py` | Mantém db/current_user por thread_id para LangGraph |
| **Criar** | `sistema/tests/test_session_registry.py` | Testes do registry |
| **Criar** | `sistema/app/ai/analytical_classifier.py` | Detecta queries analíticas sem LLM |
| **Criar** | `sistema/tests/test_analytical_classifier.py` | Testes do classifier |
| **Criar** | `sistema/app/ai/rag/schema_registry.py` | Indexa e busca schema por similaridade semântica |
| **Criar** | `sistema/tests/test_schema_registry.py` | Testes do registry |
| **Modificar** | `sistema/app/services/assistant_engine_registry.py:55-88` | Adiciona `executar_sql_analitico` em ENGINE_OPERATIONAL |
| **Modificar** | `sistema/app/main.py:368+` | Inicializa SchemaRegistry no startup |
| **Modificar** | `sistema/app/ai/agents/data_agent.py` | Injeta schema no prompt via SchemaRegistry |
| **Modificar** | `sistema/app/ai/agents/supervisor.py` | Prompt atualizado + routing para DataAgent |
| **Modificar** | `sistema/app/ai/agents/tool_runner.py:101` | max_steps 4→6 |
| **Modificar** | `sistema/app/routers/ai_hub.py:1125` | Registra sessão antes do LangGraph |
| **Modificar** | `sistema/app/ai/graph/assistant.py:184` | Usa Session Registry para db/current_user |
| **Modificar** | `sistema/app/services/cotte_ai_hub.py:4155,5699+` | MAX_ITER 8, budget dinâmico, integra classifier |

---

## Task 1: SQL Guard v2

**Files:**
- Rewrite: `sistema/app/services/analytics_sql_guard.py`
- Rewrite: `sistema/tests/test_analytics_sql_guard.py`

- [ ] **Step 1: Escrever os testes novos primeiro**

```python
# sistema/tests/test_analytics_sql_guard.py
from app.services.analytics_sql_guard import validate_analytics_sql


# ── Deve BLOQUEAR ──────────────────────────────────────────────────────────

def test_guard_bloqueia_update():
    out = validate_analytics_sql("UPDATE orcamentos SET total=0 WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code in {"sql_not_read_only", "sql_blocked_keyword"}


def test_guard_bloqueia_insert():
    out = validate_analytics_sql("INSERT INTO orcamentos (id) VALUES (1)")
    assert out.ok is False


def test_guard_bloqueia_delete():
    out = validate_analytics_sql("DELETE FROM clientes WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code in {"sql_not_read_only", "sql_blocked_keyword"}


def test_guard_bloqueia_drop():
    out = validate_analytics_sql("DROP TABLE clientes")
    assert out.ok is False


def test_guard_bloqueia_multi_statement():
    out = validate_analytics_sql(
        "SELECT * FROM orcamentos WHERE empresa_id = :empresa_id; SELECT 1"
    )
    assert out.ok is False
    assert out.code == "sql_multi_statement_blocked"


def test_guard_bloqueia_sem_tenant_scope():
    out = validate_analytics_sql("SELECT id, total FROM orcamentos")
    assert out.ok is False
    assert out.code == "sql_missing_tenant_scope"


def test_guard_bloqueia_or_1_equals_1():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id OR 1=1"
    )
    assert out.ok is False
    assert out.code == "sql_tenant_bypass_pattern"


def test_guard_bloqueia_tabela_pg():
    out = validate_analytics_sql("SELECT * FROM pg_tables WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code == "sql_system_table_blocked"


def test_guard_bloqueia_alembic():
    out = validate_analytics_sql("SELECT * FROM alembic_version WHERE schemaname = :empresa_id")
    assert out.ok is False
    assert out.code == "sql_system_table_blocked"


def test_guard_bloqueia_parenteses_desbalanceados():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id AND (id > 0"
    )
    assert out.ok is False
    assert out.code == "sql_unbalanced_parentheses"


# ── Deve PERMITIR ──────────────────────────────────────────────────────────

def test_guard_aceita_select_simples():
    out = validate_analytics_sql(
        "SELECT id, total FROM orcamentos WHERE empresa_id = :empresa_id"
    )
    assert out.ok is True
    assert out.sql is not None


def test_guard_aceita_join():
    out = validate_analytics_sql(
        "SELECT o.id, c.nome, SUM(o.valor_total) "
        "FROM orcamentos o JOIN clientes c ON o.cliente_id = c.id "
        "WHERE o.empresa_id = :empresa_id GROUP BY o.id, c.nome"
    )
    assert out.ok is True


def test_guard_aceita_union():
    out = validate_analytics_sql(
        "SELECT id, 'orcamento' as tipo FROM orcamentos WHERE empresa_id = :empresa_id "
        "UNION ALL "
        "SELECT id, 'cliente' as tipo FROM clientes WHERE empresa_id = :empresa_id"
    )
    assert out.ok is True


def test_guard_aceita_subquery_in():
    out = validate_analytics_sql(
        "SELECT * FROM clientes WHERE empresa_id = :empresa_id "
        "AND id IN (SELECT cliente_id FROM orcamentos WHERE empresa_id = :empresa_id AND status = 'aprovado')"
    )
    assert out.ok is True


def test_guard_aceita_cte():
    out = validate_analytics_sql(
        "WITH top_clientes AS ("
        "  SELECT cliente_id, SUM(valor_total) as total "
        "  FROM orcamentos WHERE empresa_id = :empresa_id GROUP BY cliente_id"
        ") SELECT c.nome, t.total FROM top_clientes t JOIN clientes c ON c.id = t.cliente_id"
    )
    assert out.ok is True


def test_guard_aceita_group_by_order_by():
    out = validate_analytics_sql(
        "SELECT status, COUNT(*) as qtd, SUM(valor_total) as total "
        "FROM orcamentos WHERE empresa_id = :empresa_id "
        "GROUP BY status ORDER BY total DESC LIMIT 10"
    )
    assert out.ok is True


def test_guard_aceita_cross_tenant_sem_empresa_id():
    out = validate_analytics_sql(
        "SELECT COUNT(*) FROM orcamentos",
        allow_cross_tenant=True,
    )
    assert out.ok is True


def test_guard_result_tem_campos_de_compatibilidade():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id"
    )
    assert out.ok is True
    assert hasattr(out, "risk_score")
    assert hasattr(out, "complexity")
```

- [ ] **Step 2: Rodar os testes para confirmar que FALHAM (guard antigo)**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_analytics_sql_guard.py -v 2>&1 | tail -30
```

Esperado: vários FAILs (UNION bloqueado, whitelist, etc.)

- [ ] **Step 3: Reescrever o SQL Guard v2**

```python
# sistema/app/services/analytics_sql_guard.py
"""Guardrails de segurança para SQL Agent analítico v2.

Política: bloqueia DML/DDL e tabelas de sistema. SELECT livre com tenant
isolation via parâmetro :empresa_id. Sem whitelist de tabelas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


_DML_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|vacuum)\b",
    flags=re.IGNORECASE,
)
_SYSTEM_TABLE_RE = re.compile(
    r"\b(pg_\w+|information_schema\b|alembic_version)\b",
    flags=re.IGNORECASE,
)
_COMMENT_RE = re.compile(r"(--[^\n]*|/\*[\s\S]*?\*/)")
_STRING_RE = re.compile(r"'(?:''|[^'])*'")
_OR_TRUE_RE = re.compile(r"\bor\s+1\s*=\s*1\b", re.IGNORECASE)
_TENANT_PARAM_RE = re.compile(r":empresa_id\b", re.IGNORECASE)


def _strip_literals_and_comments(sql: str) -> str:
    without_comments = _COMMENT_RE.sub(" ", sql or "")
    return _STRING_RE.sub("'?'", without_comments)


def _balanced_parentheses(sql: str) -> bool:
    depth = 0
    for ch in sql or "":
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            return False
    return depth == 0


@dataclass(frozen=True)
class SqlValidationResult:
    ok: bool
    sql: Optional[str] = None
    error: Optional[str] = None
    code: Optional[str] = None
    # Mantidos por compatibilidade com callers existentes (sql_analytics_tools.py)
    risk_score: int = 0
    complexity: Optional[dict] = field(default=None)


def validate_analytics_sql(sql: str, *, allow_cross_tenant: bool = False) -> SqlValidationResult:
    """Valida SQL garantindo read-only e tenant isolation.

    allow_cross_tenant=True permite omitir :empresa_id (uso exclusivo de superadmin).
    """
    raw = (sql or "").strip()

    if not raw:
        return SqlValidationResult(ok=False, error="SQL vazio.", code="invalid_input")

    if len(raw) > 8000:
        return SqlValidationResult(
            ok=False, error="SQL excede limite de 8000 caracteres.", code="invalid_input"
        )

    if ";" in raw:
        return SqlValidationResult(
            ok=False,
            error="SQL com múltiplas instruções não é permitido.",
            code="sql_multi_statement_blocked",
        )

    if not _balanced_parentheses(raw):
        return SqlValidationResult(
            ok=False,
            error="SQL com parênteses desbalanceados.",
            code="sql_unbalanced_parentheses",
        )

    cleaned = _strip_literals_and_comments(raw)

    if _OR_TRUE_RE.search(cleaned):
        return SqlValidationResult(
            ok=False,
            error="Padrão de bypass detectado (OR 1=1).",
            code="sql_tenant_bypass_pattern",
        )

    lowered = raw.lower().lstrip()
    if not (
        lowered.startswith("select ")
        or lowered.startswith("select\n")
        or lowered.startswith("select\t")
        or lowered.startswith("with ")
    ):
        return SqlValidationResult(
            ok=False,
            error="SQL Agent permite apenas SELECT/CTE read-only.",
            code="sql_not_read_only",
        )

    if _DML_RE.search(cleaned):
        return SqlValidationResult(
            ok=False,
            error="Comando SQL bloqueado por política de segurança (DML/DDL).",
            code="sql_blocked_keyword",
        )

    if _SYSTEM_TABLE_RE.search(cleaned):
        return SqlValidationResult(
            ok=False,
            error="Acesso a tabelas de sistema (pg_*, alembic_*) não é permitido.",
            code="sql_system_table_blocked",
        )

    if not allow_cross_tenant and not _TENANT_PARAM_RE.search(raw):
        return SqlValidationResult(
            ok=False,
            error=(
                "SQL analítico deve filtrar por empresa usando :empresa_id como parâmetro. "
                "Exemplo: WHERE empresa_id = :empresa_id"
            ),
            code="sql_missing_tenant_scope",
        )

    return SqlValidationResult(ok=True, sql=raw, risk_score=0, complexity={})
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_analytics_sql_guard.py -v 2>&1 | tail -20
```

Esperado: todos PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/services/analytics_sql_guard.py tests/test_analytics_sql_guard.py && git commit -m "feat(ai): rewrite SQL Guard v2 — SELECT livre, sem whitelist, DML bloqueado"
```

---

## Task 2: Session Registry

**Files:**
- Create: `sistema/app/ai/graph/session_registry.py`
- Create: `sistema/tests/test_session_registry.py`

- [ ] **Step 1: Escrever os testes**

```python
# sistema/tests/test_session_registry.py
import time
import threading
from unittest.mock import MagicMock
from app.ai.graph.session_registry import SessionRegistry


def _make_db():
    return MagicMock(name="db")


def _make_user():
    return MagicMock(name="user", empresa_id=42)


def test_register_and_get():
    db = _make_db()
    user = _make_user()
    SessionRegistry.register("thread-1", db=db, current_user=user)
    result = SessionRegistry.get("thread-1")
    assert result is not None
    got_db, got_user = result
    assert got_db is db
    assert got_user is user


def test_get_unknown_thread_returns_none():
    result = SessionRegistry.get("nao-existe-xyz")
    assert result is None


def test_ttl_expiry():
    db = _make_db()
    user = _make_user()
    SessionRegistry.register("thread-ttl", db=db, current_user=user, ttl_seconds=0)
    time.sleep(0.01)
    result = SessionRegistry.get("thread-ttl")
    assert result is None


def test_overwrite_existing():
    db1 = _make_db()
    db2 = _make_db()
    user = _make_user()
    SessionRegistry.register("thread-ow", db=db1, current_user=user)
    SessionRegistry.register("thread-ow", db=db2, current_user=user)
    got_db, _ = SessionRegistry.get("thread-ow")
    assert got_db is db2


def test_thread_safe():
    errors = []
    def _worker(thread_id):
        try:
            db = _make_db()
            user = _make_user()
            SessionRegistry.register(thread_id, db=db, current_user=user)
            result = SessionRegistry.get(thread_id)
            assert result is not None
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_worker, args=(f"t-{i}",)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors
```

- [ ] **Step 2: Rodar testes para confirmar que falham (arquivo não existe)**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_session_registry.py -v 2>&1 | tail -10
```

Esperado: ImportError ou ModuleNotFoundError

- [ ] **Step 3: Criar o Session Registry**

```python
# sistema/app/ai/graph/session_registry.py
"""Session Registry para LangGraph.

Mantém db/current_user acessíveis por thread_id sem serializar no estado do grafo.
TTL padrão de 5 minutos cobre a duração de qualquer requisição SSE.
"""
from __future__ import annotations

import threading
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 300  # 5 minutos


class SessionRegistry:
    _store: dict[str, dict[str, Any]] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def register(
        cls,
        thread_id: str,
        *,
        db: Any,
        current_user: Any,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        """Registra db e current_user para um thread_id com TTL."""
        with cls._lock:
            cls._cleanup_expired()
            cls._store[thread_id] = {
                "db": db,
                "current_user": current_user,
                "expires_at": time.monotonic() + ttl_seconds,
            }
        logger.debug("[SessionRegistry] Sessão registrada: %s", thread_id)

    @classmethod
    def get(cls, thread_id: str) -> Optional[tuple[Any, Any]]:
        """Retorna (db, current_user) ou None se não existir/expirado."""
        with cls._lock:
            entry = cls._store.get(thread_id)
            if entry is None:
                return None
            if time.monotonic() > entry["expires_at"]:
                del cls._store[thread_id]
                logger.debug("[SessionRegistry] Sessão expirada: %s", thread_id)
                return None
            return entry["db"], entry["current_user"]

    @classmethod
    def _cleanup_expired(cls) -> None:
        now = time.monotonic()
        expired = [k for k, v in cls._store.items() if now > v["expires_at"]]
        for k in expired:
            del cls._store[k]
```

- [ ] **Step 4: Rodar os testes**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_session_registry.py -v 2>&1 | tail -15
```

Esperado: todos PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/ai/graph/session_registry.py tests/test_session_registry.py && git commit -m "feat(ai): add LangGraph Session Registry para db/current_user sem serialização"
```

---

## Task 3: Analytical Classifier

**Files:**
- Create: `sistema/app/ai/analytical_classifier.py`
- Create: `sistema/tests/test_analytical_classifier.py`

- [ ] **Step 1: Escrever os testes**

```python
# sistema/tests/test_analytical_classifier.py
from app.ai.analytical_classifier import classify_analytical_intent


# ── Queries analíticas — devem retornar is_analytical=True ────────────────

def test_classifica_ranking():
    r = classify_analytical_intent("quais são os top 5 clientes que mais compraram?")
    assert r.is_analytical is True
    assert r.confidence > 0.4


def test_classifica_top_n():
    r = classify_analytical_intent("me mostra os 10 melhores clientes do mês")
    assert r.is_analytical is True


def test_classifica_agrupamento():
    r = classify_analytical_intent("faturamento por mês dos últimos 6 meses")
    assert r.is_analytical is True


def test_classifica_ticket_medio():
    r = classify_analytical_intent("qual é o ticket médio dos meus orçamentos aprovados?")
    assert r.is_analytical is True


def test_classifica_crescimento():
    r = classify_analytical_intent("qual foi o crescimento do faturamento comparando com o mês passado?")
    assert r.is_analytical is True


def test_classifica_inadimplencia():
    r = classify_analytical_intent("quais clientes estão inadimplentes?")
    assert r.is_analytical is True


def test_classifica_topicos_combinados():
    r = classify_analytical_intent("qual o faturamento por cliente nos últimos 90 dias?")
    assert r.is_analytical is True


def test_classifica_analise_historico():
    r = classify_analytical_intent("histórico de vendas por serviço")
    assert r.is_analytical is True


def test_classifica_top3():
    r = classify_analytical_intent("top 3 serviços mais vendidos")
    assert r.is_analytical is True


def test_classifica_quem_mais():
    r = classify_analytical_intent("quem mais comprou em abril?")
    assert r.is_analytical is True


# ── Queries operacionais — devem retornar is_analytical=False ─────────────

def test_nao_classifica_saldo():
    r = classify_analytical_intent("qual é meu saldo?")
    assert r.is_analytical is False


def test_nao_classifica_criar_orcamento():
    r = classify_analytical_intent("cria um orçamento para o João")
    assert r.is_analytical is False


def test_nao_classifica_aprovar():
    r = classify_analytical_intent("aprovar orçamento 5")
    assert r.is_analytical is False


def test_nao_classifica_listar_clientes():
    r = classify_analytical_intent("lista meus clientes")
    assert r.is_analytical is False


def test_nao_classifica_saudacao():
    r = classify_analytical_intent("olá, bom dia!")
    assert r.is_analytical is False


def test_nao_classifica_mensagem_vazia():
    r = classify_analytical_intent("")
    assert r.is_analytical is False


def test_retorna_triggers_quando_analitico():
    r = classify_analytical_intent("ranking dos melhores clientes")
    assert r.is_analytical is True
    assert len(r.triggers) > 0
```

- [ ] **Step 2: Rodar para confirmar que falham**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_analytical_classifier.py -v 2>&1 | tail -10
```

Esperado: ImportError (arquivo não existe)

- [ ] **Step 3: Criar o Analytical Classifier**

```python
# sistema/app/ai/analytical_classifier.py
"""Classifier de intenção analítica — zero latência, sem chamada LLM.

Detecta se uma mensagem requer análise SQL/multi-tool antes de entrar
nos fast-paths do hub. Retorna AnalyticalIntent com is_analytical, confidence e triggers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


_ANALYTICAL_KEYWORDS: frozenset[str] = frozenset({
    # Rankings e comparações
    "ranking", "top", "mais vendido", "mais comprou", "mais compraram",
    "melhores clientes", "piores clientes", "maiores clientes",
    "melhor cliente", "pior cliente", "maior cliente",
    "top clientes", "quem mais",
    # Agrupamentos temporais
    "por mês", "por semana", "por período", "por dia", "por cliente",
    "por vendedor", "por serviço", "por status", "por categoria",
    "mês passado", "ano passado", "mês anterior", "ano anterior",
    "últimos 30", "últimos 60", "últimos 90",
    "ultimos 30", "ultimos 60", "ultimos 90",
    "entre janeiro", "entre fevereiro", "de janeiro a",
    "nos últimos", "nos ultimos",
    # Métricas e análise
    "crescimento", "média", "ticket médio", "ticket medio",
    "inadimplente", "inadimplência", "inadimplencia",
    "histórico", "historico",
    "análise", "analise", "cruzar", "cruzamento", "combinar",
    # Perguntas analíticas
    "quais clientes", "quais orçamentos", "quais orcamentos",
    "quanto faturou", "quanto gastou", "quanto gerou",
    "total por", "soma por", "agrupado", "agrupa", "agrupar",
    "relatório detalhado", "relatorio detalhado",
    "faturamento por", "receita por", "despesa por",
})

_RANKING_PATTERN = re.compile(
    r"\b("
    r"top\s*\d+"
    r"|os?\s+\d+\s+(melhores?|piores?|maiores?|menores?|primeiros?)"
    r"|\d+\s+primeiros?"
    r"|primeiros?\s+\d+"
    r")\b",
    re.IGNORECASE,
)

_MULTI_FINANCIAL_PATTERN = re.compile(
    r"(?=.*\b(saldo|caixa|financeiro|receita|faturamento|despesa)\b)"
    r"(?=.*\b(cliente|orçamento|orcamento|serviço|servico|período|periodo|mês|mes)\b)",
    re.IGNORECASE,
)


@dataclass
class AnalyticalIntent:
    is_analytical: bool
    confidence: float
    triggers: List[str] = field(default_factory=list)


def classify_analytical_intent(mensagem: str) -> AnalyticalIntent:
    """Classifica se a mensagem requer análise SQL/multi-tool. Sem chamada LLM."""
    if not mensagem or not mensagem.strip():
        return AnalyticalIntent(is_analytical=False, confidence=0.0)

    normalized = mensagem.lower().strip()
    triggers: list[str] = []

    for keyword in _ANALYTICAL_KEYWORDS:
        if keyword in normalized:
            triggers.append(keyword)

    if _RANKING_PATTERN.search(normalized):
        triggers.append("ranking_pattern")

    if _MULTI_FINANCIAL_PATTERN.search(normalized):
        triggers.append("multi_financial_topic")

    if not triggers:
        return AnalyticalIntent(is_analytical=False, confidence=0.0)

    confidence = min(0.5 + len(triggers) * 0.15, 1.0)
    return AnalyticalIntent(is_analytical=True, confidence=confidence, triggers=triggers)
```

- [ ] **Step 4: Rodar os testes**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_analytical_classifier.py -v 2>&1 | tail -25
```

Esperado: todos PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/ai/analytical_classifier.py tests/test_analytical_classifier.py && git commit -m "feat(ai): add AnalyticalClassifier zero-latency para detectar queries SQL antes dos fast-paths"
```

---

## Task 4: Schema Registry

**Files:**
- Create: `sistema/app/ai/rag/schema_registry.py`
- Create: `sistema/tests/test_schema_registry.py`

- [ ] **Step 1: Escrever os testes**

```python
# sistema/tests/test_schema_registry.py
from unittest.mock import AsyncMock, MagicMock, patch
from app.ai.rag.schema_registry import SchemaRegistry, TableSchema


def test_table_schema_to_prompt_line():
    t = TableSchema(table="orcamentos", columns=["id", "empresa_id", "valor_total"], description="Tabela de orçamentos")
    line = t.to_prompt_line()
    assert "orcamentos" in line
    assert "id" in line
    assert "valor_total" in line


def test_format_schema_context_vazio():
    result = SchemaRegistry.format_schema_context([])
    assert result == ""


def test_format_schema_context_com_tabelas():
    tables = [
        TableSchema(table="orcamentos", columns=["id", "empresa_id"], description="Orçamentos"),
        TableSchema(table="clientes", columns=["id", "nome"], description="Clientes"),
    ]
    ctx = SchemaRegistry.format_schema_context(tables)
    assert "orcamentos" in ctx
    assert "clientes" in ctx
    assert ":empresa_id" in ctx


async def test_get_relevant_tables_sem_db():
    result = await SchemaRegistry.get_relevant_tables("ranking clientes", db=None)
    assert result == []


async def test_get_relevant_tables_com_falha_retorna_lista_vazia():
    db = MagicMock()
    with patch("app.ai.rag.schema_registry.SemanticRAGService.search_schema", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = Exception("pgvector indisponível")
        result = await SchemaRegistry.get_relevant_tables("ranking", db=db)
    assert result == []


async def test_get_relevant_tables_mapeia_resultado():
    db = MagicMock()
    mock_idx = MagicMock()
    mock_idx.table_name = "orcamentos"
    mock_idx.description = "Tabela de orçamentos"
    mock_idx.schema_json = {"columns": [{"name": "id"}, {"name": "empresa_id"}]}

    with patch("app.ai.rag.schema_registry.SemanticRAGService.search_schema", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [mock_idx]
        result = await SchemaRegistry.get_relevant_tables("orçamentos", db=db)

    assert len(result) == 1
    assert result[0].table == "orcamentos"
    assert "id" in result[0].columns
```

- [ ] **Step 2: Rodar para confirmar que falham**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_schema_registry.py -v 2>&1 | tail -10
```

Esperado: ImportError

- [ ] **Step 3: Criar o Schema Registry**

```python
# sistema/app/ai/rag/schema_registry.py
"""Schema Registry — singleton para indexação e busca semântica do schema do banco.

Indexado no startup via SchemaRegistry.initialize(db). Expõe
get_relevant_tables(query, db) para injeção de contexto no DataAgent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

_EXCLUDED_TABLES: frozenset[str] = frozenset({
    "ai_database_schema_index",
    "ai_documentos_conhecimento",
})
_EXCLUDED_PREFIXES = ("alembic_",)

# Colunas sensíveis nunca expostas ao LLM
_SENSITIVE_COLUMNS: frozenset[str] = frozenset({
    "senha_hash", "password_hash", "reset_token", "api_key",
    "refresh_token", "token_hash", "secret", "private_key",
})


@dataclass
class TableSchema:
    table: str
    columns: List[str]
    description: str

    def to_prompt_line(self) -> str:
        cols = ", ".join(self.columns[:15])  # limita colunas exibidas
        return f"- {self.table}({cols}): {self.description}"


class SchemaRegistry:
    _initialized: bool = False

    @classmethod
    async def initialize(cls, db) -> None:
        """Indexa todas as tabelas no pgvector. Chamado no startup do FastAPI.

        Tolerante a falha — um erro não bloqueia o startup.
        """
        from app.core.database import Base
        from app.ai.rag.service import SemanticRAGService

        count = 0
        errors = 0
        for table_name, table in Base.metadata.tables.items():
            if table_name in _EXCLUDED_TABLES:
                continue
            if any(table_name.startswith(p) for p in _EXCLUDED_PREFIXES):
                continue

            safe_columns = [
                {"name": col.name, "type": str(col.type), "nullable": col.nullable}
                for col in table.columns
                if col.name not in _SENSITIVE_COLUMNS
            ]
            column_names = [c["name"] for c in safe_columns]

            description = table.comment or f"Tabela {table_name} do sistema COTTE."
            schema_info = {"table": table_name, "columns": safe_columns}
            text_to_embed = f"Tabela: {table_name}. Colunas: {', '.join(column_names)}. {description}"

            try:
                await SemanticRAGService.index_table_schema(
                    db=db,
                    table_name=table_name,
                    description=description,
                    schema_info=schema_info,
                )
                count += 1
            except Exception as exc:
                logger.warning("[SchemaRegistry] Falha ao indexar %s: %s", table_name, exc)
                errors += 1

        cls._initialized = True
        logger.info("[SchemaRegistry] Indexação concluída: %d tabelas, %d erros.", count, errors)

    @classmethod
    async def get_relevant_tables(
        cls, query: str, *, top_k: int = 5, db=None
    ) -> List[TableSchema]:
        """Retorna tabelas mais relevantes para a query via pgvector cosine similarity."""
        if db is None:
            return []
        try:
            from app.ai.rag.service import SemanticRAGService

            results = await SemanticRAGService.search_schema(db=db, query=query, top_k=top_k)
            tables = []
            for idx in results:
                schema_info = idx.schema_json or {}
                columns = [c["name"] for c in schema_info.get("columns", [])]
                tables.append(
                    TableSchema(
                        table=idx.table_name,
                        columns=columns,
                        description=idx.description or "",
                    )
                )
            return tables
        except Exception as exc:
            logger.warning("[SchemaRegistry] Falha na busca de schema: %s", exc)
            return []

    @classmethod
    def format_schema_context(cls, tables: List[TableSchema]) -> str:
        """Formata tabelas em bloco de texto para injeção no system prompt do DataAgent."""
        if not tables:
            return ""
        lines = [
            "### Schema relevante (use para construir SQL):",
        ]
        for t in tables:
            lines.append(t.to_prompt_line())
        lines.append(
            "\nREGRA OBRIGATÓRIA: Todo SQL deve incluir `empresa_id = :empresa_id` "
            "no WHERE ou JOIN. O executor faz bind automático do valor correto."
        )
        return "\n".join(lines)
```

- [ ] **Step 4: Rodar os testes**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest tests/test_schema_registry.py -v 2>&1 | tail -15
```

Esperado: todos PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/ai/rag/schema_registry.py tests/test_schema_registry.py && git commit -m "feat(ai): add Schema Registry com indexação semântica de tabelas para DataAgent"
```

---

## Task 5: Adicionar `executar_sql_analitico` ao ENGINE_OPERATIONAL

**Files:**
- Modify: `sistema/app/services/assistant_engine_registry.py:55-88`

- [ ] **Step 1: Adicionar a tool ao ENGINE_OPERATIONAL**

No arquivo `sistema/app/services/assistant_engine_registry.py`, localizar `ENGINE_OPERATIONAL` (linha ~51) e adicionar `"executar_sql_analitico"` no final da tupla `allowed_tools`, antes de `"gerar_relatorio_ranking_clientes"`:

```python
# Localizar o bloco allowed_tools do ENGINE_OPERATIONAL (linhas 55-88)
# Adicionar APÓS "gerar_relatorio_vendas," (última linha antes do fechamento):
            "gerar_relatorio_ranking_clientes",
            "gerar_relatorio_contas_a_receber",
            "gerar_relatorio_vendas",
            "executar_sql_analitico",  # ← ADICIONAR ESTA LINHA
        ),
```

- [ ] **Step 2: Verificar que a tool aparece no payload da engine**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "
from app.services.assistant_engine_registry import tools_payload_for_engine
import os; os.environ['V2_SQL_AGENT'] = 'true'
tools = tools_payload_for_engine('operational')
names = [t['function']['name'] for t in tools]
assert 'executar_sql_analitico' in names, f'Não encontrado. Tools: {names}'
print('OK — executar_sql_analitico presente no engine operational')
print(f'Total tools: {len(names)}')
"
```

Esperado: `OK — executar_sql_analitico presente no engine operational`

- [ ] **Step 3: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/services/assistant_engine_registry.py && git commit -m "feat(ai): add executar_sql_analitico ao ENGINE_OPERATIONAL para operadores"
```

---

## Task 6: Inicializar Schema Registry no Startup

**Files:**
- Modify: `sistema/app/main.py` (dentro de `startup_event`, após linha ~389)

- [ ] **Step 1: Adicionar inicialização no startup_event**

Localizar o bloco `startup_event` em `sistema/app/main.py`. Após a linha `logging.info("Tabelas verificadas/criadas com sucesso")` (linha ~389), adicionar:

```python
    # Inicializa Schema Registry para o DataAgent
    try:
        from app.ai.rag.schema_registry import SchemaRegistry
        from app.core.database import SessionLocal as _SL

        _schema_db = _SL()
        try:
            await SchemaRegistry.initialize(_schema_db)
        finally:
            _schema_db.close()
    except Exception as _schema_exc:
        logging.warning("Falha ao inicializar SchemaRegistry (não crítico): %s", _schema_exc)
```

- [ ] **Step 2: Verificar que o startup não quebra**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "
import asyncio, logging
logging.basicConfig(level=logging.WARNING)
# Testa apenas o import sem executar o startup completo
from app.ai.rag.schema_registry import SchemaRegistry
print('Import OK')
print('SchemaRegistry.initialize está disponível:', callable(SchemaRegistry.initialize))
"
```

Esperado: `Import OK` sem erros

- [ ] **Step 3: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/main.py && git commit -m "feat(ai): inicializa SchemaRegistry no startup para indexação semântica das tabelas"
```

---

## Task 7: DataAgent com Schema Context

**Files:**
- Modify: `sistema/app/ai/agents/data_agent.py`
- Modify: `sistema/app/ai/agents/tool_runner.py:101` (default max_steps)

- [ ] **Step 1: Atualizar o DataAgent**

Substituir o conteúdo inteiro de `sistema/app/ai/agents/data_agent.py`:

```python
# sistema/app/ai/agents/data_agent.py
"""DataAgent — especialista em SQL analítico com schema-awareness."""
from __future__ import annotations

import logging
from typing import Any, List, Dict, Optional

from app.ai.agents.base import BaseAgent, AgentResponse
from app.ai.tools.sql_analytics_tools import executar_sql_analitico
from app.ai.rag.schema_registry import SchemaRegistry

logger = logging.getLogger(__name__)

_BASE_SYSTEM_PROMPT = """\
Você é o Agente de Dados do Sistema COTTE. Sua especialidade é realizar consultas \
SQL analíticas nos dados da empresa para responder perguntas de negócio.

DIRETRIZES:
1. Use a ferramenta 'executar_sql_analitico' para buscar dados quando necessário.
2. SEMPRE inclua `empresa_id = :empresa_id` no WHERE ou JOIN — o executor fará o bind.
3. Para rankings: use ORDER BY + LIMIT. Para totais: use SUM/COUNT com GROUP BY.
4. Explique os resultados de forma clara, com tabela quando houver múltiplas linhas.
5. Se o SQL falhar, leia o erro e tente novamente com a correção.

REGRAS DE NEGÓCIO DO COTTE:
- Orçamentos: status = 'rascunho' | 'enviado' | 'aprovado' | 'recusado'
- Movimentações: tipo = 'entrada' | 'saida', status = 'confirmado' | 'pendente'
- Sempre filtre por empresa_id para isolar dados do tenant correto.
"""


class DataAgent(BaseAgent):
    """Agente de dados com acesso ao schema do banco via SchemaRegistry."""

    def __init__(self, model_override: Optional[str] = None):
        tools = [executar_sql_analitico.openai_schema()]
        super().__init__(
            name="DataAgent",
            system_prompt=_BASE_SYSTEM_PROMPT,
            tools=tools,
            model_override=model_override,
        )
        self._db: Any = None

    def set_db_context(self, *, db: Any) -> None:
        """Injeta db para busca de schema. Chamado por run_agent_with_tools."""
        self._db = db

    async def __call__(self, messages: List[Dict[str, Any]], **kwargs) -> AgentResponse:
        """Enriquece o system prompt com schema relevante antes de chamar o LLM."""
        system_prompt = _BASE_SYSTEM_PROMPT

        if self._db is not None:
            try:
                user_query = next(
                    (m["content"] for m in reversed(messages) if m.get("role") == "user"),
                    "",
                )
                tables = await SchemaRegistry.get_relevant_tables(
                    user_query, top_k=6, db=self._db
                )
                schema_ctx = SchemaRegistry.format_schema_context(tables)
                if schema_ctx:
                    system_prompt = _BASE_SYSTEM_PROMPT + "\n\n" + schema_ctx
            except Exception as exc:
                logger.warning("[DataAgent] Falha ao carregar schema: %s", exc)

        # Substitui temporariamente o system_prompt para a chamada do LLM
        original = self.system_prompt
        self.system_prompt = system_prompt
        try:
            return await super().__call__(messages, **kwargs)
        finally:
            self.system_prompt = original
```

- [ ] **Step 2: Atualizar max_steps em tool_runner.py**

No arquivo `sistema/app/ai/agents/tool_runner.py`, linha 101, alterar o default:

```python
# DE:
async def run_agent_with_tools(
    agent: Agent,
    messages: list[dict[str, Any]],
    db: Session,
    current_user: Usuario,
    sessao_id: str | None,
    engine: str | None,
    max_steps: int = 4,
) -> AgentResponse:

# PARA:
async def run_agent_with_tools(
    agent: Agent,
    messages: list[dict[str, Any]],
    db: Session,
    current_user: Usuario,
    sessao_id: str | None,
    engine: str | None,
    max_steps: int = 6,
) -> AgentResponse:
```

E adicionar a chamada `set_db_context` no início do loop, logo após `working_messages = list(messages)`:

```python
    tool_results: list[dict[str, Any]] = []
    working_messages = list(messages)

    # Injeta db no agente se ele suportar (ex: DataAgent para schema lookup)
    if hasattr(agent, "set_db_context"):
        agent.set_db_context(db=db)

    for _ in range(max_steps):
```

- [ ] **Step 3: Verificar imports sem erro**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "
from app.ai.agents.data_agent import DataAgent
from app.ai.agents.tool_runner import run_agent_with_tools
agent = DataAgent()
print('DataAgent criado OK, tools:', [t['function']['name'] for t in agent.tools])
"
```

Esperado: `DataAgent criado OK, tools: ['executar_sql_analitico']`

- [ ] **Step 4: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/ai/agents/data_agent.py app/ai/agents/tool_runner.py && git commit -m "feat(ai): DataAgent injeta schema do banco no prompt + max_steps 4→6"
```

---

## Task 8: Supervisor com DataAgent routing melhorado

**Files:**
- Modify: `sistema/app/ai/agents/supervisor.py`

- [ ] **Step 1: Atualizar prompt e assinatura do route()**

Substituir o conteúdo inteiro de `sistema/app/ai/agents/supervisor.py`:

```python
# sistema/app/ai/agents/supervisor.py
"""Supervisor Agent — roteia mensagens para o agente especialista correto."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.ai.agents.base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class SupervisorOutput(BaseModel):
    next_agent: Literal[
        "FinanceAgent", "SalesAgent", "InventoryAgent", "SupportAgent",
        "OperadorAgent", "DataAgent", "ConversationalAgent", "FINISH"
    ]
    reasoning: str = Field(description="Motivo curto da escolha.")


_SUPERVISOR_SYSTEM_PROMPT = """\
Você é o Supervisor do Sistema COTTE. Analise a mensagem do usuário e decida qual \
agente especialista deve tratar o pedido.

AGENTES DISPONÍVEIS:
- FinanceAgent: saldo de caixa, receitas, despesas simples, contas a pagar/receber.
- SalesAgent: criar/editar/enviar orçamentos, CRM, leads, funil de vendas.
- InventoryAgent: catálogo de produtos e serviços, materiais.
- SupportAgent: dúvidas sobre como o sistema funciona (ajuda/documentação).
- OperadorAgent: comandos diretos com ID explícito (ex: "aprovar 5", "enviar 103").
- DataAgent: USE PARA rankings, top N clientes/serviços, agrupamentos por período, \
ticket médio, crescimento, comparativos, cruzamento de dados entre tabelas, \
relatórios complexos, inadimplência, histórico. Este agente tem acesso a SQL read-only.
- ConversationalAgent: saudações, conversa livre, perguntas fora do escopo do sistema.
- FINISH: se a conversa foi concluída ou já há resposta final.

REGRAS:
1. Prefira DataAgent para qualquer pergunta que exija cruzar dados ou calcular métricas.
2. Prefira OperadorAgent quando há um número de ID explícito na mensagem.
3. Responda APENAS com JSON válido contendo 'next_agent' e 'reasoning'.
"""


class SupervisorAgent(BaseAgent):
    def __init__(self, model_override: Optional[str] = None):
        super().__init__(
            name="Supervisor",
            system_prompt=_SUPERVISOR_SYSTEM_PROMPT,
            model_override=model_override,
        )

    async def route(
        self,
        messages: List[Dict[str, str]],
        *,
        schema_context: str = "",
    ) -> SupervisorOutput:
        """Determina o próximo agente. schema_context é injetado quando disponível."""
        routing_messages = list(messages)

        if schema_context:
            routing_messages = [
                {"role": "system", "content": f"Schema disponível para DataAgent:\n{schema_context}"},
                *routing_messages,
            ]

        response = await self.__call__(
            routing_messages,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response.content)
            return SupervisorOutput(**data)
        except Exception:
            logger.warning("[Supervisor] Falha ao parsear resposta: %s", response.content)
            return SupervisorOutput(
                next_agent="ConversationalAgent",
                reasoning="Fallback por erro de parsing.",
            )
```

- [ ] **Step 2: Verificar import**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "
from app.ai.agents.supervisor import SupervisorAgent, SupervisorOutput
s = SupervisorAgent()
print('SupervisorAgent OK, prompt len:', len(s.system_prompt))
"
```

Esperado: `SupervisorAgent OK, prompt len: <número>`

- [ ] **Step 3: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/ai/agents/supervisor.py && git commit -m "feat(ai): Supervisor atualizado com DataAgent routing e injeção de schema context"
```

---

## Task 9: LangGraph — Session Registry Integration

**Files:**
- Modify: `sistema/app/routers/ai_hub.py` (linha ~1125, antes do orchestrator)
- Modify: `sistema/app/ai/graph/assistant.py` (linha ~184, specialist_agent_node)

- [ ] **Step 1: Registrar sessão no router antes do LangGraph**

Em `sistema/app/routers/ai_hub.py`, no endpoint `assistente_stream` (volta ao redor da linha 1125), adicionar o registro logo após as linhas que setam o metadata da sessão:

```python
    channel_msg.metadata["db"] = db
    channel_msg.metadata["current_user"] = current_user
    channel_msg.metadata["engine"] = engine
    channel_msg.metadata["request_id"] = _request_id_from_http(http_request)
    channel_msg.metadata["confirmation_token"] = getattr(request, "confirmation_token", None)
    channel_msg.metadata["override_args"] = getattr(request, "override_args", None)

    # Registra db/current_user no Session Registry para o LangGraph
    try:
        from app.ai.graph.session_registry import SessionRegistry
        SessionRegistry.register(
            channel_msg.sessao_id,
            db=db,
            current_user=current_user,
        )
    except Exception:
        pass  # Não crítico — LangGraph cai para legacy_runner se não encontrar
```

- [ ] **Step 2: Usar Session Registry no specialist_agent_node**

Em `sistema/app/ai/graph/assistant.py`, no `specialist_agent_node` (linha ~180), alterar o bloco que verifica `direct_agents_enabled()`:

```python
    # Localizar este bloco (linha ~184):
    if direct_agents_enabled() and db is not None and current_user is not None:
    
    # Substituir por:
    if direct_agents_enabled():
        # Tenta obter db/current_user do Session Registry (resolve serialização do LangGraph)
        if db is None or current_user is None:
            try:
                from app.ai.graph.session_registry import SessionRegistry
                ctx = SessionRegistry.get(state.get("sessao_id") or payload.get("sessao_id", ""))
                if ctx is not None:
                    db, current_user = ctx
            except Exception as _sr_exc:
                logger.warning("[LangGraph] Falha ao obter sessão do registry: %s", _sr_exc)

        if db is not None and current_user is not None:
```

O bloco completo fica:

```python
    if direct_agents_enabled():
        if db is None or current_user is None:
            try:
                from app.ai.graph.session_registry import SessionRegistry
                ctx = SessionRegistry.get(state.get("sessao_id") or payload.get("sessao_id", ""))
                if ctx is not None:
                    db, current_user = ctx
            except Exception as _sr_exc:
                logger.warning("[LangGraph] Falha ao obter sessão do registry: %s", _sr_exc)

        if db is not None and current_user is not None:
            try:
                agent = agent_class()
                response = await run_agent_with_tools(
                    agent,
                    messages=_messages_for_agent(state.get("messages") or []),
                    db=db,
                    current_user=current_user,
                    sessao_id=state.get("sessao_id") or payload.get("sessao_id"),
                    engine=payload.get("engine", "operational"),
                )
                result = {"final_text": response.content, "content": response.content}
                if response.metadata:
                    result["metadata"] = response.metadata

                updates = {
                    "result": result,
                    "next_agent": "FINISH",
                    "payload": payload,
                    "node_trace": node_trace + [{"agent": agent_name, "mode": "direct"}],
                }
                if response.content:
                    updates["messages"] = [AIMessage(content=response.content)]
                return updates
            except Exception as e:
                logger.error(f"[Specialist {agent_name}] Erro no agente direto, usando legado: {e}")
                errors.append(str(e))
                node_trace.append({"agent": agent_name, "mode": "direct", "error": str(e)})
```

- [ ] **Step 3: Verificar imports sem erro**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "
from app.ai.graph.session_registry import SessionRegistry
from app.ai.graph.assistant import specialist_agent_node, langgraph_enabled
print('Imports OK')
"
```

Esperado: `Imports OK`

- [ ] **Step 4: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/routers/ai_hub.py app/ai/graph/assistant.py && git commit -m "feat(ai): integra Session Registry no LangGraph — agentes diretos agora têm db/current_user"
```

---

## Task 10: Hub Integration — Classifier, Limites, Full Tools para Analítico

**Files:**
- Modify: `sistema/app/services/cotte_ai_hub.py` (linhas 4155, 5014-5020, 5666-5700)

- [ ] **Step 1: Aumentar _V2_MAX_ITER de 5 para 8**

Na linha 4155:

```python
# DE:
_V2_MAX_ITER = 5

# PARA:
_V2_MAX_ITER = 8
```

- [ ] **Step 2: Integrar o AnalyticalClassifier e budget dinâmico**

Em `assistente_v2_stream_core`, logo após a resolução de `intent_str` (linha ~4920, após o bloco `if not intent_str:`) e ANTES do primeiro `if intent_str == "SALDO_RAPIDO":` (linha ~5046), adicionar:

```python
    # ── Detecção de queries analíticas — bypass dos fast-paths de regex ──────
    from app.ai.analytical_classifier import classify_analytical_intent
    _analytical_intent = classify_analytical_intent(mensagem)
    _token_budget = 20_000 if _analytical_intent.is_analytical else 15_000

    if _analytical_intent.is_analytical:
        # Queries analíticas pulam todos os fast-paths e vão direto para o loop LLM
        # com o DataAgent e executar_sql_analitico habilitados.
        logger.info(
            "[stream_v2] Analytical query detectada (confidence=%.2f, triggers=%s). "
            "Bypassing fast-paths.",
            _analytical_intent.confidence,
            _analytical_intent.triggers[:3],
        )
        intent_str = "ANALISE_SQL"  # Não matcheia nenhum fast-path existente
```

- [ ] **Step 3: Substituir o token budget hardcoded**

Localizar a linha ~5699:

```python
# DE:
        if total_in > 15000:
            logger.warning("[v2_core] Token budget excedido (total_in=%s).", total_in)

# PARA:
        if total_in > _token_budget:
            logger.warning("[v2_core] Token budget excedido (total_in=%s, budget=%s).", total_in, _token_budget)
```

- [ ] **Step 4: Usar full tools payload para queries analíticas**

Logo após o bloco `tools_payload, full_tools_payload, ...` (linha ~5666):

```python
    tools_payload, full_tools_payload, reduced_tools_active, tool_profile = (
        await _v2_select_tools_payload(
            mensagem=mensagem,
            history=history,
            prompt_strategy=prompt_strategy,
            resolved_engine=resolved_engine,
        )
    )

    # Para queries analíticas: usa o conjunto completo de tools (inclui executar_sql_analitico)
    if _analytical_intent.is_analytical:
        tools_payload = list(full_tools_payload)
        reduced_tools_active = False
        tool_profile = "analytical_full"
```

- [ ] **Step 5: Verificar que o hub importa sem erro**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "
import asyncio, os
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost/test')
from app.services.cotte_ai_hub import assistente_v2_stream_core, _V2_MAX_ITER
print('Import OK, _V2_MAX_ITER =', _V2_MAX_ITER)
assert _V2_MAX_ITER == 8, f'Esperado 8, got {_V2_MAX_ITER}'
print('_V2_MAX_ITER correto')
"
```

Esperado: `Import OK, _V2_MAX_ITER = 8`

- [ ] **Step 6: Commit**

```bash
cd /home/gk/Projeto-izi/sistema && git add app/services/cotte_ai_hub.py && git commit -m "feat(ai): integra AnalyticalClassifier no hub — fast-path bypass, budget 20k, MAX_ITER 8"
```

---

## Task 11: Verificação end-to-end dos componentes

- [ ] **Step 1: Rodar todos os testes novos em conjunto**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest \
  tests/test_analytics_sql_guard.py \
  tests/test_session_registry.py \
  tests/test_analytical_classifier.py \
  tests/test_schema_registry.py \
  -v 2>&1 | tail -40
```

Esperado: todos PASSED, zero FAILED

- [ ] **Step 2: Verificar que testes existentes não quebraram**

```bash
cd /home/gk/Projeto-izi/sistema && python -m pytest \
  tests/test_ai_assistente_contract.py \
  tests/test_ai_orchestrator_facade.py \
  tests/test_analytics_engine_service.py \
  -v 2>&1 | tail -30
```

Esperado: zero FAILED (alguns skips são aceitáveis por dependência de DB)

- [ ] **Step 3: Verificar imports de todos os módulos novos**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "
from app.services.analytics_sql_guard import validate_analytics_sql, SqlValidationResult
from app.ai.graph.session_registry import SessionRegistry
from app.ai.analytical_classifier import classify_analytical_intent, AnalyticalIntent
from app.ai.rag.schema_registry import SchemaRegistry, TableSchema
from app.ai.agents.data_agent import DataAgent
from app.ai.agents.supervisor import SupervisorAgent
from app.services.assistant_engine_registry import tools_payload_for_engine
import os; os.environ['V2_SQL_AGENT'] = 'true'

# Smoke test do classifier
r = classify_analytical_intent('top 5 clientes do mês')
assert r.is_analytical, 'Classifier falhou'

# Smoke test do guard
ok = validate_analytics_sql('SELECT id FROM orcamentos WHERE empresa_id = :empresa_id UNION ALL SELECT id FROM clientes WHERE empresa_id = :empresa_id')
assert ok.ok, f'Guard bloqueou UNION: {ok.error}'

# Smoke test da engine
tools = tools_payload_for_engine('operational')
names = [t['function']['name'] for t in tools]
assert 'executar_sql_analitico' in names, 'SQL não está no engine operational'

print('✓ Todos os smoke tests passaram')
print(f'  - Classifier detecta analítico: {r.is_analytical} (triggers: {r.triggers[:2]})')
print(f'  - Guard aceita UNION: {ok.ok}')
print(f'  - SQL no engine operational: {\"executar_sql_analitico\" in names}')
print(f'  - Tools no engine: {len(names)}')
"
```

Esperado: `✓ Todos os smoke tests passaram`

- [ ] **Step 4: Commit final de verificação**

```bash
cd /home/gk/Projeto-izi/sistema && git add -A && git status
# Verificar que não há arquivos inesperados
git commit -m "test(ai): verificação end-to-end dos 7 gargalos resolvidos"
```

---

## Variáveis de Ambiente para Ativar

Após o deploy, setar no Railway (ou `.env` local):

```bash
V2_SQL_AGENT=true                    # Habilita executar_sql_analitico
V2_LANGGRAPH_DIRECT_AGENTS=true      # Habilita agentes diretos via Session Registry
V2_LANGGRAPH_ORCHESTRATION=true      # Habilita orquestração LangGraph
```

Remover ou ignorar:
```bash
ANALYTICS_SQL_ALLOWED_SOURCES=       # Substituído por blacklist no Guard v2
```
