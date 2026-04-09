from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from app.core.database import get_db
from app.core.auth import exigir_permissao
from app.models.models import (
    Empresa, Usuario, CommercialTemplate, CommercialLead
)
from app.schemas.schemas import (
    TemplateCreate, TemplateUpdate, TemplateOut, TemplatePreview
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comercial/templates", tags=["Comercial - Templates"])


@router.post("/", response_model=TemplateOut)
async def create_template(
    request: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Cria um novo template."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    template = CommercialTemplate(
        nome=request.nome,
        tipo=request.tipo,
        canal=request.canal,
        assunto=request.assunto,
        conteudo=request.conteudo,
        ativo=True
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get("/", response_model=List[TemplateOut])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
    ativo: Optional[bool] = Query(
        None,
        description="Omitir ou true = só ativos (padrão). false = só inativos.",
    ),
):
    """Lista templates comerciais. Respeita ?ativo=true|false como o frontend envia."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    q = db.query(CommercialTemplate)
    if ativo is None:
        q = q.filter(CommercialTemplate.ativo == True)
    else:
        q = q.filter(CommercialTemplate.ativo == ativo)
    templates = q.all()

    return templates


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura"))
):
    """Obtém um template."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    template = db.query(CommercialTemplate).filter(
        CommercialTemplate.id == template_id,
        CommercialTemplate.ativo == True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    return template


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    request: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Atualiza um template."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    template = db.query(CommercialTemplate).filter(
        CommercialTemplate.id == template_id,
        CommercialTemplate.ativo == True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    if request.nome:
        template.nome = request.nome
    if request.tipo:
        template.tipo = request.tipo
    if request.canal:
        template.canal = request.canal
    if request.assunto is not None:
        template.assunto = request.assunto
    if request.conteudo:
        template.conteudo = request.conteudo
    if request.ativo is not None:
        template.ativo = request.ativo

    db.commit()
    db.refresh(template)

    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "admin"))
):
    """Deleta um template (soft delete)."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    template = db.query(CommercialTemplate).filter(
        CommercialTemplate.id == template_id,
        CommercialTemplate.ativo == True
    ).first()

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
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita"))
):
    """Pré-visualiza um template com dados de um lead."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    template = db.query(CommercialTemplate).filter(
        CommercialTemplate.id == template_id,
        CommercialTemplate.ativo == True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    # Obter lead
    lead = db.query(CommercialLead).filter(
        CommercialLead.id == lead_id,
        CommercialLead.empresa_id == empresa.id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Renderizar template com variáveis
    conteudo = template.conteudo
    conteudo = conteudo.replace("{nome_responsavel}", lead.nome_responsavel)
    conteudo = conteudo.replace("{nome_empresa}", lead.nome_empresa)
    conteudo = conteudo.replace("{whatsapp}", lead.whatsapp or "")
    conteudo = conteudo.replace("{email}", lead.email or "")
    conteudo = conteudo.replace("{cidade}", lead.cidade or "")

    assunto = template.assunto
    if assunto:
        assunto = assunto.replace("{nome_responsavel}", lead.nome_responsavel)
        assunto = assunto.replace("{nome_empresa}", lead.nome_empresa)

    return TemplatePreview(
        assunto=assunto,
        conteudo=conteudo
    )