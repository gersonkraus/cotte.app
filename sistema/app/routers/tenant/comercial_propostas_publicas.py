from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    PropostaPublica,
    StatusProposta,
    TenantCommercialLead,
    TenantPropostaEnviada,
    TenantPropostaVisualizacao,
    Usuario,
)
from app.schemas.schemas import (
    PropostaAnalytics,
    PropostaEnviadaCreate,
    PropostaEnviadaOut,
    PropostaPublicaCreate,
    PropostaPublicaOut,
    PropostaPublicaUpdate,
)


router = APIRouter(
    prefix="/propostas-publicas",
    tags=["Tenant Comercial Propostas Públicas"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


@router.post("/", response_model=PropostaPublicaOut)
async def create_proposta_publica(
    request: PropostaPublicaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    blocos_json = [bloc.model_dump() for bloc in request.blocos] if request.blocos else []
    variaveis_json = [var.model_dump() for var in request.variaveis] if request.variaveis else []
    proposta = PropostaPublica(
        empresa_id=current_user.empresa_id,
        nome=request.nome,
        tipo="proposta_publica",
        blocos=blocos_json,
        variaveis=variaveis_json,
        ativo=True,
    )
    db.add(proposta)
    db.commit()
    db.refresh(proposta)
    return proposta


@router.get("/", response_model=List[PropostaPublicaOut])
async def list_propostas_publicas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
    ativo: Optional[bool] = Query(None),
):
    q = db.query(PropostaPublica).filter(PropostaPublica.empresa_id == current_user.empresa_id)
    if ativo is not None:
        q = q.filter(PropostaPublica.ativo == ativo)
    return q.order_by(PropostaPublica.criado_em.desc()).all()


@router.post("/leads/{lead_id}/propostas", response_model=PropostaEnviadaOut)
async def enviar_proposta_para_lead(
    lead_id: int,
    request: PropostaEnviadaCreate,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.id == lead_id,
            TenantCommercialLead.empresa_id == current_user.empresa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    proposta_template = (
        db.query(PropostaPublica)
        .filter(
            PropostaPublica.id == request.proposta_publica_id,
            PropostaPublica.empresa_id == current_user.empresa_id,
            PropostaPublica.ativo.is_(True),
        )
        .first()
    )
    if not proposta_template:
        raise HTTPException(status_code=404, detail="Template de proposta não encontrado")

    if not force:
        existente = (
            db.query(TenantPropostaEnviada)
            .filter(
                TenantPropostaEnviada.proposta_publica_id == request.proposta_publica_id,
                TenantPropostaEnviada.tenant_lead_id == lead_id,
                TenantPropostaEnviada.empresa_id == current_user.empresa_id,
                TenantPropostaEnviada.status.in_([StatusProposta.ENVIADA, StatusProposta.VISUALIZADA]),
            )
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=400,
                detail="Proposta já enviada para este lead. Use force=true para reenviar.",
            )
    else:
        anteriores = (
            db.query(TenantPropostaEnviada)
            .filter(
                TenantPropostaEnviada.proposta_publica_id == request.proposta_publica_id,
                TenantPropostaEnviada.tenant_lead_id == lead_id,
                TenantPropostaEnviada.empresa_id == current_user.empresa_id,
                TenantPropostaEnviada.status.in_([StatusProposta.ENVIADA, StatusProposta.VISUALIZADA]),
            )
            .all()
        )
        for a in anteriores:
            a.status = StatusProposta.SUBSTITUIDA

    proposta_enviada = TenantPropostaEnviada(
        empresa_id=current_user.empresa_id,
        proposta_publica_id=request.proposta_publica_id,
        tenant_lead_id=lead_id,
        slug=str(uuid.uuid4()),
        dados_personalizados=request.dados_personalizados,
        validade_dias=request.validade_dias,
        expira_em=datetime.now(timezone.utc) + timedelta(days=request.validade_dias),
        status=StatusProposta.ENVIADA,
    )
    db.add(proposta_enviada)
    db.commit()
    db.refresh(proposta_enviada)
    return proposta_enviada


@router.get("/leads/{lead_id}/propostas", response_model=List[PropostaEnviadaOut])
async def list_propostas_do_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    _ = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.id == lead_id,
            TenantCommercialLead.empresa_id == current_user.empresa_id,
        )
        .first()
    )
    return (
        db.query(TenantPropostaEnviada)
        .options(joinedload(TenantPropostaEnviada.proposta_template))
        .filter(
            TenantPropostaEnviada.tenant_lead_id == lead_id,
            TenantPropostaEnviada.empresa_id == current_user.empresa_id,
        )
        .order_by(TenantPropostaEnviada.criado_em.desc())
        .all()
    )


@router.get("/enviadas/{enviada_id}/analytics", response_model=PropostaAnalytics)
async def get_proposta_analytics(
    enviada_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    proposta_enviada = (
        db.query(TenantPropostaEnviada)
        .join(PropostaPublica, TenantPropostaEnviada.proposta_publica_id == PropostaPublica.id)
        .filter(
            TenantPropostaEnviada.id == enviada_id,
            PropostaPublica.empresa_id == current_user.empresa_id,
        )
        .first()
    )
    if not proposta_enviada:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    visualizacoes = (
        db.query(TenantPropostaVisualizacao)
        .filter(TenantPropostaVisualizacao.proposta_enviada_id == enviada_id)
        .order_by(TenantPropostaVisualizacao.criado_em.desc())
        .all()
    )
    total_visualizacoes = len(visualizacoes)
    tempo_medio = (
        sum(v.tempo_segundos for v in visualizacoes) / total_visualizacoes
        if total_visualizacoes
        else 0
    )
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
        visualizacoes=visualizacoes,
    )


@router.get("/{proposta_id}", response_model=PropostaPublicaOut)
async def get_proposta_publica(
    proposta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    proposta = (
        db.query(PropostaPublica)
        .filter(
            PropostaPublica.id == proposta_id,
            PropostaPublica.empresa_id == current_user.empresa_id,
        )
        .first()
    )
    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return proposta


@router.put("/{proposta_id}", response_model=PropostaPublicaOut)
async def update_proposta_publica(
    proposta_id: int,
    request: PropostaPublicaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    proposta = await get_proposta_publica(proposta_id, db, current_user)
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
    current_user: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    proposta = await get_proposta_publica(proposta_id, db, current_user)
    proposta.ativo = False
    db.commit()
    return {"message": "Proposta removida com sucesso"}
