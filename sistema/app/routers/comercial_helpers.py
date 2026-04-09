"""
Helpers compartilhados do módulo comercial.
Funções utilitárias reutilizadas pelos routers comerciais.
"""

from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import (
    CommercialLead,
    CommercialConfig,
    LeadScore,
    StatusPipeline,
)


def _validar_contato_lead(lead_data):
    """Valida que lead tem whatsapp ou email."""
    whatsapp = getattr(lead_data, "whatsapp", None)
    email = getattr(lead_data, "email", None)
    if not whatsapp and not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe pelo menos um contato: WhatsApp ou e-mail.",
        )


def _lead_to_out(lead: CommercialLead) -> dict:
    """Converte lead ORM para dict com segmento_nome e origem_nome."""
    d = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
    d["segmento_nome"] = lead.segmento_rel.nome if lead.segmento_rel else None
    d["origem_nome"] = lead.origem_rel.nome if lead.origem_rel else None
    return d


def _render_template(
    conteudo: str, lead: CommercialLead, config: CommercialConfig = None
) -> str:
    """Renderiza variáveis do template com dados do lead."""
    vars_map = {
        "{{nome}}": lead.nome_responsavel or "",
        "{{empresa}}": lead.nome_empresa or "",
        "{{cidade}}": lead.cidade or "",
        "{{segmento}}": lead.segmento_rel.nome if lead.segmento_rel else "",
        "{{plano}}": lead.interesse_plano.value if lead.interesse_plano else "",
        "{{valor}}": f"R$ {lead.valor_proposto:,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        if lead.valor_proposto
        else "",
        "{{link_demo}}": config.link_demo if config and config.link_demo else "",
        "{{link_proposta}}": config.link_proposta
        if config and config.link_proposta
        else "",
    }
    resultado = conteudo
    for var, val in vars_map.items():
        resultado = resultado.replace(var, val)
    return resultado


def _calcular_score(lead: CommercialLead) -> LeadScore:
    """Calcula lead score baseado em critérios simples."""
    pontos = 0
    agora = datetime.now(timezone.utc)
    # Proposta enviada ou negociação
    if lead.status_pipeline in (
        StatusPipeline.PROPOSTA_ENVIADA,
        StatusPipeline.NEGOCIACAO,
    ):
        pontos += 3
    elif lead.status_pipeline == StatusPipeline.CONTATO_INICIADO:
        pontos += 1
    # Último contato recente (< 3 dias)
    if lead.ultimo_contato_em:
        dias = (agora - lead.ultimo_contato_em).days
        if dias <= 3:
            pontos += 2
        elif dias <= 7:
            pontos += 1
    # Tem valor proposto
    if lead.valor_proposto and lead.valor_proposto > 0:
        pontos += 1
    # Follow-up em dia
    if lead.proximo_contato_em and lead.proximo_contato_em >= agora:
        pontos += 1

    if pontos >= 5:
        return LeadScore.QUENTE
    elif pontos >= 2:
        return LeadScore.MORNO
    return LeadScore.FRIO


def _is_usuario_online(usuario) -> bool:
    """Verifica se o usuário está online (atividade nos últimos 5 minutos)."""
    if not usuario.ultima_atividade_em:
        return False
    agora = datetime.now(timezone.utc)
    diferenca = (agora - usuario.ultima_atividade_em).total_seconds()
    return diferenca < 300
