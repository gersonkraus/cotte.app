import base64
import csv
import io
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    LeadScore,
    TenantCampaignLead,
    TenantCommercialCampaign,
    TenantCommercialLead,
    TenantLeadImportacao,
    TenantLeadImportacaoItem,
    Usuario,
)
from app.schemas.schemas import LeadImportItem, LeadImportPreview, LeadImportRequest


router = APIRouter(
    prefix="/import",
    tags=["Tenant Comercial Importação"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


def _parse_colar(data: str) -> List[LeadImportItem]:
    leads: List[LeadImportItem] = []
    lines = data.strip().split("\n")
    for line in lines:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("-")]
        nome = parts[0] if parts else ""
        tel = parts[1] if len(parts) > 1 else None
        email = parts[2] if len(parts) > 2 else None
        cidade = parts[3] if len(parts) > 3 else None
        if nome:
            leads.append(
                LeadImportItem(
                    nome_responsavel=nome,
                    nome_empresa=nome,
                    whatsapp=tel,
                    email=email,
                    cidade=cidade,
                    observacoes="Importado via texto",
                )
            )
    return leads


def _parse_csv(data: str) -> List[LeadImportItem]:
    raw = data
    try:
        raw = base64.b64decode(data).decode("utf-8")
    except Exception:
        pass
    f = io.StringIO(raw)
    reader = csv.DictReader(f)
    out: List[LeadImportItem] = []
    for row in reader:
        nome = row.get("nome_responsavel") or row.get("nome") or row.get("responsavel")
        empresa = row.get("nome_empresa") or row.get("empresa") or nome
        if not nome:
            continue
        out.append(
            LeadImportItem(
                nome_responsavel=nome,
                nome_empresa=empresa or nome,
                whatsapp=row.get("whatsapp"),
                email=row.get("email"),
                cidade=row.get("cidade"),
                observacoes=row.get("observacoes"),
            )
        )
    return out


def _parse_request(req: LeadImportRequest) -> List[LeadImportItem]:
    if req.metodo == "colar":
        return _parse_colar(req.dados)
    if req.metodo == "csv":
        return _parse_csv(req.dados)
    raise HTTPException(status_code=400, detail="Método inválido")


@router.post("/preview", response_model=LeadImportPreview)
async def preview_import(
    request: LeadImportRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    leads = _parse_request(request)
    duplicatas = 0
    validos = []
    for lead in leads:
        exists = (
            db.query(TenantCommercialLead)
            .filter(
                TenantCommercialLead.empresa_id == current_user.empresa_id,
                ((TenantCommercialLead.telefone == lead.whatsapp) if lead.whatsapp else False)
                | ((TenantCommercialLead.email == lead.email) if lead.email else False),
            )
            .first()
        )
        if exists:
            duplicatas += 1
        else:
            validos.append(lead)
    return LeadImportPreview(
        leads=validos,
        total=len(leads),
        duplicatas=duplicatas,
        invalidos=max(len(leads) - len(validos) - duplicatas, 0),
    )


@router.post("/execute")
async def execute_import(
    request: LeadImportRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    leads = _parse_request(request)
    importacao = TenantLeadImportacao(
        empresa_id=current_user.empresa_id,
        criado_por_id=current_user.id,
        nome=f"Importação {request.metodo.title()} - {uuid.uuid4().hex[:8]}",
        metodo=request.metodo,
    )
    db.add(importacao)
    db.flush()

    created = []
    erros = []
    for item in leads:
        try:
            lead = TenantCommercialLead(
                empresa_id=current_user.empresa_id,
                nome=item.nome_responsavel,
                nome_empresa=item.nome_empresa,
                telefone=item.whatsapp,
                email=item.email,
                observacoes=item.observacoes,
                status_pipeline="novo",
                lead_score=LeadScore.FRIO,
                ativo=True,
            )
            db.add(lead)
            db.flush()
            db.add(
                TenantLeadImportacaoItem(
                    importacao_id=importacao.id,
                    nome_responsavel=item.nome_responsavel,
                    nome_empresa=item.nome_empresa,
                    whatsapp=item.whatsapp,
                    email=item.email,
                    cidade=item.cidade,
                    observacoes=item.observacoes,
                    status="valido",
                    lead_id=lead.id,
                )
            )
            created.append(lead)
        except Exception as e:
            erros.append(str(e))
    importacao.total_importados = len(leads)
    importacao.total_validos = len(created)
    importacao.total_invalidos = len(erros)

    if request.campaign_id and created:
        campaign = (
            db.query(TenantCommercialCampaign)
            .filter(
                TenantCommercialCampaign.id == request.campaign_id,
                TenantCommercialCampaign.empresa_id == current_user.empresa_id,
            )
            .first()
        )
        if campaign:
            for lead in created:
                db.add(TenantCampaignLead(campaign_id=campaign.id, lead_id=lead.id, status="pendente"))
            campaign.total_leads = (campaign.total_leads or 0) + len(created)
    db.commit()
    return {
        "total_importados": len(leads),
        "total_validos": len(created),
        "total_invalidos": len(erros),
        "leads_criados": [
            {
                "id": l.id,
                "nome_responsavel": l.nome,
                "nome_empresa": l.nome_empresa or l.nome,
                "whatsapp": l.telefone,
                "email": l.email,
                "status_pipeline": l.status_pipeline,
                "lead_score": l.lead_score,
                "criado_em": l.criado_em,
                "ativo": l.ativo,
            }
            for l in created
        ],
        "erros": erros,
    }


@router.get("/segments")
async def list_segments(
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return []


@router.get("/sources")
async def list_sources(
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return []


@router.get("/list")
async def list_imports(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    importacoes = (
        db.query(TenantLeadImportacao)
        .filter(TenantLeadImportacao.empresa_id == usuario.empresa_id)
        .order_by(TenantLeadImportacao.criado_em.desc())
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
    imp = (
        db.query(TenantLeadImportacao)
        .filter(
            TenantLeadImportacao.id == importacao_id,
            TenantLeadImportacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    items = (
        db.query(TenantLeadImportacaoItem)
        .filter(TenantLeadImportacaoItem.importacao_id == importacao_id)
        .order_by(TenantLeadImportacaoItem.id.asc())
        .all()
    )
    return items


@router.delete("/{importacao_id}")
async def delete_import(
    importacao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    imp = (
        db.query(TenantLeadImportacao)
        .filter(
            TenantLeadImportacao.id == importacao_id,
            TenantLeadImportacao.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    db.query(TenantLeadImportacaoItem).filter(
        TenantLeadImportacaoItem.importacao_id == importacao_id
    ).delete()
    db.delete(imp)
    db.commit()
    return {"ok": True}
