"""Base types for AI tool registry (Tool Use / function calling)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Type

from pydantic import BaseModel

# Handler signature: async (input_model, *, db, current_user) -> dict
ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: Type[BaseModel]
    handler: ToolHandler
    destrutiva: bool = False
    cacheable_ttl: Optional[int] = None  # segundos; None = sem cache
    # Permissão exigida pelo tool_executor antes de executar
    permissao_recurso: Optional[str] = None
    permissao_acao: str = "leitura"

    def openai_schema(self) -> dict[str, Any]:
        """Retorna o schema no formato OpenAI/LiteLLM function calling."""
        params = self.input_model.model_json_schema()
        # Limpa $defs/title que o OpenAI não precisa
        params.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }
