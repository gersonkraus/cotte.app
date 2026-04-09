from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import List, Optional
import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.auth import exigir_permissao
from app.models.models import (
    Empresa, Usuario, PropostaPublica, PropostaEnviada, 
    CommercialLead, PropostaVisualizacao, StatusProposta
)
from app.schemas.schemas import (
    PropostaPublicaCreate, PropostaPublicaUpdate, PropostaPublicaOut,
    PropostaEnviadaCreate, PropostaEnviadaOut, PropostaAnalytics
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comercial/propostas-publicas", tags=["Comercial - Propostas Públicas"])


@router.post("/", response_model=PropostaPublicaOut)
async def create_proposta_publica(
    request: PropostaPublicaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Cria um novo template de proposta pública."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Converter blocos e variáveis para JSON
    blocos_json = [bloc.model_dump() for bloc in request.blocos] if request.blocos else []
    variaveis_json = [var.model_dump() for var in request.variaveis] if request.variaveis else []

    proposta = PropostaPublica(
        empresa_id=empresa.id,
        nome=request.nome,
        tipo="proposta_publica",
        blocos=blocos_json,
        variaveis=variaveis_json,
        ativo=True
    )
    db.add(proposta)
    db.commit()
    db.refresh(proposta)

    return proposta


@router.get("/", response_model=List[PropostaPublicaOut])
async def list_propostas_publicas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo")
):
    """Lista templates de propostas públicas da empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    query = db.query(PropostaPublica).filter(PropostaPublica.empresa_id == empresa.id)
    
    if ativo is not None:
        query = query.filter(PropostaPublica.ativo == ativo)
    
    propostas = query.order_by(PropostaPublica.criado_em.desc()).all()
    return propostas


@router.post("/leads/{lead_id}/propostas", response_model=PropostaEnviadaOut)
async def enviar_proposta_para_lead(
    lead_id: int,
    request: PropostaEnviadaCreate,
    force: bool = Query(False, description="Forçar reenvio mesmo se já existir proposta ativa"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Envia uma proposta para um lead específico."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Verificar se o lead pertence à empresa
    lead = db.query(CommercialLead).filter(
        CommercialLead.id == lead_id,
        (CommercialLead.empresa_id == empresa.id)
        | (CommercialLead.empresa_id.is_(None))
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Verificar se a proposta pública pertence à empresa
    proposta_template = db.query(PropostaPublica).filter(
        PropostaPublica.id == request.proposta_publica_id,
        PropostaPublica.empresa_id == empresa.id,
        PropostaPublica.ativo == True
    ).first()
    if not proposta_template:
        raise HTTPException(status_code=404, detail="Template de proposta não encontrado")

    # Verificar se já foi enviada proposta igual para este lead (apenas se não estiver forçando)
    if not force:
        existente = db.query(PropostaEnviada).filter(
            PropostaEnviada.proposta_publica_id == request.proposta_publica_id,
            PropostaEnviada.lead_id == lead_id,
            PropostaEnviada.status.in_([StatusProposta.ENVIADA, StatusProposta.VISUALIZADA])
        ).first()
        if existente:
            raise HTTPException(
                status_code=400, 
                detail=f"Proposta já enviada para este lead em {existente.criado_em.strftime('%d/%m/%Y')}. Deseja enviar novamente?"
            )
    
    # Se estiver forçando, inativar proposta anterior
    if force:
        propostas_anteriores = db.query(PropostaEnviada).filter(
            PropostaEnviada.proposta_publica_id == request.proposta_publica_id,
            PropostaEnviada.lead_id == lead_id,
            PropostaEnviada.status.in_([StatusProposta.ENVIADA, StatusProposta.VISUALIZADA])
        ).all()
        for pa in propostas_anteriores:
            pa.status = StatusProposta.SUBSTITUIDA

    # Criar proposta enviada
    slug = str(uuid.uuid4())
    expira_em = datetime.now(timezone.utc) + timedelta(days=request.validade_dias)

    proposta_enviada = PropostaEnviada(
        proposta_publica_id=request.proposta_publica_id,
        lead_id=lead_id,
        slug=slug,
        dados_personalizados=request.dados_personalizados,
        validade_dias=request.validade_dias,
        expira_em=expira_em,
        status=StatusProposta.ENVIADA
    )
    db.add(proposta_enviada)
    db.commit()
    db.refresh(proposta_enviada)
    db.refresh(proposta_enviada, attribute_names=["proposta_template"])

    return proposta_enviada


@router.get("/leads/{lead_id}/propostas", response_model=List[PropostaEnviadaOut])
async def list_propostas_do_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Lista propostas enviadas para um lead."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Verificar se o lead pertence à empresa
    lead = db.query(CommercialLead).filter(
        CommercialLead.id == lead_id,
        (CommercialLead.empresa_id == empresa.id)
        | (CommercialLead.empresa_id.is_(None))
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    propostas = db.query(PropostaEnviada).options(
        joinedload(PropostaEnviada.proposta_template)
    ).filter(
        PropostaEnviada.lead_id == lead_id
    ).order_by(PropostaEnviada.criado_em.desc()).all()

    return propostas


@router.get("/enviadas/{enviada_id}/analytics", response_model=PropostaAnalytics)
async def get_proposta_analytics(
    enviada_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Obtém analytics de uma proposta enviada."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Buscar proposta enviada
    proposta_enviada = db.query(PropostaEnviada).join(PropostaPublica).filter(
        PropostaEnviada.id == enviada_id,
        PropostaPublica.empresa_id == empresa.id
    ).first()
    if not proposta_enviada:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    # Buscar visualizações
    visualizacoes = db.query(PropostaVisualizacao).filter(
        PropostaVisualizacao.proposta_enviada_id == enviada_id
    ).order_by(PropostaVisualizacao.criado_em.desc()).all()

    # Calcular métricas
    total_visualizacoes = len(visualizacoes)
    tempo_medio = sum(v.tempo_segundos for v in visualizacoes) / total_visualizacoes if total_visualizacoes > 0 else 0
    
    # Seção mais vista
    secoes_count = {}
    for v in visualizacoes:
        if v.secao_mais_vista:
            secoes_count[v.secao_mais_vista] = secoes_count.get(v.secao_mais_vista, 0) + 1
    secao_mais_vista = max(secoes_count, key=secoes_count.get) if secoes_count else None

    return PropostaAnalytics(
        proposta=proposta_enviada,
        total_visualizacoes=total_visualizacoes,
        tempo_medio_segundos=tempo_medio,
        secao_mais_vista=secao_mais_vista,
        visualizacoes=visualizacoes
    )


@router.get("/{proposta_id}", response_model=PropostaPublicaOut)
async def get_proposta_publica(
    proposta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Obtém um template de proposta pública."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    proposta = db.query(PropostaPublica).filter(
        PropostaPublica.id == proposta_id,
        PropostaPublica.empresa_id == empresa.id
    ).first()

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    return proposta


@router.put("/{proposta_id}", response_model=PropostaPublicaOut)
async def update_proposta_publica(
    proposta_id: int,
    request: PropostaPublicaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Atualiza um template de proposta pública."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    proposta = db.query(PropostaPublica).filter(
        PropostaPublica.id == proposta_id,
        PropostaPublica.empresa_id == empresa.id
    ).first()

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    # Atualizar campos
    if request.nome:
        proposta.nome = request.nome
    if request.blocos is not None:
        proposta.blocos = [bloc.model_dump() for bloc in request.blocos]
    if request.variaveis is not None:
        proposta.variaveis = [var.model_dump() for var in request.variaveis]
    if request.ativo is not None:
        proposta.ativo = request.ativo

    db.commit()
    db.refresh(proposta)

    return proposta


@router.delete("/{proposta_id}")
async def delete_proposta_publica(
    proposta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "admin"))
):
    """Remove um template de proposta pública (soft delete)."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    proposta = db.query(PropostaPublica).filter(
        PropostaPublica.id == proposta_id,
        PropostaPublica.empresa_id == empresa.id
    ).first()

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    proposta.ativo = False
    db.commit()

    return {"message": "Proposta removida com sucesso"}

