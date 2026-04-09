from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
import logging
from datetime import datetime, timezone
import time

from app.core.database import get_db
from app.models.models import (
    PropostaEnviada, PropostaPublica, PropostaVisualizacao, 
    StatusProposta, Empresa, StatusPipeline, CommercialLead
)
from app.schemas.schemas import (
    PropostaPublicaView, PropostaAceite, PropostaPing
)

logger = logging.getLogger(__name__)


def _agora_utc() -> datetime:
    """Datetime aware em UTC (compatível com colunas DateTime(timezone=True))."""
    return datetime.now(timezone.utc)


def _expirou(expira_em: Optional[datetime]) -> bool:
    """Compara expiração com agora sem TypeError (naive vs aware)."""
    if not expira_em:
        return False
    alvo = expira_em
    if alvo.tzinfo is None:
        alvo = alvo.replace(tzinfo=timezone.utc)
    return alvo < _agora_utc()


# Rate limiting simples em memória
_rate_limit_store = {}

def check_rate_limit(request: Request, limit: int = 60, window: int = 60) -> bool:
    """Verifica rate limit baseado em IP."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Limpar entradas antigas
    _rate_limit_store[client_ip] = [
        timestamp for timestamp in _rate_limit_store.get(client_ip, [])
        if now - timestamp < window
    ]
    
    # Verificar limite
    if len(_rate_limit_store[client_ip]) >= limit:
        return False
    
    # Adicionar requisição atual
    _rate_limit_store[client_ip].append(now)
    return True

router = APIRouter(tags=["Propostas Públicas"])


@router.get("/p/{slug}/data", response_model=PropostaPublicaView)
async def visualizar_proposta_publica(
    slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Renderiza página pública da proposta."""
    # Buscar proposta enviada
    proposta_enviada = db.query(PropostaEnviada).join(PropostaPublica).filter(
        PropostaEnviada.slug == slug,
        PropostaPublica.ativo == True
    ).first()
    
    if not proposta_enviada:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    
    # Verificar validade (evita TypeError entre naive e aware)
    if _expirou(proposta_enviada.expira_em):
        proposta_enviada.status = StatusProposta.EXPIRADA
        db.commit()
        raise HTTPException(status_code=410, detail="Proposta expirada")
    
    # Atualizar status para visualizada na primeira visita
    if proposta_enviada.status == StatusProposta.ENVIADA:
        proposta_enviada.status = StatusProposta.VISUALIZADA
        db.commit()
    
    # Preparar dados da empresa
    empresa = db.query(Empresa).filter(
        Empresa.id == proposta_enviada.proposta_template.empresa_id
    ).first()
    
    empresa_data = None
    if empresa:
        empresa_data = {
            "nome": empresa.nome,
            "logo_url": empresa.logo_url,
            "cor_primaria": empresa.cor_primaria or "#00e5a0"
        }
    
    # Registrar visualização inicial (sem tempo)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    visualizacao = PropostaVisualizacao(
        proposta_enviada_id=proposta_enviada.id,
        ip=ip,
        user_agent=user_agent,
        tempo_segundos=0
    )
    db.add(visualizacao)
    db.commit()
    
    tpl = proposta_enviada.proposta_template
    blocos = tpl.blocos if isinstance(tpl.blocos, list) else []
    dados = (
        proposta_enviada.dados_personalizados
        if isinstance(proposta_enviada.dados_personalizados, dict)
        else {}
    )

    return PropostaPublicaView(
        slug=proposta_enviada.slug,
        nome=tpl.nome,
        blocos=blocos,
        dados_personalizados=dados,
        validade_dias=proposta_enviada.validade_dias,
        expira_em=proposta_enviada.expira_em,
        status=proposta_enviada.status.value,
        empresa=empresa_data,
    )


@router.post("/p/{slug}/aceitar")
async def aceitar_proposta(
    slug: str,
    request: Request,
    aceite: PropostaAceite,
    db: Session = Depends(get_db)
):
    """Registra aceite da proposta."""
    # Rate limit: 5 tentativas por minuto
    if not check_rate_limit(request, limit=5, window=60):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente novamente em alguns minutos.")
    
    # Buscar proposta enviada
    proposta_enviada = db.query(PropostaEnviada).join(PropostaPublica).filter(
        PropostaEnviada.slug == slug,
        PropostaPublica.ativo == True
    ).first()
    
    if not proposta_enviada:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    
    # Verificar se já foi aceita
    if proposta_enviada.status == StatusProposta.ACEITA:
        raise HTTPException(status_code=400, detail="Proposta já foi aceita")
    
    # Verificar validade
    if _expirou(proposta_enviada.expira_em):
        raise HTTPException(status_code=410, detail="Proposta expirada")
    
    # Registrar aceite
    proposta_enviada.status = StatusProposta.ACEITA
    proposta_enviada.aceita_em = _agora_utc()
    proposta_enviada.aceita_por_nome = aceite.nome
    proposta_enviada.aceita_por_email = aceite.email
    
    # Atualizar o lead associado para FECHADO_GANHO
    if proposta_enviada.lead_id:
        lead = db.query(CommercialLead).filter(CommercialLead.id == proposta_enviada.lead_id).first()
        if lead:
            lead.status_pipeline = StatusPipeline.FECHADO_GANHO
            logger.info(f"Lead {lead.id} atualizado para FECHADO_GANHO após aceite de proposta {proposta_enviada.id}")
    
    db.commit()
    
    return {
        "message": "Proposta aceita com sucesso!",
        "data": proposta_enviada.aceita_em.isoformat(),
        "nome": aceite.nome
    }


@router.post("/p/{slug}/ping")
async def ping_proposta(
    slug: str,
    request: Request,
    ping: PropostaPing,
    db: Session = Depends(get_db)
):
    """Registra rastreamento de visualização."""
    # Rate limit: 60 pings por minuto
    if not check_rate_limit(request, limit=60, window=60):
        raise HTTPException(status_code=429, detail="Too many requests")
    
    # Buscar proposta enviada
    proposta_enviada = db.query(PropostaEnviada).join(PropostaPublica).filter(
        PropostaEnviada.slug == slug,
        PropostaPublica.ativo == True
    ).first()
    
    if not proposta_enviada:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    
    # Buscar última visualização deste IP
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    ultima_visualizacao = db.query(PropostaVisualizacao).filter(
        PropostaVisualizacao.proposta_enviada_id == proposta_enviada.id,
        PropostaVisualizacao.ip == ip
    ).order_by(PropostaVisualizacao.criado_em.desc()).first()
    
    # Atualizar ou criar visualização
    if ultima_visualizacao:
        # Atualizar tempo e seção
        ultima_visualizacao.tempo_segundos = ping.tempo
        if ping.secao:
            ultima_visualizacao.secao_mais_vista = ping.secao
        ultima_visualizacao.criado_em = _agora_utc()
    else:
        # Criar nova visualização
        visualizacao = PropostaVisualizacao(
            proposta_enviada_id=proposta_enviada.id,
            ip=ip,
            user_agent=user_agent,
            secao_mais_vista=ping.secao,
            tempo_segundos=ping.tempo
        )
        db.add(visualizacao)
    
    db.commit()
    
    return {"status": "ok"}
