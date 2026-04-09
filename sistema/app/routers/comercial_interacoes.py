"""
Router de Interações Comerciais — Histórico, observações,
envio WhatsApp/e-mail, lembretes e templates.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.auth import get_superadmin
from app.models.models import (
    CommercialLead,
    CommercialInteraction,
    CommercialReminder,
    CommercialTemplate,
    CommercialConfig,
    TipoInteracao,
    CanalInteracao,
    StatusLembrete,
)
from app.schemas.schemas import (
    CommercialInteractionOut,
    CommercialInteractionCreate,
    WhatsAppSend,
    EmailSend,
    TemplateCreate,
    TemplateUpdate,
    TemplateOut,
    TemplatePreview,
    ReminderCreate,
    ReminderUpdate,
    ReminderOut,
)
from app.services.whatsapp_service import enviar_mensagem_texto
from app.services.email_service import send_email_simples
from app.routers.comercial_helpers import _calcular_score, _render_template

router = APIRouter(prefix="/comercial", tags=["Comercial - Interações"])


# ═══════════════════════════════════════════════════════════════════════════════
# INTERAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/leads/{lead_id}/interactions", response_model=List[CommercialInteractionOut]
)
def list_interactions(
    lead_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Retorna histórico de interações de um lead."""
    lead = db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    return (
        db.query(CommercialInteraction)
        .filter(CommercialInteraction.lead_id == lead_id)
        .order_by(CommercialInteraction.criado_em.desc())
        .all()
    )


