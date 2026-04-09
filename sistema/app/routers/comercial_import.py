from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
import logging
from app.core.database import get_db
from app.core.auth import exigir_permissao
from app.models.models import (
    Empresa,
    Usuario,
    CommercialLead,
    CommercialLeadSource,
    LeadImportacao,
    LeadImportacaoItem,
    CommercialSegment,
    Campaign,
    CampaignLead,
)
from app.schemas.schemas import (
    LeadImportRequest,
    LeadImportResponse,
    LeadImportPreview,
    LeadImportItem,
    SegmentOut,
    LeadSourceOut,
)
from app.services.lead_import_service import LeadImportService
from app.utils.csv_parser import parse_csv_to_leads
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comercial/import", tags=["Comercial - Importação"])


@router.post("/preview", response_model=LeadImportPreview)
async def preview_import(
    request: LeadImportRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    """Pré-visualização de importação de leads."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    service = LeadImportService(db, empresa, current_user)

    if request.metodo == "colar":
        leads = service.parse_text_to_leads(request.dados)
    elif request.metodo == "csv":
        leads = parse_csv_to_leads(request.dados)
    else:
        raise HTTPException(status_code=400, detail="Método inválido")

    # Contar duplicatas e inválidos
    duplicatas = 0
    invalidos = 0
    validos = []

    for lead in leads:
        # Verificar duplicata por WhatsApp ou Email
        exists = (
            db.query(CommercialLead)
            .filter(
                CommercialLead.empresa_id == empresa.id,
                (CommercialLead.whatsapp == lead.whatsapp)
                | (CommercialLead.email == lead.email),
            )
            .first()
        )

        if exists:
            duplicatas += 1
        else:
            validos.append(lead)

    return LeadImportPreview(
        leads=validos, total=len(leads), duplicatas=duplicatas, invalidos=invalidos
    )


@router.post("/execute", response_model=LeadImportResponse)
async def execute_import(
    request: LeadImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    """Executa importação de leads em massa."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    service = LeadImportService(db, empresa, current_user)

    # Criar registro de importação
    importacao = LeadImportacao(
        empresa_id=empresa.id,
        criado_por_id=current_user.id,
        nome=f"Importação {request.metodo.title()} - {uuid.uuid4().hex[:8]}",
        metodo=request.metodo,
        total_importados=0,
        total_validos=0,
        total_invalidos=0,
    )
    db.add(importacao)
    db.flush()

    if request.metodo == "colar":
        leads = service.parse_text_to_leads(request.dados)
    elif request.metodo == "csv":
        leads = parse_csv_to_leads(request.dados)
    else:
        raise HTTPException(status_code=400, detail="Método inválido")

    # Obter origem padrão "Importação em Massa"
    origem = (
        db.query(CommercialLeadSource)
        .filter(
            CommercialLeadSource.nome == "Importação em Massa",
            CommercialLeadSource.empresa_id == empresa.id,
        )
        .first()
    )

    if not origem:
        origem = CommercialLeadSource(
            nome="Importação em Massa", empresa_id=empresa.id, ativo=True
        )
        db.add(origem)
        db.flush()

    # Processar leads
    leads_criados = []
    erros = []

    for lead_data in leads:
        try:
            lead = CommercialLead(
                nome_responsavel=lead_data.nome_responsavel,
                nome_empresa=lead_data.nome_empresa,
                whatsapp=lead_data.whatsapp,
                email=lead_data.email,
                cidade=lead_data.cidade,
                observacoes=lead_data.observacoes,
                origem_lead_id=origem.id,
                segmento_id=request.segmento_id,
                status_pipeline="novo",
                lead_score="frio",
                empresa_id=empresa.id,
            )
            db.add(lead)
            db.flush()
            leads_criados.append(lead)
        except Exception as e:
            erros.append(f"Erro ao criar lead {lead_data.nome_responsavel}: {str(e)}")

    # Atualizar estatísticas da importação
    importacao.total_importados = len(leads)
    importacao.total_validos = len(leads_criados)
    importacao.total_invalidos = len(erros)

    # Vincular leads à campanha se campaign_id foi fornecido
    if request.campaign_id and leads_criados:
        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == request.campaign_id, Campaign.empresa_id == empresa.id
            )
            .first()
        )

        if campaign:
            for lead in leads_criados:
                campaign_lead = CampaignLead(
                    campaign_id=campaign.id, lead_id=lead.id, status="pendente"
                )
                db.add(campaign_lead)

            # Atualizar contador de leads na campanha
            campaign.total_leads = (campaign.total_leads or 0) + len(leads_criados)

    db.commit()

    return LeadImportResponse(
        total_importados=len(leads),
        total_validos=len(leads_criados),
        total_invalidos=len(erros),
        leads_criados=leads_criados,
        erros=erros,
    )


