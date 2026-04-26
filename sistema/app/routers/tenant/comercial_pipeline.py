from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantCommercialLead, TenantPipelineEtapa, Usuario
from app.schemas.schemas import PipelineStageCreate, PipelineStageOut, PipelineStageUpdate
from app.routers.tenant.tenant_comercial_serialization import slugify_nome


class EtapaCreate(BaseModel):
    nome: str
    cor: str = "#6B7280"
    ordem: int = 0
    slug: str | None = None


class EtapaUpdate(BaseModel):
    nome: str | None = None
    cor: str | None = None
    ordem: int | None = None
    ativo: bool | None = None


class EtapaResponse(BaseModel):
    id: int
    empresa_id: int
    nome: str
    ordem: int
    cor: str
    ativo: bool

    class Config:
        from_attributes = True


router = APIRouter(
    prefix="/pipeline",
    tags=["Tenant Comercial Pipeline"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)

ETAPAS_PADRAO = [
    {"nome": "Novo", "slug": "novo", "ordem": 1, "cor": "#3B82F6"},
    {"nome": "Contato", "slug": "contato_iniciado", "ordem": 2, "cor": "#8B5CF6"},
    {"nome": "Proposta", "slug": "proposta_enviada", "ordem": 3, "cor": "#F59E0B"},
    {"nome": "Negociação", "slug": "negociacao", "ordem": 4, "cor": "#06b6d4"},
    {"nome": "Ganho", "slug": "fechado_ganho", "ordem": 5, "cor": "#10B981"},
    {"nome": "Perdido", "slug": "fechado_perdido", "ordem": 6, "cor": "#ef4444"},
]


def _listar_etapas(db: Session, empresa_id: int) -> list[TenantPipelineEtapa]:
    etapas = (
        db.query(TenantPipelineEtapa)
        .filter(TenantPipelineEtapa.empresa_id == empresa_id)
        .order_by(TenantPipelineEtapa.ordem.asc(), TenantPipelineEtapa.id.asc())
        .all()
    )
    if etapas:
        return etapas

    for etapa in ETAPAS_PADRAO:
        db.add(
            TenantPipelineEtapa(
                empresa_id=empresa_id,
                ativo=True,
                nome=etapa["nome"],
                slug=etapa.get("slug"),
                ordem=etapa["ordem"],
                cor=etapa["cor"],
            )
        )
    db.commit()
    return (
        db.query(TenantPipelineEtapa)
        .filter(TenantPipelineEtapa.empresa_id == empresa_id)
        .order_by(TenantPipelineEtapa.ordem.asc(), TenantPipelineEtapa.id.asc())
        .all()
    )


@router.get("/etapas", response_model=list[EtapaResponse])
def list_etapas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return _listar_etapas(db, usuario.empresa_id)


@router.post("/etapas", response_model=EtapaResponse, status_code=status.HTTP_201_CREATED)
def create_etapa(
    payload: EtapaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    etapa = TenantPipelineEtapa(
        empresa_id=usuario.empresa_id,
        nome=payload.nome,
        slug=payload.slug or slugify_nome(payload.nome),
        cor=payload.cor,
        ordem=payload.ordem,
        ativo=True,
    )
    db.add(etapa)
    db.commit()
    db.refresh(etapa)
    return etapa


@router.put("/etapas/{etapa_id}", response_model=EtapaResponse)
def update_etapa(
    etapa_id: int,
    payload: EtapaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.id == etapa_id,
            TenantPipelineEtapa.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if etapa is None:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(etapa, field, value)
    db.commit()
    db.refresh(etapa)
    return etapa


@router.delete("/etapas/{etapa_id}")
def delete_etapa(
    etapa_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.id == etapa_id,
            TenantPipelineEtapa.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if etapa is None:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")

    count = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.etapa_pipeline_id == etapa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .count()
    )
    if count:
        raise HTTPException(
            status_code=409,
            detail=f"Não é possível excluir: {count} lead(s) nessa etapa",
        )

    db.delete(etapa)
    db.commit()
    return {"ok": True}


def _etapa_to_stage_out(e: TenantPipelineEtapa) -> PipelineStageOut:
    slug = e.slug or slugify_nome(e.nome)
    fechado = slug in ("fechado_ganho", "fechado_perdido")
    return PipelineStageOut(
        id=e.id,
        slug=slug,
        label=e.nome,
        cor=e.cor or "#94a3b8",
        emoji="",
        ordem=e.ordem or 0,
        ativo=bool(e.ativo),
        fechado=fechado,
    )


router_stages = APIRouter(
    tags=["Tenant Comercial Pipeline"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


@router_stages.get("/pipeline-stages", response_model=List[PipelineStageOut])
def list_pipeline_stages_compat(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    etapas = _listar_etapas(db, usuario.empresa_id)
    return [_etapa_to_stage_out(e) for e in etapas]


@router_stages.post("/pipeline-stages", response_model=PipelineStageOut, status_code=status.HTTP_201_CREATED)
def create_pipeline_stage_compat(
    data: PipelineStageCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    etapa = TenantPipelineEtapa(
        empresa_id=usuario.empresa_id,
        nome=data.label,
        slug=data.slug,
        cor=data.cor,
        ordem=data.ordem,
        ativo=True,
    )
    db.add(etapa)
    db.commit()
    db.refresh(etapa)
    return _etapa_to_stage_out(etapa)


@router_stages.put("/pipeline-stages/{etapa_id}", response_model=PipelineStageOut)
def update_pipeline_stage_compat(
    etapa_id: int,
    data: PipelineStageUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.id == etapa_id,
            TenantPipelineEtapa.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if etapa is None:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    if data.label is not None:
        etapa.nome = data.label
    if data.cor is not None:
        etapa.cor = data.cor
    if data.ordem is not None:
        etapa.ordem = data.ordem
    if data.ativo is not None:
        etapa.ativo = data.ativo
    db.commit()
    db.refresh(etapa)
    return _etapa_to_stage_out(etapa)


@router_stages.delete("/pipeline-stages/{etapa_id}")
def delete_pipeline_stage_compat(
    etapa_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    return delete_etapa(etapa_id, db, usuario)
