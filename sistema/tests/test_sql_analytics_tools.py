from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.ai_tools import sql_analytics_tools as svc


class _FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _FakeMappings(self._rows)


class _FakeDb:
    def __init__(self):
        self.last_stmt = None
        self.last_params = None

    def execute(self, stmt, params):
        self.last_stmt = str(stmt)
        self.last_params = params
        return _FakeResult([{"id": 10, "empresa_id": 3}])


def test_ensure_limit_envolve_query():
    out = svc._ensure_limit("SELECT id FROM orcamentos WHERE empresa_id = :empresa_id", 25)
    assert "SELECT * FROM (" in out
    assert "LIMIT :_agent_limit" in out


@pytest.mark.asyncio
async def test_executar_sql_analitico_aplica_parametros_tenant_e_limit(monkeypatch):
    db = _FakeDb()
    user = SimpleNamespace(id=9, empresa_id=3)
    audit_payload: dict = {}

    def fake_audit(*args, **kwargs):
        audit_payload.update(kwargs.get("detalhes") or {})

    monkeypatch.setattr(svc, "registrar_auditoria", fake_audit)

    out = await svc._executar_sql_analitico(
        svc.ExecutarSqlAnaliticoInput(
            sql="SELECT id, empresa_id FROM orcamentos WHERE empresa_id = :empresa_id",
            limit=40,
        ),
        db=db,
        current_user=user,
    )

    assert out.get("row_count") == 1
    assert "risk_score" in out
    assert db.last_params == {"empresa_id": 3, "_agent_limit": 40}
    assert "LIMIT :_agent_limit" in (db.last_stmt or "")
    assert audit_payload.get("tenant_scope", {}).get("empresa_id_param") == 3


@pytest.mark.asyncio
async def test_executar_sql_analitico_falha_sem_empresa():
    db = _FakeDb()
    user = SimpleNamespace(id=9, empresa_id=None)
    out = await svc._executar_sql_analitico(
        svc.ExecutarSqlAnaliticoInput(
            sql="SELECT id FROM orcamentos WHERE empresa_id = :empresa_id",
            limit=10,
        ),
        db=db,
        current_user=user,
    )
    assert out.get("code") == "tenant_scope_required"
