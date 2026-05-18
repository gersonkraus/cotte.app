"""Execucao controlada de tool calls emitidas por agentes especializados."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.ai.agents.base import Agent, AgentResponse
from app.models.models import Usuario
from app.services import tool_executor


logger = logging.getLogger(__name__)


def _get_attr_or_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _parse_args(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _tool_call_name_and_args(tool_call: Any) -> tuple[str | None, dict[str, Any]]:
    function = _get_attr_or_key(tool_call, "function")
    if function is not None:
        name = _get_attr_or_key(function, "name")
        raw_args = _get_attr_or_key(function, "arguments")
    else:
        name = _get_attr_or_key(tool_call, "name")
        raw_args = _get_attr_or_key(tool_call, "args")

    clean_name = str(name).strip() if name else ""
    return clean_name or None, _parse_args(raw_args)


async def execute(
    name: str,
    args: dict[str, Any],
    *,
    db: Session,
    current_user: Usuario,
    sessao_id: str | None = None,
    request_id: str | None = None,
    confirmation_token: str | None = None,
    engine: str | None = None,
) -> Any:
    """Adapter fino para manter o runner independente do formato bruto da tool call."""
    try:
        return await tool_executor.execute(
            name,
            args,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            confirmation_token=confirmation_token,
            engine=engine,
        )
    except TypeError as exc:
        if "positional" not in str(exc) and "required positional" not in str(exc):
            raise
        tool_call = {
            "type": "function",
            "function": {
                "name": name,
                "arguments": json.dumps(args or {}, ensure_ascii=False, default=str),
            },
        }
        return await tool_executor.execute(
            tool_call,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            confirmation_token=confirmation_token,
            engine=engine,
        )


def _tool_call_id(tool_call: Any) -> Any:
    return _get_attr_or_key(tool_call, "id")


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


async def run_agent_with_tools(
    agent: Agent,
    messages: list[dict[str, Any]],
    db: Session,
    current_user: Usuario,
    sessao_id: str | None,
    engine: str | None,
    max_steps: int = 6,
) -> AgentResponse:
    tool_results: list[dict[str, Any]] = []
    working_messages = list(messages)

    # Injeta db no agente se ele suportar (ex: DataAgent para schema lookup)
    if hasattr(agent, "set_db_context"):
        agent.set_db_context(db=db)

    for _ in range(max_steps):
        response = await agent(working_messages)
        if not response.tool_calls:
            response.metadata = dict(response.metadata or {})
            response.metadata["tool_results"] = tool_results
            return response

        working_messages.append(
            {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            }
        )

        for tool_call in response.tool_calls:
            name, args = _tool_call_name_and_args(tool_call)
            if not name:
                continue

            result = await execute(
                name,
                args,
                db=db,
                current_user=current_user,
                sessao_id=sessao_id,
                engine=engine,
            )
            payload = result.to_llm_payload()
            tool_results.append(
                {
                    "tool": name,
                    "status": getattr(result, "status", None),
                    "payload": payload,
                }
            )
            working_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": _tool_call_id(tool_call),
                    "name": name,
                    "content": _safe_json(payload),
                }
            )

    logger.warning("Agent %s reached max tool steps", getattr(agent, "name", "unknown"))
    return AgentResponse(
        content="Não consegui concluir a ação dentro do limite seguro de etapas.",
        metadata={"tool_results": tool_results, "max_steps_reached": True},
    )
