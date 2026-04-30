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
async def test_runtime_builds_count_for_quantidade_orcamentos_aprovados(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    def fake_validate(**kwargs):
        assert kwargs["sql"] == "SELECT COUNT(*) as total FROM orcamentos WHERE status = 'APROVADO'"
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT COUNT(*) as total FROM orcamentos WHERE status = 'APROVADO' AND orcamentos.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["total"], "rows": [[42]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="quantidade de orcamentos aprovados",
        sessao_id="sess-count-1",
        request_id="req-count-1",
    )

    assert result["success"] is True
    assert result["data"]["table"][0]["total"] == 42


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
async def test_runtime_returns_textual_fallback_when_sql_is_not_allowed(monkeypatch):
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

    async def fake_textual_fallback(*, mensagem, llm_rationale):
        return {"answer": "Nao foi possivel gerar uma consulta para esse pedido.", "input_tokens": 0, "output_tokens": 0}

    def fake_audit(*args, **kwargs):
        pass

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._interpret_message", fake_interpret)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._build_plan", fake_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._ask_llm_textual_fallback", fake_textual_fallback)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.registrar_auditoria", fake_audit)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="apagar orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["success"] is True
    assert "Nao foi possivel" in result["data"]["answer"]


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
async def test_runtime_returns_textual_fallback_when_scope_cannot_be_proved(monkeypatch):
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

    async def fake_textual_fallback(*, mensagem, llm_rationale):
        return {"answer": "Nao foi possivel gerar uma consulta para esse pedido.", "input_tokens": 0, "output_tokens": 0}

    def fake_audit(*args, **kwargs):
        pass

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._interpret_message", fake_interpret)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._build_plan", fake_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._ask_llm_textual_fallback", fake_textual_fallback)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.registrar_auditoria", fake_audit)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="DROP TABLE orcamentos",
        sessao_id="sess-1",
        request_id="req-1",
    )

    assert result["success"] is True
    assert "Nao foi possivel" in result["data"]["answer"]


@pytest.mark.asyncio
async def test_runtime_uses_llm_planner_when_enabled(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy
    from app.services.assistant_autonomy.llm_sql_planner import LLMSqlPlan

    def fake_enabled():
        return True

    async def fake_llm_plan(message, *, period_days, historico=""):
        return LLMSqlPlan(
            sql="SELECT COUNT(*) as total FROM clientes",
            rationale="Contagem de clientes solicitada",
            used=True,
        )

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT COUNT(*) as total FROM clientes WHERE clientes.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["total"], "rows": [[15]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.llm_sql_planner_enabled", fake_enabled)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.try_generate_sql_from_llm", fake_llm_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="quantos clientes temos",
        sessao_id="sess-llm-1",
        request_id="req-llm-1",
    )

    assert result["success"] is True
    assert result["data"]["table"][0]["total"] == 15
    assert result["data"]["llm_rationale"] == "Contagem de clientes solicitada"
    assert result["dados"]["semantic_contract"]["llm_rationale"] == "Contagem de clientes solicitada"


@pytest.mark.asyncio
async def test_runtime_falls_back_to_hardcoded_when_llm_disabled(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy

    def fake_enabled():
        return False

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

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.llm_sql_planner_enabled", fake_enabled)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="listar orcamentos",
        sessao_id="sess-fb-1",
        request_id="req-fb-1",
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_runtime_interpret_sets_llm_query_for_unknown_intents(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import _interpret_message

    result = await _interpret_message(
        mensagem="quantas vendas tivemos este mês",
        current_user=SimpleNamespace(id=7, empresa_id=3),
        sessao_id=None,
        request_id=None,
    )

    assert result["intent"] == "llm_query"
    assert result["preferred_output"] == "table"


@pytest.mark.asyncio
async def test_runtime_llm_planner_failure_triggers_textual_fallback(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy
    from app.services.assistant_autonomy.llm_sql_planner import LLMSqlPlan

    def fake_enabled():
        return True

    async def fake_llm_plan(message, *, period_days, historico=""):
        return LLMSqlPlan(sql=None, rationale="Falha no LLM", used=False)

    async def fake_textual_fallback(*, mensagem, llm_rationale):
        return {"answer": "Nao foi possivel gerar uma consulta para esse pedido. Tente reformular com termos mais especificos.", "input_tokens": 0, "output_tokens": 0}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.llm_sql_planner_enabled", fake_enabled)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.try_generate_sql_from_llm", fake_llm_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._ask_llm_textual_fallback", fake_textual_fallback)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="algo que o LLM nao consegue",
        sessao_id="sess-fail-1",
        request_id="req-fail-1",
    )

    assert result["success"] is True
    assert "Nao foi possivel" in result["data"]["answer"]


@pytest.mark.asyncio
async def test_runtime_includes_llm_rationale_in_audit(monkeypatch):
    from app.services.internal_copilot_autonomy_runtime import run_internal_copilot_autonomy
    from app.services.assistant_autonomy.llm_sql_planner import LLMSqlPlan

    captured_audit = {}

    def fake_audit(*args, **kwargs):
        captured_audit.update(kwargs.get("detalhes") or {})

    def fake_enabled():
        return True

    async def fake_llm_plan(message, *, period_days, historico=""):
        return LLMSqlPlan(
            sql="SELECT COUNT(*) as total FROM orcamentos",
            rationale="LLM resolveu contar orcamentos",
            used=True,
        )

    def fake_validate(**kwargs):
        return SimpleNamespace(
            allowed=True,
            mode="read_only",
            needs_confirmation=False,
            reason=None,
            rewritten_sql="SELECT COUNT(*) as total FROM orcamentos WHERE orcamentos.empresa_id = 3 LIMIT 100",
        )

    async def fake_execute(**kwargs):
        return {"columns": ["total"], "rows": [[10]], "row_count": 1}

    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.llm_sql_planner_enabled", fake_enabled)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.try_generate_sql_from_llm", fake_llm_plan)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.validate_sql_query", fake_validate)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime._execute_validated_query", fake_execute)
    monkeypatch.setattr("app.services.internal_copilot_autonomy_runtime.registrar_auditoria", fake_audit)

    result = await run_internal_copilot_autonomy(
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=3),
        mensagem="total de orcamentos",
        sessao_id="sess-ra-1",
        request_id="req-ra-1",
    )

    assert result["success"] is True
    assert captured_audit.get("llm_rationale") == "LLM resolveu contar orcamentos"


def test_schema_context_provides_allowed_tables():
    from app.services.assistant_autonomy.schema_context import get_allowed_tables_for_guard

    tables = get_allowed_tables_for_guard()
    assert "orcamentos" in tables
    assert "clientes" in tables
    assert "servicos" in tables
    assert "agendamentos" in tables
    assert "contas_financeiras" in tables
    assert "commercial_leads" in tables
    assert tables["orcamentos"]["empresa_column"] == "empresa_id"
