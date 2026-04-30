"""Serialização de leads tenant no formato esperado pelo CRM (paridade com CommercialLeadOut)."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.orm import Session

from app.models.models import LeadScore, TenantCommercialLead, TenantPipelineEtapa

if TYPE_CHECKING:
    pass


def slugify_nome(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s.lower()).strip("_")
    return s or "etapa"


def _etapa_slug(db: Session, lead: TenantCommercialLead) -> str:
    if lead.etapa_pipeline_id is None:
        return lead.status_pipeline or "novo"
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.id == lead.etapa_pipeline_id,
            TenantPipelineEtapa.empresa_id == lead.empresa_id,
        )
        .first()
    )
    if not etapa:
        return lead.status_pipeline or "novo"
    return etapa.slug or slugify_nome(etapa.nome)


def tenant_lead_to_out(db: Session, lead: TenantCommercialLead) -> dict[str, Any]:
    """Dict compatível com CommercialLeadOut + campos extras usados no frontend."""
    nome = lead.nome or ""
    nome_emp = lead.nome_empresa or nome
    nome_resp = nome if lead.nome_empresa else nome
    status = _etapa_slug(db, lead)
    score = lead.lead_score if lead.lead_score is not None else LeadScore.FRIO
    return {
        "id": lead.id,
        "nome_responsavel": nome_resp,
        "nome_empresa": nome_emp,
        "whatsapp": lead.telefone,
        "email": lead.email,
        "cidade": None,
        "endereco": lead.endereco,
        "cep": getattr(lead, "cep", None),
        "logradouro": getattr(lead, "logradouro", None),
        "numero": getattr(lead, "numero", None),
        "complemento": getattr(lead, "complemento", None),
        "bairro": getattr(lead, "bairro", None),
        "uf": getattr(lead, "uf", None),
        "segmento_id": None,
        "origem_lead_id": None,
        "segmento_nome": lead.segmento,
        "origem_nome": lead.origem,
        "interesse_plano": None,
        "valor_proposto": lead.valor_estimado,
        "status_pipeline": status,
        "lead_score": score,
        "observacoes": lead.observacoes,
        "proximo_contato_em": lead.proximo_contato_em,
        "ultimo_contato_em": lead.ultimo_contato_em,
        "ativo": bool(lead.ativo),
        "criado_em": lead.criado_em or datetime.now(timezone.utc),
        "atualizado_em": lead.atualizado_em,
        "empresa_id": lead.empresa_id,
        "conta_criada_em": None,
        "ultimo_disparo_em": None,
        "etapa_pipeline_id": lead.etapa_pipeline_id,
    }


def sync_lead_status_from_etapa(db: Session, lead: TenantCommercialLead) -> None:
    """Mantém status_pipeline alinhado à etapa do pipeline."""
    lead.status_pipeline = _etapa_slug(db, lead)
