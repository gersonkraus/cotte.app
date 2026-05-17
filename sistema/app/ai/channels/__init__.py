"""Camada de canais do assistente IA."""

from app.ai.channels.types import ChannelKind, ChannelMessage, ChannelResponse
from app.ai.channels.web import from_web_payload
from app.ai.channels.whatsapp import from_whatsapp_payload
from app.ai.channels.voice import from_voice_payload

__all__ = [
    "ChannelKind", 
    "ChannelMessage", 
    "ChannelResponse",
    "from_web_payload",
    "from_whatsapp_payload",
    "from_voice_payload"
]
