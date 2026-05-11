import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

_running_campaigns: dict[int, bool] = {}
_campaign_start_times: dict[int, float] = {}


def _proximo_agendamento(data_atual: datetime, recorrencia: str) -> datetime | None:
    if recorrencia == "diario":
        return data_atual + timedelta(days=1)
    if recorrencia == "semanal":
        return data_atual + timedelta(weeks=1)
    return None

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


def _calcular_eta(campaign, started_at: float | None = None) -> str | None:
    if campaign.status != "em_andamento" or not started_at or not campaign.total_leads:
        return None
    enviados = campaign.enviados or 0
    if enviados < 1:
        return None
    elapsed = time.time() - started_at
    rate = enviados / elapsed
    restantes = campaign.total_leads - enviados
    if restantes <= 0 or rate <= 0:
        return None
    segundos = restantes / rate
    if segundos < 60:
        return f"{int(segundos)}s"
    minutos = segundos / 60
    if minutos < 60:
        return f"{int(minutos)}min"
    horas = int(minutos / 60)
    mins = int(minutos % 60)
    return f"{horas}h{mins}min"


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
        data_agendamento=request.data_agendamento,
        recorrencia=request.recorrencia or "nenhuma",
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
    campanhas = (
        db.query(TenantCommercialCampaign)
        .filter(TenantCommercialCampaign.empresa_id == current_user.empresa_id)
        .order_by(TenantCommercialCampaign.criado_em.desc())
        .all()
    )
    resultado = []
    for c in campanhas:
        eta = _calcular_eta(c, _campaign_start_times.get(c.id))
        out = CampaignOut.model_validate(c)
        out.tempo_estimado_restante = eta
        resultado.append(out)
    return resultado


def _get_campaign_orm(campaign_id: int, empresa_id: int, db: Session):
    campaign = (
        db.query(TenantCommercialCampaign)
        .filter(
            TenantCommercialCampaign.id == campaign_id,
            TenantCommercialCampaign.empresa_id == empresa_id,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    campaign = _get_campaign_orm(campaign_id, current_user.empresa_id, db)
    eta = _calcular_eta(campaign, _campaign_start_times.get(campaign.id))
    out = CampaignOut.model_validate(campaign)
    out.tempo_estimado_restante = eta
    return out


@router.put("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: int,
    request: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    campaign = _get_campaign_orm(campaign_id, current_user.empresa_id, db)
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
    campaign = _get_campaign_orm(campaign_id, current_user.empresa_id, db)
    if campaign.status == "concluida":
        raise HTTPException(status_code=400, detail="Esta campanha já foi concluída")
    if campaign.status == "em_andamento":
        raise HTTPException(status_code=400, detail="Esta campanha já está em andamento")

    # Iniciar disparo em background
    background_tasks.add_task(
        _executar_disparo_background,
        campaign_id,
        request.lead_ids,
        request.canal,
        current_user.empresa_id,
        request.delay_segundos
    )

    return {"message": "Disparo iniciado em background"}


@router.post("/{campaign_id}/cancelar")
async def cancelar_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    campaign = _get_campaign_orm(campaign_id, current_user.empresa_id, db)
    if campaign.status != "em_andamento":
        raise HTTPException(status_code=400, detail="Somente campanhas em andamento podem ser canceladas")
    _running_campaigns[campaign_id] = False
    campaign.status = "cancelada"
    campaign.atualizado_em = datetime.now()
    db.commit()
    return {"message": "Campanha cancelada"}


async def _executar_disparo_background(
    campaign_id: int,
    lead_ids: List[int],
    canal_override: str,
    empresa_id: int,
    delay_segundos: float | None = None
):
    """Função que roda em background para realizar o disparo real da campanha."""
    from app.core.database import SessionLocal
    from app.models.models import TenantCommercialInteraction, TipoInteracao, CanalInteracao

    db = SessionLocal()
    if delay_segundos is not None:
        delay_min = delay_segundos
        delay_max = delay_segundos
    else:
        delay_min = 2.0
        delay_max = 5.0

    _running_campaigns[campaign_id] = True
    _campaign_start_times[campaign_id] = time.time()
    inicio_ts = time.time()
    try:
        campaign = db.query(TenantCommercialCampaign).filter(TenantCommercialCampaign.id == campaign_id).first()
        if not campaign:
            return

        campaign.status = "em_andamento"
        campaign.atualizado_em = datetime.now()
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
            if not _running_campaigns.get(campaign_id):
                break

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
                campaign.enviados = enviados
                campaign.entregues = enviados
                campaign.atualizado_em = datetime.now()
                db.commit()
                await asyncio.sleep(random.uniform(delay_min, delay_max))

            except Exception as e:
                logger.error(f"Erro ao processar lead {lead.id} na campanha {campaign_id}: {e}")
                cl.status = "erro"
                falhas += 1
                campaign.enviados = enviados
                campaign.atualizado_em = datetime.now()
                db.commit()

        if _running_campaigns.get(campaign_id) is False:
            campaign.status = "cancelada"
            campaign.atualizado_em = datetime.now()
            db.commit()
        else:
            # Recorrência: reiniciar campanha se configurada
            proxima = None
            if campaign.recorrencia and campaign.recorrencia != "nenhuma" and campaign.data_agendamento:
                proxima = _proximo_agendamento(campaign.data_agendamento, campaign.recorrencia)

            if proxima:
                # Resetar leads para próxima execução
                db.query(TenantCampaignLead).filter(
                    TenantCampaignLead.campaign_id == campaign.id
                ).update({"status": "pendente", "data_envio": None, "data_entrega": None, "data_resposta": None})
                campaign.ultima_execucao = datetime.now()
                campaign.data_agendamento = proxima
                campaign.enviados = 0
                campaign.entregues = 0
                campaign.respondidos = 0
                campaign.status = "agendada"
                campaign.atualizado_em = datetime.now()
                db.commit()
                logger.info(f"Campanha recorrente {campaign_id} reagendada para {proxima}")
            else:
                campaign.status = "concluida"
                campaign.atualizado_em = datetime.now()
                db.commit()

    except Exception as e:
        logger.exception(f"Erro fatal no processamento da campanha {campaign_id}: {e}")
    finally:
        _running_campaigns.pop(campaign_id, None)
        _campaign_start_times.pop(campaign_id, None)
        db.close()


@router.get("/{campaign_id}/leads", response_model=List[CampaignLeadOut])
async def list_campaign_leads(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    _ = _get_campaign_orm(campaign_id, current_user.empresa_id, db)
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
    c = _get_campaign_orm(campaign_id, current_user.empresa_id, db)
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
        tempo_estimado_restante=_calcular_eta(c, _campaign_start_times.get(c.id)),
    )


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    campaign = _get_campaign_orm(campaign_id, current_user.empresa_id, db)
    db.query(TenantCampaignLead).filter(TenantCampaignLead.campaign_id == campaign_id).delete()
    db.delete(campaign)
    db.commit()
    return {"message": "Campanha removida"}
