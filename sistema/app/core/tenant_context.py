"""Contexto de tenant por sessão SQLAlchemy."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

_TENANT_CONTEXT_KEY = "_tenant_context"


def _context_template() -> dict[str, Any]:
    return {
        "empresa_id": None,
        "usuario_id": None,
        "is_superadmin": False,
        "bypass": False,
        "bypass_reason": None,
        "scope_source": None,
    }


def get_tenant_context(db: Session) -> dict[str, Any]:
    """Retorna o contexto tenant associado à sessão."""
    return db.info.setdefault(_TENANT_CONTEXT_KEY, _context_template())


def clear_tenant_context(db: Session) -> None:
    """Limpa o contexto tenant da sessão."""
    db.info.pop(_TENANT_CONTEXT_KEY, None)


def set_tenant_context(
    db: Session,
    *,
    empresa_id: Optional[int],
    usuario_id: Optional[int] = None,
    is_superadmin: bool = False,
    scope_source: str = "request_auth",
) -> dict[str, Any]:
    """Associa escopo tenant à sessão atual."""
    ctx = get_tenant_context(db)
    ctx.update(
        {
            "empresa_id": int(empresa_id) if empresa_id else None,
            "usuario_id": int(usuario_id) if usuario_id else None,
            "is_superadmin": bool(is_superadmin),
            "bypass": False,
            "bypass_reason": None,
            "scope_source": scope_source,
        }
    )
    return ctx


def get_scoped_empresa_id(db: Session) -> Optional[int]:
    """Retorna o `empresa_id` ativo para scoping automático."""
    return get_tenant_context(db).get("empresa_id")


def tenant_bypass_enabled(db: Session) -> bool:
    """True quando a sessão está em modo bypass explícito."""
    return bool(get_tenant_context(db).get("bypass"))


def enable_superadmin_bypass(
    db: Session,
    *,
    usuario: Any,
    reason: str,
) -> dict[str, Any]:
    """Ativa bypass explícito de tenant para superadmin."""
    if not getattr(usuario, "is_superadmin", False):
        raise HTTPException(
            status_code=403,
            detail="Bypass de tenant permitido apenas para superadmin.",
        )
    ctx = get_tenant_context(db)
    ctx["bypass"] = True
    ctx["bypass_reason"] = reason
    ctx["is_superadmin"] = True
    return ctx
