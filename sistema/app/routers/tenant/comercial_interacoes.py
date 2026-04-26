from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    CanalInteracao,
    StatusLembrete,
    TenantCommercialInteraction,
    TenantCommercialLead,
    TenantCommercialReminder,
    TipoInteracao,
    Usuario,
)
from app.schemas.schemas import ReminderCreate, ReminderUpdate


router = APIRouter(
    dependencies=[Depends(exigir_modulo("comercial"))],
    tags=["Tenant Comercial Interações"],
)


def _lead(db: Session, empresa_id: int, lead_id: int) -> TenantCommercialLead:
    lead = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.id == lead_id,
            TenantCommercialLead.empresa_id == empresa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


@router.get("/leads/{lead_id}/interactions")
def list_interactions(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    _lead(db, usuario.empresa_id, lead_id)
    items = (
        db.query(TenantCommercialInteraction)
        .filter(
            TenantCommercialInteraction.empresa_id == usuario.empresa_id,
            TenantCommercialInteraction.lead_id == lead_id,
        )
        .order_by(TenantCommercialInteraction.criado_em.desc())
        .all()
    )
    return items


@router.post("/lembretes", status_code=201)
def create_lembrete(
    data: ReminderCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _lead(db, usuario.empresa_id, data.lead_id)
    reminder = TenantCommercialReminder(
        empresa_id=usuario.empresa_id,
        lead_id=data.lead_id,
        titulo=data.titulo,
        descricao=data.descricao,
        data_hora=data.data_hora,
        canal_sugerido=data.canal_sugerido,
        status=StatusLembrete.PENDENTE,
    )
    db.add(reminder)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=data.lead_id,
            tipo=TipoInteracao.LEMBRETE,
            canal=CanalInteracao.SISTEMA,
            conteudo=f"Lembrete criado: {data.titulo}",
        )
    )
    db.commit()
    db.refresh(reminder)
    out = {c.name: getattr(reminder, c.name) for c in reminder.__table__.columns}
    out["lead_nome_empresa"] = lead.nome_empresa or lead.nome
    out["lead_nome_responsavel"] = lead.nome
    return out


@router.get("/lembretes")
def list_lembretes(
    status: Optional[StatusLembrete] = None,
    lead_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    q = db.query(TenantCommercialReminder).filter(
        TenantCommercialReminder.empresa_id == usuario.empresa_id
    )
    if status:
        q = q.filter(TenantCommercialReminder.status == status)
    if lead_id:
        q = q.filter(TenantCommercialReminder.lead_id == lead_id)

    agora = datetime.now(timezone.utc)
    atrasados = (
        q.filter(
            TenantCommercialReminder.status == StatusLembrete.PENDENTE,
            TenantCommercialReminder.data_hora < agora,
        )
        .all()
    )
    for r in atrasados:
        r.status = StatusLembrete.ATRASADO
    if atrasados:
        db.commit()

    lembretes = q.order_by(TenantCommercialReminder.data_hora.asc()).all()
    out = []
    for r in lembretes:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        lead = _lead(db, usuario.empresa_id, r.lead_id)
        d["lead_nome_empresa"] = lead.nome_empresa or lead.nome
        d["lead_nome_responsavel"] = lead.nome
        out.append(d)
    return out


@router.patch("/lembretes/{lembrete_id}")
def update_lembrete(
    lembrete_id: int,
    data: ReminderUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    reminder = (
        db.query(TenantCommercialReminder)
        .filter(
            TenantCommercialReminder.id == lembrete_id,
            TenantCommercialReminder.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    update = data.model_dump(exclude_unset=True)
    if update.get("status") == StatusLembrete.CONCLUIDO:
        update["concluido_em"] = datetime.now(timezone.utc)
    for k, v in update.items():
        setattr(reminder, k, v)
    db.commit()
    db.refresh(reminder)
    lead = _lead(db, usuario.empresa_id, reminder.lead_id)
    rd = {c.name: getattr(reminder, c.name) for c in reminder.__table__.columns}
    rd["lead_nome_empresa"] = lead.nome_empresa or lead.nome
    rd["lead_nome_responsavel"] = lead.nome
    return rd


@router.post("/lembretes/{lembrete_id}/concluir")
def concluir_lembrete(
    lembrete_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    reminder = (
        db.query(TenantCommercialReminder)
        .filter(
            TenantCommercialReminder.id == lembrete_id,
            TenantCommercialReminder.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    reminder.status = StatusLembrete.CONCLUIDO
    reminder.concluido_em = datetime.now(timezone.utc)
    db.commit()
    return {"status": "concluido"}
