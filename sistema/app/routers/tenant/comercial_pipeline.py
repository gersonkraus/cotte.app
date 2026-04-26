from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantCommercialLead, TenantPipelineEtapa, Usuario


class EtapaCreate(BaseModel):
    nome: str
    cor: str = "#6B7280"
    ordem: int = 0


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
    {"nome": "Novo", "ordem": 1, "cor": "#3B82F6"},
    {"nome": "Qualificado", "ordem": 2, "cor": "#8B5CF6"},
    {"nome": "Proposta", "ordem": 3, "cor": "#F59E0B"},
    {"nome": "Fechado", "ordem": 4, "cor": "#10B981"},
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
        db.add(TenantPipelineEtapa(empresa_id=empresa_id, ativo=True, **etapa))
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
