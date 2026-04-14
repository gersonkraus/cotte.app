from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import analytics_engine_service as svc


@pytest.mark.asyncio
async def test_analytics_flow_success_expoe_flow_trace_metrics(monkeypatch):
    audit_payload: dict = {}

    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        if name == "listar_movimentacoes_financeiras":
            return SimpleNamespace(status="ok", data={"total": 2}, error=None, pending_action=None)
        raise AssertionError(f"tool inesperada: {name}")

    def fake_audit(*args, **kwargs):
        audit_payload.update(kwargs.get("detalhes") or {})

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(svc, "registrar_auditoria", fake_audit)

    user = SimpleNamespace(id=50, empresa_id=2)
    out = await svc.run_analytics_flow(
        db=None,
        current_user=user,
        request_id="req-an-1",
        sessao_id="sess-an-1",
        scope="financeiro_resumo",
        dias=30,
        limit=20,
    )

    assert out["success"] is True
    assert out.get("flow_id")
    assert out["data"]["registro"]["flow_id"] == out["flow_id"]
    assert audit_payload.get("flow_id") == out["flow_id"]
    assert out["metrics"]["total_steps"] == 2


@pytest.mark.asyncio
async def test_analytics_sql_flow_disabled(monkeypatch):
    monkeypatch.setattr(svc, "is_sql_agent_enabled", lambda: False)
    user = SimpleNamespace(id=51, empresa_id=3)
    out = await svc.run_analytics_sql_query_flow(
        db=None,
        current_user=user,
        request_id="req-an-2",
        sessao_id="sess-an-2",
        sql="SELECT 1 FROM orcamentos",
        limit=10,
    )
    assert out["success"] is False
    assert out["code"] == "sql_agent_disabled"
