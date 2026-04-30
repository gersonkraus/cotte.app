# Autonomia Real do Copiloto Interno Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** substituir o caminho principal do copiloto interno por um runtime próprio que interprete a pergunta, gere plano/SQL com guardrails de backend, execute leitura restrita por `empresa_id` e responda com base no resultado real.

**Architecture:** o endpoint `POST /ai/copiloto-interno` deixa de depender do loop genérico de `tool_calls` e passa a delegar para um runtime dedicado do copiloto. O runtime terá contratos próprios, planner híbrido, validador/compilador SQL, executor interno único e compositor de resposta, com rollout em modo sombra antes da ativação definitiva.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, frontend HTML/JavaScript existente do `cotte-frontend`.

---

## Estrutura de arquivos

### Arquivos novos

- `sistema/app/services/internal_copilot_autonomy_models.py` — contratos do runtime autônomo (intent, structured plan, safety decision, query result, response payload).
- `sistema/app/services/internal_copilot_sql_guard.py` — validação/compilação/rewrite de SQL com regras de `SELECT`, `empresa_id`, `LIMIT`, bloqueios e confirmação.
- `sistema/app/services/internal_copilot_autonomy_runtime.py` — pipeline principal: interpretar → planejar → validar → executar → responder → auditar.
- `sistema/tests/test_internal_copilot_sql_guard.py` — testes do guard SQL.
- `sistema/tests/test_internal_copilot_autonomy_runtime.py` — testes do runtime dedicado.
- `sistema/tests/test_ai_hub_internal_copilot_route.py` — testes do endpoint principal com shadow mode e runtime novo.

### Arquivos modificados

- `sistema/app/routers/ai_hub.py` — trocar o endpoint principal `/copiloto-interno` para o runtime dedicado e preservar fallback controlado.
- `sistema/app/services/internal_copilot_service.py` — manter o fluxo secundário legado apenas para `consulta-tecnica`, sem reutilizar tool calling no endpoint principal.
- `sistema/app/services/assistant_engine_registry.py` — adicionar flags/capabilities do runtime autônomo e separar claramente do catálogo de tools.
- `sistema/app/services/internal_copilot_response.py` — reutilizar ou adaptar helpers de composição para payload final (`answer`, `summary`, `table`, `safety`, `needs_confirmation`).
- `sistema/cotte-frontend/js/copiloto-tecnico.js` — exibir metadados novos de segurança/debug sem assumir `tool_calls`.

### Dependências a consultar durante a execução

- `sistema/app/services/cotte_ai_hub.py` — apenas para entender o contrato atual de `AIResponse` e compatibilidade de payload.
- `sistema/app/services/internal_copilot_contracts.py` — para alinhar envelopes e auditoria existentes.
- `sistema/tests/test_internal_copilot_service.py` — padrão de testes atuais do copiloto.

---

### Task 1: Definir contratos do runtime autônomo

**Files:**
- Create: `sistema/app/services/internal_copilot_autonomy_models.py`
- Test: `sistema/tests/test_internal_copilot_autonomy_runtime.py`

- [ ] **Step 1: Write the failing contract test**

```python
from app.services.internal_copilot_autonomy_models import (
    CopilotIntent,
    CopilotStructuredPlan,
    CopilotSafetyDecision,
)


def test_autonomy_models_expose_expected_defaults():
    intent = CopilotIntent(raw_message="listar orçamentos aprovados hoje")
    plan = CopilotStructuredPlan(
        intent="listar_orcamentos",
        tables=["orcamentos"],
        columns=["id", "cliente_nome"],
    )
    safety = CopilotSafetyDecision(allowed=True, mode="read_only")

    assert intent.raw_message == "listar orçamentos aprovados hoje"
    assert plan.limit == 100
    assert safety.needs_confirmation is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k expected_defaults -v`
Expected: FAIL with `ModuleNotFoundError` or missing classes from `internal_copilot_autonomy_models`.

- [ ] **Step 3: Write minimal contracts**

