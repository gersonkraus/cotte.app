from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_usuario_atual as get_current_user, exigir_permissao
from app.models.models import (
    Empresa, Usuario, CommercialLead, CommercialTemplate,
    Campaign, CampaignLead
)
from app.schemas.schemas import (
    CampaignCreate, CampaignUpdate, CampaignOut,
    CampaignLeadOut, CampaignMetrics, CampaignDisparoRequest
)
from app.services.campaign_service import CampaignService
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comercial/campaigns", tags=["Comercial - Campanhas"])


@router.post("/", response_model=CampaignOut)
async def create_campaign(
    request: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Cria uma nova campanha de disparo."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    service = CampaignService(db, empresa, current_user)

    # Verificar se template existe
    template = db.query(CommercialTemplate).filter(
        CommercialTemplate.id == request.template_id,
        CommercialTemplate.ativo == True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    campaign = service.create_campaign(
        nome=request.nome,
        template_id=request.template_id,
        canal=request.canal,
        lead_ids=request.lead_ids
    )

    return campaign


@router.get("/", response_model=List[CampaignOut])
async def list_campaigns(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Lista campanhas da empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaigns = db.query(Campaign).filter(
        Campaign.empresa_id == empresa.id
    ).order_by(Campaign.criado_em.desc()).all()

    return campaigns


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Obtém detalhes de uma campanha."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.empresa_id == empresa.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    return campaign


@router.put("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: int,
    request: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Atualiza uma campanha."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.empresa_id == empresa.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    service = CampaignService(db, empresa, current_user)
    updated = service.update_campaign(campaign, request)

    return updated


@router.post("/{campaign_id}/disparo")
async def disparo_campaign(
    campaign_id: int,
    request: CampaignDisparoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Inicia disparo de campanha."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.empresa_id == empresa.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    service = CampaignService(db, empresa, current_user)

    # Iniciar disparo em background
    background_tasks.add_task(
        service.disparo_campaign,
        campaign,
        lead_ids=request.lead_ids,
        canal=request.canal
    )

    return {"message": "Disparo iniciado em background"}


@router.post("/{campaign_id}/leads")
async def add_leads_to_campaign(
    campaign_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Adiciona leads a uma campanha existente."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.empresa_id == empresa.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    lead_ids = body.get("lead_ids", [])
    if not lead_ids:
        raise HTTPException(status_code=400, detail="Nenhum lead informado")

    existentes = {
        cl.lead_id for cl in db.query(CampaignLead).filter(
            CampaignLead.campaign_id == campaign_id
        ).all()
    }

    novos = []
    for lid in lead_ids:
        if lid not in existentes:
            lead = db.query(CommercialLead).filter(CommercialLead.id == lid).first()
            if lead:
                novos.append(CampaignLead(campaign_id=campaign_id, lead_id=lid, status="pendente"))

    if novos:
        db.add_all(novos)
        db.commit()

    return {"adicionados": len(novos), "ja_existentes": len(lead_ids) - len(novos)}


@router.get("/{campaign_id}/leads", response_model=List[CampaignLeadOut])
async def list_campaign_leads(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Lista leads de uma campanha."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.empresa_id == empresa.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    leads = db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id
    ).all()

    return leads


@router.get("/{campaign_id}/metrics", response_model=CampaignMetrics)
async def get_campaign_metrics(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Obtém métricas de uma campanha."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.empresa_id == empresa.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    service = CampaignService(db, empresa, current_user)
    metrics = service.get_campaign_metrics(campaign)

    return metrics


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "admin"))
):
    """Deleta uma campanha."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.empresa_id == empresa.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    db.delete(campaign)
    db.commit()

    return {"message": "Campanha deletada com sucesso"}