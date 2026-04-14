"""
Serviço de auditoria: registra ações sensíveis de forma assíncrona e não-bloqueante.

Uso:
    from app.services.audit_service import registrar_auditoria

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="usuario_criado",
        recurso="usuario",
        recurso_id=str(novo.id),
        detalhes={"email": novo.email},
        request=request,  # opcional — extrai IP
    )

Ações padronizadas:
    usuario_criado, usuario_atualizado, usuario_permissao_alterada
    orcamento_aprovado, orcamento_recusado, orcamento_excluido
    financeiro_pagamento_registrado, financeiro_movimentacao_criada
    admin_impersonate
"""
import json
import logging
from typing import Optional, Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import AuditLog, Usuario

logger = logging.getLogger(__name__)


def _extrair_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    for header in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
        val = request.headers.get(header)
        if val:
            return val.split(",")[0].strip()
    return request.client.host if request.client else None


def _extrair_request_id(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    log_context = getattr(getattr(request, "state", None), "log_context", None)
    request_id = getattr(log_context, "request_id", None)
    if request_id:
        return str(request_id)
    return request.headers.get("x-request-id")


def _enriquecer_detalhes(
    detalhes: Optional[Any],
    request: Optional[Request],
) -> Optional[Any]:
    request_id = _extrair_request_id(request)
    if not request and not request_id:
        return detalhes

    request_data = {
        "request_id": request_id,
        "request_method": request.method if request else None,
        "request_path": request.url.path if request else None,
    }
    request_data = {k: v for k, v in request_data.items() if v is not None}
    if not request_data:
        return detalhes
    if detalhes is None:
        return request_data
    if isinstance(detalhes, dict):
        return {**request_data, **detalhes}
    return {"request": request_data, "payload": detalhes}


def registrar_auditoria(
    db: Session,
    usuario: Optional[Usuario],
    acao: str,
    recurso: Optional[str] = None,
    recurso_id: Optional[str] = None,
    detalhes: Optional[Any] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Insere um registro de auditoria. Falhas são logadas mas nunca propagadas —
    o fluxo principal nunca deve ser interrompido por uma falha de log.
    """
    audit_db: Optional[Session] = None
    try:
        audit_db = SessionLocal()
        detalhes = _enriquecer_detalhes(detalhes, request)
        detalhes_str = json.dumps(detalhes, ensure_ascii=False, default=str) if detalhes else None
        log = AuditLog(
            empresa_id=usuario.empresa_id if usuario else None,
            usuario_id=usuario.id if usuario else None,
            usuario_nome=usuario.nome if usuario else None,
            acao=acao,
            recurso=recurso,
            recurso_id=str(recurso_id) if recurso_id is not None else None,
            detalhes=detalhes_str,
            ip=_extrair_ip(request),
        )
        audit_db.add(log)
        audit_db.commit()
    except Exception:
        logger.exception("Falha ao registrar auditoria: acao=%s recurso=%s id=%s", acao, recurso, recurso_id)
        if audit_db is not None:
            try:
                audit_db.rollback()
            except Exception:
                pass
    finally:
        if audit_db is not None:
            audit_db.close()
