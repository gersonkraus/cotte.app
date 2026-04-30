from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.services.internal_copilot_autonomy_models import (
    CopilotIntent,
    CopilotSafetyDecision,
    CopilotStructuredPlan,
)


@pytest.mark.asyncio
async def test_runtime_returns_table_response_from_validated_select(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    async def fake_interpret(*args, **kwargs):
        return {
            "raw_message": "listar orcamentos",
            "intent": "listar_orcamentos",
            "preferred_output": "table",
        }

    async def fake_plan(*args, **kwargs):
        return {"sql_candidate": "SELECT id, cliente_nome FROM orcamentos"}

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT id, cliente_nome FROM orcamentos WHERE orcamentos.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["id", "cliente_nome"], "rows": [[1, "Maria"]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._interpret_message", fake_interpret)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._build_plan", fake_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="listar orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["success"] is True
    assert result["data"]["answer"]
    assert result["data"]["table"][0]["cliente_nome"] == "Maria"
    assert result["data"]["safety"]["mode"] == "read_only"


@pytest.mark.asyncio
async def test_runtime_exposes_legacy_semantic_contract_compatibility(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT id, cliente_nome FROM orcamentos WHERE orcamentos.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["id", "cliente_nome"], "rows": [[1, "Maria"]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="listar orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["sucesso"] is True
    assert result["dados"]["semantic_contract"]["summary"] == "Consulta executada com leitura validada."
    assert result["dados"]["semantic_contract"]["table"][0]["cliente_nome"] == "Maria"


@pytest.mark.asyncio
async def test_runtime_builds_real_minimal_select_for_listar_orcamentos(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    def fake_validate(**kwargs):
        assert kwargs["sql"] == "SELECT id, cliente_nome FROM orcamentos"
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT id, cliente_nome FROM orcamentos WHERE orcamentos.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["id", "cliente_nome"], "rows": [[1, "Maria"]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="listar orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["success"] is True
    assert result["data"]["table"][0]["cliente_nome"] == "Maria"


@pytest.mark.asyncio
async def test_execute_validated_query_accepts_async_db_execute():
    from app.services.internal_copilot_autonomy_runtime import _execute_validated_query

    class FakeAsyncResult:
        def fetchall(self):
            return [(1, "Maria")]

        def keys(self):
            return ["id", "cliente_nome"]

    class FakeAsyncDb:
        async def execute(self, _sql):
            return FakeAsyncResult()

    result = await _execute_validated_query(db=FakeAsyncDb(), sql="SELECT id, cliente_nome FROM orcamentos")

    assert result == {
        "columns": ["id", "cliente_nome"],
        "rows": [[1, "Maria"]],
        "row_count": 1,
    }


@pytest.mark.asyncio
async def test_runtime_returns_blocked_response_when_sql_is_not_allowed(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    async def fake_interpret(*args, **kwargs):
        return {
            "raw_message": "apagar orcamentos",
            "intent": "alterar_orcamentos",
            "preferred_output": "summary",
        }

    async def fake_plan(*args, **kwargs):
        return {"sql_candidate": "DELETE FROM orcamentos"}

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=False,
            mode="confirmation_required",
            needs_confirmation=True,
            reason="write_requires_confirmation",
            rewritten_sql=None,
        )

    async def fake_execute(**kwargs):
        raise AssertionError("nao deveria executar query bloqueada")

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._interpret_message", fake_interpret)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._build_plan", fake_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="apagar orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["success"] is False
    assert result["data"]["needs_confirmation"] is True
    assert result["data"]["safety"]["reason"] == "write_requires_confirmation"


def test_autonomy_models_expose_expected_defaults():
    intent = CopilotIntent(raw_message="listar orcamentos aprovados hoje")
    plan = CopilotStructuredPlan(
        intent="listar_orcamentos",
        tables=["orcamentos"],
        columns=["id", "cliente_nome"],
    )
    safety = CopilotSafetyDecision(allowed=True, mode="read_only")

    assert intent.raw_message == "listar orcamentos aprovados hoje"
    assert plan.limit == 100
    assert safety.needs_confirmation is False


def test_copilot_intent_rejects_invalid_preferred_output():
    with pytest.raises(ValidationError):
        CopilotIntent(raw_message="listar", preferred_output="banana")


def test_copilot_structured_plan_rejects_negative_limit():
    with pytest.raises(ValidationError):
        CopilotStructuredPlan(
            intent="listar_orcamentos",
            tables=["orcamentos"],
            columns=["id"],
            limit=-1,
        )


def test_copilot_safety_decision_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        CopilotSafetyDecision(allowed=True, mode="whatever")


@pytest.mark.asyncio
async def test_runtime_records_audit_payload_with_sql_and_safety(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    captured_audit = {}

    def fake_audit(*args, **kwargs):
        captured_audit.update(kwargs.get("detalhes") or {})

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT id, cliente_nome FROM orcamentos WHERE orcamentos.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["id", "cliente_nome"], "rows": [[1, "Maria"]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.registrar_auditoria", fake_audit)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="listar orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["success"] is True
    assert captured_audit.get("safety_mode") == "read_only"
    assert captured_audit.get("needs_confirmation") is False
    assert "sql_final" in captured_audit
    assert "intent" in captured_audit
    assert "structured_plan" in captured_audit


@pytest.mark.asyncio
async def test_runtime_returns_blocked_payload_when_scope_cannot_be_proved(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    async def fake_interpret(*args, **kwargs):
        return {
            "raw_message": "DROP TABLE orcamentos",
            "intent": "destruir_dados",
            "preferred_output": "summary",
        }

    async def fake_plan(*args, **kwargs):
        return {"sql_candidate": "DROP TABLE orcamentos"}

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=False,
            mode="blocked",
            needs_confirmation=False,
            reason="blocked_statement",
            rewritten_sql=None,
        )

    async def fake_execute(**kwargs):
        raise AssertionError("nao deveria executar query bloqueada")

    def fake_audit(*args, **kwargs):
        pass

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._interpret_message", fake_interpret)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._build_plan", fake_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.registrar_auditoria", fake_audit)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="DROP TABLE orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["success"] is False
    assert result.get("code") == "scope_not_proven"
    assert result["data"]["safety"]["mode"] == "blocked"
    assert result["data"]["safety"]["reason"] == "blocked_statement"
