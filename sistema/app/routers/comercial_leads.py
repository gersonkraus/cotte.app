"""
Router de Leads Comerciais — CRUD, dashboard, criação de empresa,
reenvio de senha, importações e envio em lote.
"""

from datetime import datetime, timezone
from typing import List, Optional
import re
import asyncio
import random
import logging
import string

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.core.database import get_db
from app.core.auth import get_superadmin, hash_senha, exigir_permissao
from app.core.config import settings
from app.models.models import (
    Usuario,
    Empresa,
    Orcamento,
    CommercialLead,
    CommercialInteraction,
    CommercialSegment,
    CommercialLeadSource,
    CommercialReminder,
    CommercialConfig,
    CommercialTemplate,
    LeadImportacao,
    LeadImportacaoItem,
    CampaignLead,
    StatusPipeline,
    TipoInteracao,
    CanalInteracao,
    LeadScore,
    StatusOrcamento,
    StatusLembrete,
)
from app.schemas.schemas import (
    CommercialLeadCreate,
    CommercialLeadUpdate,
    DashboardMetrics,
    ReenviarSenhaResponse,
)
from app.services.whatsapp_service import enviar_mensagem_texto
from app.services.email_service import send_email_simples, enviar_email_boas_vindas
from app.services.ia_service import analisar_leads
from app.routers.comercial_helpers import (
    _validar_contato_lead,
    _lead_to_out,
    _calcular_score,
    _is_usuario_online,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comercial", tags=["Comercial - Leads"])


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Retorna métricas do dashboard comercial."""
    hoje = datetime.now(timezone.utc)
    ativos = db.query(CommercialLead).filter(CommercialLead.ativo == True)

    total = ativos.count()
    novos = ativos.filter(CommercialLead.status_pipeline == StatusPipeline.NOVO).count()
    propostas = ativos.filter(
        CommercialLead.status_pipeline == StatusPipeline.PROPOSTA_ENVIADA
    ).count()
    negociacoes = ativos.filter(
        CommercialLead.status_pipeline == StatusPipeline.NEGOCIACAO
    ).count()
    ganhos = ativos.filter(
        CommercialLead.status_pipeline == StatusPipeline.FECHADO_GANHO
    ).count()
    perdidos = ativos.filter(
        CommercialLead.status_pipeline == StatusPipeline.FECHADO_PERDIDO
    ).count()

    followups = ativos.filter(
        CommercialLead.proximo_contato_em <= hoje,
        CommercialLead.status_pipeline.notin_(
            [StatusPipeline.FECHADO_GANHO, StatusPipeline.FECHADO_PERDIDO]
        ),
    ).count()

    lembretes_pendentes = (
        db.query(CommercialReminder)
        .filter(
            CommercialReminder.status.in_(
                [StatusLembrete.PENDENTE, StatusLembrete.ATRASADO]
            )
        )
        .count()
    )

    leads_sem_contato = ativos.filter(
        CommercialLead.status_pipeline == StatusPipeline.NOVO,
        CommercialLead.ultimo_contato_em == None,
    ).count()

    propostas_sem_retorno = ativos.filter(
        CommercialLead.status_pipeline == StatusPipeline.PROPOSTA_ENVIADA,
        or_(
            CommercialLead.proximo_contato_em == None,
            CommercialLead.proximo_contato_em < hoje,
        ),
    ).count()

    empresas_em_trial = (
        db.query(Empresa)
        .filter(
            Empresa.ativo == True,
            func.lower(Empresa.plano) == "trial",
            or_(Empresa.trial_ate.is_(None), Empresa.trial_ate > hoje),
        )
        .count()
    )

    return DashboardMetrics(
        total_leads=total,
        novos=novos,
        propostas_enviadas=propostas,
        negociacoes=negociacoes,
        fechados_ganho=ganhos,
        fechados_perdido=perdidos,
        follow_ups_hoje=followups,
        lembretes_pendentes=lembretes_pendentes,
        leads_sem_contato=leads_sem_contato,
        propostas_sem_retorno=propostas_sem_retorno,
        empresas_em_trial=empresas_em_trial,
    )


@router.get("/leads/follow-ups-hoje")
def get_followups_hoje(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Retorna leads com follow-up para hoje."""
    hoje = datetime.now(timezone.utc)
    leads = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
        )
        .filter(
            CommercialLead.ativo == True,
            CommercialLead.proximo_contato_em <= hoje,
            CommercialLead.status_pipeline.notin_(
                [StatusPipeline.FECHADO_GANHO, StatusPipeline.FECHADO_PERDIDO]
            ),
        )
        .order_by(CommercialLead.proximo_contato_em.asc())
        .all()
    )
    return [_lead_to_out(l) for l in leads]


