from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    Empresa,
    TenantCampaignLead,
    TenantCommercialCampaign,
    TenantCommercialLead,
    TenantCommercialTemplate,
    Usuario,
)
from app.services.template_anexos_service import obter_bytes_anexo
from app.services.whatsapp_service import enviar_imagem, enviar_mensagem_texto, enviar_pdf
from app.services.email_service import send_email_simples
import logging

logger = logging.getLogger(__name__)
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
    campaign = await get_campaign(campaign_id, db, current_user)
    if campaign.status == "concluida":
        raise HTTPException(status_code=400, detail="Esta campanha já foi concluída")

    # Iniciar disparo em background
    background_tasks.add_task(
        _executar_disparo_background,
        campaign_id,
        request.lead_ids,
        request.canal,
        current_user.empresa_id
    )

    return {"message": "Disparo iniciado em background"}


async def _executar_disparo_background(
    campaign_id: int,
    lead_ids: List[int],
    canal_override: str,
    empresa_id: int
):
    """Função que roda em background para realizar o disparo real da campanha."""
    from app.core.database import SessionLocal
    from app.models.models import TenantCommercialInteraction, TipoInteracao, CanalInteracao

    db = SessionLocal()
    try:
        campaign = db.query(TenantCommercialCampaign).filter(TenantCommercialCampaign.id == campaign_id).first()
        if not campaign:
            return

        campaign.status = "em_andamento"
        db.commit()

        template = campaign.template
        canal = canal_override or campaign.canal
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()

        leads_q = db.query(TenantCampaignLead).filter(TenantCampaignLead.campaign_id == campaign.id)
        if lead_ids:
            leads_q = leads_q.filter(TenantCampaignLead.lead_id.in_(lead_ids))
        
        campaign_leads = leads_q.all()
        
        enviados = 0
        falhas = 0

        # Carregar anexo se existir
        anexo_bytes = None
        if template and template.anexo_arquivo_path:
            try:
                anexo_bytes = await obter_bytes_anexo(template.anexo_arquivo_path)
            except Exception as e:
                logger.warning(f"Falha ao carregar anexo da campanha {campaign_id}: {e}")

        for cl in campaign_leads:
            lead = cl.lead
            if not lead:
                continue

            sucesso = False
            mensagem_final = template.conteudo
            # Substituições básicas de variáveis
            mensagem_final = mensagem_final.replace("{nome_responsavel}", lead.nome or "")
            mensagem_final = mensagem_final.replace("{nome_empresa}", lead.nome_empresa or lead.nome or "")
            
            try:
                if canal in ["whatsapp", "ambos"] and lead.telefone:
                    if anexo_bytes:
                        mime = template.anexo_mime_type or ""
                        if mime.startswith("image/"):
                            sucesso = await enviar_imagem(lead.telefone, anexo_bytes, caption=mensagem_final, mime_type=mime, empresa=empresa)
                        elif mime == "application/pdf":
                            sucesso = await enviar_pdf(lead.telefone, anexo_bytes, numero=template.anexo_nome_original or "documento", caption=mensagem_final, empresa=empresa)
                        else:
                            sucesso = await enviar_mensagem_texto(lead.telefone, mensagem_final, empresa=empresa)
                    else:
                        sucesso = await enviar_mensagem_texto(lead.telefone, mensagem_final, empresa=empresa)
                    
                    if sucesso:
                        db.add(TenantCommercialInteraction(
                            empresa_id=empresa_id,
                            lead_id=lead.id,
                            tipo=TipoInteracao.WHATSAPP,
                            canal=CanalInteracao.WHATSAPP,
                            conteudo=f"Campanha [{campaign.nome}]: {mensagem_final}",
                        ))

                if canal in ["email", "ambos"] and lead.email:
                    attachments = None
                    if anexo_bytes:
                        attachments = [{
                            "path": template.anexo_arquivo_path,
                            "name": template.anexo_nome_original,
                            "mime_type": template.anexo_mime_type,
                            "content_bytes": anexo_bytes
                        }]
                    
                    email_sucesso = send_email_simples(
                        lead.email,
                        template.assunto or f"Campanha {campaign.nome}",
                        mensagem_final,
                        attachments=attachments
                    )
                    if email_sucesso:
                        sucesso = True # Se pelo menos um canal enviou, marcamos sucesso
                        db.add(TenantCommercialInteraction(
                            empresa_id=empresa_id,
                            lead_id=lead.id,
                            tipo=TipoInteracao.EMAIL,
                            canal=CanalInteracao.EMAIL,
                            conteudo=f"Campanha [{campaign.nome}] - Assunto: {template.assunto or campaign.nome}",
                        ))

                if sucesso:
                    cl.status = "enviado"
                    cl.data_envio = datetime.now()
                    enviados += 1
                else:
                    cl.status = "erro"
                    falhas += 1
                
                db.commit()
                # Delay básico anti-spam entre envios em lote
                import asyncio
                import random
                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.error(f"Erro ao processar lead {lead.id} na campanha {campaign_id}: {e}")
                cl.status = "erro"
                falhas += 1
                db.commit()

        campaign.enviados += enviados
        campaign.entregues += enviados # Simplificação
        campaign.status = "concluida"
        campaign.atualizado_em = datetime.now()
        db.commit()

    except Exception as e:
        logger.exception(f"Erro fatal no processamento da campanha {campaign_id}: {e}")
    finally:
        db.close()


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
