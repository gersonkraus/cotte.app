from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantCommercialLead, TenantPipelineEtapa, Usuario


class LeadBase(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    segmento: Optional[str] = None
    origem: Optional[str] = None
    etapa_pipeline_id: Optional[int] = None
    valor_estimado: Optional[Decimal] = None
    observacoes: Optional[str] = None
    responsavel_id: Optional[int] = None


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


router = APIRouter(
    prefix="/leads",
    tags=["Tenant Comercial Leads"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


def _buscar_lead(db: Session, empresa_id: int, lead_id: int) -> TenantCommercialLead:
    lead = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.id == lead_id,
            TenantCommercialLead.empresa_id == empresa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .first()
    )
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
    lead_data = payload.model_dump()
    if lead_data.get("etapa_pipeline_id") is None:
        lead_data["etapa_pipeline_id"] = _etapa_padrao(db, usuario.empresa_id)

    agora = datetime.now(timezone.utc)
    lead = TenantCommercialLead(
        **lead_data,
        empresa_id=usuario.empresa_id,
        ativo=True,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=LeadListResponse)
def list_leads(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    query = db.query(TenantCommercialLead).filter(
        TenantCommercialLead.empresa_id == usuario.empresa_id,
        TenantCommercialLead.ativo.is_(True),
    )
    return {
        "items": query.order_by(TenantCommercialLead.id.desc()).offset(skip).limit(limit).all(),
        "total": query.count(),
    }


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return _buscar_lead(db, usuario.empresa_id, lead_id)


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    lead.atualizado_em = datetime.now(timezone.utc)
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

    lead.etapa_pipeline_id = etapa.id
    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lead)
    return lead