@router.get("/leads/recentes")
def get_leads_recentes(
    limit: int = 5, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Retorna leads mais recentes."""
    leads = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
        )
        .filter(CommercialLead.ativo == True)
        .order_by(CommercialLead.criado_em.desc())
        .limit(limit)
        .all()
    )
    return [_lead_to_out(l) for l in leads]


@router.get("/leads/sem-contato")
def get_leads_sem_contato(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Retorna leads novos sem primeiro contato."""
    leads = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
        )
        .filter(
            CommercialLead.ativo == True,
            CommercialLead.status_pipeline == StatusPipeline.NOVO,
            CommercialLead.ultimo_contato_em == None,
        )
        .order_by(CommercialLead.criado_em.asc())
        .all()
    )
    return [_lead_to_out(l) for l in leads]


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD LEADS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/leads")
def list_leads(
    status_pipeline: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    segmento_id: Optional[int] = None,
    origem_lead_id: Optional[int] = None,
    lead_score: Optional[LeadScore] = None,
    ativo: Optional[bool] = True,
    empresa_trial: Optional[bool] = Query(
        None,
        description="Quando true, apenas leads vinculados a empresas em trial ativo.",
    ),
    follow_up_hoje: Optional[bool] = Query(
        None,
        description=(
            "Quando true, apenas leads com próximo contato até agora, "
            "pipeline aberto (não ganho/perdido)."
        ),
    ),
    has_whatsapp: Optional[bool] = Query(
        None,
        description="Apenas leads com WhatsApp",
    ),
    has_email: Optional[bool] = Query(
        None,
        description="Apenas leads com E-mail",
    ),
    sem_contato_dias: Optional[int] = Query(
        None,
        description="Apenas leads sem contato nos últimos N dias",
    ),
    novo_dias: Optional[int] = Query(
        None,
        description="Apenas leads criados nos últimos N dias",
    ),
    status_pipeline_notin: Optional[str] = Query(
        None,
        description="Status a excluir (separados por vírgula)",
    ),
    order_by: Optional[str] = "criado_em",
    order_dir: Optional[str] = "desc",
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Lista leads com busca, filtros, ordenação e paginação."""
    from app.models.models import Empresa

    query = db.query(CommercialLead).options(
        joinedload(CommercialLead.segmento_rel),
        joinedload(CommercialLead.origem_rel),
    )

    if ativo is not None:
        query = query.filter(CommercialLead.ativo == ativo)
    if status_pipeline:
        query = query.filter(CommercialLead.status_pipeline == status_pipeline)
    if segmento_id:
        query = query.filter(CommercialLead.segmento_id == segmento_id)
    if origem_lead_id:
        query = query.filter(CommercialLead.origem_lead_id == origem_lead_id)
    if lead_score:
        query = query.filter(CommercialLead.lead_score == lead_score)
    if empresa_trial:
        hoje = datetime.now(timezone.utc)
        query = query.join(Empresa, CommercialLead.empresa_id == Empresa.id).filter(
            Empresa.ativo == True,
            func.lower(Empresa.plano) == "trial",
            or_(Empresa.trial_ate.is_(None), Empresa.trial_ate > hoje),
        )
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                CommercialLead.nome_responsavel.ilike(term),
                CommercialLead.nome_empresa.ilike(term),
                CommercialLead.email.ilike(term),
                CommercialLead.whatsapp.ilike(term),
                CommercialLead.cidade.ilike(term),
            )
        )

    if status_pipeline_notin:
        excluir = [s.strip() for s in status_pipeline_notin.split(",") if s.strip()]
        if excluir:
            query = query.filter(CommercialLead.status_pipeline.notin_(excluir))

    if has_whatsapp is True:
        query = query.filter(
            CommercialLead.whatsapp.isnot(None), CommercialLead.whatsapp != ""
        )
    elif has_whatsapp is False:
        query = query.filter(
            or_(CommercialLead.whatsapp.is_(None), CommercialLead.whatsapp == "")
        )

    if has_email is True:
        query = query.filter(
            CommercialLead.email.isnot(None), CommercialLead.email != ""
        )
    elif has_email is False:
        query = query.filter(
            or_(CommercialLead.email.is_(None), CommercialLead.email == "")
        )

    agora = datetime.now(timezone.utc)
    if novo_dias:
        from datetime import timedelta

        data_limite = agora - timedelta(days=novo_dias)
        query = query.filter(CommercialLead.criado_em >= data_limite)

    if sem_contato_dias:
        from datetime import timedelta

        data_limite = agora - timedelta(days=sem_contato_dias)
        query = query.filter(
            or_(
                CommercialLead.ultimo_contato_em.is_(None),
                CommercialLead.ultimo_contato_em <= data_limite,
            )
        )

    if follow_up_hoje:
        query = query.filter(CommercialLead.proximo_contato_em.isnot(None))
        query = query.filter(CommercialLead.proximo_contato_em <= agora)
        query = query.filter(
            CommercialLead.status_pipeline.notin_(
                [StatusPipeline.FECHADO_GANHO, StatusPipeline.FECHADO_PERDIDO]
            )
        )

    col = getattr(CommercialLead, order_by, CommercialLead.criado_em)
    if order_dir == "asc":
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())

    total = query.count()
    offset = (page - 1) * per_page
    leads = query.offset(offset).limit(per_page).all()

    # Busca ultimo disparo para os leads da página (Termostato de Spam)
    lead_ids = [l.id for l in leads]
    ultimos_disparos = {}
    if lead_ids:
        from app.models.models import CampaignLead

        resultados = (
            db.query(
                CampaignLead.lead_id, func.max(CampaignLead.criado_em).label("ultimo")
            )
            .filter(CampaignLead.lead_id.in_(lead_ids))
            .group_by(CampaignLead.lead_id)
            .all()
        )
        ultimos_disparos = {r.lead_id: r.ultimo for r in resultados}

    items = []
    for l in leads:
        out = _lead_to_out(l)
        ultimo = ultimos_disparos.get(l.id)
        out["ultimo_disparo_em"] = ultimo.isoformat() if ultimo else None
        items.append(out)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page else 1,
    }


@router.post("/leads", status_code=status.HTTP_201_CREATED)
def create_lead(
    data: CommercialLeadCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria um novo lead comercial."""
    _validar_contato_lead(data)

    lead_data = data.model_dump()
    lead = CommercialLead(**lead_data)
    db.add(lead)
    db.flush()

    interacao = CommercialInteraction(
        lead_id=lead.id,
        tipo=TipoInteracao.OBSERVACAO,
        canal=CanalInteracao.OUTRO,
        conteudo="Lead criado",
    )
    db.add(interacao)
    db.commit()
    db.refresh(lead)
    db.refresh(lead, attribute_names=["segmento_rel", "origem_rel"])
    return _lead_to_out(lead)


@router.get("/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Retorna detalhes de um lead com histórico, lembretes e dados da empresa vinculada."""
    lead = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.interacoes),
            joinedload(CommercialLead.lembretes),
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
            joinedload(CommercialLead.empresa_rel),
        )
        .filter(CommercialLead.id == lead_id)
        .first()
    )

    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    d = _lead_to_out(lead)
    d["interacoes"] = [
        {c.name: getattr(i, c.name) for c in i.__table__.columns}
        for i in lead.interacoes
    ]
    d["lembretes"] = []
    for r in lead.lembretes:
        rd = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        rd["lead_nome_empresa"] = lead.nome_empresa
        rd["lead_nome_responsavel"] = lead.nome_responsavel
        d["lembretes"].append(rd)

    if lead.empresa_id and lead.empresa_rel:
        empresa = lead.empresa_rel
        usuarios = db.query(Usuario).filter(Usuario.empresa_id == empresa.id).all()

        total_orcamentos = (
            db.query(func.count(Orcamento.id))
            .filter(Orcamento.empresa_id == empresa.id)
            .scalar()
            or 0
        )
        orcamentos_aprovados = (
            db.query(func.count(Orcamento.id))
            .filter(
                Orcamento.empresa_id == empresa.id,
                Orcamento.status == StatusOrcamento.APROVADO,
            )
            .scalar()
            or 0
        )
        orcamentos_pendentes = (
            db.query(func.count(Orcamento.id))
            .filter(
                Orcamento.empresa_id == empresa.id,
                Orcamento.status.in_(
                    [StatusOrcamento.ENVIADO, StatusOrcamento.RASCUNHO]
                ),
            )
            .scalar()
            or 0
        )

        empresa_status = "trial"
        if (
            empresa.assinatura_valida_ate
            and empresa.assinatura_valida_ate < datetime.now(timezone.utc)
        ):
            empresa_status = "expirado"
        elif empresa.plano and empresa.plano != "trial":
            empresa_status = "pagante"
        elif empresa.ativo is False:
            empresa_status = "bloqueado"

        d["empresa"] = {
            "id": empresa.id,
            "nome": empresa.nome,
            "plano": empresa.plano,
            "ativo": empresa.ativo,
            "trial_ate": empresa.trial_ate,
            "assinatura_valida_ate": empresa.assinatura_valida_ate,
            "ultima_atividade_em": empresa.ultima_atividade_em,
            "status": empresa_status,
            "usuarios": [
                {
                    "id": u.id,
                    "nome": u.nome,
                    "email": u.email,
                    "ultima_atividade_em": u.ultima_atividade_em,
                    "ativo": u.ativo,
                    "online": _is_usuario_online(u),
                }
                for u in usuarios
            ],
            "total_orcamentos": total_orcamentos,
            "orcamentos_aprovados": orcamentos_aprovados,
            "orcamentos_pendentes": orcamentos_pendentes,
        }
    else:
        d["empresa"] = None

    return d


