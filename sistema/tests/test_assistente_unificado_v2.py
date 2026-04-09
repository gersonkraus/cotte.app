"""Testes do loop assistente_unificado_v2 (Tool Use)."""
from __future__ import annotations

import asyncio
import json

import pytest

from app.services import cotte_ai_hub, ia_service as ia_service_module
from app.services.ai_tools import REGISTRY
from app.services.ai_tools._base import ToolSpec
from app.services.cotte_context_builder import SessionStore
from pydantic import BaseModel, Field
from tests.conftest import make_empresa, make_usuario


# ── Mock tool de leitura ──────────────────────────────────────────────────
class _EchoInput(BaseModel):
    txt: str = Field(min_length=1)


async def _echo_handler(inp: _EchoInput, *, db, current_user):
    return {"echo": inp.txt}


_ECHO = ToolSpec(
    name="mock_echo",
    description="echo",
    input_model=_EchoInput,
    handler=_echo_handler,
    destrutiva=False,
    permissao_recurso="ia",
    permissao_acao="leitura",
)


@pytest.fixture(autouse=True)
def _register_echo():
    REGISTRY["mock_echo"] = _ECHO
    yield
    REGISTRY.pop("mock_echo", None)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _fake_response(*, content=None, tool_calls=None, finish="stop"):
    return {
        "choices": [
            {
                "finish_reason": finish,
                "message": {"content": content or "", "tool_calls": tool_calls},
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _fake_tool_call(call_id, name, args):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def test_loop_resposta_direta(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(messages, tools=None, **kw):
        return _fake_response(content="Olá!", finish="stop")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="oi", sessao_id="sess-1", db=db, current_user=user
        )
    )
    assert out.sucesso is True
    assert "Olá" in (out.resposta or "")
    # histórico foi gravado
    hist = SessionStore.get_or_create("sess-1")
    assert any(m["role"] == "assistant" for m in hist)


def test_loop_com_tool_call_e_resposta_final(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    calls = {"n": 0}

    async def fake_chat(messages, tools=None, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _fake_response(
                tool_calls=[_fake_tool_call("c1", "mock_echo", {"txt": "ping"})],
                finish="tool_calls",
            )
        return _fake_response(content="resultado: ping", finish="stop")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="ecoa ping", sessao_id="sess-2", db=db, current_user=user
        )
    )
    assert out.sucesso is True
    assert calls["n"] == 2
    assert out.tool_trace and out.tool_trace[0]["tool"] == "mock_echo"
    assert out.tool_trace[0]["status"] == "ok"


def test_loop_pending_action_interrompe(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    # Mock destrutivo
    class _WInput(BaseModel):
        x: str

    async def _wh(inp, *, db, current_user):
        return {"ok": True}

    REGISTRY["mock_destr"] = ToolSpec(
        name="mock_destr",
        description="destrutivo",
        input_model=_WInput,
        handler=_wh,
        destrutiva=True,
        permissao_recurso="ia",
        permissao_acao="leitura",
    )

    try:
        async def fake_chat(messages, tools=None, **kw):
            return _fake_response(
                tool_calls=[_fake_tool_call("c1", "mock_destr", {"x": "a"})],
                finish="tool_calls",
            )

        monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

        out = _run(
            cotte_ai_hub.assistente_unificado_v2(
                mensagem="faz aí", sessao_id="sess-3", db=db, current_user=user
            )
        )
        assert out.pending_action is not None
        assert out.pending_action.get("tool") == "mock_destr"
        assert out.pending_action.get("confirmation_token")
        assert out.dados is not None
        assert out.dados.get("x") == "a"
        assert "input_tokens" in out.dados and "output_tokens" in out.dados
    finally:
        REGISTRY.pop("mock_destr", None)


def test_loop_limite_iteracoes(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    calls = {"n": 0}

    async def fake_chat(messages, tools=None, **kw):
        calls["n"] += 1
        # Sempre devolve uma nova tool_call → loop deve estourar em 5
        return _fake_response(
            tool_calls=[_fake_tool_call(f"c{calls['n']}", "mock_echo", {"txt": "x"})],
            finish="tool_calls",
        )

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="loop", sessao_id="sess-4", db=db, current_user=user
        )
    )
    assert calls["n"] == 5
    assert "Limite" in (out.resposta or "")