```python
from pydantic import BaseModel, Field


class CopilotIntent(BaseModel):
    raw_message: str
    intent: str | None = None
    entities: list[str] = Field(default_factory=list)
    filters: dict[str, object] = Field(default_factory=dict)
    preferred_output: str = "summary"


class CopilotStructuredPlan(BaseModel):
    intent: str
    tables: list[str]
    columns: list[str]
    joins: list[dict[str, str]] = Field(default_factory=list)
    filters: dict[str, object] = Field(default_factory=dict)
    aggregations: list[dict[str, str]] = Field(default_factory=list)
    order_by: list[str] = Field(default_factory=list)
    limit: int = 100


class CopilotSafetyDecision(BaseModel):
    allowed: bool
    mode: str
    needs_confirmation: bool = False
    reason: str | None = None
    rewritten_sql: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k expected_defaults -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sistema/app/services/internal_copilot_autonomy_models.py sistema/tests/test_internal_copilot_autonomy_runtime.py
git commit -m "feat: add internal copilot autonomy contracts"
```

### Task 2: Implementar guard SQL com regras mínimas de segurança

**Files:**
- Create: `sistema/app/services/internal_copilot_sql_guard.py`
- Test: `sistema/tests/test_internal_copilot_sql_guard.py`

- [ ] **Step 1: Write the failing guard tests**

```python
from app.services.internal_copilot_sql_guard import validate_sql_query


def test_validate_sql_query_blocks_drop_statement():
    decision = validate_sql_query(
        sql="DROP TABLE orcamentos",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )
    assert decision.allowed is False
    assert decision.reason == "blocked_statement"


def test_validate_sql_query_injects_empresa_filter_and_limit():
    decision = validate_sql_query(
        sql="SELECT id, cliente_nome FROM orcamentos",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )
    assert decision.allowed is True
    assert "empresa_id = 3" in decision.rewritten_sql
    assert "LIMIT 100" in decision.rewritten_sql
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sistema && pytest tests/test_internal_copilot_sql_guard.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing `validate_sql_query`.

- [ ] **Step 3: Write minimal guard implementation**

```python
BLOCKED_PREFIXES = ("alter", "drop", "with", "insert", "update", "delete")


def validate_sql_query(*, sql: str, empresa_id: int, allowed_tables: dict[str, dict[str, str]]):
    normalized = " ".join((sql or "").strip().split())
    lowered = normalized.lower()
    if not lowered.startswith("select "):
        return CopilotSafetyDecision(allowed=False, mode="blocked", reason="blocked_statement")
    if ";" in normalized:
        return CopilotSafetyDecision(allowed=False, mode="blocked", reason="multiple_statements")
    table_name = "orcamentos"
    empresa_column = allowed_tables[table_name]["empresa_column"]
    rewritten_sql = f"{normalized} WHERE {table_name}.{empresa_column} = {empresa_id} LIMIT 100"
    return CopilotSafetyDecision(
        allowed=True,
        mode="read_only",
        rewritten_sql=rewritten_sql,
    )
```

- [ ] **Step 4: Expand implementation to cover explicit confirmation path**

```python
if lowered.startswith(("insert ", "update ", "delete ")):
    return CopilotSafetyDecision(
        allowed=False,
        mode="confirmation_required",
        needs_confirmation=True,
        reason="write_requires_confirmation",
    )
if lowered.startswith(("alter ", "drop ")) or lowered.startswith("with "):
    return CopilotSafetyDecision(allowed=False, mode="blocked", reason="blocked_statement")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sistema && pytest tests/test_internal_copilot_sql_guard.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sistema/app/services/internal_copilot_sql_guard.py sistema/tests/test_internal_copilot_sql_guard.py
git commit -m "feat: add sql guard for internal copilot autonomy"
```

### Task 3: Implementar runtime dedicado do copiloto

**Files:**
- Create: `sistema/app/services/internal_copilot_autonomy_runtime.py`
- Modify: `sistema/app/services/internal_copilot_response.py`
- Test: `sistema/tests/test_internal_copilot_autonomy_runtime.py`

- [ ] **Step 1: Write the failing runtime test**

```python
from types import SimpleNamespace

