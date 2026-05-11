"""Leads comerciais tenant — CRUD, listagem filtrada, dashboard aux, interações (sem criar usuário/senha)."""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    CanalInteracao,
    Empresa,
    LeadScore,
    TenantCommercialTemplate,
    TenantCommercialInteraction,
    TenantCommercialLead,
    TenantCommercialLeadSource,
    TenantCommercialSegment,
    TenantLeadImportacao,
    TenantLeadImportacaoItem,
    TenantPipelineEtapa,
    TipoInteracao,
    Usuario,
)
from app.services.email_service import send_email_simples
from app.services.ia_service import analisar_leads
from app.services.template_anexos_service import obter_bytes_anexo, validar_template_anexo_path
from app.services.whatsapp_service import enviar_imagem, enviar_mensagem_texto, enviar_pdf
from app.routers.tenant.tenant_comercial_serialization import (
    sync_lead_status_from_etapa,
    tenant_lead_to_out,
)


class LeadBase(BaseModel):
    nome: Optional[str] = None
    nome_responsavel: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    whatsapp: Optional[str] = None
    cidade: Optional[str] = None
    endereco: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    uf: Optional[str] = None
    segmento: Optional[str] = None
    segmento_id: Optional[int] = None
    origem: Optional[str] = None
    origem_lead_id: Optional[int] = None
    etapa_pipeline_id: Optional[int] = None
    valor_estimado: Optional[Decimal] = None
    valor_proposto: Optional[Decimal] = None
    interesse_plano: Optional[str] = None
    observacoes: Optional[str] = None
    responsavel_id: Optional[int] = None
    empresa_id: Optional[int] = None
    nome_empresa: Optional[str] = None
    status_pipeline: Optional[str] = None
    lead_score: Optional[LeadScore] = None
    proximo_contato_em: Optional[datetime] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    uf: Optional[str] = None
    segmento: Optional[str] = None
    origem: Optional[str] = None
    etapa_pipeline_id: Optional[int] = None
    valor_estimado: Optional[Decimal] = None
    observacoes: Optional[str] = None
    responsavel_id: Optional[int] = None
    nome_empresa: Optional[str] = None
    status_pipeline: Optional[str] = None
    lead_score: Optional[LeadScore] = None
    proximo_contato_em: Optional[datetime] = None
    ultimo_contato_em: Optional[datetime] = None
    ativo: Optional[bool] = None


class LeadResponse(LeadBase):
    id: int
    empresa_id: int
    ativo: bool
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int


class MoveEtapaRequest(BaseModel):
    etapa_id: int


class ObservacaoBody(BaseModel):
    conteudo: str


class MensagemBody(BaseModel):
    mensagem: str
    template_id: Optional[int] = None


class EmailBody(BaseModel):
    assunto: str
    mensagem: str
    template_id: Optional[int] = None


router = APIRouter(
    prefix="/leads",
    tags=["Tenant Comercial Leads"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


def _buscar_lead(db: Session, empresa_id: int, lead_id: int, incluir_inativos: bool = False) -> TenantCommercialLead:
    q = db.query(TenantCommercialLead).filter(
        TenantCommercialLead.id == lead_id,
        TenantCommercialLead.empresa_id == empresa_id,
    )
    if not incluir_inativos:
        q = q.filter(TenantCommercialLead.ativo.is_(True))
    lead = q.first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


def _etapa_padrao(db: Session, empresa_id: int) -> Optional[int]:
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.empresa_id == empresa_id,
            TenantPipelineEtapa.ativo.is_(True),
        )
        .order_by(TenantPipelineEtapa.ordem.asc(), TenantPipelineEtapa.id.asc())
        .first()
    )
    return etapa.id if etapa else None


