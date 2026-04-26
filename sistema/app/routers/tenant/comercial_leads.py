"""Leads comerciais tenant — CRUD, listagem filtrada, dashboard aux, interações (sem criar usuário/senha)."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    CanalInteracao,
    LeadScore,
    TenantCommercialInteraction,
    TenantCommercialLead,
    TenantCommercialLeadSource,
    TenantCommercialSegment,
    TenantPipelineEtapa,
    TipoInteracao,
    Usuario,
)
from app.routers.tenant.tenant_comercial_serialization import (
    sync_lead_status_from_etapa,
    tenant_lead_to_out,
)


class LeadBase(BaseModel):
    nome: Optional[str] = None
    nome_responsavel: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    whatsapp: Optional[str] = None
    cidade: Optional[str] = None
    segmento: Optional[str] = None
    segmento_id: Optional[int] = None
    origem: Optional[str] = None
    origem_lead_id: Optional[int] = None
    etapa_pipeline_id: Optional[int] = None
    valor_estimado: Optional[Decimal] = None
    valor_proposto: Optional[Decimal] = None
    interesse_plano: Optional[str] = None
    observacoes: Optional[str] = None
    responsavel_id: Optional[int] = None
    empresa_id: Optional[int] = None
    nome_empresa: Optional[str] = None
    status_pipeline: Optional[str] = None
    lead_score: Optional[LeadScore] = None
    proximo_contato_em: Optional[datetime] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    segmento: Optional[str] = None
    origem: Optional[str] = None
    etapa_pipeline_id: Optional[int] = None
    valor_estimado: Optional[Decimal] = None
    observacoes: Optional[str] = None
    responsavel_id: Optional[int] = None
    nome_empresa: Optional[str] = None
    status_pipeline: Optional[str] = None
    lead_score: Optional[LeadScore] = None
    proximo_contato_em: Optional[datetime] = None
    ultimo_contato_em: Optional[datetime] = None
    ativo: Optional[bool] = None


class LeadResponse(LeadBase):
    id: int
    empresa_id: int
    ativo: bool
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int


class MoveEtapaRequest(BaseModel):
    etapa_id: int


class ObservacaoBody(BaseModel):
    conteudo: str


class MensagemBody(BaseModel):
    mensagem: str


class EmailBody(BaseModel):
    assunto: str
    mensagem: str


router = APIRouter(
    prefix="/leads",
    tags=["Tenant Comercial Leads"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


def _buscar_lead(db: Session, empresa_id: int, lead_id: int, incluir_inativos: bool = False) -> TenantCommercialLead:
    q = db.query(TenantCommercialLead).filter(
        TenantCommercialLead.id == lead_id,
        TenantCommercialLead.empresa_id == empresa_id,
    )
    if not incluir_inativos:
        q = q.filter(TenantCommercialLead.ativo.is_(True))
    lead = q.first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


def _etapa_padrao(db: Session, empresa_id: int) -> Optional[int]:
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.empresa_id == empresa_id,
            TenantPipelineEtapa.ativo.is_(True),
        )
        .order_by(TenantPipelineEtapa.ordem.asc(), TenantPipelineEtapa.id.asc())
        .first()
    )
    return etapa.id if etapa else None


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead_data = payload.model_dump(exclude_unset=True)
    # empresa_id vem do contexto autenticado do tenant e não deve vir do payload.
    lead_data.pop("empresa_id", None)
    if not lead_data.get("nome") and lead_data.get("nome_responsavel"):
        lead_data["nome"] = lead_data.get("nome_responsavel")
    if not lead_data.get("telefone") and lead_data.get("whatsapp"):
        lead_data["telefone"] = lead_data.get("whatsapp")
    if lead_data.get("valor_estimado") is None and lead_data.get("valor_proposto") is not None:
        lead_data["valor_estimado"] = lead_data.get("valor_proposto")
    if not lead_data.get("segmento") and lead_data.get("segmento_id"):
        seg = (
            db.query(TenantCommercialSegment)
            .filter(
                TenantCommercialSegment.id == lead_data["segmento_id"],
                TenantCommercialSegment.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if seg:
            lead_data["segmento"] = seg.nome
    if not lead_data.get("origem") and lead_data.get("origem_lead_id"):
        origem = (
            db.query(TenantCommercialLeadSource)
            .filter(
                TenantCommercialLeadSource.id == lead_data["origem_lead_id"],
                TenantCommercialLeadSource.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if origem:
            lead_data["origem"] = origem.nome
    if not lead_data.get("nome"):
        raise HTTPException(status_code=422, detail="Campo 'nome' (ou 'nome_responsavel') é obrigatório.")

    if lead_data.get("etapa_pipeline_id") is None:
        lead_data["etapa_pipeline_id"] = _etapa_padrao(db, usuario.empresa_id)

    agora = datetime.now(timezone.utc)
    lead = TenantCommercialLead(
        **{k: v for k, v in lead_data.items() if k in LeadCreate.model_fields},
        empresa_id=usuario.empresa_id,
        ativo=True,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(lead)
    db.flush()
    sync_lead_status_from_etapa(db, lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=dict[str, Any])
def list_leads(
    status: Optional[str] = None,
    search: Optional[str] = None,
    origem_lead_id: Optional[int] = None,
    lead_score: Optional[LeadScore] = None,
    ativo: Optional[bool] = True,
    follow_up_hoje: Optional[bool] = None,
    status_pipeline_notin: Optional[str] = None,
    order_by: str = "criado_em",
    order_dir: str = "desc",
    page: int = 1,
    per_page: int = 50,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Lista leads (formato paginado tipo superadmin ou skip/limit legado)."""
    eid = usuario.empresa_id
    query = db.query(TenantCommercialLead).filter(TenantCommercialLead.empresa_id == eid)

    if ativo is not None:
        query = query.filter(TenantCommercialLead.ativo == ativo)
    if status:
        query = query.filter(TenantCommercialLead.status_pipeline == status)
    if lead_score:
        query = query.filter(TenantCommercialLead.lead_score == lead_score)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                TenantCommercialLead.nome.ilike(term),
                TenantCommercialLead.nome_empresa.ilike(term),
                TenantCommercialLead.email.ilike(term),
                TenantCommercialLead.telefone.ilike(term),
                TenantCommercialLead.segmento.ilike(term),
                TenantCommercialLead.origem.ilike(term),
            )
        )
    if origem_lead_id:
        query = query.filter(False)

    agora = datetime.now(timezone.utc)
    if follow_up_hoje:
        query = query.filter(TenantCommercialLead.proximo_contato_em.isnot(None))
        query = query.filter(TenantCommercialLead.proximo_contato_em <= agora)
        query = query.filter(
            TenantCommercialLead.status_pipeline.notin_(["fechado_ganho", "fechado_perdido"])
        )

    if status_pipeline_notin:
        excluir = [s.strip() for s in status_pipeline_notin.split(",") if s.strip()]
        if excluir:
            query = query.filter(TenantCommercialLead.status_pipeline.notin_(excluir))

    col = getattr(TenantCommercialLead, order_by, TenantCommercialLead.criado_em)
    if order_dir == "asc":
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())

    total = query.count()

    if skip is not None and limit is not None:
        leads = query.offset(skip).limit(limit).all()
        return {
            "items": [tenant_lead_to_out(db, l) for l in leads],
            "total": total,
        }

    offset = (page - 1) * per_page
    leads = query.offset(offset).limit(per_page).all()
    pages = (total + per_page - 1) // per_page if per_page else 1
    return {
        "items": [tenant_lead_to_out(db, l) for l in leads],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get("/follow-ups-hoje", response_model=list[dict[str, Any]])
def follow_ups_hoje(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    agora = datetime.now(timezone.utc)
    leads = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo.is_(True),
            TenantCommercialLead.proximo_contato_em.isnot(None),
            TenantCommercialLead.proximo_contato_em <= agora,
            TenantCommercialLead.status_pipeline.notin_(["fechado_ganho", "fechado_perdido"]),
        )
        .order_by(TenantCommercialLead.proximo_contato_em.asc())
        .limit(50)
        .all()
    )
    return [tenant_lead_to_out(db, l) for l in leads]