@router.get("/segments", response_model=List[SegmentOut])
async def list_segments(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Lista segmentos disponíveis para importação."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    segments = (
        db.query(CommercialSegment)
        .filter(
            CommercialSegment.empresa_id == empresa.id, CommercialSegment.ativo == True
        )
        .all()
    )

    return segments


@router.get("/sources", response_model=List[LeadSourceOut])
async def list_sources(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Lista origens de lead disponíveis."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    sources = (
        db.query(CommercialLeadSource)
        .filter(
            CommercialLeadSource.empresa_id == empresa.id,
            CommercialLeadSource.ativo == True,
        )
        .all()
    )

    return sources


@router.get("/list")
async def list_imports(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Lista todas as importações da empresa."""
    importacoes = (
        db.query(LeadImportacao)
        .filter(LeadImportacao.empresa_id == usuario.empresa_id)
        .order_by(LeadImportacao.criado_em.desc())
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


@router.get("/{importacao_id}/leads")
async def get_import_leads(
    importacao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    """Retorna os leads vinculados a uma importação específica."""
    importacao = (
        db.query(LeadImportacao)
        .filter(
            LeadImportacao.id == importacao_id,
            LeadImportacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not importacao:
        raise HTTPException(status_code=404, detail="Importação não encontrada")

    itens = (
        db.query(LeadImportacaoItem)
        .filter(LeadImportacaoItem.importacao_id == importacao_id)
        .all()
    )
    lead_ids = [item.lead_id for item in itens if item.lead_id]

    leads = []
    segmento_id = None
    segmento_nome = None
    if lead_ids:
        leads_db = (
            db.query(CommercialLead)
            .options(joinedload(CommercialLead.segmento_rel))
            .filter(
                CommercialLead.id.in_(lead_ids),
                CommercialLead.empresa_id == usuario.empresa_id,
            )
            .all()
        )
        leads = [
            {
                "id": l.id,
                "nome_responsavel": l.nome_responsavel,
                "nome_empresa": l.nome_empresa,
                "whatsapp": l.whatsapp,
                "email": l.email,
            }
            for l in leads_db
        ]
        # Segmento fica nos leads; a importação não persiste segmento_id na tabela.
        if leads_db:
            primeiro = leads_db[0]
            segmento_id = primeiro.segmento_id
            segmento_nome = (
                primeiro.segmento_rel.nome if primeiro.segmento_rel else None
            )

    return {
        "importacao_id": importacao.id,
        "nome": importacao.nome,
        "metodo": importacao.metodo,
        "total": importacao.total_importados,
        "validos": importacao.total_validos,
        "invalidos": importacao.total_invalidos,
        "criado_em": importacao.criado_em.isoformat() if importacao.criado_em else None,
        "segmento_id": segmento_id,
        "segmento_nome": segmento_nome,
        "leads": leads,
    }


@router.delete("/{importacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import(
    importacao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "exclusao")),
):
    """Exclui uma importação e todos os leads vinculados a ela."""
    importacao = (
        db.query(LeadImportacao)
        .filter(
            LeadImportacao.id == importacao_id,
            LeadImportacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not importacao:
        raise HTTPException(status_code=404, detail="Importação não encontrada")

    # Buscar itens da importação para pegar os lead_ids
    itens = (
        db.query(LeadImportacaoItem)
        .filter(LeadImportacaoItem.importacao_id == importacao_id)
        .all()
    )
    lead_ids = [item.lead_id for item in itens if item.lead_id]

    # Deletar leads vinculados
    if lead_ids:
        db.query(CommercialLead).filter(
            CommercialLead.id.in_(lead_ids),
            CommercialLead.empresa_id == usuario.empresa_id,
        ).delete(synchronize_session=False)

    # Deletar itens da importação
    db.query(LeadImportacaoItem).filter(
        LeadImportacaoItem.importacao_id == importacao_id
    ).delete(synchronize_session=False)

    # Deletar a importação
    db.delete(importacao)
    db.commit()
    return None
