"""Serialização de leads tenant no formato esperado pelo CRM (paridade com CommercialLeadOut)."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import (
    LeadScore,
    TenantCommercialInteraction,
    TenantCommercialLead,
    TenantPipelineEtapa,
    TipoInteracao,
)

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


def _dt_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def max_criado_whatsapp_recebido_por_lead(
    db: Session, empresa_id: int, lead_ids: list[int]
) -> dict[int, datetime]:
    """Máximo de criado_em por lead_id para interações WhatsApp recebidas."""
    if not lead_ids:
        return {}
    rows = (
        db.query(
            TenantCommercialInteraction.lead_id,
            func.max(TenantCommercialInteraction.criado_em).label("mx"),
        )
        .filter(
            TenantCommercialInteraction.empresa_id == empresa_id,
            TenantCommercialInteraction.lead_id.in_(lead_ids),
            TenantCommercialInteraction.tipo == TipoInteracao.WHATSAPP,
            TenantCommercialInteraction.direcao == "recebido",
        )
        .group_by(TenantCommercialInteraction.lead_id)
        .all()
    )
    return {int(r.lead_id): r.mx for r in rows if r.mx is not None}


def nova_resposta_whatsapp_para_lead(
    lead: TenantCommercialLead, max_recebido_em: datetime | None
) -> bool:
    """True se a última resposta WhatsApp do lead é mais recente que a última visualização."""
    if max_recebido_em is None:
        return False
    mx = _dt_utc(max_recebido_em)
    vista = _dt_utc(getattr(lead, "whatsapp_conversa_vista_em", None))
    if mx is None:
        return False
    if vista is None:
        return True
    return mx > vista


def leads_to_out_com_nova_whatsapp(
    db: Session, empresa_id: int, leads: list[TenantCommercialLead]
) -> list[dict[str, Any]]:
    """Serializa leads com flag ``nova_resposta_whatsapp`` (uma query agregada por página)."""
    if not leads:
        return []
    mx_map = max_criado_whatsapp_recebido_por_lead(db, empresa_id, [l.id for l in leads])
    out: list[dict[str, Any]] = []
    for lead in leads:
        d = tenant_lead_to_out(db, lead)
        d["nova_resposta_whatsapp"] = nova_resposta_whatsapp_para_lead(lead, mx_map.get(lead.id))
        out.append(d)
    return out


def lead_to_out_com_nova_whatsapp(db: Session, empresa_id: int, lead: TenantCommercialLead) -> dict[str, Any]:
    """Um lead com flag ``nova_resposta_whatsapp``."""
    return leads_to_out_com_nova_whatsapp(db, empresa_id, [lead])[0]


def sync_lead_status_from_etapa(db: Session, lead: TenantCommercialLead) -> None:
    """Mantém status_pipeline alinhado à etapa do pipeline."""
    lead.status_pipeline = _etapa_slug(db, lead)
