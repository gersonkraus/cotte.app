from app.ai.observability.events import agent_event, final_event, tool_event


def test_agent_event_padronizado():
    event = agent_event("FinanceAgent", "Consultando financeiro")

    assert event["type"] == "agent"
    assert event["agent"] == "FinanceAgent"
    assert event["message"] == "Consultando financeiro"


def test_tool_event_nao_expoe_args_por_padrao():
    event = tool_event("listar_orcamentos", status="ok")

    assert event["type"] == "tool"
    assert event["tool"] == "listar_orcamentos"
    assert event["status"] == "ok"
    assert "args" not in event
    assert "arguments" not in event
    assert "input" not in event


def test_final_event_preserva_metadata():
    event = final_event("ok", metadata={"engine": "langgraph"})

    assert event["type"] == "final"
    assert event["text"] == "ok"
    assert event["metadata"]["engine"] == "langgraph"


def test_final_event_metadata_default_sem_mutabilidade_compartilhada():
    first = final_event("primeiro")
    first["metadata"]["engine"] = "langgraph"
    second = final_event("segundo")

    assert second["metadata"] == {}


def test_final_event_copia_metadata_recebida():
    metadata = {"engine": "langgraph"}
    event = final_event("ok", metadata=metadata)

    metadata["engine"] = "legacy"

    assert event["metadata"] == {"engine": "langgraph"}