@router.get("/recentes", response_model=list[dict[str, Any]])
def leads_recentes(
    limit: int = 5,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    leads = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .order_by(TenantCommercialLead.criado_em.desc())
        .limit(limit)
        .all()
    )
    return [tenant_lead_to_out(db, l) for l in leads]


@router.get("/{lead_id}", response_model=dict[str, Any])
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    return tenant_lead_to_out(db, lead)


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    data = payload.model_dump(exclude_unset=True)
    if not data.get("nome") and data.get("nome_responsavel"):
        data["nome"] = data.get("nome_responsavel")
    if not data.get("telefone") and data.get("whatsapp"):
        data["telefone"] = data.get("whatsapp")
    if data.get("valor_estimado") is None and data.get("valor_proposto") is not None:
        data["valor_estimado"] = data.get("valor_proposto")
    if not data.get("segmento") and data.get("segmento_id"):
        seg = (
            db.query(TenantCommercialSegment)
            .filter(
                TenantCommercialSegment.id == data["segmento_id"],
                TenantCommercialSegment.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if seg:
            data["segmento"] = seg.nome
    if not data.get("origem") and data.get("origem_lead_id"):
        origem = (
            db.query(TenantCommercialLeadSource)
            .filter(
                TenantCommercialLeadSource.id == data["origem_lead_id"],
                TenantCommercialLeadSource.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if origem:
            data["origem"] = origem.nome
    for field, value in data.items():
        setattr(lead, field, value)
    lead.atualizado_em = datetime.now(timezone.utc)
    sync_lead_status_from_etapa(db, lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    lead.ativo = False
    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Lead desativado com sucesso"}


@router.post("/{lead_id}/mover-etapa", response_model=LeadResponse)
def move_lead_stage(
    lead_id: int,
    payload: MoveEtapaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.id == payload.etapa_id,
            TenantPipelineEtapa.empresa_id == usuario.empresa_id,
            TenantPipelineEtapa.ativo.is_(True),
        )
        .first()
    )
    if etapa is None:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")

    old = lead.status_pipeline
    lead.etapa_pipeline_id = etapa.id
    sync_lead_status_from_etapa(db, lead)
    lead.atualizado_em = datetime.now(timezone.utc)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.MUDANCA_STATUS,
            canal=CanalInteracao.SISTEMA,
            conteudo=f"Status alterado de '{old}' para '{lead.status_pipeline}'",
        )
    )
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/observacao")
def add_observacao(
    lead_id: int,
    body: ObservacaoBody,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.OBSERVACAO,
            canal=CanalInteracao.SISTEMA,
            conteudo=body.conteudo,
        )
    )
    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/{lead_id}/whatsapp")
def log_whatsapp(
    lead_id: int,
    body: MensagemBody,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    lead.ultimo_contato_em = datetime.now(timezone.utc)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.WHATSAPP,
            canal=CanalInteracao.WHATSAPP,
            conteudo=body.mensagem,
        )
    )
    db.commit()
    return {"ok": True, "detail": "Registrado (disparo WhatsApp real depende da integração da empresa)."}


@router.post("/{lead_id}/email")
def log_email(
    lead_id: int,
    body: EmailBody,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    lead.ultimo_contato_em = datetime.now(timezone.utc)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.EMAIL,
            canal=CanalInteracao.EMAIL,
            conteudo=f"[{body.assunto}] {body.mensagem}",
        )
    )
    db.commit()
    return {"ok": True, "detail": "Registrado (envio de e-mail real depende da configuração da empresa)."}


@router.post("/{lead_id}/criar-empresa", include_in_schema=False)
def tenant_forbidden_criar_empresa(lead_id: int):
    """Bloqueado no CRM tenant: criação de conta a partir de lead é exclusiva do superadmin."""
    raise HTTPException(status_code=403, detail="Operação não disponível no comercial da empresa.")


@router.post("/{lead_id}/reenviar-senha", include_in_schema=False)
def tenant_forbidden_reenviar_senha(lead_id: int):
    """Bloqueado no CRM tenant."""
    raise HTTPException(status_code=403, detail="Operação não disponível no comercial da empresa.")
