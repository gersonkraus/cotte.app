from typing import List, Optional, Dict, Any
import re
import logging
from sqlalchemy.orm import Session
from app.models.models import (
    Empresa,
    Usuario,
    CommercialLead,
    CommercialLeadSource,
    CommercialSegment,
)
from app.schemas.schemas import LeadImportItem
from app.services.ai_json_extractor import AIJSONExtractor

logger = logging.getLogger(__name__)


class LeadImportService:
    def __init__(self, db: Session, empresa: Empresa, usuario: Usuario):
        self.db = db
        self.empresa = empresa
        self.usuario = usuario

    def parse_text_to_leads(self, text: str) -> List[LeadImportItem]:
        """Parse texto colado para lista de leads (fallback sem AI)."""
        leads = []
        lines = text.strip().split("\n")

        for line in lines:
            if not line.strip():
                continue

            parts = [p.strip() for p in line.split("-")]
            if len(parts) >= 2:
                nome = parts[0]
                whatsapp = parts[1] if len(parts) > 1 else None
                email = parts[2] if len(parts) > 2 else None
                cidade = parts[3] if len(parts) > 3 else None

                leads.append(
                    LeadImportItem(
                        nome_responsavel=nome,
                        nome_empresa=nome,
                        whatsapp=whatsapp,
                        email=email,
                        cidade=cidade,
                        observacoes="Importado via texto",
                    )
                )

        return leads

    async def parse_text_to_leads_with_ai(
        self,
        text: str,
        segmentos_map: Optional[Dict[str, int]] = None,
        origens_map: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Usa AI para extrair leads de texto colado, com fallback para parse simples.
        """
        if segmentos_map is None:
            segmentos_map = {
                s.nome.lower(): s.id
                for s in self.db.query(CommercialSegment)
                .filter(CommercialSegment.ativo == True)
                .all()
            }
        if origens_map is None:
            origens_map = {
                o.nome.lower(): o.id
                for o in self.db.query(CommercialLeadSource)
                .filter(CommercialLeadSource.ativo == True)
                .all()
            }

        try:
            from app.services.ia_service import analisar_leads

            resposta = await analisar_leads(text)

            if resposta and resposta.get("items"):
                return self._process_ai_response(
                    resposta["items"], segmentos_map, origens_map
                )
        except Exception as e:
            logger.warning(f"AI falhou, usando fallback: {e}")

        items_fallback = self._parse_fallback_regex(text)
        return self._process_ai_response(items_fallback, segmentos_map, origens_map)

    def _process_ai_response(
        self,
        items: List[Dict],
        segmentos_map: Dict[str, int],
        origens_map: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """Processa resposta da AI, validando e resolvendo IDs."""
        processed = []
        for item in items:
            nr = (item.get("nome_responsavel") or item.get("nome") or "").strip()
            ne = (item.get("nome_empresa") or item.get("empresa") or "").strip()
            if not nr and ne:
                item["nome_responsavel"] = ne

            whatsapp = (item.get("whatsapp") or "").strip()
            email = (item.get("email") or "").strip()

            if not whatsapp and not email:
                continue

            if whatsapp:
                clean_whatsapp = re.sub(r"\D", "", whatsapp)
                if len(clean_whatsapp) < 10:
                    continue
                whatsapp = clean_whatsapp
                item["whatsapp"] = whatsapp

            dup_filters = []
            if whatsapp:
                dup_filters.append(CommercialLead.whatsapp == whatsapp)
            if email:
                dup_filters.append(CommercialLead.email == email)

            duplicado = (
                self.db.query(CommercialLead)
                .filter(CommercialLead.empresa_id == self.empresa.id)
                .filter(*dup_filters)
                .first()
                if dup_filters
                else None
            )

            item["duplicado"] = duplicado is not None
            item["selecionado"] = duplicado is None

            segmento_nome = (item.get("segmento_nome") or "").strip().lower()
            origem_nome = (item.get("origem_nome") or "").strip().lower()
            item["segmento_id"] = segmentos_map.get(segmento_nome)
            item["origem_lead_id"] = origens_map.get(origem_nome)

            processed.append(item)

        return processed

    def _parse_fallback_regex(self, text: str) -> List[Dict[str, Any]]:
        """Parser regex de fallback quando AI falha."""
        items = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split("-")]
            if len(parts) >= 2:
                nome = parts[0]
                whatsapp = re.sub(r"\D", "", parts[1]) if len(parts) > 1 else ""
                email = parts[2] if len(parts) > 2 else ""
                cidade = parts[3] if len(parts) > 3 else ""

                if nome and (whatsapp or email):
                    items.append(
                        {
                            "nome_responsavel": nome,
                            "nome_empresa": nome,
                            "whatsapp": whatsapp if len(whatsapp) >= 10 else "",
                            "email": email,
                            "cidade": cidade,
                            "segmento_nome": "",
                            "origem_nome": "",
                        }
                    )
            else:
                nome_match = re.match(r"^([A-Za-zÀ-ú\s]+?)[,\s]", line)
                tel_match = re.search(r"(\d{10,13})", line)
                email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", line)

                if nome_match or tel_match or email_match:
                    items.append(
                        {
                            "nome_responsavel": nome_match.group(1).strip()
                            if nome_match
                            else "",
                            "nome_empresa": "",
                            "whatsapp": tel_match.group(1) if tel_match else "",
                            "email": email_match.group(0) if email_match else "",
                            "cidade": "",
                            "segmento_nome": "",
                            "origem_nome": "",
                        }
                    )

        return items

    def validate_lead(self, lead: LeadImportItem) -> bool:
        """Valida se o lead tem dados mínimos."""
        return bool(lead.nome_responsavel and (lead.whatsapp or lead.email))

    def check_duplicate(self, lead: LeadImportItem) -> bool:
        """Verifica se já existe lead com mesmo WhatsApp ou Email."""
        exists = (
            self.db.query(CommercialLead)
            .filter(
                CommercialLead.empresa_id == self.empresa.id,
                (CommercialLead.whatsapp == lead.whatsapp)
                | (CommercialLead.email == lead.email),
            )
            .first()
        )

        return exists is not None

    def check_duplicate_dict(
        self, lead_data: Dict[str, Any]
    ) -> Optional[CommercialLead]:
        """Verifica duplicata para dicionário (usado no fluxo AI)."""
        whatsapp = lead_data.get("whatsapp")
        email = lead_data.get("email")

        if not whatsapp and not email:
            return None

        filters = []
        if whatsapp:
            filters.append(CommercialLead.whatsapp == whatsapp)
        if email:
            filters.append(CommercialLead.email == email)

        return (
            self.db.query(CommercialLead)
            .filter(CommercialLead.empresa_id == self.empresa.id)
            .filter(*filters)
            .first()
        )

    def get_or_create_default_source(self) -> CommercialLeadSource:
        """Obtém ou cria origem padrão 'Importação em Massa'."""
        source = (
            self.db.query(CommercialLeadSource)
            .filter(
                CommercialLeadSource.nome == "Importação em Massa",
                CommercialLeadSource.empresa_id == self.empresa.id,
            )
            .first()
        )

        if not source:
            source = CommercialLeadSource(
                nome="Importação em Massa", empresa_id=self.empresa.id, ativo=True
            )
            self.db.add(source)
            self.db.flush()

        return source
