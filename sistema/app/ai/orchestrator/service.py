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
    def __init__(self, legacy_runner: Callable[[dict[str, Any]], Any]) -> None:
        self.legacy_runner = legacy_runner

    def run(self, message: ChannelMessage) -> ChannelResponse:
        result = self.legacy_runner(self._legacy_payload(message))
        return self._to_channel_response(result)

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
            "metadata": copy.deepcopy(message.metadata),
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
            metadata = copy.deepcopy(raw_metadata) if isinstance(raw_metadata, dict) else {}
            return ChannelResponse(text=text, metadata=metadata)
        if result is None:
            return ChannelResponse(text="")
        return ChannelResponse(text=str(result))