def _buscar_template_ativo(
    db: Session,
    empresa_id: int,
    template_id: Optional[int],
) -> Optional[TenantCommercialTemplate]:
    if template_id is None:
        return None

    template = (
        db.query(TenantCommercialTemplate)
        .filter(
            TenantCommercialTemplate.id == template_id,
            TenantCommercialTemplate.empresa_id == empresa_id,
            TenantCommercialTemplate.ativo.is_(True),
        )
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return template


@router.get("/check-duplicata")
def check_duplicata_lead(
    whatsapp: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Verifica se existe lead com o WhatsApp ou e-mail informado. Retorna o lead ou null."""
    if not whatsapp and not email:
        return None

    from sqlalchemy import func as sa_func

    filters = []
    if whatsapp:
        wa_norm = re.sub(r"\D", "", whatsapp)
        filters.append(sa_func.regexp_replace(TenantCommercialLead.telefone, r"\D", "", "g") == wa_norm)
    if email:
        filters.append(sa_func.lower(TenantCommercialLead.email) == email.lower().strip())

    lead = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo == True,
            or_(*filters),
        )
        .first()
    )

    return tenant_lead_to_out(db, lead) if lead else None


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead_data = payload.model_dump(exclude_unset=True)
    # empresa_id vem do contexto autenticado do tenant e não deve vir do payload.
    lead_data.pop("empresa_id", None)
    if not lead_data.get("nome") and lead_data.get("nome_responsavel"):
        lead_data["nome"] = lead_data.get("nome_responsavel")
    if not lead_data.get("telefone") and lead_data.get("whatsapp"):
        lead_data["telefone"] = lead_data.get("whatsapp")
    if lead_data.get("telefone"):
        lead_data["telefone"] = _normalizar_telefone_br(lead_data.get("telefone") or "") or None
    if lead_data.get("valor_estimado") is None and lead_data.get("valor_proposto") is not None:
        lead_data["valor_estimado"] = lead_data.get("valor_proposto")
    if not lead_data.get("segmento") and lead_data.get("segmento_id"):
        seg = (
            db.query(TenantCommercialSegment)
            .filter(
                TenantCommercialSegment.id == lead_data["segmento_id"],
                TenantCommercialSegment.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if seg:
            lead_data["segmento"] = seg.nome
    if not lead_data.get("origem") and lead_data.get("origem_lead_id"):
        origem = (
            db.query(TenantCommercialLeadSource)
            .filter(
                TenantCommercialLeadSource.id == lead_data["origem_lead_id"],
                TenantCommercialLeadSource.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if origem:
            lead_data["origem"] = origem.nome
    if not lead_data.get("nome"):
        raise HTTPException(status_code=422, detail="Campo 'nome' (ou 'nome_responsavel') é obrigatório.")

    if lead_data.get("etapa_pipeline_id") is None:
        lead_data["etapa_pipeline_id"] = _etapa_padrao(db, usuario.empresa_id)

    campos_modelo_lead = {
        "nome",
        "nome_empresa",
        "email",
        "telefone",
        "endereco",
        "segmento",
        "origem",
        "etapa_pipeline_id",
        "valor_estimado",
        "observacoes",
        "status_pipeline",
        "lead_score",
        "proximo_contato_em",
        "ultimo_contato_em",
        "responsavel_id",
        "ativo",
    }
    lead_data_modelo = {k: v for k, v in lead_data.items() if k in campos_modelo_lead}

    agora = datetime.now(timezone.utc)
    lead = TenantCommercialLead(
        **lead_data_modelo,
        empresa_id=usuario.empresa_id,
        ativo=True,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(lead)
    db.flush()
    sync_lead_status_from_etapa(db, lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=dict[str, Any])
def list_leads(
    status: Optional[str] = None,
    search: Optional[str] = None,
    origem_lead_id: Optional[int] = None,
    lead_score: Optional[LeadScore] = None,
    ativo: Optional[bool] = True,
    follow_up_hoje: Optional[bool] = None,
    status_pipeline_notin: Optional[str] = None,
    order_by: str = "criado_em",
    order_dir: str = "desc",
    page: int = 1,
    per_page: int = 50,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Lista leads (formato paginado tipo superadmin ou skip/limit legado)."""
    eid = usuario.empresa_id
    query = db.query(TenantCommercialLead).filter(TenantCommercialLead.empresa_id == eid)

    if ativo is not None:
        query = query.filter(TenantCommercialLead.ativo == ativo)
    if status:
        query = query.filter(TenantCommercialLead.status_pipeline == status)
    if lead_score:
        query = query.filter(TenantCommercialLead.lead_score == lead_score)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                TenantCommercialLead.nome.ilike(term),
                TenantCommercialLead.nome_empresa.ilike(term),
                TenantCommercialLead.email.ilike(term),
                TenantCommercialLead.telefone.ilike(term),
                TenantCommercialLead.segmento.ilike(term),
                TenantCommercialLead.origem.ilike(term),
            )
        )
    if origem_lead_id:
        query = query.filter(False)

    agora = datetime.now(timezone.utc)
    if follow_up_hoje:
        query = query.filter(TenantCommercialLead.proximo_contato_em.isnot(None))
        query = query.filter(TenantCommercialLead.proximo_contato_em <= agora)
        query = query.filter(
            TenantCommercialLead.status_pipeline.notin_(["fechado_ganho", "fechado_perdido"])
        )

    if status_pipeline_notin:
        excluir = [s.strip() for s in status_pipeline_notin.split(",") if s.strip()]
        if excluir:
            query = query.filter(TenantCommercialLead.status_pipeline.notin_(excluir))

    col = getattr(TenantCommercialLead, order_by, TenantCommercialLead.criado_em)
    if order_dir == "asc":
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())

    total = query.count()

    if skip is not None and limit is not None:
        leads = query.offset(skip).limit(limit).all()
        return {
            "items": [tenant_lead_to_out(db, l) for l in leads],
            "total": total,
        }

    offset = (page - 1) * per_page
    leads = query.offset(offset).limit(per_page).all()
    pages = (total + per_page - 1) // per_page if per_page else 1
    return {
        "items": [tenant_lead_to_out(db, l) for l in leads],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get("/follow-ups-hoje", response_model=list[dict[str, Any]])
def follow_ups_hoje(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    agora = datetime.now(timezone.utc)
    leads = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo.is_(True),
            TenantCommercialLead.proximo_contato_em.isnot(None),
            TenantCommercialLead.proximo_contato_em <= agora,
            TenantCommercialLead.status_pipeline.notin_(["fechado_ganho", "fechado_perdido"]),
        )
        .order_by(TenantCommercialLead.proximo_contato_em.asc())
        .limit(50)
        .all()
    )
    return [tenant_lead_to_out(db, l) for l in leads]


