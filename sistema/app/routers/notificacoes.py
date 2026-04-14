from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.auth import get_usuario_atual
from app.models.models import Notificacao, Usuario
from app.services.audit_service import registrar_auditoria

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("/", response_model=List[dict])
def listar_notificacoes(
    nao_lidas_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Lista notificações da empresa do usuário."""
    query = db.query(Notificacao).filter(Notificacao.empresa_id == usuario.empresa_id)
    if nao_lidas_only:
        query = query.filter(Notificacao.lida == False)
    notifs = query.order_by(Notificacao.criado_em.desc()).limit(limit).all()
    return [
        {
            "id": n.id,
            "tipo": n.tipo,
            "titulo": n.titulo,
            "mensagem": n.mensagem,
            "orcamento_id": n.orcamento_id,
            "lida": n.lida,
            "criado_em": n.criado_em.isoformat() if n.criado_em else None,
        }
        for n in notifs
    ]


@router.get("/contagem-nao-lidas")
def contagem_nao_lidas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Retorna o número de notificações não lidas."""
    from sqlalchemy import func
    count = db.query(func.count(Notificacao.id)).filter(
        Notificacao.empresa_id == usuario.empresa_id,
        Notificacao.lida == False,
    ).scalar()
    return {"contagem": count or 0}


@router.patch("/{notificacao_id}/lida")
def marcar_como_lida(
    notificacao_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Marca uma notificação como lida."""
    n = db.query(Notificacao).filter(
        Notificacao.id == notificacao_id,
        Notificacao.empresa_id == usuario.empresa_id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    ja_estava_lida = bool(n.lida)
    n.lida = True
    db.commit()
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="notificacao_marcada_lida",
        recurso="notificacao",
        recurso_id=str(n.id),
        detalhes={"ja_estava_lida": ja_estava_lida},
        request=request,
    )
    return {"ok": True}


@router.patch("/marcar-todas-lidas")
def marcar_todas_lidas(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Marca todas as notificações da empresa como lidas."""
    total_marcadas = db.query(Notificacao).filter(
        Notificacao.empresa_id == usuario.empresa_id,
        Notificacao.lida == False,
    ).update({"lida": True}, synchronize_session=False)
    db.commit()
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="notificacoes_marcadas_lidas",
        recurso="notificacao",
        detalhes={"total_marcadas": int(total_marcadas or 0)},
        request=request,
    )
    return {"ok": True}
