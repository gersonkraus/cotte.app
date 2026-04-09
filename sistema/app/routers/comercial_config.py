"""
Router de Configurações Comerciais — Segmentos, origens de lead e configurações gerais.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.auth import get_superadmin
from app.models.models import (
    CommercialSegment,
    CommercialLeadSource,
    CommercialConfig,
)
from app.schemas.schemas import (
    SegmentCreate,
    SegmentUpdate,
    SegmentOut,
    LeadSourceCreate,
    LeadSourceUpdate,
    LeadSourceOut,
    CommercialConfigUpdate,
    CommercialConfigOut,
)

router = APIRouter(prefix="/comercial", tags=["Comercial - Config"])


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD SEGMENTOS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/segmentos", response_model=List[SegmentOut])
def list_segmentos(
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Lista segmentos."""
    query = db.query(CommercialSegment)
    if ativo is not None:
        query = query.filter(CommercialSegment.ativo == ativo)
    return query.order_by(CommercialSegment.nome.asc()).all()


@router.post("/segmentos", response_model=SegmentOut, status_code=201)
def create_segmento(
    data: SegmentCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria um segmento."""
    existente = (
        db.query(CommercialSegment)
        .filter(func.lower(CommercialSegment.nome) == data.nome.strip().lower())
        .first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="Segmento já existe")
    seg = CommercialSegment(nome=data.nome.strip())
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
    _=Depends(get_superadmin),
):
    """Atualiza segmento."""
    seg = db.query(CommercialSegment).filter(CommercialSegment.id == seg_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="Segmento não encontrado")
    update = data.model_dump(exclude_unset=True)
    if "nome" in update:
        existente = (
            db.query(CommercialSegment)
            .filter(
                func.lower(CommercialSegment.nome) == update["nome"].strip().lower(),
                CommercialSegment.id != seg_id,
            )
            .first()
        )
        if existente:
            raise HTTPException(status_code=409, detail="Segmento já existe")
        update["nome"] = update["nome"].strip()
    for k, v in update.items():
        setattr(seg, k, v)
    seg.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(seg)
    return seg


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD ORIGENS DE LEAD
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/origens", response_model=List[LeadSourceOut])
def list_origens(
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Lista origens de lead."""
    query = db.query(CommercialLeadSource)
    if ativo is not None:
        query = query.filter(CommercialLeadSource.ativo == ativo)
    return query.order_by(CommercialLeadSource.nome.asc()).all()


@router.post("/origens", response_model=LeadSourceOut, status_code=201)
def create_origem(
    data: LeadSourceCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria uma origem de lead."""
    existente = (
        db.query(CommercialLeadSource)
        .filter(func.lower(CommercialLeadSource.nome) == data.nome.strip().lower())
        .first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="Origem já existe")
    origem = CommercialLeadSource(nome=data.nome.strip())
    db.add(origem)
    db.commit()
    db.refresh(origem)
    return origem


@router.patch("/origens/{origem_id}", response_model=LeadSourceOut)
def update_origem(
    origem_id: int,
    data: LeadSourceUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza origem de lead."""
    origem = (
        db.query(CommercialLeadSource)
        .filter(CommercialLeadSource.id == origem_id)
        .first()
    )
    if not origem:
        raise HTTPException(status_code=404, detail="Origem não encontrada")
    update = data.model_dump(exclude_unset=True)
    if "nome" in update:
        existente = (
            db.query(CommercialLeadSource)
            .filter(
                func.lower(CommercialLeadSource.nome) == update["nome"].strip().lower(),
                CommercialLeadSource.id != origem_id,
            )
            .first()
        )
        if existente:
            raise HTTPException(status_code=409, detail="Origem já existe")
        update["nome"] = update["nome"].strip()
    for k, v in update.items():
        setattr(origem, k, v)
    origem.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(origem)
    return origem


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/config")
def get_config(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Retorna configurações do módulo comercial."""
    config = db.query(CommercialConfig).first()
    if not config:
        config = CommercialConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.patch("/config")
def update_config(
    data: CommercialConfigUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza configurações do módulo comercial."""
    config = db.query(CommercialConfig).first()
    if not config:
        config = CommercialConfig(id=1)
        db.add(config)
        db.flush()

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(config, k, v)
    config.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config
