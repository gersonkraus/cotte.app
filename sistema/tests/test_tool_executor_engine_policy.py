from __future__ import annotations

import json

import pytest

from app.services.tool_executor import execute
from tests.conftest import make_empresa, make_usuario


@pytest.mark.asyncio
async def test_execute_blocks_tool_not_allowed_by_engine(db):
    emp = make_empresa(db, nome="Engine Policy")
    user = make_usuario(db, emp, email="engine-policy@teste.com", is_gestor=True)
    db.commit()

    tool_call = {
        "id": "t1",
        "type": "function",
        "function": {
            "name": "executar_sql_analitico",
            "arguments": json.dumps(
                {
                    "sql": "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id",
                    "limit": 10,
                }
            ),
        },
    }
    out = await execute(
        tool_call,
        db=db,
        current_user=user,
        sessao_id="sess-engine-pol",
        request_id="req-engine-pol",
        engine="operational",
    )
    assert out.status == "forbidden"
    assert out.code == "engine_tool_not_allowed"
