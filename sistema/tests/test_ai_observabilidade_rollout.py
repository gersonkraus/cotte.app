from __future__ import annotations

import uuid

import pytest

from app.core.auth import criar_token
from app.models.models import Empresa, ToolCallLog, Usuario
from tests.conftest import TestingSessionLocal


async def _create_superadmin_token() -> str:
    with TestingSessionLocal() as db:
        empresa = Empresa(
            nome=f"Empresa SA {uuid.uuid4().hex[:8]}",
            telefone_operador=f"5511{uuid.uuid4().int % 10**8:08d}",
            ativo=True,
            plano="pro",
        )
        db.add(empresa)
        db.commit()
        db.refresh(empresa)

        usuario = Usuario(
            empresa_id=empresa.id,
            nome="Superadmin Teste",
            email=f"superadmin_{uuid.uuid4().hex[:10]}@teste.com",
            senha_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehash12",
            ativo=True,
            is_gestor=True,
            is_superadmin=True,
            token_versao=1,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return criar_token(data={"sub": str(usuario.id), "v": 1})


@pytest.mark.asyncio
async def test_observabilidade_resumo_contract(client, admin_token, db_session, empresa_id):
    db_session.add(
        ToolCallLog(
            empresa_id=empresa_id,
            usuario_id=None,
            sessao_id="sess-obsv-1",
            tool="listar_orcamentos",
            args_json={"_meta": {"engine": "operational"}},
            resultado_json={"ok": True},
            status="ok",
            latencia_ms=120,
        )
    )
    await db_session.commit()

    resp = await client.get(
        "/api/v1/ai/observabilidade/resumo?hours=24",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert "overview" in data
    assert "engines" in data
    overview = data.get("overview") or {}
    assert "total_tool_calls" in overview
    assert "error_rate_pct" in overview


@pytest.mark.asyncio
async def test_rollout_status_contract(client, admin_token):
    resp = await client.get(
        "/api/v1/ai/rollout/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert "rollout" in data
    assert "available_engines" in data
    assert "effective_available_engines" in data


@pytest.mark.asyncio
async def test_rollout_plan_requires_superadmin(client, admin_token):
    resp_get = await client.get(
        "/api/v1/ai/rollout/plan",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_get.status_code == 403

    resp_put = await client.put(
        "/api/v1/ai/rollout/plan",
        json={"default_phase": "pilot", "companies": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_put.status_code == 403


@pytest.mark.asyncio
async def test_rollout_plan_superadmin_update_and_read(client):
    superadmin_token = await _create_superadmin_token()
    payload = {
        "default_phase": "pilot",
        "companies": [
            {
                "empresa_id": 123,
                "phase": "ga",
                "enabled_engines": ["operational", "analytics"],
                "notes": "rollout canary",
            }
        ],
    }
    put_resp = await client.put(
        "/api/v1/ai/rollout/plan",
        json=payload,
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert put_resp.status_code == 200
    put_data = put_resp.json().get("data") or {}
    assert put_data.get("default_phase") == "pilot"
    assert "123" in (put_data.get("companies") or {})

    get_resp = await client.get(
        "/api/v1/ai/rollout/plan",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json().get("data") or {}
    assert get_data.get("default_phase") == "pilot"
