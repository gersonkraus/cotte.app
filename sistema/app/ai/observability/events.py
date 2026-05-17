"""Eventos internos padronizados para streaming, logs e UI do assistente."""
from __future__ import annotations

from typing import Any


def agent_event(agent: str, message: str) -> dict[str, Any]:
    return {"type": "agent", "agent": agent, "message": message}


def tool_event(tool: str, status: str = "running") -> dict[str, Any]:
    return {"type": "tool", "tool": tool, "status": status}


def final_event(text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "final", "text": text, "metadata": dict(metadata) if metadata is not None else {}}
