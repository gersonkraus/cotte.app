from typing import List
from sqlalchemy.orm import Session
from app.models.models import (
    Empresa,
    Usuario,
    CommercialLead,
    CommercialTemplate,
    Campaign,
    CampaignLead,
)
from app.schemas.schemas import CampaignMetrics
from app.services.whatsapp_service import enviar_mensagem_texto
from app.services.email_service import send_email_simples
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

                    # Enviar mensagem
                    if canal_disparo in ["whatsapp", "ambos"]:
                        if lead.whatsapp:
                            success = await enviar_mensagem_texto(
                                lead.whatsapp, template.conteudo, empresa=self.empresa
                            )
                            if success:
                                campaign_lead.status = "entregue"
                                campaign_lead.data_entrega = datetime.now()
                                entregues += 1

                    if canal_disparo in ["email", "ambos"]:
                        if lead.email:
                            success = send_email_simples(
                                lead.email,
                                template.assunto or f"Campanha {campaign.nome}",
                                template.conteudo,
                            )
                            if success:
                                campaign_lead.status = "entregue"
                                campaign_lead.data_entrega = datetime.now()
                                entregues += 1

                    enviados += 1
                    self.db.commit()

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
