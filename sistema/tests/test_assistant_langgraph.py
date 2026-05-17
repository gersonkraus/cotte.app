import pytest
from langchain_core.messages import HumanMessage

from app.ai.agents.supervisor import SupervisorAgent
from app.ai.agents.base import AgentResponse
from app.ai.graph import assistant as assistant_graph
from app.ai.graph.assistant import langgraph_enabled, specialist_agent_node


def test_langgraph_enabled_por_flag_v2(monkeypatch):
    monkeypatch.delenv("USE_LANGGRAPH_ASSISTANT", raising=False)
    monkeypatch.setenv("V2_LANGGRAPH_ORCHESTRATION", "true")
    assert langgraph_enabled() is True


def test_langgraph_enabled_por_flag_legada(monkeypatch):
    monkeypatch.delenv("V2_LANGGRAPH_ORCHESTRATION", raising=False)
    monkeypatch.setenv("USE_LANGGRAPH_ASSISTANT", "true")
    assert langgraph_enabled() is True


def test_langgraph_disabled_sem_flags(monkeypatch):
    monkeypatch.delenv("V2_LANGGRAPH_ORCHESTRATION", raising=False)
    monkeypatch.delenv("USE_LANGGRAPH_ASSISTANT", raising=False)
    assert langgraph_enabled() is False


@pytest.mark.asyncio
async def test_supervisor_fallback_quando_modelo_retorna_json_invalido(monkeypatch):
    async def fake_call(self, messages, **kwargs):
        class FakeResponse:
            content = "nao eh json"

        return FakeResponse()

    monkeypatch.setattr(SupervisorAgent, "__call__", fake_call)

    result = await SupervisorAgent().route([{"role": "user", "content": "ola"}])

    assert result.next_agent == "ConversationalAgent"
    assert "Fallback" in result.reasoning


def _specialist_state(messages=None, **payload_overrides):
    payload = {"engine": "operational", **payload_overrides}
    return {
        "messages": messages or [HumanMessage(content="qual meu saldo?")],
        "empresa_id": 5,
        "usuario_id": 7,
        "sessao_id": "sess-state",
        "payload": payload,
        "errors": [],
        "node_trace": [],
    }


class FakeDirectAgent:
    instances = []

    def __init__(self):
        self.name = "FakeDirectAgent"
        FakeDirectAgent.instances.append(self)


@pytest.mark.asyncio
async def test_specialist_agent_node_flag_falsa_usa_legacy_runner(monkeypatch):
    monkeypatch.delenv("V2_LANGGRAPH_DIRECT_AGENTS", raising=False)
    monkeypatch.setattr(assistant_graph, "_log_node_telemetry", lambda *args, **kwargs: None)
    direct_calls = []
    legacy_calls = []

    async def fake_direct(*args, **kwargs):
        direct_calls.append((args, kwargs))
        return AgentResponse(content="direto")

    async def fake_legacy(payload):
        legacy_calls.append(payload)
        return {"final_text": "Resposta legada"}

    monkeypatch.setattr(assistant_graph, "run_agent_with_tools", fake_direct, raising=False)

    result = await specialist_agent_node(
        _specialist_state(db=object(), current_user=object()),
        agent_name="FinanceAgent",
        agent_class=FakeDirectAgent,
        legacy_runner=fake_legacy,
    )

    assert result["result"] == {"final_text": "Resposta legada"}
    assert legacy_calls
    assert direct_calls == []


@pytest.mark.asyncio
async def test_specialist_agent_node_flag_true_usa_runner_direto(monkeypatch):
    monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", "true")
    monkeypatch.setattr(assistant_graph, "_log_node_telemetry", lambda *args, **kwargs: None)
    FakeDirectAgent.instances = []
    db = object()
    current_user = object()
    direct_calls = []
    legacy_calls = []

    async def fake_direct(agent, messages, **kwargs):
        direct_calls.append({"agent": agent, "messages": messages, **kwargs})
        return AgentResponse(content="Resposta direta", metadata={"origem": "direct"})

    async def fake_legacy(payload):
        legacy_calls.append(payload)
        return {"final_text": "Resposta legada"}

    monkeypatch.setattr(assistant_graph, "run_agent_with_tools", fake_direct, raising=False)

    result = await specialist_agent_node(
        _specialist_state(
            messages=[{"role": "user", "content": "qual meu saldo?"}],
            db=db,
            current_user=current_user,
        ),
        agent_name="FinanceAgent",
        agent_class=FakeDirectAgent,
        legacy_runner=fake_legacy,
    )

    assert legacy_calls == []
    assert len(FakeDirectAgent.instances) == 1
    assert direct_calls == [
        {
            "agent": FakeDirectAgent.instances[0],
            "messages": [{"role": "user", "content": "qual meu saldo?"}],
            "db": db,
            "current_user": current_user,
            "sessao_id": "sess-state",
            "engine": "operational",
        }
    ]
    assert result["result"]["final_text"] == "Resposta direta"
    assert result["result"]["metadata"] == {"origem": "direct"}
    assert result["node_trace"][-1]["agent"] == "FinanceAgent"


@pytest.mark.asyncio
async def test_specialist_agent_node_flag_true_sem_contexto_cai_para_legacy(monkeypatch):
    monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", "true")
    monkeypatch.setattr(assistant_graph, "_log_node_telemetry", lambda *args, **kwargs: None)
    direct_calls = []
    legacy_calls = []

    async def fake_direct(*args, **kwargs):
        direct_calls.append((args, kwargs))
        return AgentResponse(content="direto")

    async def fake_legacy(payload):
        legacy_calls.append(payload)
        return {"final_text": "Resposta legada"}

    monkeypatch.setattr(assistant_graph, "run_agent_with_tools", fake_direct, raising=False)

    result = await specialist_agent_node(
        _specialist_state(),
        agent_name="FinanceAgent",
        agent_class=FakeDirectAgent,
        legacy_runner=fake_legacy,
    )

    assert result["result"] == {"final_text": "Resposta legada"}
    assert legacy_calls
    assert direct_calls == []


@pytest.mark.asyncio
async def test_specialist_agent_node_runner_direto_com_erro_cai_para_legacy(monkeypatch):
    monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", "true")
    monkeypatch.setattr(assistant_graph, "_log_node_telemetry", lambda *args, **kwargs: None)
    legacy_calls = []

    async def fake_direct(*args, **kwargs):
        raise RuntimeError("falha direta")

    async def fake_legacy(payload):
        legacy_calls.append(payload)
        return {"final_text": "Resposta legada"}

    monkeypatch.setattr(assistant_graph, "run_agent_with_tools", fake_direct, raising=False)

    result = await specialist_agent_node(
        _specialist_state(db=object(), current_user=object()),
        agent_name="FinanceAgent",
        agent_class=FakeDirectAgent,
        legacy_runner=fake_legacy,
    )

    assert result["result"] == {"final_text": "Resposta legada"}
    assert legacy_calls
    assert "falha direta" in result["errors"][-1]
