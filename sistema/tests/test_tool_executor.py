"""Testes do tool_executor (Tool Use v2)."""
from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import BaseModel, Field

from app.services import tool_executor
from app.services.ai_tools import REGISTRY
from app.services.ai_tools._base import ToolSpec
from tests.conftest import make_empresa, make_usuario


# ── Mock tools registradas só durante o teste ─────────────────────────────
class _PingInput(BaseModel):
    msg: str = Field(min_length=1, max_length=50)


async def _ping_handler(inp: _PingInput, *, db, current_user):
    return {"pong": inp.msg, "user": current_user.id}


async def _boom_handler(inp: _PingInput, *, db, current_user):
    raise RuntimeError("explodiu")


_MOCK_READ = ToolSpec(
    name="mock_ping",
    description="ping leitura para testes",
    input_model=_PingInput,
    handler=_ping_handler,
    destrutiva=False,
    permissao_recurso="ia",
    permissao_acao="leitura",
)

_MOCK_WRITE = ToolSpec(
    name="mock_write",
    description="ping destrutivo para testes",
    input_model=_PingInput,
    handler=_ping_handler,
    destrutiva=True,
    permissao_recurso="ia",
    permissao_acao="leitura",  # usa "leitura" pra passar perm; gating é destrutiva
)

_MOCK_BOOM = ToolSpec(
    name="mock_boom",
    description="handler que estoura",
    input_model=_PingInput,
    handler=_boom_handler,
    destrutiva=False,
    permissao_recurso="ia",
    permissao_acao="leitura",
)

_MOCK_FORBIDDEN = ToolSpec(
    name="mock_forbidden",
    description="exige escrita em recurso proibido",
    input_model=_PingInput,
    handler=_ping_handler,
    destrutiva=False,
    permissao_recurso="equipe",
    permissao_acao="admin",
)


@pytest.fixture(autouse=True)
def _register_mock_tools():
    for spec in (_MOCK_READ, _MOCK_WRITE, _MOCK_BOOM, _MOCK_FORBIDDEN):
        REGISTRY[spec.name] = spec
    yield
    for spec in (_MOCK_READ, _MOCK_WRITE, _MOCK_BOOM, _MOCK_FORBIDDEN):
        REGISTRY.pop(spec.name, None)


def _tc(name: str, args: dict) -> dict:
    return {
        "id": f"call_{name}",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_user(db, *, is_gestor=True):
    emp = make_empresa(db)
    return make_usuario(db, emp, is_gestor=is_gestor)


# ── Casos ────────────────────────────────────────────────────────────────
def test_unknown_tool(db):
    user = _make_user(db)
    res = _run(tool_executor.execute(_tc("nao_existe", {}), db=db, current_user=user))
    assert res.status == "unknown_tool"


def test_invalid_input(db):
    user = _make_user(db)
    res = _run(
        tool_executor.execute(_tc("mock_ping", {"msg": ""}), db=db, current_user=user)
    )
    assert res.status == "invalid_input"


def test_invalid_json_arguments(db):
    user = _make_user(db)
    bad_call = {"id": "x", "function": {"name": "mock_ping", "arguments": "{not json"}}
    res = _run(tool_executor.execute(bad_call, db=db, current_user=user))
    assert res.status == "invalid_input"


def test_forbidden(db):
    # usuário não-gestor sem nenhuma permissão → tool exige equipe:admin
    user = _make_user(db, is_gestor=False)
    user.permissoes = {}
    db.commit()
    res = _run(
        tool_executor.execute(
            _tc("mock_forbidden", {"msg": "oi"}), db=db, current_user=user
        )
    )
    assert res.status == "forbidden"


def test_destrutiva_sem_token_emite_pending(db):
    user = _make_user(db)
    res = _run(
        tool_executor.execute(
            _tc("mock_write", {"msg": "oi"}), db=db, current_user=user
        )
    )
    assert res.status == "pending"
    assert res.pending_action and res.pending_action.get("confirmation_token")


def test_destrutiva_com_token_executa(db):
    user = _make_user(db)
    args = {"msg": "oi"}
    first = _run(
        tool_executor.execute(_tc("mock_write", args), db=db, current_user=user)
    )
    assert first.status == "pending"
    token = first.pending_action["confirmation_token"]
    second = _run(
        tool_executor.execute(
            _tc("mock_write", args),
            db=db,
            current_user=user,
            confirmation_token=token,
        )
    )
    assert second.status == "ok"
    assert second.data["pong"] == "oi"


def test_token_invalido_para_args_diferentes(db):
    user = _make_user(db)
    first = _run(
        tool_executor.execute(
            _tc("mock_write", {"msg": "a"}), db=db, current_user=user
        )
    )
    token = first.pending_action["confirmation_token"]
    # Tenta consumir o token para args diferentes — deve falhar e abrir novo pending
    second = _run(
        tool_executor.execute(
            _tc("mock_write", {"msg": "b"}),
            db=db,
            current_user=user,
            confirmation_token=token,
        )
    )
    assert second.status == "pending"


def test_handler_exception(db):
    user = _make_user(db)
    res = _run(
        tool_executor.execute(
            _tc("mock_boom", {"msg": "x"}), db=db, current_user=user
        )
    )
    assert res.status == "erro"
    assert res.code == "exception"


def test_normalize_listar_orcamentos_dias_limite_e_ontem_hoje():
    n = tool_executor._normalize_tool_args(
        "listar_orcamentos",
        {
            "dias": 0,
            "limit": 999,
            "aprovado_em_de": "ontem",
            "aprovado_em_ate": "hoje",
            "status": "aprovado",
        },
    )
    assert n["dias"] == 1
    assert n["limit"] == 50
    assert n["status"] == "APROVADO"
    assert len(str(n["aprovado_em_de"])) == 10
    assert len(str(n["aprovado_em_ate"])) == 10
