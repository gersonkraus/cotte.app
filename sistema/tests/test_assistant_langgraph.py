from app.services.assistant_langgraph import langgraph_enabled


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
