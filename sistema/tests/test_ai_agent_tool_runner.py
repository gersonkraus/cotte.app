import json
from types import SimpleNamespace

import pytest

from app.ai.agents.base import AgentResponse, BaseAgent
from app.ai.agents.tool_runner import _tool_call_name_and_args, run_agent_with_tools


class FakeAgent(BaseAgent):
    def __init__(self, responses):
        super().__init__(name="FakeAgent", system_prompt="fake")
        self.responses = list(responses)
        self.messages_seen = []

    async def __call__(self, messages, **kwargs):
        self.messages_seen.append(list(messages))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_tool_runner_executa_tool_call_e_retorna_resposta_final(monkeypatch):
    calls = []

    async def fake_execute(
        name,
        args,
        *,
        db,
        current_user,
        sessao_id=None,
        request_id=None,
        confirmation_token=None,
        engine=None,
    ):
        calls.append(
            {
                "name": name,
                "args": args,
                "db": db,
                "current_user": current_user,
                "sessao_id": sessao_id,
                "engine": engine,
            }
        )

        class FakeResult:
            status = "ok"

            def to_llm_payload(self):
                return {"status": "ok", "data": {"saldo": 100}}

        return FakeResult()

    monkeypatch.setattr("app.ai.agents.tool_runner.execute", fake_execute)

    initial_messages = [{"role": "user", "content": "qual meu saldo?"}]
    db = object()
    current_user = SimpleNamespace(id=1, empresa_id=2)
    agent = FakeAgent(
        [
            AgentResponse(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "obter_saldo_caixa",
                            "arguments": '{"periodo":"hoje"}',
                        },
                    }
                ],
                metadata={},
            ),
            AgentResponse(content="Saldo consultado.", tool_calls=[], metadata={}),
        ]
    )

    result = await run_agent_with_tools(
        agent,
        messages=initial_messages,
        db=db,
        current_user=current_user,
        sessao_id="sess-1",
        engine="operational",
    )

    assert result.content == "Saldo consultado."
    assert calls == [
        {
            "name": "obter_saldo_caixa",
            "args": {"periodo": "hoje"},
            "db": db,
            "current_user": current_user,
            "sessao_id": "sess-1",
            "engine": "operational",
        }
    ]
    assert initial_messages == [{"role": "user", "content": "qual meu saldo?"}]

    second_step_messages = agent.messages_seen[1]
    assert second_step_messages[0] == initial_messages[0]
    assert second_step_messages[1]["role"] == "assistant"
    assert second_step_messages[1]["content"] == ""
    assert second_step_messages[1]["tool_calls"] == [
        {
            "id": "call-1",
            "type": "function",
            "function": {
                "name": "obter_saldo_caixa",
                "arguments": '{"periodo":"hoje"}',
            },
        }
    ]
    assert second_step_messages[2]["role"] == "tool"
    assert second_step_messages[2]["name"] == "obter_saldo_caixa"
    assert json.loads(second_step_messages[2]["content"]) == {
        "status": "ok",
        "data": {"saldo": 100},
    }
    assert result.metadata["tool_results"][0]["tool"] == "obter_saldo_caixa"


@pytest.mark.asyncio
async def test_tool_runner_retorna_direto_sem_tool_calls(monkeypatch):
    async def fail_execute(*args, **kwargs):
        raise AssertionError("execute nao deveria ser chamado")

    monkeypatch.setattr("app.ai.agents.tool_runner.execute", fail_execute)
    agent = FakeAgent([AgentResponse(content="Resposta direta.", metadata={"origem": "agent"})])

    result = await run_agent_with_tools(
        agent,
        messages=[{"role": "user", "content": "oi"}],
        db=object(),
        current_user=SimpleNamespace(id=1, empresa_id=2),
        sessao_id="sess-1",
        engine="operational",
    )

    assert result.content == "Resposta direta."
    assert result.metadata == {"origem": "agent", "tool_results": []}


def test_tool_call_name_and_args_parseia_argumentos_json_string():
    name, args = _tool_call_name_and_args(
        {"function": {"name": "listar_orcamentos", "arguments": '{"status":"APROVADO"}'}}
    )

    assert name == "listar_orcamentos"
    assert args == {"status": "APROVADO"}


def test_agent_response_metadata_default_e_dict():
    response = AgentResponse(content="ok")

    assert response.metadata == {}
    assert isinstance(response.metadata, dict)