@router.get("/recentes", response_model=list[dict[str, Any]])
def leads_recentes(
    limit: int = 5,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    leads = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .order_by(TenantCommercialLead.criado_em.desc())
        .limit(limit)
        .all()
    )
    return [tenant_lead_to_out(db, l) for l in leads]


@router.get("/briefing")
async def get_briefing(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Gera o briefing diário de leads prioritários com sugestões de ação e rascunhos de mensagem."""
    from app.services.ia_service import gerar_briefing_lead, _briefing_fallback

    agora = datetime.now(timezone.utc)

    leads = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo.is_(True),
            TenantCommercialLead.status_pipeline.notin_(["fechado_ganho", "fechado_perdido"]),
        )
        .order_by(TenantCommercialLead.criado_em.desc())
        .limit(30)
        .all()
    )

    contextos = []
    for lead in leads:
        interacoes = (
            db.query(TenantCommercialInteraction)
            .filter(TenantCommercialInteraction.lead_id == lead.id)
            .order_by(TenantCommercialInteraction.criado_em.desc())
            .limit(3)
            .all()
        )
        historico = []
        for inter in interacoes:
            ref_dt = inter.criado_em
            if ref_dt and ref_dt.tzinfo is None:
                ref_dt = ref_dt.replace(tzinfo=timezone.utc)
            dias_atras = (agora - ref_dt).days if ref_dt else 0
            historico.append({
                "tipo": inter.tipo.value if inter.tipo else "outro",
                "dias_atras": dias_atras,
                "resumo": (inter.conteudo or "")[:80],
            })

        ref_contato = lead.ultimo_contato_em or lead.criado_em
        if ref_contato and ref_contato.tzinfo is None:
            ref_contato = ref_contato.replace(tzinfo=timezone.utc)
        dias_sem_contato = (agora - ref_contato).days if ref_contato else 0

        contextos.append({
            "lead_id": lead.id,
            "nome": lead.nome or "",
            "empresa": lead.nome_empresa or "",
            "etapa": lead.status_pipeline or "novo",
            "score": lead.lead_score.value if lead.lead_score else "frio",
            "valor_proposto": float(lead.valor_estimado) if lead.valor_estimado else 0.0,
            "dias_sem_contato": dias_sem_contato,
            "proximo_contato_em": lead.proximo_contato_em.isoformat() if lead.proximo_contato_em else None,
            "historico": historico,
        })

    resultados = await asyncio.gather(*[gerar_briefing_lead(ctx) for ctx in contextos], return_exceptions=True)

    PRIORIDADE_ORDEM = {"urgente": 0, "hoje": 1, "esta_semana": 2, "ok": 3}
    items = []
    for ctx, resultado in zip(contextos, resultados):
        if isinstance(resultado, Exception):
            resultado = _briefing_fallback(ctx)
        prioridade = resultado.get("prioridade", "ok")
        confianca = resultado.get("confianca", 1.0)
        if prioridade == "ok" or confianca < 0.5:
            continue
        items.append({**ctx, **resultado})

    items.sort(key=lambda x: PRIORIDADE_ORDEM.get(x.get("prioridade", "ok"), 3))

    return {
        "success": True,
        "data": {
            "items": items,
            "total_leads": len(leads),
            "total_acoes": len(items),
            "gerado_em": agora.isoformat(),
        },
    }


def _parse_fallback(texto: str) -> list:
    items = []
    for line in texto.split("\n"):
        line = line.strip()
        if not line:
            continue
        email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
        email = email_m.group(0) if email_m else ""
        phone_m = re.search(r"\(?\d{2}\)?[\s\-]?\d{4,5}[\s\-]?\d{4}", line)
        whatsapp = re.sub(r"\D", "", phone_m.group(0)) if phone_m else ""
        if whatsapp and len(whatsapp) < 10:
            whatsapp = ""
        if not email and not whatsapp:
            continue
        ref = line.split(email)[0] if email else (line.split(phone_m.group(0))[0] if phone_m else line)
        nome = " ".join(ref.strip().split()[:3])
        items.append({"nome_responsavel": nome, "nome_empresa": "", "whatsapp": whatsapp,
                      "email": email, "cidade": "", "segmento_nome": "", "origem_nome": ""})
    return items


def _normalizar_telefone_br(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor or "")
    if not digitos:
        return ""
    if digitos.startswith("55") and len(digitos) in {12, 13}:
        base = digitos[2:]
    else:
        base = digitos
    if len(base) not in {10, 11}:
        return ""
    return f"55{base}"


@router.post("/analisar-importacao")
async def analisar_importacao_tenant(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    texto = (data.get("texto") or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto vazio")

    segmentos = {
        s.nome.lower(): s.id
        for s in db.query(TenantCommercialSegment)
        .filter(TenantCommercialSegment.empresa_id == usuario.empresa_id, TenantCommercialSegment.ativo.is_(True))
        .all()
    }
    origens = {
        o.nome.lower(): o.id
        for o in db.query(TenantCommercialLeadSource)
        .filter(TenantCommercialLeadSource.empresa_id == usuario.empresa_id, TenantCommercialLeadSource.ativo.is_(True))
        .all()
    }

    try:
        resposta = await analisar_leads(texto)
        if not resposta or not resposta.get("items"):
            resposta = {"items": _parse_fallback(texto)}
    except Exception:
        resposta = {"items": _parse_fallback(texto)}

    if not resposta["items"]:
        raise HTTPException(status_code=400, detail="Nenhum lead identificado no texto")

    items = []
    for item in resposta["items"]:
        nr = (item.get("nome_responsavel") or item.get("nome") or "").strip()
        ne = (item.get("nome_empresa") or item.get("empresa") or "").strip()
        if not nr and ne:
            nr = ne
        if nr:
            item["nome_responsavel"] = nr
        if ne:
            item["nome_empresa"] = ne
        whatsapp = _normalizar_telefone_br(item.get("whatsapp") or "")
        email = (item.get("email") or "").strip()
        cidade = (item.get("cidade") or item.get("city") or item.get("localidade") or "").strip()
        endereco = (item.get("endereco") or item.get("logradouro") or item.get("rua") or "").strip()
        if not whatsapp and not email:
            continue
        item["whatsapp"] = whatsapp
        item["cidade"] = cidade
        item["endereco"] = endereco
        dup_filters = []
        if whatsapp:
            dup_filters.append(TenantCommercialLead.telefone == whatsapp)
        if email:
            dup_filters.append(TenantCommercialLead.email == email)
        duplicado = (
            db.query(TenantCommercialLead)
            .filter(TenantCommercialLead.empresa_id == usuario.empresa_id, or_(*dup_filters))
            .first()
        ) if dup_filters else None
        item["duplicado"] = bool(duplicado)
        item["selecionado"] = not bool(duplicado)
        item["segmento_id"] = segmentos.get((item.get("segmento_nome") or "").strip().lower())
        item["origem_lead_id"] = origens.get((item.get("origem_nome") or "").strip().lower())
        item["endereco"] = (
            item.get("endereco") or item.get("logradouro") or item.get("rua") or ""
        ).strip() or None
        items.append(item)

    return {"items": items}


@router.post("/importar")
async def importar_leads_tenant(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    leads_data = payload.get("leads", [])
    if not leads_data:
        raise HTTPException(status_code=400, detail="Nenhum lead para importar")

    importacao = TenantLeadImportacao(
        empresa_id=usuario.empresa_id,
        criado_por_id=usuario.id,
        nome=f"Importação {datetime.now().strftime('%d/%m/%Y %H:%M')} - {uuid.uuid4().hex[:6]}",
        metodo=payload.get("metodo", "ia"),
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

    for item in leads_data:
        try:
            nr = (item.get("nome_responsavel") or item.get("nome_empresa") or "").strip()
            if not nr:
                raise ValueError("Nome obrigatório")
            whatsapp = _normalizar_telefone_br(str(item.get("whatsapp") or ""))
            if item.get("whatsapp") and not whatsapp:
                raise ValueError("WhatsApp inválido")
            email = (item.get("email") or "").strip() or None
            endereco = (
                (item.get("endereco") or item.get("logradouro") or item.get("rua") or "")
                .strip()
                or None
            )
            observacoes = (item.get("observacoes") or "").strip() or None

            dup_filters = []
            if whatsapp:
                dup_filters.append(TenantCommercialLead.telefone == whatsapp)
            if email:
                dup_filters.append(TenantCommercialLead.email == email)
            if dup_filters:
                dup = db.query(TenantCommercialLead).filter(
                    TenantCommercialLead.empresa_id == usuario.empresa_id, or_(*dup_filters)
                ).first()
                if dup:
                    raise ValueError(f"Lead duplicado (ID: {dup.id})")

            lead = TenantCommercialLead(
                empresa_id=usuario.empresa_id,
                nome=nr,
                nome_empresa=item.get("nome_empresa") or nr,
                telefone=whatsapp or None,
                endereco=endereco,
                email=email,
                observacoes=observacoes,
                status_pipeline="novo",
                lead_score=LeadScore.FRIO,
                ativo=True,
            )
            db.add(lead)
            db.flush()
            db.add(TenantLeadImportacaoItem(
                importacao_id=importacao.id,
                nome_responsavel=nr,
                nome_empresa=item.get("nome_empresa") or nr,
                whatsapp=whatsapp or None,
                email=email,
                cidade=item.get("cidade"),
                observacoes=observacoes,
                status="valido",
                lead_id=lead.id,
            ))
            leads_criados.append({"id": lead.id, "nome_responsavel": nr,
                                   "nome_empresa": lead.nome_empresa})
            sucesso += 1
        except Exception as e:
            erros += 1
            erros_detalhes.append({"lead": item.get("nome_responsavel") or item.get("nome_empresa") or "?",
                                    "erro": str(e)})
            db.add(TenantLeadImportacaoItem(
                importacao_id=importacao.id,
                nome_responsavel=item.get("nome_responsavel") or "",
                nome_empresa=item.get("nome_empresa") or "",
                whatsapp=item.get("whatsapp"),
                email=item.get("email"),
                status="erro",
                erro=str(e),
            ))

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


@router.get("/{lead_id}", response_model=dict[str, Any])
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    from sqlalchemy.orm import joinedload
    lead = (
        db.query(TenantCommercialLead)
        .options(joinedload(TenantCommercialLead.interacoes))
        .filter(
            TenantCommercialLead.id == lead_id,
            TenantCommercialLead.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    d = tenant_lead_to_out(db, lead)
    d["interacoes"] = [
        {c.name: getattr(i, c.name) for c in i.__table__.columns}
        for i in sorted(lead.interacoes, key=lambda x: x.criado_em or datetime.now(timezone.utc), reverse=True)
    ]
    return d


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    data = payload.model_dump(exclude_unset=True)
    if not data.get("nome") and data.get("nome_responsavel"):
        data["nome"] = data.get("nome_responsavel")
    if not data.get("telefone") and data.get("whatsapp"):
        data["telefone"] = data.get("whatsapp")
    if data.get("telefone"):
        data["telefone"] = _normalizar_telefone_br(data.get("telefone") or "") or None
    if not data.get("endereco") and data.get("logradouro"):
        data["endereco"] = data.get("logradouro")
    if data.get("valor_estimado") is None and data.get("valor_proposto") is not None:
        data["valor_estimado"] = data.get("valor_proposto")
    if not data.get("segmento") and data.get("segmento_id"):
        seg = (
            db.query(TenantCommercialSegment)
            .filter(
                TenantCommercialSegment.id == data["segmento_id"],
                TenantCommercialSegment.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if seg:
            data["segmento"] = seg.nome
    if not data.get("origem") and data.get("origem_lead_id"):
        origem = (
            db.query(TenantCommercialLeadSource)
            .filter(
                TenantCommercialLeadSource.id == data["origem_lead_id"],
                TenantCommercialLeadSource.empresa_id == usuario.empresa_id,
            )
            .first()
        )
        if origem:
            data["origem"] = origem.nome
    for field, value in data.items():
        setattr(lead, field, value)
    lead.atualizado_em = datetime.now(timezone.utc)
    sync_lead_status_from_etapa(db, lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    lead.ativo = False
    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Lead desativado com sucesso"}


@router.post("/{lead_id}/mover-etapa", response_model=LeadResponse)
def move_lead_stage(
    lead_id: int,
    payload: MoveEtapaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    etapa = (
        db.query(TenantPipelineEtapa)
        .filter(
            TenantPipelineEtapa.id == payload.etapa_id,
            TenantPipelineEtapa.empresa_id == usuario.empresa_id,
            TenantPipelineEtapa.ativo.is_(True),
        )
        .first()
    )
    if etapa is None:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")

    old = lead.status_pipeline
    lead.etapa_pipeline_id = etapa.id
    sync_lead_status_from_etapa(db, lead)
    lead.atualizado_em = datetime.now(timezone.utc)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.MUDANCA_STATUS,
            canal=CanalInteracao.SISTEMA,
            conteudo=f"Status alterado de '{old}' para '{lead.status_pipeline}'",
        )
    )
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/observacao")
def add_observacao(
    lead_id: int,
    body: ObservacaoBody,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.OBSERVACAO,
            canal=CanalInteracao.SISTEMA,
            conteudo=body.conteudo,
        )
    )
    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/{lead_id}/whatsapp")
async def enviar_whatsapp(
    lead_id: int,
    body: MensagemBody,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    if not lead.telefone:
        raise HTTPException(status_code=400, detail="Lead não possui WhatsApp cadastrado")

    template = _buscar_template_ativo(db, usuario.empresa_id, body.template_id)
    mensagem_final = body.mensagem
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()

    sucesso = False
    erro_msg = None

    _inst = getattr(empresa, "evolution_instance", None)
    _ativo = getattr(empresa, "whatsapp_proprio_ativo", False)
    _conectado = getattr(empresa, "whatsapp_conectado", False)
    logger.info(
        "[WA] empresa=%s instance=%s ativo=%s conectado=%s telefone=%s",
        usuario.empresa_id, _inst, _ativo, _conectado, lead.telefone
    )

    try:
        if template and template.anexo_arquivo_path:
            # Tenta enviar com anexo real
            try:
                anexo_bytes = await obter_bytes_anexo(template.anexo_arquivo_path)
                mime = template.anexo_mime_type or ""
                
                if mime.startswith("image/"):
                    sucesso = await enviar_imagem(
                        lead.telefone, 
                        anexo_bytes, 
                        caption=mensagem_final, 
                        mime_type=mime,
                        empresa=empresa
                    )
                elif mime == "application/pdf":
                    # Para PDF, o caption costuma ir separado ou em campo específico dependendo do provider
                    # No EvolutionProvider.enviar_pdf, o caption é usado como caption do documento
                    sucesso = await enviar_pdf(
                        lead.telefone,
                        anexo_bytes,
                        numero=template.anexo_nome_original or "documento",
                        caption=mensagem_final,
                        empresa=empresa
                    )
                else:
                    # Fallback para texto se o mime não for suportado como mídia direta
                    sucesso = await enviar_mensagem_texto(lead.telefone, mensagem_final, empresa=empresa)
            except Exception as e:
                logger.warning(f"Falha ao processar anexo do template: {e}. Enviando apenas texto.")
                sucesso = await enviar_mensagem_texto(lead.telefone, mensagem_final, empresa=empresa)
        else:
            # Envio normal apenas texto
            sucesso = await enviar_mensagem_texto(lead.telefone, mensagem_final, empresa=empresa)
    except Exception as e:
        erro_msg = str(e)

    lead.ultimo_contato_em = datetime.now(timezone.utc)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.WHATSAPP,
            canal=CanalInteracao.WHATSAPP,
            conteudo=mensagem_final,
        )
    )
    db.commit()

    if not sucesso:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao enviar WhatsApp: {erro_msg or 'Erro desconhecido'}"
        )
    return {
        "ok": True,
        "success": True,
        "detail": "Mensagem enviada com sucesso via WhatsApp",
    }


@router.post("/{lead_id}/email")
def enviar_email(
    lead_id: int,
    body: EmailBody,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    if not lead.email:
        raise HTTPException(status_code=400, detail="Lead não possui e-mail cadastrado")

    template = _buscar_template_ativo(db, usuario.empresa_id, body.template_id)
    attachments = None
    if template and template.anexo_arquivo_path:
        anexo_path = validar_template_anexo_path(template.anexo_arquivo_path, usuario.empresa_id)
        attachments = [
            {
                "path": anexo_path,
                "name": template.anexo_nome_original,
                "mime_type": template.anexo_mime_type,
                "size_bytes": template.anexo_tamanho_bytes,
            }
        ]

    sucesso = False
    erro_msg = None
    try:
        sucesso = send_email_simples(
            lead.email,
            body.assunto,
            body.mensagem,
            attachments=attachments,
        )
    except Exception as e:
        erro_msg = str(e)

    lead.ultimo_contato_em = datetime.now(timezone.utc)
    db.add(
        TenantCommercialInteraction(
            empresa_id=usuario.empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.EMAIL,
            canal=CanalInteracao.EMAIL,
            conteudo=f"[{body.assunto}] {body.mensagem}",
        )
    )
    db.commit()

    if not sucesso:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao enviar e-mail: {erro_msg or 'Verifique a configuração de e-mail da empresa'}"
        )
    return {
        "ok": True,
        "success": True,
        "detail": "E-mail enviado com sucesso",
    }


log_whatsapp = enviar_whatsapp
log_email = enviar_email


@router.patch("/{lead_id}", response_model=LeadResponse)
def patch_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    return update_lead(lead_id, payload, db, usuario)


@router.patch("/{lead_id}/status")
def patch_lead_status(
    lead_id: int,
    body: dict,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    novo_status = body.get("status") or body.get("status_pipeline")
    if not novo_status:
        raise HTTPException(status_code=422, detail="Campo 'status' obrigatório")
    lead.status_pipeline = novo_status
    etapa = db.query(TenantPipelineEtapa).filter(
        TenantPipelineEtapa.empresa_id == usuario.empresa_id,
        TenantPipelineEtapa.slug == novo_status,
        TenantPipelineEtapa.ativo.is_(True),
    ).first()
    lead.etapa_pipeline_id = etapa.id if etapa else None
    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status_pipeline": novo_status}


@router.patch("/{lead_id}/arquivar")
def arquivar_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = _buscar_lead(db, usuario.empresa_id, lead_id)
    lead.ativo = False
    lead.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "message": "Lead arquivado"}


@router.post("/{lead_id}/criar-empresa", include_in_schema=False)
def tenant_forbidden_criar_empresa(lead_id: int):
    """Bloqueado no CRM tenant: criação de conta a partir de lead é exclusiva do superadmin."""
    raise HTTPException(status_code=403, detail="Operação não disponível no comercial da empresa.")


@router.post("/{lead_id}/reenviar-senha", include_in_schema=False)
def tenant_forbidden_reenviar_senha(lead_id: int):
    """Bloqueado no CRM tenant."""
    raise HTTPException(status_code=403, detail="Operação não disponível no comercial da empresa.")
