import copy
from typing import Any

from app.ai.channels.types import ChannelMessage

def from_whatsapp_payload(empresa_id: int, telefone: str, mensagem: str, contexto_extra: dict[str, Any] | None = None) -> ChannelMessage:
    metadata = copy.deepcopy(contexto_extra) if contexto_extra else {}
    
    return ChannelMessage(
        channel="whatsapp",
        text=mensagem or "",
        empresa_id=empresa_id,
        phone=telefone,
        metadata=metadata
    )
