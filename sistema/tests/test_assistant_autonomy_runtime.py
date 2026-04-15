from types import SimpleNamespace

import pytest

from app.services.assistant_autonomy.capability_layer import build_tool_calls_for_plan
from app.services.assistant_autonomy.runtime import try_handle_semantic_autonomy
from app.services.assistant_autonomy.semantic_planner import build_semantic_plan


def test_build_tool_calls_analytics_uses_tenant_scoped_sql():
    plan = build_semantic_plan("me mostre os clientes que mais compraram neste mês")
    calls = build_tool_calls_for_plan(plan)
    assert calls
    assert calls[0].name == "executar_sql_analitico"
    assert "empresa_id = :empresa_id" in calls[0].args.get("sql", "")


def test_build_tool_calls_commission_report():
    plan = build_semantic_plan("relatório de comissão de 8% por vendedor neste trimestre")
    calls = build_tool_calls_for_plan(plan)
    assert calls
    assert calls[0].name == "executar_sql_analitico"
    assert "comissao_estimada" in calls[0].args.get("sql", "").lower()


def test_build_tool_calls_commission_report_detailed_sales():
    plan = build_semantic_plan(
        "Crie um relatório para imprimir com todas as vendas do vendedor João mostrando comissão de 8%"
    )
    calls = build_tool_calls_for_plan(plan)
    assert calls
    assert calls[0].name == "executar_sql_analitico"
    sql = calls[0].args.get("sql", "").lower()
    assert "valor_comissao" in sql
    assert "numero_orcamento" in sql


def test_build_tool_calls_composite_workflow():
    plan = build_semantic_plan("crie orçamento para cliente Joao e envie por whatsapp e e-mail")
    calls = build_tool_calls_for_plan(plan)
    assert len(calls) >= 2
    assert calls[0].name == "criar_orcamento"
    assert any(c.name == "enviar_orcamento_whatsapp" for c in calls)
    assert any(c.name == "enviar_orcamento_email" for c in calls)


@pytest.mark.asyncio
async def test_runtime_returns_none_when_disabled(monkeypatch):
    monkeypatch.setenv("V2_SEMANTIC_AUTONOMY", "false")
    out = await try_handle_semantic_autonomy(
        mensagem="quero um relatório financeiro",
        sessao_id="sess-1",
        db=None,
        current_user=SimpleNamespace(empresa_id=1, is_superadmin=False, is_gestor=True),
        engine="analytics",
        request_id="req-1",
        confirmation_token=None,
        override_args=None,
    )
    assert out is None


@pytest.mark.asyncio
async def test_runtime_blocks_when_policy_fails(monkeypatch):
    monkeypatch.setenv("V2_SEMANTIC_AUTONOMY", "true")
    monkeypatch.setattr(
        "app.services.assistant_autonomy.runtime.evaluate_policy",
        lambda **kwargs: SimpleNamespace(
            allowed=False,
            reasons=["policy_blocked"],
            risk_level="high",
        ),
    )
    out = await try_handle_semantic_autonomy(
        mensagem="quero um relatório financeiro",
        sessao_id="sess-2",
        db=None,
        current_user=SimpleNamespace(empresa_id=1, is_superadmin=False, is_gestor=True),
        engine="analytics",
        request_id="req-2",
        confirmation_token=None,
        override_args=None,
    )
    assert isinstance(out, dict)
    assert out.get("sucesso") is True
    assert "degradado por política" in (out.get("resposta") or "").lower()
    assert (out.get("dados") or {}).get("policy_degraded") is True


@pytest.mark.asyncio
async def test_runtime_degrades_when_token_budget_exceeded(monkeypatch):
    monkeypatch.setenv("V2_SEMANTIC_AUTONOMY", "true")
    monkeypatch.setenv("SEMANTIC_TOKEN_BUDGET_PER_CALL", "2000")
    out = await try_handle_semantic_autonomy(
        mensagem="x" * 12000,
        sessao_id="sess-3",
        db=None,
        current_user=SimpleNamespace(empresa_id=1, is_superadmin=False, is_gestor=True),
        engine="analytics",
        request_id="req-3",
        confirmation_token=None,
        override_args=None,
    )
    assert isinstance(out, dict)
    assert out.get("sucesso") is True
    budget = (out.get("dados") or {}).get("token_budget") or {}
    assert budget.get("allowed") is False


@pytest.mark.asyncio
async def test_runtime_includes_pending_action_when_execution_requires_confirmation(monkeypatch):
    monkeypatch.setenv("V2_SEMANTIC_AUTONOMY", "true")
    monkeypatch.setattr(
        "app.services.assistant_autonomy.runtime.evaluate_policy",
        lambda **kwargs: SimpleNamespace(
            allowed=True,
            reasons=[],
            risk_level="high",
            requires_confirmation=True,
            governance_mode="mixed_by_risk",
            recommended_engine="operational",
            allowed_export_formats=[],
            limits={"max_rows": 50},
        ),
    )

    async def _fake_execution_graph(**kwargs):
        from app.services.assistant_autonomy.contracts import ExecutionResult, ExecutionStepResult

        return ExecutionResult(
            success=True,
            capability="PrepareQuotePackage",
            trace=[
                ExecutionStepResult(step="resolve_intent", stage="resolve", status="ok", latency_ms=2),
                ExecutionStepResult(step="tool:criar_orcamento", stage="fetch", status="pending", latency_ms=8),
            ],
            outputs={"tools": []},
            metrics={"total_steps": 2, "total_duration_ms": 10, "generated_at": "2026-04-14T00:00:00+00:00"},
            pending_action={"tool": "criar_orcamento", "confirmation_token": "tok-123"},
        )

    monkeypatch.setattr(
        "app.services.assistant_autonomy.runtime.run_execution_graph",
        _fake_execution_graph,
    )

    out = await try_handle_semantic_autonomy(
        mensagem="crie um orçamento para cliente Maria",
        sessao_id="sess-4",
        db=None,
        current_user=SimpleNamespace(empresa_id=1, is_superadmin=False, is_gestor=True),
        engine="operational",
        request_id="req-4",
        confirmation_token=None,
        override_args={"cliente_nome": "Maria", "itens": [{"descricao": "Teste", "quantidade": 1, "valor_unit": 10}]},
    )
    assert out.get("sucesso") is True
    assert (out.get("pending_action") or {}).get("confirmation_token") == "tok-123"
