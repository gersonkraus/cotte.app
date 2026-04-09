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
    try:
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
        db.add(log)
        db.flush()  # persiste junto com o commit do chamador
    except Exception:
        logger.exception("Falha ao registrar auditoria: acao=%s recurso=%s id=%s", acao, recurso, recurso_id)
