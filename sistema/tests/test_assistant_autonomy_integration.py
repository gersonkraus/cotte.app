from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import cotte_ai_hub


@pytest.mark.asyncio
async def test_assistente_unificado_v2_prefers_semantic_runtime(monkeypatch):
    async def fake_semantic_handler(**kwargs):
        return {
            "sucesso": True,
            "resposta": "fluxo semântico",
            "confianca": 0.9,
            "modulo_origem": "assistente_autonomia",
            "dados": {"semantic_contract": {"summary": "ok"}},
        }

    async def fake_legacy(**kwargs):
        raise AssertionError("legacy não deveria ser chamado quando runtime semântico responde")

    monkeypatch.setattr("app.services.assistant_autonomy.semantic_autonomy_enabled", lambda: True)
    monkeypatch.setattr("app.services.assistant_autonomy.try_handle_semantic_autonomy", fake_semantic_handler)
    monkeypatch.setattr(cotte_ai_hub, "_assistente_unificado_v2_legacy", fake_legacy)

    user = SimpleNamespace(id=1, empresa_id=1, is_superadmin=False, is_gestor=True, permissoes={})
    out = await cotte_ai_hub.assistente_unificado_v2(
        mensagem="quero relatório financeiro",
        sessao_id="sess-sem-1",
        db=None,
        current_user=user,
        engine="analytics",
    )

    assert out.sucesso is True
    assert out.modulo_origem == "assistente_autonomia"
    assert out.resposta == "fluxo semântico"
