from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantCommercialLead, TenantCommercialTemplate, Usuario
from app.schemas.schemas import TemplateCreate, TemplateOut, TemplatePreview, TemplateUpdate


router = APIRouter(
    prefix="/templates",
    tags=["Tenant Comercial Templates"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


@router.post("/", response_model=TemplateOut)
async def create_template(
    request: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    template = TenantCommercialTemplate(
        empresa_id=current_user.empresa_id,
        nome=request.nome,
        tipo=request.tipo,
        canal=request.canal,
        assunto=request.assunto,
        conteudo=request.conteudo,
        ativo=True,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/", response_model=List[TemplateOut])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
    ativo: Optional[bool] = Query(None),
):
    q = db.query(TenantCommercialTemplate).filter(
        TenantCommercialTemplate.empresa_id == current_user.empresa_id
    )
    if ativo is None:
        q = q.filter(TenantCommercialTemplate.ativo.is_(True))
    else:
        q = q.filter(TenantCommercialTemplate.ativo == ativo)
    return q.order_by(TenantCommercialTemplate.id.desc()).all()


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    template = (
        db.query(TenantCommercialTemplate)
        .filter(
            TenantCommercialTemplate.id == template_id,
            TenantCommercialTemplate.empresa_id == current_user.empresa_id,
            TenantCommercialTemplate.ativo.is_(True),
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return template


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    request: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    template = (
        db.query(TenantCommercialTemplate)
        .filter(
            TenantCommercialTemplate.id == template_id,
            TenantCommercialTemplate.empresa_id == current_user.empresa_id,
            TenantCommercialTemplate.ativo.is_(True),
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    template = (
        db.query(TenantCommercialTemplate)
        .filter(
            TenantCommercialTemplate.id == template_id,
            TenantCommercialTemplate.empresa_id == current_user.empresa_id,
            TenantCommercialTemplate.ativo.is_(True),
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    template.ativo = False
    db.commit()
    return {"message": "Template deletado com sucesso"}


@router.post("/{template_id}/preview", response_model=TemplatePreview)
async def preview_template(
    template_id: int,
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    template = (
        db.query(TenantCommercialTemplate)
        .filter(
            TenantCommercialTemplate.id == template_id,
            TenantCommercialTemplate.empresa_id == current_user.empresa_id,
            TenantCommercialTemplate.ativo.is_(True),
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    lead = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.id == lead_id,
            TenantCommercialLead.empresa_id == current_user.empresa_id,
        )
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    conteudo = template.conteudo
    conteudo = conteudo.replace("{nome_responsavel}", lead.nome or "")
    conteudo = conteudo.replace("{nome_empresa}", lead.nome_empresa or lead.nome or "")
    conteudo = conteudo.replace("{whatsapp}", lead.telefone or "")
    conteudo = conteudo.replace("{email}", lead.email or "")
    conteudo = conteudo.replace("{cidade}", "")

    assunto = template.assunto
    if assunto:
        assunto = assunto.replace("{nome_responsavel}", lead.nome or "")
        assunto = assunto.replace("{nome_empresa}", lead.nome_empresa or lead.nome or "")

    return TemplatePreview(assunto=assunto, conteudo=conteudo)
