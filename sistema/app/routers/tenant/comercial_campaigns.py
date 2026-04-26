from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    TenantCampaignLead,
    TenantCommercialCampaign,
    TenantCommercialLead,
    TenantCommercialTemplate,
    Usuario,
)
from app.schemas.schemas import (
    CampaignCreate,
    CampaignDisparoRequest,
    CampaignLeadOut,
    CampaignMetrics,
    CampaignOut,
    CampaignUpdate,
)


router = APIRouter(
    prefix="/campaigns",
    tags=["Tenant Comercial Campanhas"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


@router.post("/", response_model=CampaignOut)
async def create_campaign(
    request: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    template = (
        db.query(TenantCommercialTemplate)
        .filter(
            TenantCommercialTemplate.id == request.template_id,
            TenantCommercialTemplate.empresa_id == current_user.empresa_id,
            TenantCommercialTemplate.ativo.is_(True),
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    campaign = TenantCommercialCampaign(
        empresa_id=current_user.empresa_id,
        nome=request.nome,
        template_id=request.template_id,
        canal=request.canal,
        status="agendada",
        total_leads=len(request.lead_ids),
    )
    db.add(campaign)
    db.flush()
    for lead_id in request.lead_ids:
        lead = (
            db.query(TenantCommercialLead)
            .filter(
                TenantCommercialLead.id == lead_id,
                TenantCommercialLead.empresa_id == current_user.empresa_id,
            )
            .first()
        )
        if lead:
            db.add(TenantCampaignLead(campaign_id=campaign.id, lead_id=lead.id, status="pendente"))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/", response_model=List[CampaignOut])
async def list_campaigns(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return (
        db.query(TenantCommercialCampaign)
        .filter(TenantCommercialCampaign.empresa_id == current_user.empresa_id)
        .order_by(TenantCommercialCampaign.criado_em.desc())
        .all()
    )


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    campaign = (
        db.query(TenantCommercialCampaign)
        .filter(
            TenantCommercialCampaign.id == campaign_id,
            TenantCommercialCampaign.empresa_id == current_user.empresa_id,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campaign


@router.put("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: int,
    request: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    campaign = await get_campaign(campaign_id, db, current_user)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    campaign.atualizado_em = datetime.now()
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/disparo")
async def disparo_campaign(
    campaign_id: int,
    request: CampaignDisparoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    _ = background_tasks
    campaign = await get_campaign(campaign_id, db, current_user)
    campaign.status = "em_andamento"
    leads_q = db.query(TenantCampaignLead).filter(TenantCampaignLead.campaign_id == campaign.id)
    if request.lead_ids:
        leads_q = leads_q.filter(TenantCampaignLead.lead_id.in_(request.lead_ids))
    leads = leads_q.all()
    for cl in leads:
        cl.status = "enviado"
        cl.data_envio = datetime.now()
    campaign.enviados = len(leads)
    campaign.entregues = len(leads)
    campaign.respondidos = 0
    campaign.status = "concluida"
    db.commit()
    return {"message": "Disparo processado", "total": len(leads)}


@router.get("/{campaign_id}/leads", response_model=List[CampaignLeadOut])
async def list_campaign_leads(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    _ = await get_campaign(campaign_id, db, current_user)
    return (
        db.query(TenantCampaignLead)
        .filter(TenantCampaignLead.campaign_id == campaign_id)
        .all()
    )


@router.get("/{campaign_id}/metrics", response_model=CampaignMetrics)
async def get_campaign_metrics(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    c = await get_campaign(campaign_id, db, current_user)
    total = c.total_leads or 0
    enviados = c.enviados or 0
    entregues = c.entregues or 0
    respondidos = c.respondidos or 0
    return CampaignMetrics(
        total_leads=total,
        enviados=enviados,
        entregues=entregues,
        respondidos=respondidos,
        taxa_entrega=(entregues / enviados * 100.0) if enviados else 0.0,
        taxa_resposta=(respondidos / enviados * 100.0) if enviados else 0.0,
        leads_por_status={
            "pendente": max(total - enviados, 0),
            "enviado": enviados,
            "entregue": entregues,
            "respondido": respondidos,
        },
    )


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    campaign = await get_campaign(campaign_id, db, current_user)
    db.query(TenantCampaignLead).filter(TenantCampaignLead.campaign_id == campaign_id).delete()
    db.delete(campaign)
    db.commit()
    return {"message": "Campanha removida"}
