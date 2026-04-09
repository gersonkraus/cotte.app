"""
Router de Pipeline Comercial — Etapas do kanban e atualização de status.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.auth import get_superadmin, exigir_permissao
from app.models.models import (
    CommercialLead,
    CommercialInteraction,
    PipelineStage,
    StatusPipeline,
    TipoInteracao,
    CanalInteracao,
    LeadScore,
)
from app.schemas.schemas import (
    StatusUpdate,
    PipelineStageCreate,
    PipelineStageUpdate,
    PipelineStageOut,
    PipelineStageReorder,
)
from app.routers.comercial_helpers import _calcular_score, _lead_to_out

router = APIRouter(prefix="/comercial", tags=["Comercial - Pipeline"])


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE STATUS
# ═══════════════════════════════════════════════════════════════════════════════


@router.patch("/leads/{lead_id}/status")
def update_lead_status(
    lead_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza o status do pipeline de um lead."""
    lead = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
        )
        .filter(CommercialLead.id == lead_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    status_anterior = lead.status_pipeline
    lead.status_pipeline = data.status
    lead.atualizado_em = datetime.now(timezone.utc)

    # Recalcular score
    lead.lead_score = _calcular_score(lead)

    interacao = CommercialInteraction(
        lead_id=lead.id,
        tipo=TipoInteracao.MUDANCA_STATUS,
        canal=CanalInteracao.OUTRO,
        conteudo=f"Status alterado de '{status_anterior}' para '{data.status}'",
    )
    db.add(interacao)

    db.commit()
    db.refresh(lead)
    return _lead_to_out(lead)


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE STAGES (etapas configuráveis do kanban)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/pipeline-stages", response_model=List[PipelineStageOut])
def list_pipeline_stages(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Lista todas as etapas do pipeline, ordenadas por ordem."""
    return db.query(PipelineStage).order_by(PipelineStage.ordem).all()


@router.post("/pipeline-stages", response_model=PipelineStageOut, status_code=201)
def create_pipeline_stage(
    data: PipelineStageCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria uma nova etapa do pipeline."""
    if db.query(PipelineStage).filter(PipelineStage.slug == data.slug).first():
        raise HTTPException(status_code=409, detail=f"Slug '{data.slug}' já existe")
    stage = PipelineStage(**data.model_dump())
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


@router.patch("/pipeline-stages/reorder")
def reorder_pipeline_stages(
    items: List[PipelineStageReorder],
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Reordena as etapas recebendo lista de {id, ordem}."""
    for item in items:
        db.query(PipelineStage).filter(PipelineStage.id == item.id).update(
            {"ordem": item.ordem}
        )
    db.commit()
    return {"ok": True}


@router.patch("/pipeline-stages/{stage_id}", response_model=PipelineStageOut)
def update_pipeline_stage(
    stage_id: int,
    data: PipelineStageUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Edita label, cor, emoji, ordem ou ativo de uma etapa."""
    stage = db.query(PipelineStage).filter(PipelineStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(stage, field, value)
    db.commit()
    db.refresh(stage)
    return stage


@router.delete("/pipeline-stages/{stage_id}")
def delete_pipeline_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_permissao("comercial", "exclusao")),
):
    """Exclui uma etapa. Retorna 409 se existirem leads nesse status."""
    stage = (
        db.query(PipelineStage)
        .filter(
            PipelineStage.id == stage_id,
            PipelineStage.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not stage:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    count = (
        db.query(CommercialLead)
        .filter(CommercialLead.status_pipeline == stage.slug)
        .count()
    )
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Não é possível excluir: {count} lead(s) nessa etapa",
        )
    db.delete(stage)
    db.commit()
    return {"ok": True}