@router.post("/leads/{lead_id}/observacao", response_model=CommercialInteractionOut)
def add_observacao(
    lead_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Adiciona uma observação ao histórico do lead."""
    conteudo = data.get("conteudo", "")
    if not conteudo:
        raise HTTPException(
            status_code=400, detail="Conteúdo da observação é obrigatório"
        )

    lead = db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    interacao = CommercialInteraction(
        lead_id=lead_id,
        tipo=TipoInteracao.OBSERVACAO,
        canal=CanalInteracao.OUTRO,
        conteudo=conteudo,
    )
    db.add(interacao)
    lead.ultimo_contato_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(interacao)
    return interacao


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIO DE MENSAGENS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/leads/{lead_id}/whatsapp")
async def send_whatsapp(
    lead_id: int,
    data: WhatsAppSend,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Envia mensagem WhatsApp para o lead e registra interação."""
    lead = db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    if not lead.whatsapp:
        raise HTTPException(
            status_code=400, detail="Lead não possui WhatsApp cadastrado"
        )

    try:
        sucesso = await enviar_mensagem_texto(lead.whatsapp, data.mensagem)

        interacao = CommercialInteraction(
            lead_id=lead_id,
            tipo=TipoInteracao.WHATSAPP,
            canal=CanalInteracao.WHATSAPP,
            conteudo=data.mensagem,
            status_envio="enviado" if sucesso else "falha",
            enviado_em=datetime.now(timezone.utc) if sucesso else None,
        )
        db.add(interacao)
        lead.ultimo_contato_em = datetime.now(timezone.utc)
        lead.lead_score = _calcular_score(lead)
        db.commit()

        return {
            "sucesso": sucesso,
            "mensagem": "Mensagem enviada com sucesso"
            if sucesso
            else "Falha ao enviar mensagem",
        }
    except Exception as e:
        interacao = CommercialInteraction(
            lead_id=lead_id,
            tipo=TipoInteracao.WHATSAPP,
            canal=CanalInteracao.WHATSAPP,
            conteudo=data.mensagem,
            status_envio="falha",
        )
        db.add(interacao)
        db.commit()
        raise HTTPException(
            status_code=500, detail=f"Erro ao enviar WhatsApp: {str(e)}"
        )


@router.post("/leads/{lead_id}/email")
async def send_email(
    lead_id: int,
    data: EmailSend,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Envia e-mail para o lead e registra interação."""
    lead = db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    if not lead.email:
        raise HTTPException(status_code=400, detail="Lead não possui e-mail cadastrado")

    try:
        sucesso = send_email_simples(lead.email, data.assunto, data.mensagem)

        interacao = CommercialInteraction(
            lead_id=lead_id,
            tipo=TipoInteracao.EMAIL,
            canal=CanalInteracao.EMAIL,
            conteudo=f"Assunto: {data.assunto}\n\n{data.mensagem}",
            status_envio="enviado" if sucesso else "falha",
            enviado_em=datetime.now(timezone.utc) if sucesso else None,
        )
        db.add(interacao)
        lead.ultimo_contato_em = datetime.now(timezone.utc)
        lead.lead_score = _calcular_score(lead)
        db.commit()

        if not sucesso:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Não foi possível enviar o e-mail. Verifique BREVO_API_KEY ou "
                    "SMTP (host, usuário e senha) nas variáveis de ambiente do servidor."
                ),
            )

        return {"sucesso": True, "mensagem": "E-mail enviado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        interacao = CommercialInteraction(
            lead_id=lead_id,
            tipo=TipoInteracao.EMAIL,
            canal=CanalInteracao.EMAIL,
            conteudo=f"Assunto: {data.assunto}\n\n{data.mensagem}",
            status_envio="falha",
        )
        db.add(interacao)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erro ao enviar e-mail: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD LEMBRETES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/lembretes")
def list_lembretes(
    status_lembrete: Optional[StatusLembrete] = Query(None, alias="status"),
    lead_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Lista lembretes com filtros."""
    query = db.query(CommercialReminder).join(CommercialLead)
    if status_lembrete:
        query = query.filter(CommercialReminder.status == status_lembrete)
    if lead_id:
        query = query.filter(CommercialReminder.lead_id == lead_id)

    # Marcar atrasados automaticamente
    agora = datetime.now(timezone.utc)
    atrasados = (
        db.query(CommercialReminder)
        .filter(
            CommercialReminder.status == StatusLembrete.PENDENTE,
            CommercialReminder.data_hora < agora,
        )
        .all()
    )
    for r in atrasados:
        r.status = StatusLembrete.ATRASADO
    if atrasados:
        db.commit()

    lembretes = query.order_by(CommercialReminder.data_hora.asc()).all()
    result = []
    for r in lembretes:
        rd = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        rd["lead_nome_empresa"] = r.lead.nome_empresa if r.lead else None
        rd["lead_nome_responsavel"] = r.lead.nome_responsavel if r.lead else None
        result.append(rd)
    return result


@router.post("/lembretes", status_code=201)
def create_lembrete(
    data: ReminderCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria um lembrete."""
    lead = db.query(CommercialLead).filter(CommercialLead.id == data.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    reminder = CommercialReminder(**data.model_dump())
    db.add(reminder)

    interacao = CommercialInteraction(
        lead_id=data.lead_id,
        tipo=TipoInteracao.LEMBRETE,
        canal=CanalInteracao.OUTRO,
        conteudo=f"Lembrete criado: {data.titulo}",
    )
    db.add(interacao)
    db.commit()
    db.refresh(reminder)

    rd = {c.name: getattr(reminder, c.name) for c in reminder.__table__.columns}
    rd["lead_nome_empresa"] = lead.nome_empresa
    rd["lead_nome_responsavel"] = lead.nome_responsavel
    return rd


@router.patch("/lembretes/{lembrete_id}")
def update_lembrete(
    lembrete_id: int,
    data: ReminderUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza lembrete."""
    reminder = (
        db.query(CommercialReminder)
        .filter(CommercialReminder.id == lembrete_id)
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

    lead = reminder.lead
    rd = {c.name: getattr(reminder, c.name) for c in reminder.__table__.columns}
    rd["lead_nome_empresa"] = lead.nome_empresa if lead else None
    rd["lead_nome_responsavel"] = lead.nome_responsavel if lead else None
    return rd


@router.post("/lembretes/{lembrete_id}/concluir")
def concluir_lembrete(
    lembrete_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Marca lembrete como concluído."""
    reminder = (
        db.query(CommercialReminder)
        .filter(CommercialReminder.id == lembrete_id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")

    reminder.status = StatusLembrete.CONCLUIDO
    reminder.concluido_em = datetime.now(timezone.utc)
    db.commit()
    return {"status": "concluido"}


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/templates", response_model=List[TemplateOut])
def list_templates(
    tipo: Optional[str] = None,
    canal: Optional[str] = None,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Lista templates com filtros."""
    query = db.query(CommercialTemplate)
    if tipo:
        query = query.filter(CommercialTemplate.tipo == tipo)
    if canal:
        query = query.filter(CommercialTemplate.canal == canal)
    if ativo is not None:
        query = query.filter(CommercialTemplate.ativo == ativo)
    return query.order_by(CommercialTemplate.nome.asc()).all()


@router.post("/templates", response_model=TemplateOut, status_code=201)
def create_template(
    data: TemplateCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria um template."""
    tpl = CommercialTemplate(**data.model_dump())
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.get("/templates/{tpl_id}", response_model=TemplateOut)
def get_template(tpl_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Retorna um template."""
    tpl = db.query(CommercialTemplate).filter(CommercialTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return tpl


@router.patch("/templates/{tpl_id}", response_model=TemplateOut)
def update_template(
    tpl_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza um template."""
    tpl = db.query(CommercialTemplate).filter(CommercialTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(tpl, k, v)
    tpl.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/templates/{tpl_id}", status_code=204)
def delete_template(
    tpl_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Remove um template."""
    tpl = db.query(CommercialTemplate).filter(CommercialTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    db.delete(tpl)
    db.commit()
    return None


@router.post("/templates/{tpl_id}/preview")
def preview_template(
    tpl_id: int,
    lead_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Renderiza preview de template com dados de um lead."""
    tpl = db.query(CommercialTemplate).filter(CommercialTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    lead = (
        db.query(CommercialLead)
        .options(joinedload(CommercialLead.segmento_rel))
        .filter(CommercialLead.id == lead_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    config = db.query(CommercialConfig).first()
    conteudo = _render_template(tpl.conteudo, lead, config)
    assunto = _render_template(tpl.assunto, lead, config) if tpl.assunto else None
    return {"assunto": assunto, "conteudo": conteudo}
