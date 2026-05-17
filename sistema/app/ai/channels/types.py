"""Contratos internos para entrada e saída dos canais do assistente IA."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChannelKind = Literal["web", "whatsapp", "voice", "internal"]


class ChannelMessage(BaseModel):
    channel: ChannelKind
    text: str
    empresa_id: int
    usuario_id: int | None = None
    sessao_id: str | None = None
    external_id: str | None = None
    phone: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelResponse(BaseModel):
    text: str
    events: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
