"""Orquestração opcional via LangGraph para o assistente v2."""

from __future__ import annotations

import os
from typing import Any, Awaitable, Callable


def langgraph_enabled() -> bool:
    return os.getenv("USE_LANGGRAPH_ASSISTANT", "false").lower() == "true"


async def run_assistant_graph(
    *,
    payload: dict[str, Any],
    legacy_runner: Callable[[dict[str, Any]], Awaitable[Any]],
) -> Any:
    """
    Executa a orquestração por LangGraph quando disponível.

    Fallback:
    - se LangGraph não estiver instalado, roda o runner legado.
    """
    try:
        from langgraph.graph import StateGraph, END
    except Exception:
        return await legacy_runner(payload)

    async def execute_legacy_node(state: dict[str, Any]) -> dict[str, Any]:
        result = await legacy_runner(state["payload"])
        return {"payload": state["payload"], "result": result}

    graph = StateGraph(dict)
    graph.add_node("execute_legacy", execute_legacy_node)
    graph.set_entry_point("execute_legacy")
    graph.add_edge("execute_legacy", END)
    app = graph.compile()
    out = await app.ainvoke({"payload": payload})
    return out["result"]