@router.patch("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    data: CommercialLeadUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza dados de um lead."""
    lead = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
        )
        .filter(CommercialLead.id == lead_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    update_data = data.model_dump(exclude_unset=True)

    if "whatsapp" in update_data or "email" in update_data:
        novo_whatsapp = update_data.get("whatsapp", lead.whatsapp)
        novo_email = update_data.get("email", lead.email)
        if not novo_whatsapp and not novo_email:
            raise HTTPException(
                status_code=400,
                detail="Lead deve ter pelo menos um contato (WhatsApp ou e-mail).",
            )

    campos_alterados = [k for k in update_data.keys() if k != "observacoes"]
    if campos_alterados:
        interacao = CommercialInteraction(
            lead_id=lead.id,
            tipo=TipoInteracao.OBSERVACAO,
            canal=CanalInteracao.OUTRO,
            conteudo=f"Lead editado: {', '.join(campos_alterados)}",
        )
        db.add(interacao)

    for field, value in update_data.items():
        setattr(lead, field, value)

    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lead)
    return _lead_to_out(lead)


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_permissao("comercial", "exclusao")),
):
    """Remove um lead e suas interações."""
    lead = (
        db.query(CommercialLead)
        .filter(
            CommercialLead.id == lead_id,
            (CommercialLead.empresa_id == usuario.empresa_id)
            | (CommercialLead.empresa_id.is_(None)),
        )
        .first()
    )
    if not lead:
        return None

    db.query(CampaignLead).filter(CampaignLead.lead_id == lead_id).delete(
        synchronize_session=False
    )
    db.query(LeadImportacaoItem).filter(LeadImportacaoItem.lead_id == lead_id).delete(
        synchronize_session=False
    )
    db.query(CommercialInteraction).filter(
        CommercialInteraction.lead_id == lead_id
    ).delete(synchronize_session=False)
    db.query(CommercialReminder).filter(CommercialReminder.lead_id == lead_id).delete(
        synchronize_session=False
    )

    db.delete(lead)
    db.commit()
    return None


