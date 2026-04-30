from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.auth import criar_token
from app.routers import ai_hub as ai_hub_router
from app.services import assistant_engine_registry
from app.services.assistant_engine_registry import ENGINE_INTERNAL_COPILOT
from app.services.cotte_ai_hub import AIResponse
from tests.conftest import make_empresa, make_usuario


def _headers_for(user_id: int, token_version: int = 0) -> dict[str, str]:
    token = criar_token({"sub": str(user_id), "v": token_version})
    return {"Authorization": f"Bearer {token}"}


def test_copiloto_interno_uses_autonomy_runtime_when_enabled(http_client, db, monkeypatch):
    monkeypatch.setenv("V2_INTERNAL_COPILOT", "true")
    monkeypatch.setenv("V2_INTERNAL_COPILOT_AUTONOMY", "true")
    monkeypatch.setenv("V2_INTERNAL_COPILOT_AUTONOMY_SHADOW", "false")

    empresa = make_empresa(db)
    usuario = make_usuario(db, empresa, permissoes={"ia": "admin"})
    db.commit()

    async def fake_runtime(**kwargs):
        assert kwargs["mensagem"] == "listar orcamentos"
        assert kwargs["sessao_id"] == "sess-autonomy-1"
        return {
            "success": True,
            "data": {
                "answer": "ok",
                "summary": "resumo",
                "table": [{"id": 1, "cliente_nome": "Maria"}],
                "safety": {"mode": "read_only", "needs_confirmation": False, "reason": None},
                "needs_confirmation": False,
                "suggested_followups": [],
            },
            "sucesso": True,
            "dados": {
                "semantic_contract": {
                    "answer": "ok",
                    "summary": "resumo",
                    "table": [{"id": 1, "cliente_nome": "Maria"}],
                    "safety": {"mode": "read_only", "needs_confirmation": False, "reason": None},
                    "needs_confirmation": False,
                    "suggested_followups": [],
                }
            },
        }

    async def fake_legacy(**kwargs):
        raise AssertionError("fluxo legado nao deveria ser chamado com autonomia ativa")

    monkeypatch.setattr(ai_hub_router, "run_internal_copilot_autonomy", fake_runtime)
    monkeypatch.setattr("app.services.cotte_ai_hub.assistente_unificado_v2", fake_legacy)

    response = http_client.post(
        "/api/v1/ai/copiloto-interno",
        json={"mensagem": "listar orcamentos", "sessao_id": "sess-autonomy-1"},
        headers=_headers_for(usuario.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resposta"] == "ok"
    assert payload["modulo_origem"] == "internal_copilot_autonomy"
    assert payload["dados"]["semantic_contract"]["table"][0]["cliente_nome"] == "Maria"


def test_copiloto_interno_shadow_mode_keeps_legacy_response(http_client, db, monkeypatch):
    monkeypatch.setenv("V2_INTERNAL_COPILOT", "true")
    monkeypatch.setenv("V2_INTERNAL_COPILOT_AUTONOMY", "false")
    monkeypatch.setenv("V2_INTERNAL_COPILOT_AUTONOMY_SHADOW", "true")

    empresa = make_empresa(db)
    usuario = make_usuario(db, empresa, permissoes={"ia": "admin"})
    db.commit()

    shadow_calls: list[str] = []

    async def fake_legacy(**kwargs):
        return AIResponse(
            sucesso=True,
            resposta="legado ok",
            tipo_resposta="texto",
            confianca=0.91,
            modulo_origem="assistente_interno_legado",
            dados={"origem": "legacy"},
        )

    def fake_schedule_shadow(**kwargs):
        shadow_calls.append(kwargs["sessao_id"])

    monkeypatch.setattr(ai_hub_router, "_schedule_internal_copilot_autonomy_shadow", fake_schedule_shadow)
    monkeypatch.setattr("app.services.cotte_ai_hub.assistente_unificado_v2", fake_legacy)

    response = http_client.post(
        "/api/v1/ai/copiloto-interno",
        json={"mensagem": "listar orcamentos", "sessao_id": "sess-shadow-1"},
        headers=_headers_for(usuario.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resposta"] == "legado ok"
    assert payload["modulo_origem"] == "assistente_interno_legado"
    assert shadow_calls == ["sess-shadow-1"]


def test_internal_copilot_registry_hides_code_rag_tools_when_flag_disabled(monkeypatch):
    monkeypatch.setenv("V2_CODE_RAG", "false")
    monkeypatch.setenv("V2_SQL_AGENT", "true")

    monkeypatch.setattr(
        assistant_engine_registry,
        "openai_tools_payload",
        lambda: [
            {"function": {"name": "ler_arquivo_repositorio"}},
            {"function": {"name": "buscar_codigo_repositorio"}},
            {"function": {"name": "analisar_estrutura_html"}},
            {"function": {"name": "executar_sql_analitico"}},
            {"function": {"name": "listar_orcamentos"}},
        ],
    )

    payload = assistant_engine_registry.tools_payload_for_engine(ENGINE_INTERNAL_COPILOT)
    names = [item["function"]["name"] for item in payload]

    assert "ler_arquivo_repositorio" not in names
    assert "buscar_codigo_repositorio" not in names
    assert "analisar_estrutura_html" not in names
    assert "executar_sql_analitico" in names
    assert "listar_orcamentos" in names


@pytest.mark.asyncio
async def test_internal_copilot_shadow_worker_uses_isolated_session(monkeypatch):
    shadow_db = SimpleNamespace(info={})
    closed = []

    def fake_session_local():
        return shadow_db

    async def fake_runtime(**kwargs):
        assert kwargs["db"] is shadow_db
        assert kwargs["current_user"].empresa_id == 3
        return {"success": True}

    def fake_close():
        closed.append(True)

    shadow_db.close = fake_close

    monkeypatch.setattr(ai_hub_router, "SessionLocal", fake_session_local)
    monkeypatch.setattr(ai_hub_router, "run_internal_copilot_autonomy", fake_runtime)

    await ai_hub_router._run_internal_copilot_autonomy_shadow(
        current_user_id=7,
        current_user_empresa_id=3,
        current_user_is_superadmin=False,
        current_user_is_gestor=True,
        mensagem="listar orcamentos",
        sessao_id="sess-shadow-worker",
        request_id="req-shadow-worker",
    )

    assert closed == [True]
