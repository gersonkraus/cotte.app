import copy
from typing import Any

from app.ai.channels.types import ChannelMessage

def from_web_payload(payload: dict[str, Any]) -> ChannelMessage:
    text = payload.get("mensagem") or payload.get("texto") or ""
    
    metadata = {}
    if "engine" in payload:
        metadata["engine"] = payload["engine"]
    if "contexto_operacional" in payload:
        metadata["contexto_operacional"] = copy.deepcopy(payload["contexto_operacional"])
        
    return ChannelMessage(
        channel="web",
        text=text,
        empresa_id=payload.get("empresa_id"),
        usuario_id=payload.get("usuario_id"),
        sessao_id=payload.get("sessao_id"),
        metadata=metadata
    )
