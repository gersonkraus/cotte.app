from typing import List
from sqlalchemy.orm import Session
from app.models.models import (
    Empresa,
    Usuario,
    CommercialLead,
    CommercialTemplate,
    Campaign,
    CampaignLead,
    CommercialInteraction,
    TipoInteracao,
    CanalInteracao,
)
from app.schemas.schemas import CampaignMetrics
from app.services.whatsapp_service import enviar_imagem_comercial, enviar_mensagem_texto_comercial, enviar_pdf_comercial
from app.services.email_service import send_email_simples
from app.services.template_anexos_service import obter_bytes_anexo
import logging

logger = logging.getLogger(__name__)
from datetime import datetime


class CampaignService:
    def __init__(self, db: Session, empresa: Empresa, usuario: Usuario):
        self.db = db
        self.empresa = empresa
        self.usuario = usuario

    def create_campaign(
        self, nome: str, template_id: int, canal: str, lead_ids: List[int]
    ) -> Campaign:
        """Cria uma nova campanha."""
        campaign = Campaign(
            empresa_id=self.empresa.id,
            nome=nome,
            template_id=template_id,
            canal=canal,
            status="agendada",
            total_leads=len(lead_ids),
        )
        self.db.add(campaign)
        self.db.flush()

        # Criar relacionamentos com leads
        for lead_id in lead_ids:
            lead = (
                self.db.query(CommercialLead)
                .filter(CommercialLead.id == lead_id)
                .first()
            )

            if lead:
                campaign_lead = CampaignLead(
                    campaign_id=campaign.id, lead_id=lead.id, status="pendente"
                )
                self.db.add(campaign_lead)

        self.db.commit()
        return campaign

    def update_campaign(self, campaign: Campaign, request) -> Campaign:
        """Atualiza uma campanha."""
        if request.nome:
            campaign.nome = request.nome
        if request.template_id:
            campaign.template_id = request.template_id
        if request.canal:
            campaign.canal = request.canal
        if request.status:
            campaign.status = request.status

        if hasattr(request, 'lead_ids') and request.lead_ids is not None:
            # Remover antigos
            self.db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign.id).delete()
            # Adicionar novos
            for lead_id in request.lead_ids:
                lead = self.db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
                if lead:
                    self.db.add(CampaignLead(campaign_id=campaign.id, lead_id=lead.id, status="pendente"))
            campaign.total_leads = len(request.lead_ids)

        self.db.commit()
        return campaign

    async def disparo_campaign(
        self, campaign: Campaign, lead_ids: List[int] = None, canal: str = None
    ):
        """Executa disparo de campanha em background."""
        try:
            campaign.status = "em_andamento"
            self.db.commit()

            # Obter template
            template = (
                self.db.query(CommercialTemplate)
                .filter(CommercialTemplate.id == campaign.template_id)
                .first()
            )

            if not template:
                logger.error(f"Template {campaign.template_id} não encontrado")
                return

            # Definir canal e leads
            canal_disparo = canal or campaign.canal
            leads_query = self.db.query(CampaignLead).filter(
                CampaignLead.campaign_id == campaign.id
            )

            if lead_ids:
                leads_query = leads_query.filter(CampaignLead.lead_id.in_(lead_ids))

            campaign_leads = leads_query.all()

            # Contadores
            enviados = 0
            entregues = 0
            respondidos = 0

            # Carregar anexo se existir (Internal CRM)
            anexo_bytes = None
            if hasattr(template, "anexo_arquivo_path") and template.anexo_arquivo_path:
                try:
                    anexo_bytes = await obter_bytes_anexo(template.anexo_arquivo_path)
                except Exception as e:
                    logger.warning(f"Falha ao carregar anexo da campanha {campaign.id}: {e}")

            for campaign_lead in campaign_leads:
                lead = (
                    self.db.query(CommercialLead)
                    .filter(CommercialLead.id == campaign_lead.lead_id)
                    .first()
                )

                if not lead:
                    continue

                try:
                    # Atualizar status
                    campaign_lead.status = "enviado"
                    campaign_lead.data_envio = datetime.now()
                    self.db.commit()

                    sucesso = False
                    mensagem_final = template.conteudo
                    # Substituições básicas
                    mensagem_final = mensagem_final.replace("{nome}", lead.nome_responsavel or "")
                    mensagem_final = mensagem_final.replace("{empresa}", lead.nome_empresa or "")

                    # Enviar mensagem
                    if canal_disparo in ["whatsapp", "ambos"]:
                        if lead.whatsapp:
                            if anexo_bytes:
                                mime = getattr(template, "anexo_mime_type", "image/png")
                                if mime.startswith("image/"):
                                    sucesso = await enviar_imagem_comercial(lead.whatsapp, anexo_bytes, caption=mensagem_final, mime_type=mime)
                                elif mime == "application/pdf":
                                    sucesso = await enviar_pdf_comercial(lead.whatsapp, anexo_bytes, numero=getattr(template, "anexo_nome_original", "documento"), caption=mensagem_final)
                                else:
                                    sucesso = await enviar_mensagem_texto_comercial(lead.whatsapp, mensagem_final)
                            else:
                                sucesso = await enviar_mensagem_texto_comercial(
                                    lead.whatsapp, mensagem_final
                                )
                            
                            if sucesso:
                                entregues += 1
                                campaign_lead.status = "entregue"
                                campaign_lead.data_entrega = datetime.now()
                                self.db.add(CommercialInteraction(
                                    lead_id=lead.id,
                                    tipo=TipoInteracao.WHATSAPP,
                                    canal=CanalInteracao.WHATSAPP,
                                    conteudo=f"Campanha [{campaign.nome}]: {mensagem_final}",
                                ))

                    if canal_disparo in ["email", "ambos"]:
                        if lead.email:
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
                                sucesso = True
                                entregues += 1
                                campaign_lead.status = "entregue"
                                campaign_lead.data_entrega = datetime.now()
                                self.db.add(CommercialInteraction(
                                    lead_id=lead.id,
                                    tipo=TipoInteracao.EMAIL,
                                    canal=CanalInteracao.EMAIL,
                                    conteudo=f"Campanha [{campaign.nome}] - Assunto: {template.assunto or campaign.nome}",
                                ))

                    if sucesso:
                        enviados += 1
                    
                    self.db.commit()

                    # Delay básico anti-spam
                    import asyncio
                    import random
                    await asyncio.sleep(random.uniform(2, 5))

                except Exception as e:
                    logger.error(f"Erro ao disparar para lead {lead.id}: {e}")
                    campaign_lead.status = "erro"
                    self.db.commit()

            # Atualizar estatísticas da campanha
            campaign.enviados = enviados
            campaign.entregues = entregues
            campaign.respondidos = respondidos
            campaign.status = "concluida"
            campaign.atualizado_em = datetime.now()

            self.db.commit()

        except Exception as e:
            logger.error(f"Erro no disparo da campanha {campaign.id}: {e}")
            campaign.status = "erro"
            self.db.commit()

    def get_campaign_metrics(self, campaign: Campaign) -> CampaignMetrics:
        """Obtém métricas de uma campanha."""
        leads = (
            self.db.query(CampaignLead)
            .filter(CampaignLead.campaign_id == campaign.id)
            .all()
        )

        total_leads = len(leads)
        enviados = len(
            [l for l in leads if l.status in ["enviado", "entregue", "respondido"]]
        )
        entregues = len([l for l in leads if l.status in ["entregue", "respondido"]])
        respondidos = len([l for l in leads if l.status == "respondido"])

        taxa_entrega = (entregues / enviados * 100) if enviados > 0 else 0
        taxa_resposta = (respondidos / entregues * 100) if entregues > 0 else 0

        # Contagem por status
        leads_por_status = {}
        for lead in leads:
            status = lead.status
            leads_por_status[status] = leads_por_status.get(status, 0) + 1

        return CampaignMetrics(
            total_leads=total_leads,
            enviados=enviados,
            entregues=entregues,
            respondidos=respondidos,
            taxa_entrega=taxa_entrega,
            taxa_resposta=taxa_resposta,
            leads_por_status=leads_por_status,
        )
