from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import internal_copilot_service as svc


def test_can_use_internal_copilot():
    assert svc.can_use_internal_copilot(is_superadmin=True, is_gestor=False) is True
    assert svc.can_use_internal_copilot(is_superadmin=False, is_gestor=True) is True
    assert svc.can_use_internal_copilot(is_superadmin=False, is_gestor=False) is False


@pytest.mark.asyncio
async def test_internal_flow_success_code_rag_sql(monkeypatch):
    audit_payload: dict = {}

    async def fake_execute_tool(tool_call, **kwargs):
        return SimpleNamespace(status="ok", data={"row_count": 1}, error=None, code=None)

    def fake_build_code_context(**kwargs):
        return {"context": "snippet", "sources": ["sistema/app/a.py"], "matches": 1}

    def fake_audit(*args, **kwargs):
        audit_payload.update(kwargs.get("detalhes") or {})

    monkeypatch.setattr(svc, "is_code_rag_enabled", lambda: True)
    monkeypatch.setattr(svc, "is_sql_agent_enabled", lambda: True)
    monkeypatch.setattr(svc, "build_code_context", fake_build_code_context)
    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(svc, "registrar_auditoria", fake_audit)

    user = SimpleNamespace(id=7, empresa_id=3)
    out = await svc.run_internal_technical_flow(
        db=None,
        current_user=user,
        request_id="req-int-1",
        sessao_id="sess-int-1",
        mensagem="erro em calcular total",
        include_code_context=True,
        sql_query="SELECT id FROM orcamentos",
        sql_limit=10,
    )
    assert out["success"] is True
    assert out.get("flow_id")
    assert out["data"]["registro"]["flow_id"] == out["flow_id"]
    assert audit_payload.get("flow_id") == out["flow_id"]


@pytest.mark.asyncio
async def test_internal_flow_sql_disabled(monkeypatch):
    monkeypatch.setattr(svc, "is_code_rag_enabled", lambda: True)
    monkeypatch.setattr(svc, "is_sql_agent_enabled", lambda: False)
    user = SimpleNamespace(id=7, empresa_id=3)
    out = await svc.run_internal_technical_flow(
        db=None,
        current_user=user,
        request_id="req-int-2",
        sessao_id="sess-int-2",
        mensagem="erro em calcular total",
        include_code_context=False,
        sql_query="SELECT id FROM orcamentos",
        sql_limit=10,
    )
    assert out["success"] is False
    assert out["code"] == "sql_agent_disabled"
