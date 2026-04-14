from __future__ import annotations

from app.services import assistant_engine_registry as registry


def test_tools_payload_for_internal_copilot_respects_sql_agent_flag(monkeypatch):
    monkeypatch.setattr(
        registry,
        "openai_tools_payload",
        lambda: [
            {
                "type": "function",
                "function": {"name": "executar_sql_analitico", "arguments": "{}"},
            },
            {
                "type": "function",
                "function": {"name": "analisar_tool_logs", "arguments": "{}"},
            },
        ],
    )
    monkeypatch.setattr(registry, "is_sql_agent_enabled", lambda: False)
    monkeypatch.setattr(registry, "is_code_rag_enabled", lambda: True)

    payload = registry.tools_payload_for_engine(registry.ENGINE_INTERNAL_COPILOT)
    names = [((item.get("function") or {}).get("name")) for item in payload]

    assert "executar_sql_analitico" not in names
    assert "analisar_tool_logs" in names


def test_tools_payload_for_internal_copilot_allows_sql_when_enabled(monkeypatch):
    monkeypatch.setattr(
        registry,
        "openai_tools_payload",
        lambda: [
            {
                "type": "function",
                "function": {"name": "executar_sql_analitico", "arguments": "{}"},
            },
            {
                "type": "function",
                "function": {"name": "analisar_tool_logs", "arguments": "{}"},
            },
        ],
    )
    monkeypatch.setattr(registry, "is_sql_agent_enabled", lambda: True)
    monkeypatch.setattr(registry, "is_code_rag_enabled", lambda: False)

    payload = registry.tools_payload_for_engine(registry.ENGINE_INTERNAL_COPILOT)
    names = [((item.get("function") or {}).get("name")) for item in payload]

    assert "executar_sql_analitico" in names
    assert "analisar_tool_logs" in names
