from __future__ import annotations

import os
import copy
from collections.abc import Callable
from typing import Any

from app.ai.channels.types import ChannelMessage, ChannelResponse


def direct_agents_enabled() -> bool:
    raw = os.getenv("V2_LANGGRAPH_DIRECT_AGENTS")
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class AssistantOrchestrator:
    def __init__(
        self, 
        legacy_runner: Callable[[dict[str, Any]], Any],
        legacy_stream_runner: Callable[[dict[str, Any]], Any] | None = None
    ) -> None:
        self.legacy_runner = legacy_runner
        self.legacy_stream_runner = legacy_stream_runner

    def run(self, message: ChannelMessage) -> ChannelResponse:
        result = self.legacy_runner(self._legacy_payload(message))
        return self._to_channel_response(result)

    async def run_stream(self, message: ChannelMessage) -> Any:
        try:
            from app.ai.graph.assistant import langgraph_enabled
            is_langgraph = langgraph_enabled()
        except ImportError:
            is_langgraph = False

        payload = self._legacy_payload(message)

        if direct_agents_enabled() and is_langgraph:
            try:
                # Graph stream execution
                from app.ai.graph.assistant import run_assistant_v2_graph_stream
                async for event in run_assistant_v2_graph_stream(
                    message=message.text,
                    empresa_id=message.empresa_id,
                    usuario_id=message.usuario_id,
                    thread_id=message.sessao_id,
                    payload=payload,
                    legacy_runner=self.legacy_runner
                ):
                    yield event
                return
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"[AssistantOrchestrator] Falha no LangGraph, caindo para legado: {e}", exc_info=True)

        if self.legacy_stream_runner:
            async for chunk in self.legacy_stream_runner(payload):
                yield chunk
        else:
            yield "Streaming not supported by legacy runner configuration."

    def _legacy_payload(self, message: ChannelMessage) -> dict[str, Any]:
        return {
            "mensagem": message.text,
            "empresa_id": message.empresa_id,
            "usuario_id": message.usuario_id,
            "sessao_id": message.sessao_id,
            "channel": message.channel,
            "external_id": message.external_id,
            "phone": message.phone,
            "attachments": copy.deepcopy(message.attachments),
            "metadata": dict(message.metadata),
        }

    def _to_channel_response(self, result: Any) -> ChannelResponse:
        if isinstance(result, ChannelResponse):
            return result
        if isinstance(result, dict):
            text = ""
            for key in ("text", "resposta", "content", "message"):
                if key in result:
                    value = result.get(key)
                    text = "" if value is None else str(value)
                    break
            raw_metadata = result.get("metadata")
            metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
            return ChannelResponse(text=text, metadata=metadata)
        if result is None:
            return ChannelResponse(text="")
        return ChannelResponse(text=str(result))
