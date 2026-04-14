"""Guard rails utilitários para escopo de tenant no assistente."""

from __future__ import annotations

from typing import Any


def sanitize_context_with_tenant(
    contexto: dict[str, Any] | None, *, empresa_id: int, usuario_id: int
) -> dict[str, Any]:
    """
    Retorna um contexto seguro para multi-tenant.

    Regras:
    - Nunca confia em `empresa_id` vindo do cliente.
    - Sempre injeta `empresa_id` e `usuario_id` do usuário autenticado.
    """
    data = dict(contexto or {})
    data["empresa_id"] = empresa_id
    data["usuario_id"] = usuario_id
    return data


def ensure_scoped_empresa_id(empresa_id: int | None) -> int:
    """Valida presença de empresa_id para operações scoping-sensitive."""
    if not empresa_id:
        raise ValueError("empresa_id é obrigatório para operação com escopo de tenant")
    return int(empresa_id)

