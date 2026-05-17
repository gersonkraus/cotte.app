from typing import Any

from app.ai.channels.types import ChannelMessage

def from_voice_payload(empresa_id: int, texto_transcrito: str, usuario_id: int | None = None, sessao_id: str | None = None) -> ChannelMessage:
    return ChannelMessage(
        channel="voice",
        text=texto_transcrito or "",
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        sessao_id=sessao_id
    )
