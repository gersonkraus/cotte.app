from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    TenantCommercialLeadSource,
    TenantCommercialSegment,
    TenantConfig,
    Usuario,
)
from app.schemas.schemas import (
    CommercialConfigOut,
    CommercialConfigUpdate,
    LeadSourceCreate,
    LeadSourceOut,
    LeadSourceUpdate,
    SegmentCreate,
    SegmentOut,
    SegmentUpdate,
)


router = APIRouter(
    dependencies=[Depends(exigir_modulo("comercial"))],
    tags=["Tenant Comercial Config"],
)


@router.get("/segmentos", response_model=List[SegmentOut])
def list_segmentos(
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    q = db.query(TenantCommercialSegment).filter(
        TenantCommercialSegment.empresa_id == usuario.empresa_id
    )
    if ativo is not None:
        q = q.filter(TenantCommercialSegment.ativo == ativo)
    return q.order_by(TenantCommercialSegment.nome.asc()).all()


@router.post("/segmentos", response_model=SegmentOut, status_code=201)
def create_segmento(
    data: SegmentCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    nome = data.nome.strip()
    existente = (
        db.query(TenantCommercialSegment)
        .filter(
            TenantCommercialSegment.empresa_id == usuario.empresa_id,
            func.lower(TenantCommercialSegment.nome) == nome.lower(),
        )
        .first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="Segmento já existe")
    seg = TenantCommercialSegment(empresa_id=usuario.empresa_id, nome=nome)
    db.add(seg)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Segmento já existe")
    db.refresh(seg)
    return seg


@router.patch("/segmentos/{seg_id}", response_model=SegmentOut)
def update_segmento(
    seg_id: int,
    data: SegmentUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    seg = (
        db.query(TenantCommercialSegment)
        .filter(
            TenantCommercialSegment.id == seg_id,
            TenantCommercialSegment.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not seg:
        raise HTTPException(status_code=404, detail="Segmento não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(seg, k, v.strip() if isinstance(v, str) else v)
    seg.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(seg)
    return seg


@router.delete("/segmentos/{seg_id}")
def delete_segmento(
    seg_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    seg = (
        db.query(TenantCommercialSegment)
        .filter(
            TenantCommercialSegment.id == seg_id,
            TenantCommercialSegment.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not seg:
        raise HTTPException(status_code=404, detail="Segmento não encontrado")
    seg.ativo = False
    seg.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.get("/origens", response_model=List[LeadSourceOut])
def list_origens(
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    q = db.query(TenantCommercialLeadSource).filter(
        TenantCommercialLeadSource.empresa_id == usuario.empresa_id
    )
    if ativo is not None:
        q = q.filter(TenantCommercialLeadSource.ativo == ativo)
    return q.order_by(TenantCommercialLeadSource.nome.asc()).all()


@router.post("/origens", response_model=LeadSourceOut, status_code=201)
def create_origem(
    data: LeadSourceCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    nome = data.nome.strip()
    existente = (
        db.query(TenantCommercialLeadSource)
        .filter(
            TenantCommercialLeadSource.empresa_id == usuario.empresa_id,
            func.lower(TenantCommercialLeadSource.nome) == nome.lower(),
        )
        .first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="Origem já existe")
    src = TenantCommercialLeadSource(empresa_id=usuario.empresa_id, nome=nome)
    db.add(src)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Origem já existe")
    db.refresh(src)
    return src


@router.patch("/origens/{origem_id}", response_model=LeadSourceOut)
def update_origem(
    origem_id: int,
    data: LeadSourceUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    origem = (
        db.query(TenantCommercialLeadSource)
        .filter(
            TenantCommercialLeadSource.id == origem_id,
            TenantCommercialLeadSource.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not origem:
        raise HTTPException(status_code=404, detail="Origem não encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(origem, k, v.strip() if isinstance(v, str) else v)
    origem.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(origem)
    return origem


@router.delete("/origens/{origem_id}")
def delete_origem(
    origem_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    origem = (
        db.query(TenantCommercialLeadSource)
        .filter(
            TenantCommercialLeadSource.id == origem_id,
            TenantCommercialLeadSource.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not origem:
        raise HTTPException(status_code=404, detail="Origem não encontrada")
    origem.ativo = False
    origem.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.get("/config", response_model=CommercialConfigOut)
def get_config(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    c = (
        db.query(TenantConfig)
        .filter(
            TenantConfig.empresa_id == usuario.empresa_id,
            TenantConfig.tipo == "config",
            TenantConfig.ativo.is_(True),
        )
        .first()
    )
    if not c:
        c = TenantConfig(
            empresa_id=usuario.empresa_id,
            tipo="config",
            nome="default",
            ativo=True,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
    return {
        "id": c.id,
        "link_demo": None,
        "link_proposta": None,
        "assinatura_comercial": None,
        "canal_preferencial": "whatsapp",
        "textos_auxiliares": None,
        "atualizado_em": None,
    }


@router.patch("/config", response_model=CommercialConfigOut)
def update_config(
    data: CommercialConfigUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    _ = data
    # Mantido para compatibilidade visual; no tenant atual, settings ficam no frontend/local.
    return get_config(db=db, usuario=usuario)