@router.patch("/leads/{lead_id}/arquivar")
def arquivar_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_permissao("comercial", "escrita")),
):
    """Arquiva/desarquiva um lead (soft delete)."""
    lead = (
        db.query(CommercialLead)
        .filter(
            CommercialLead.id == lead_id,
            CommercialLead.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead.ativo = not lead.ativo
    lead.atualizado_em = datetime.now(timezone.utc)

    interacao = CommercialInteraction(
        lead_id=lead.id,
        tipo=TipoInteracao.OBSERVACAO,
        canal=CanalInteracao.OUTRO,
        conteudo=f"Lead {'reativado' if lead.ativo else 'arquivado'}",
    )
    db.add(interacao)
    db.commit()
    return {"ativo": lead.ativo}


@router.post("/leads/{lead_id}/recalcular-score")
def recalcular_score(
    lead_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Recalcula o lead score."""
    lead = db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead.lead_score = _calcular_score(lead)
    db.commit()
    return {"lead_score": lead.lead_score.value}


# ═══════════════════════════════════════════════════════════════════════════════
# CRIAÇÃO DE EMPRESA A PARTIR DO LEAD
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/leads/{lead_id}/criar-empresa")
async def criar_empresa_from_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Cria uma empresa e usuário a partir de um lead manual/importado."""
    from datetime import timedelta
    from app.services.admin_config import get_admin_config

    lead = db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    if lead.empresa_id:
        raise HTTPException(
            status_code=400, detail="Este lead já possui uma empresa vinculada"
        )

    if not lead.email:
        raise HTTPException(
            status_code=400, detail="Lead precisa ter e-mail para criar acesso"
        )

    senha = "".join(random.choices(string.ascii_uppercase, k=4)) + "".join(
        random.choices(string.digits, k=4)
    )

    cfg_admin = get_admin_config(db)
    dias_trial = cfg_admin.get("dias_trial_padrao", 14)

    try:
        agora = datetime.now(timezone.utc)

        empresa = Empresa(
            nome=lead.nome_empresa or lead.nome_responsavel,
            telefone=lead.whatsapp,
            plano="trial",
            trial_ate=agora + timedelta(days=dias_trial),
            ativo=True,
        )
        db.add(empresa)
        db.flush()

        usuario = Usuario(
            empresa_id=empresa.id,
            nome=lead.nome_responsavel,
            email=lead.email,
            senha_hash=hash_senha(senha),
            ativo=True,
            is_gestor=True,
        )
        db.add(usuario)

        lead.empresa_id = empresa.id
        lead.conta_criada_em = agora

        interacao = CommercialInteraction(
            lead_id=lead.id,
            tipo=TipoInteracao.OBSERVACAO,
            canal=CanalInteracao.OUTRO,
            conteudo=f"Empresa criada automaticamente. Usuário: {lead.email}",
        )
        db.add(interacao)

        db.commit()
        db.refresh(empresa)
        db.refresh(lead)

        whatsapp_enviado = False
        if lead.whatsapp:
            try:
                primeiro = (
                    lead.nome_responsavel.strip().split()[0]
                    if lead.nome_responsavel
                    else "Cliente"
                )
                link = f"{settings.APP_URL}/app/index.html"
                msg = (
                    f"🎉 *Bem-vindo ao COTTE, {primeiro}!*\n\n"
                    f"Sua conta foi criada com sucesso.\n\n"
                    f"📧 *E-mail:* {lead.email}\n"
                    f"🔑 *Senha:* `{senha}`\n\n"
                    f"🔗 *Acesse agora:*\n{link}\n\n"
                    f"⏰ Seu trial gratuito é válido por *{dias_trial} dias*.\n\n"
                    f"Qualquer dúvida é só chamar! — Equipe COTTE"
                )
                await enviar_mensagem_texto(lead.whatsapp, msg)
                whatsapp_enviado = True
            except Exception as e:
                logging.warning(f"Falha ao enviar WhatsApp para lead {lead_id}: {e}")

        try:
            enviar_email_boas_vindas(lead.email, lead.nome_responsavel, senha)
        except Exception as e:
            logging.warning(f"Falha ao enviar e-mail para lead {lead_id}: {e}")

        return {
            "sucesso": True,
            "empresa_id": empresa.id,
            "usuario_id": usuario.id,
            "whatsapp_enviado": whatsapp_enviado,
            "mensagem": f"Empresa criada com sucesso! Credenciais enviadas para {lead.email}",
        }

    except Exception as e:
        db.rollback()
        logging.exception(f"Erro ao criar empresa a partir do lead {lead_id}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar empresa: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# REENVIO DE SENHA
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/leads/{lead_id}/reenviar-senha", response_model=ReenviarSenhaResponse)
async def reenviar_senha(
    lead_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Gera nova senha e envia para o lead por WhatsApp/e-mail."""
    lead = db.query(CommercialLead).filter(CommercialLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    if not lead.empresa_id:
        raise HTTPException(
            status_code=400, detail="Este lead não possui empresa vinculada"
        )

    usuario = (
        db.query(Usuario)
        .filter(Usuario.empresa_id == lead.empresa_id, Usuario.email == lead.email)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=404, detail="Usuário não encontrado para esta empresa"
        )

    nova_senha = "".join(random.choices(string.ascii_uppercase, k=4)) + "".join(
        random.choices(string.digits, k=4)
    )

    usuario.senha_hash = hash_senha(nova_senha)
    db.flush()

    interacao = CommercialInteraction(
        lead_id=lead.id,
        tipo=TipoInteracao.OBSERVACAO,
        canal=CanalInteracao.OUTRO,
        conteudo="Nova senha gerada e enviada ao cliente",
    )
    db.add(interacao)
    db.commit()

    whatsapp_enviado = False
    if lead.whatsapp:
        try:
            primeiro = (
                lead.nome_responsavel.strip().split()[0]
                if lead.nome_responsavel
                else "Cliente"
            )
            link = f"{settings.APP_URL}/app/index.html"
            msg = (
                f"🔐 *Nova senha do COTTE*\n\n"
                f"Olá, {primeiro}!\n\n"
                f"Sua nova senha de acesso é:\n\n"
                f"🔑 *Senha:* `{nova_senha}`\n\n"
                f"🔗 *Acesse agora:*\n{link}\n\n"
                f"Qualquer dúvida é só chamar! — Equipe COTTE"
            )
            await enviar_mensagem_texto(lead.whatsapp, msg)
            whatsapp_enviado = True
        except Exception as e:
            logging.warning(f"Falha ao enviar WhatsApp para lead {lead_id}: {e}")

    try:
        if lead.email:
            enviar_email_boas_vindas(lead.email, lead.nome_responsavel, nova_senha)
    except Exception as e:
        logging.warning(f"Falha ao enviar e-mail para lead {lead_id}: {e}")

    return ReenviarSenhaResponse(
        sucesso=True,
        mensagem=f"Nova senha gerada e enviada para {lead.email}"
        + (" por WhatsApp" if whatsapp_enviado else ""),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS LEGADOS DE IMPORTAÇÃO (mantidos para compatibilidade com frontend)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/leads/importacao/{importacao_id}")
def get_leads_por_importacao(
    importacao_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Retorna leads de uma importação específica."""
    importacao = (
        db.query(LeadImportacao).filter(LeadImportacao.id == importacao_id).first()
    )
    if not importacao:
        raise HTTPException(status_code=404, detail="Importação não encontrada")

    lead_ids = (
        db.query(LeadImportacaoItem.lead_id)
        .filter(LeadImportacaoItem.importacao_id == importacao_id)
        .subquery()
    )
    leads = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
        )
        .filter(CommercialLead.id.in_(lead_ids))
        .all()
    )
    return {
        "importacao_id": importacao_id,
        "importacao_nome": importacao.nome,
        "total_importados": importacao.total_importados,
        "total_validos": importacao.total_validos,
        "leads": [_lead_to_out(l) for l in leads],
    }


@router.get("/leads/importacoes")
async def listar_importacoes(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_superadmin),
):
    """Lista as importações recentes da empresa."""
    importacoes = (
        db.query(LeadImportacao)
        .filter(LeadImportacao.empresa_id == usuario.empresa_id)
        .order_by(LeadImportacao.criado_em.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": imp.id,
            "nome": imp.nome,
            "metodo": imp.metodo,
            "total_importados": imp.total_importados,
            "total_validos": imp.total_validos,
            "total_invalidos": imp.total_invalidos,
            "criado_em": imp.criado_em.isoformat() if imp.criado_em else None,
        }
        for imp in importacoes
    ]


@router.post("/leads/enviar-lote")
async def enviar_lote(
    payload: dict = Body(...), db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Envia WhatsApp ou E-mail em lote para leads selecionados com template obrigatório."""
    lead_ids = payload.get("lead_ids", [])
    template_id = payload.get("campaign_id")
    canal = payload.get("canal", "whatsapp")
    delay_min = payload.get("delay_min", 9)
    delay_max = payload.get("delay_max", 15)

    if not lead_ids:
        raise HTTPException(status_code=400, detail="Selecione pelo menos um lead")
    if not template_id:
        raise HTTPException(status_code=400, detail="Selecione um template")
    if delay_min < 1 or delay_max < delay_min:
        raise HTTPException(
            status_code=400,
            detail="Delay mínimo deve ser >= 1 segundo e máximo deve ser >= mínimo",
        )

    template = (
        db.query(CommercialTemplate)
        .filter(
            CommercialTemplate.id == template_id,
            CommercialTemplate.ativo == True,
        )
        .first()
    )
    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template não encontrado ou inativo",
        )

    mensagem_campaign = template.conteudo if template.conteudo else template.nome
    if canal == "whatsapp" and not mensagem_campaign.strip():
        raise HTTPException(
            status_code=400,
            detail="Template não possui conteúdo de mensagem. Edite o template antes de enviar.",
        )

    leads = (
        db.query(CommercialLead)
        .filter(CommercialLead.id.in_(lead_ids), CommercialLead.ativo == True)
        .all()
    )
    if not leads:
        raise HTTPException(status_code=404, detail="Nenhum lead válido encontrado")

    def _preparar_mensagem(lead: CommercialLead, mensagem: str) -> str:
        substituicoes = {
            "{{nome}}": lead.nome_responsavel or "",
            "{{empresa}}": lead.nome_empresa or "",
            "{{cidade}}": lead.cidade or "",
        }
        resultado = mensagem
        for var, valor in substituicoes.items():
            resultado = resultado.replace(var, valor)
        return resultado

    resultados = []
    enviados = 0
    falhas = 0
    total_leads = len(leads)

    for idx, lead in enumerate(leads):
        try:
            if canal == "whatsapp":
                if not lead.whatsapp:
                    resultados.append(
                        {
                            "lead_id": lead.id,
                            "nome": lead.nome_responsavel or lead.nome_empresa,
                            "status": "ignorado",
                            "motivo": "Sem WhatsApp cadastrado",
                        }
                    )
                    continue
                mensagem_personalizada = _preparar_mensagem(lead, mensagem_campaign)
                sucesso = await enviar_mensagem_texto(
                    lead.whatsapp, mensagem_personalizada
                )
                if sucesso:
                    enviados += 1
                    resultados.append(
                        {
                            "lead_id": lead.id,
                            "nome": lead.nome_responsavel or lead.nome_empresa,
                            "status": "enviado",
                        }
                    )
                    interacao = CommercialInteraction(
                        lead_id=lead.id,
                        tipo=TipoInteracao.WHATSAPP,
                        canal=CanalInteracao.WHATSAPP,
                        conteudo=f"Envio em lote - Campanha: {template.nome}",
                        status_envio="enviado",
                        enviado_em=datetime.now(timezone.utc),
                    )
                    db.add(interacao)
                else:
                    falhas += 1
                    resultados.append(
                        {
                            "lead_id": lead.id,
                            "nome": lead.nome_responsavel or lead.nome_empresa,
                            "status": "falha",
                            "motivo": "Erro ao enviar mensagem",
                        }
                    )
            elif canal == "email":
                if not lead.email:
                    resultados.append(
                        {
                            "lead_id": lead.id,
                            "nome": lead.nome_responsavel or lead.nome_empresa,
                            "status": "ignorado",
                            "motivo": "Sem e-mail cadastrado",
                        }
                    )
                    continue
                assunto_personalizado = _preparar_mensagem(
                    lead, template.assunto or template.nome
                )
                corpo_personalizado = _preparar_mensagem(lead, mensagem_campaign)
                sucesso = send_email_simples(
                    lead.email, assunto_personalizado, corpo_personalizado
                )
                if sucesso:
                    enviados += 1
                    resultados.append(
                        {
                            "lead_id": lead.id,
                            "nome": lead.nome_responsavel or lead.nome_empresa,
                            "status": "enviado",
                        }
                    )
                    interacao = CommercialInteraction(
                        lead_id=lead.id,
                        tipo=TipoInteracao.EMAIL,
                        canal=CanalInteracao.EMAIL,
                        conteudo=f"Envio em lote - Campanha: {template.nome}",
                        status_envio="enviado",
                        enviado_em=datetime.now(timezone.utc),
                    )
                    db.add(interacao)
                else:
                    falhas += 1
                    resultados.append(
                        {
                            "lead_id": lead.id,
                            "nome": lead.nome_responsavel or lead.nome_empresa,
                            "status": "falha",
                            "motivo": "Erro ao enviar e-mail",
                        }
                    )
        except Exception as e:
            falhas += 1
            resultados.append(
                {
                    "lead_id": lead.id,
                    "nome": lead.nome_responsavel or lead.nome_empresa,
                    "status": "erro",
                    "motivo": str(e),
                }
            )
        if idx < total_leads - 1:
            delay_segundos = random.uniform(delay_min, delay_max)
            await asyncio.sleep(delay_segundos)

    db.commit()
    return {
        "total": total_leads,
        "enviados": enviados,
        "falhas": falhas,
        "delay_configurado": {"min": delay_min, "max": delay_max},
        "resultados": resultados,
    }


def _parse_fallback(texto: str) -> list:
    """Parser básico de fallback para extrair contatos de texto simples."""
    items = []
    lines = texto.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
        email = email_match.group(0) if email_match else ""
        phone_match = re.search(r"\(?\d{2}\)?[\s\-]?\d{4,5}[\s\-]?\d{4}", line)
        whatsapp = phone_match.group(0) if phone_match else ""
        if whatsapp:
            whatsapp = re.sub(r"\D", "", whatsapp)
            if len(whatsapp) < 10:
                whatsapp = ""
        nome = ""
        if email:
            nome_part = line.split(email)[0].strip()
        elif whatsapp:
            nome_part = line.split(phone_match.group(0))[0].strip()
        else:
            nome_part = line
        nome_words = nome_part.split()[:3]
        nome = " ".join(nome_words) if nome_words else ""
        empresa = ""
        empresa_patterns = [r"da\s+([^,]+)", r"de\s+([^,]+)", r"empresa\s+([^,]+)"]
        for pattern in empresa_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                empresa = match.group(1).strip()
                break
        if email or whatsapp:
            items.append(
                {
                    "nome_responsavel": nome,
                    "nome_empresa": empresa,
                    "whatsapp": whatsapp,
                    "email": email,
                    "cidade": "",
                    "segmento_nome": "",
                    "origem_nome": "",
                }
            )
    return items


@router.post("/leads/analisar-importacao")
async def analisar_importacao(
    data: dict = Body(...), db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Analisa texto colado e extrai leads usando IA."""
    texto = data.get("texto", "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto vazio")

    segmentos = {
        s.nome.lower(): s.id
        for s in db.query(CommercialSegment)
        .filter(CommercialSegment.ativo == True)
        .all()
    }
    origens = {
        o.nome.lower(): o.id
        for o in db.query(CommercialLeadSource)
        .filter(CommercialLeadSource.ativo == True)
        .all()
    }

    try:
        resposta = await analisar_leads(texto)
        if not resposta or not resposta.get("items"):
            items_fallback = _parse_fallback(texto)
            if not items_fallback:
                raise HTTPException(
                    status_code=400, detail="Nenhum lead identificado no texto"
                )
            resposta = {"items": items_fallback}

        items = []
        for item in resposta["items"]:
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
            _dup_filters = []
            if whatsapp:
                _dup_filters.append(CommercialLead.whatsapp == whatsapp)
            if email:
                _dup_filters.append(CommercialLead.email == email)
            duplicado = (
                db.query(CommercialLead).filter(or_(*_dup_filters)).first()
                if _dup_filters
                else None
            )
            if duplicado:
                item["duplicado"] = True
                item["selecionado"] = False
            else:
                item["duplicado"] = False
                item["selecionado"] = True
            segmento_nome = (item.get("segmento_nome") or "").strip().lower()
            origem_nome = (item.get("origem_nome") or "").strip().lower()
            item["segmento_id"] = segmentos.get(segmento_nome)
            item["origem_lead_id"] = origens.get(origem_nome)
            items.append(item)
        return {"items": items}
    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.error(f"Erro em analisar_importacao: {str(e)}", exc_info=True)
        items_fallback = _parse_fallback(texto)
        if items_fallback:
            return {
                "items": items_fallback,
                "warning": "Usando parser básico devido a erro na IA",
            }
        raise HTTPException(status_code=500, detail=f"Erro ao analisar texto: {str(e)}")


@router.post("/leads/importar")
async def importar_leads(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_superadmin),
):
    """Importa múltiplos leads de uma vez."""
    leads_data = payload.get("leads", [])
    send_welcome = payload.get("send_welcome", False)

    if not leads_data:
        raise HTTPException(status_code=400, detail="Nenhum lead para importar")

    importacao = LeadImportacao(
        empresa_id=current_user.empresa_id,
        criado_por_id=current_user.id,
        nome=f"Importação {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        metodo=payload.get("metodo", "colar"),
        total_importados=len(leads_data),
        total_validos=0,
        total_invalidos=0,
    )
    db.add(importacao)
    db.flush()

    sucesso = 0
    erros = 0
    leads_criados = []
    erros_detalhes = []

    for idx, lead_data in enumerate(leads_data):
        try:
            if not lead_data.get("nome_responsavel") and not lead_data.get(
                "nome_empresa"
            ):
                raise ValueError("Informe pelo menos nome do responsável ou empresa")

            whatsapp = lead_data.get("whatsapp")
            email = lead_data.get("email")
            if not whatsapp and not email:
                raise ValueError("Informe pelo menos WhatsApp ou e-mail")

            if whatsapp:
                whatsapp = re.sub(r"\D", "", str(whatsapp))
                if len(whatsapp) < 10:
                    raise ValueError("WhatsApp inválido (mínimo 10 dígitos)")
                lead_data["whatsapp"] = whatsapp

            _dup_filters = []
            if whatsapp:
                _dup_filters.append(CommercialLead.whatsapp == whatsapp)
            if email:
                _dup_filters.append(CommercialLead.email == email)
            duplicado = (
                db.query(CommercialLead).filter(or_(*_dup_filters)).first()
                if _dup_filters
                else None
            )

            lead_status = "valido"
            if duplicado:
                lead_status = "duplicata"
                raise ValueError(f"Lead duplicado (ID: {duplicado.id})")

            lead = CommercialLead(
                nome_responsavel=lead_data.get("nome_responsavel", ""),
                nome_empresa=lead_data.get("nome_empresa", ""),
                whatsapp=whatsapp,
                email=email,
                cidade=lead_data.get("cidade"),
                segmento_id=lead_data.get("segmento_id"),
                origem_lead_id=lead_data.get("origem_lead_id"),
                observacoes=lead_data.get("observacoes"),
                status_pipeline=StatusPipeline.NOVO,
                lead_score=LeadScore.FRIO,
                status_envio="nao_enviado",
            )
            db.add(lead)
            db.flush()

            interacao = CommercialInteraction(
                lead_id=lead.id,
                tipo=TipoInteracao.OBSERVACAO,
                canal=CanalInteracao.OUTRO,
                conteudo="Lead importado em lote",
            )
            db.add(interacao)

            item = LeadImportacaoItem(
                importacao_id=importacao.id,
                nome_responsavel=lead_data.get("nome_responsavel", ""),
                nome_empresa=lead_data.get("nome_empresa", ""),
                whatsapp=whatsapp,
                email=email,
                cidade=lead_data.get("cidade"),
                observacoes=lead_data.get("observacoes"),
                status=lead_status,
                erro=None,
                lead_id=lead.id,
            )
            db.add(item)

            sucesso += 1
            leads_criados.append(
                {
                    "id": lead.id,
                    "nome_responsavel": lead.nome_responsavel,
                    "nome_empresa": lead.nome_empresa,
                    "whatsapp": lead.whatsapp,
                    "email": lead.email,
                }
            )
        except Exception as e:
            erros += 1
            erros_detalhes.append(
                {
                    "lead": lead_data.get("nome_responsavel")
                    or lead_data.get("nome_empresa", f"Lead #{idx + 1}"),
                    "erro": str(e),
                }
            )
            item = LeadImportacaoItem(
                importacao_id=importacao.id,
                nome_responsavel=lead_data.get("nome_responsavel", ""),
                nome_empresa=lead_data.get("nome_empresa", ""),
                whatsapp=lead_data.get("whatsapp"),
                email=lead_data.get("email"),
                cidade=lead_data.get("cidade"),
                observacoes=lead_data.get("observacoes"),
                status="invalido",
                erro=str(e),
                lead_id=None,
            )
            db.add(item)

    db.commit()
    importacao.total_validos = sucesso
    importacao.total_invalidos = erros
    db.commit()

    return {
        "sucesso": sucesso,
        "erros": erros,
        "leads_criados": leads_criados,
        "erros_detalhes": erros_detalhes,
        "importacao_id": importacao.id,
    }