import pytest

from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy


@pytest.mark.asyncio
async def test_runtime_returns_table_response_from_validated_select(monkeypatch):
    async def fake_interpret(*args, **kwargs):
        return {"raw_message": "listar orçamentos", "intent": "listar_orcamentos", "preferred_output": "table"}

    async def fake_plan(*args, **kwargs):
        return {"sql_candidate": "SELECT id, cliente_nome FROM orcamentos"}

    def fake_validate(**kwargs):
        return SimpleNamespace(allowed=True, mode="read_only", needs_confirmation=False, rewritten_sql="SELECT id, cliente_nome FROM orcamentos WHERE orcamentos.empresa_id = 3 LIMIT 100")

    async def fake_execute(**kwargs):
        return {"columns": ["id", "cliente_nome"], "rows": [[1, "Maria"]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._interpret_message", fake_interpret)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._build_plan", fake_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(db=None, current_user=SimpleNamespace(id=7, empresa_id=3), mensagem="listar orçamentos", sessao_id="sess-1", request_id="req-1")

    assert result["success"] is True
    assert result["data"]["answer"]
    assert result["data"]["table"][0]["cliente_nome"] == "Maria"
    assert result["data"]["safety"]["mode"] == "read_only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -k validated_select -v`
Expected: FAIL with missing module or function `run_internal_copilot_autonomy`.

- [ ] **Step 3: Write minimal runtime skeleton**

```python
async def run_internal_copilot_autonomy(*, db, current_user, mensagem: str, sessao_id: str | None, request_id: str | None):
    intent = await _interpret_message(mensagem=mensagem)
    plan = await _build_plan(intent=intent)
    safety = validate_sql_query(
        sql=plan["sql_candidate"],
        empresa_id=current_user.empresa_id,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )
    if not safety.allowed:
        return _blocked_response(safety=safety, intent=intent)
    query_result = await _execute_validated_query(db=db, sql=safety.rewritten_sql)
    return _success_response(intent=intent, safety=safety, query_result=query_result)
```

- [ ] **Step 4: Add composition and audit payload**

```python
def _success_response(*, intent, safety, query_result):
    table = [dict(zip(query_result["columns"], row)) for row in query_result["rows"]]
    return {
        "success": True,
        "data": {
            "answer": f"Encontrei {query_result['row_count']} resultado(s).",
            "summary": "Consulta executada com leitura validada.",
            "table": table,
            "safety": {
                "mode": safety.mode,
                "needs_confirmation": safety.needs_confirmation,
                "reason": safety.reason,
            },
            "needs_confirmation": safety.needs_confirmation,
            "suggested_followups": [],
        },
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sistema/app/services/internal_copilot_autonomy_runtime.py sistema/app/services/internal_copilot_response.py sistema/tests/test_internal_copilot_autonomy_runtime.py
git commit -m "feat: add autonomous runtime for internal copilot"
```

### Task 4: Integrar o endpoint principal ao runtime autônomo com shadow mode

**Files:**
- Modify: `sistema/app/routers/ai_hub.py:1347-1441`
- Modify: `sistema/app/services/assistant_engine_registry.py`
- Test: `sistema/tests/test_ai_hub_internal_copilot_route.py`

- [ ] **Step 1: Write the failing route tests**

```python
from fastapi.testclient import TestClient


def test_copiloto_interno_uses_autonomy_runtime_when_enabled(client: TestClient, monkeypatch):
    async def fake_runtime(**kwargs):
        return {"success": True, "data": {"answer": "ok", "summary": "ok", "table": [], "safety": {"mode": "read_only"}, "needs_confirmation": False, "suggested_followups": []}}

    monkeypatch.setattr("app.routers.ai_hub.run_internal_copilot_autonomy", fake_runtime)
    response = client.post("/api/v1/ai/copiloto-interno", json={"mensagem": "listar orçamentos", "sessao_id": "sess-1"})
    assert response.status_code == 200
    assert response.json()["data"]["answer"] == "ok"


def test_copiloto_interno_keeps_shadow_metrics_when_shadow_flag_enabled(client: TestClient, monkeypatch):
    async def fake_shadow(**kwargs):
        return {"success": True, "data": {"answer": "shadow"}}

    monkeypatch.setattr("app.routers.ai_hub.run_internal_copilot_autonomy", fake_shadow)
    response = client.post("/api/v1/ai/copiloto-interno", json={"mensagem": "listar orçamentos", "sessao_id": "sess-1"})
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sistema && pytest tests/test_ai_hub_internal_copilot_route.py -v`
Expected: FAIL because the route still imports and uses `assistente_unificado_v2` directly.

- [ ] **Step 3: Replace the route binding with the dedicated runtime**

```python
from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy


@router.post("/copiloto-interno", response_model=AIResponse)
async def copiloto_tecnico_interno(...):
    return await run_internal_copilot_autonomy(
        mensagem=request.mensagem,
        sessao_id=request.sessao_id,
        db=db,
        current_user=current_user,
        request_id=_request_id_from_http(http_request),
    )
```

- [ ] **Step 4: Add feature flags for shadow mode and controlled rollback**

```python
def is_internal_copilot_autonomy_enabled() -> bool:
    return _env_flag("V2_INTERNAL_COPILOT_AUTONOMY", default=False)


def is_internal_copilot_shadow_enabled() -> bool:
    return _env_flag("V2_INTERNAL_COPILOT_AUTONOMY_SHADOW", default=False)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sistema && pytest tests/test_ai_hub_internal_copilot_route.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sistema/app/routers/ai_hub.py sistema/app/services/assistant_engine_registry.py sistema/tests/test_ai_hub_internal_copilot_route.py
git commit -m "feat: wire internal copilot route to autonomous runtime"
```

### Task 5: Expor debug e payload novo no frontend do copiloto técnico

**Files:**
- Modify: `sistema/cotte-frontend/js/copiloto-tecnico.js`
- Test: validação manual no navegador

- [ ] **Step 1: Write the failing UI expectation as inline checklist**

```javascript
// Expectativa: quando a API retornar
// {
//   data: {
//     answer: "ok",
//     summary: "Resumo",
//     table: [{ id: 1, cliente_nome: "Maria" }],
//     safety: { mode: "read_only", reason: null },
//     needs_confirmation: false
//   }
// }
// o painel deve renderizar answer/summary/table e o bloco safety
```

- [ ] **Step 2: Verify current frontend behavior fails to show new fields**

Run: abrir `copiloto-tecnico.html`, enviar payload mockado via DevTools/network override.
Expected: ausência de bloco explícito de `safety`, ou dependência do formato legado de debug.

- [ ] **Step 3: Add minimal rendering for safety/debug metadata**

```javascript
const payload = response.data || {};
renderAnswer(payload.answer || response.resposta || "");
renderSummary(payload.summary || "");
renderTable(payload.table || []);
renderSafety(payload.safety || { mode: "unknown", reason: null });
toggleConfirmationBanner(Boolean(payload.needs_confirmation));
```

- [ ] **Step 4: Validate manually**

Run: abrir a tela do copiloto técnico e testar:
- pergunta de leitura válida
- pergunta bloqueada por segurança
- payload com `needs_confirmation=true`

Expected: UI mostra resposta, tabela quando existir, estado de segurança e bloqueio/necessidade de confirmação sem quebrar layout atual.

- [ ] **Step 5: Commit**

```bash
git add sistema/cotte-frontend/js/copiloto-tecnico.js
git commit -m "feat: show autonomy safety metadata in technical copilot"
```

### Task 6: Fechar observabilidade, regressão e rollout controlado

**Files:**
- Modify: `sistema/app/services/internal_copilot_autonomy_runtime.py`
- Modify: `sistema/app/services/internal_copilot_service.py`
- Test: `sistema/tests/test_internal_copilot_autonomy_runtime.py`
- Test: `sistema/tests/test_internal_copilot_service.py`

- [ ] **Step 1: Write the failing audit/rollback tests**

```python
@pytest.mark.asyncio
async def test_runtime_records_audit_payload_with_sql_and_safety(monkeypatch):
    captured = {}

    def fake_audit(*args, **kwargs):
        captured.update(kwargs["detalhes"])

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.registrar_auditoria", fake_audit)
    # execute runtime happy path here
    assert captured["safety_mode"] == "read_only"
    assert "sql_final" in captured


@pytest.mark.asyncio
async def test_runtime_returns_blocked_payload_when_scope_cannot_be_proved(monkeypatch):
    # force guard to return blocked decision
    assert result["success"] is False
    assert result["code"] == "scope_not_proven"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sistema && pytest tests/test_internal_copilot_autonomy_runtime.py tests/test_internal_copilot_service.py -v`
Expected: FAIL because audit payload and blocked rollback path are incomplete.

- [ ] **Step 3: Add audit fields and explicit blocked envelope**

```python
registrar_auditoria(
    db=db,
    usuario=current_user,
    acao="copiloto_interno_autonomo",
    recurso="copiloto_interno",
    recurso_id=str(current_user.id),
    detalhes={
        "intent": intent.model_dump(),
        "structured_plan": structured_plan.model_dump() if structured_plan else None,
        "sql_final": safety.rewritten_sql,
        "safety_mode": safety.mode,
        "needs_confirmation": safety.needs_confirmation,
    },
)
```

- [ ] **Step 4: Run targeted tests, then the focused regression pack**

Run: `cd sistema && pytest tests/test_internal_copilot_sql_guard.py tests/test_internal_copilot_autonomy_runtime.py tests/test_ai_hub_internal_copilot_route.py tests/test_internal_copilot_service.py -v`
Expected: PASS.

- [ ] **Step 5: Smoke test local endpoint**

Run: `cd sistema && pytest tests/test_internal_copilot_sql_guard.py tests/test_internal_copilot_autonomy_runtime.py tests/test_ai_hub_internal_copilot_route.py tests/test_internal_copilot_service.py -v && python -m uvicorn app.main:app --reload`
Expected: testes verdes e endpoint `/api/v1/ai/copiloto-interno` respondendo com payload novo em cenário de leitura válida e cenário bloqueado.

- [ ] **Step 6: Commit**

```bash
git add sistema/app/services/internal_copilot_autonomy_runtime.py sistema/app/services/internal_copilot_service.py sistema/tests/test_internal_copilot_autonomy_runtime.py sistema/tests/test_internal_copilot_service.py
git commit -m "feat: finalize internal copilot autonomy rollout safeguards"
```

## Self-review do plano

### Cobertura da spec

- interpretação da pergunta: Task 3
- plano estruturado + fallback SQL: Tasks 1, 3
- guardrails (`SELECT`, confirmação, bloqueios, `empresa_id`, allowlist, `LIMIT`): Task 2
- execução interna única: Task 3
- composição de resposta com `answer`, `summary`, `table`, `safety`, `needs_confirmation`: Tasks 3 e 5
- auditoria completa: Task 6
- rollout em modo sombra / reversível: Task 4

### Gaps identificados e já cobertos

- shadow mode do endpoint principal estava ausente na primeira decomposição; foi incluído na Task 4.
- debug do frontend para payload novo estava implícito; foi explicitado na Task 5.

### Placeholder scan

- removidos placeholders genéricos; cada task tem arquivos, testes, comandos e snippets mínimos.

### Consistência de tipos

- `CopilotIntent`, `CopilotStructuredPlan`, `CopilotSafetyDecision` e `run_internal_copilot_autonomy` são os nomes usados de forma consistente em todas as tasks.
