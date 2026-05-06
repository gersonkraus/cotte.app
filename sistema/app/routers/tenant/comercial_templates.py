from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantCommercialLead, TenantCommercialTemplate, Usuario
from app.schemas.tenant_comercial_templates import (
    TemplatePreviewBody,
    TenantTemplateCreate,
    TenantTemplateOut,
    TenantTemplatePreview,
    TenantTemplateUpdate,
)
from app.services.template_anexos_service import (
    salvar_upload_template_anexo,
    validar_template_anexo_path,
)


router = APIRouter(
    prefix="/templates",
    tags=["Tenant Comercial Templates"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


def _limpar_anexo_template(template: TenantCommercialTemplate) -> None:
    template.anexo_arquivo_path = None
    template.anexo_nome_original = None
    template.anexo_mime_type = None
    template.anexo_tamanho_bytes = None


def _validar_metadados_anexo_template(data: dict, empresa_id: int) -> None:
    campos_anexo = (
        "anexo_arquivo_path",
        "anexo_nome_original",
        "anexo_mime_type",
        "anexo_tamanho_bytes",
    )
    if not any(data.get(campo) is not None for campo in campos_anexo):
        return

    validar_template_anexo_path(data.get("anexo_arquivo_path"), empresa_id)


@router.post("/", response_model=TenantTemplateOut)
async def create_template(
    request: TenantTemplateCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    data = request.model_dump()
    _validar_metadados_anexo_template(data, current_user.empresa_id)
    template = TenantCommercialTemplate(
        empresa_id=current_user.empresa_id,
        ativo=True,
        **data,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.post("/upload-anexo")
async def upload_template_anexo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    return salvar_upload_template_anexo(current_user.empresa_id, file)


@router.get("/", response_model=List[TenantTemplateOut])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
    ativo: Optional[bool] = Query(None),
    tipo: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
):
    q = db.query(TenantCommercialTemplate).filter(
        TenantCommercialTemplate.empresa_id == current_user.empresa_id
    )
    if ativo is None:
        q = q.filter(TenantCommercialTemplate.ativo.is_(True))
    else:
        q = q.filter(TenantCommercialTemplate.ativo == ativo)
    if tipo:
        q = q.filter(TenantCommercialTemplate.tipo == tipo)
    if canal:
        q = q.filter(TenantCommercialTemplate.canal.in_([canal, "ambos"]))
    return q.order_by(TenantCommercialTemplate.id.desc()).all()


@router.get("/{template_id}", response_model=TenantTemplateOut)
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


@router.put("/{template_id}", response_model=TenantTemplateOut)
async def update_template(
    template_id: int,
    request: TenantTemplateUpdate,
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

    data = request.model_dump(exclude_unset=True)
    remover_anexo = data.pop("remover_anexo", False)
    _validar_metadados_anexo_template(data, current_user.empresa_id)

    for field, value in data.items():
        setattr(template, field, value)
    if remover_anexo:
        _limpar_anexo_template(template)
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


@router.post("/{template_id}/preview", response_model=TenantTemplatePreview)
async def preview_template(
    template_id: int,
    body: TemplatePreviewBody,
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
            TenantCommercialLead.id == getattr(body, "lead_id", body),
            TenantCommercialLead.empresa_id == current_user.empresa_id,
        )
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    dias_sem_contato = 0
    if lead.ultimo_contato_em:
        try:
            ultimo = lead.ultimo_contato_em
            if ultimo.tzinfo is None:
                ultimo = ultimo.replace(tzinfo=timezone.utc)
            agora = datetime.now(timezone.utc)
            dias_sem_contato = (agora - ultimo).days
        except Exception:
            pass

    score_str = (lead.lead_score.value if lead.lead_score else "frio") if lead.lead_score else "frio"
    etapa_str = (lead.status_pipeline or "").replace("_", " ").title()

    valor_str = ""
    if lead.valor_estimado:
        try:
            valor_float = float(lead.valor_estimado)
            valor_str = f"R$ {valor_float:,.0f}".replace(",", ".")
        except Exception:
            pass

    conteudo = template.conteudo
    conteudo = conteudo.replace("{nome_responsavel}", lead.nome or "")
    conteudo = conteudo.replace("{nome_empresa}", lead.nome_empresa or lead.nome or "")
    conteudo = conteudo.replace("{whatsapp}", lead.telefone or "")
    conteudo = conteudo.replace("{email}", lead.email or "")
    conteudo = conteudo.replace("{cidade}", "")
    conteudo = conteudo.replace("{dias_sem_contato}", str(dias_sem_contato))
    conteudo = conteudo.replace("{score}", score_str)
    conteudo = conteudo.replace("{etapa}", etapa_str)
    conteudo = conteudo.replace("{valor}", valor_str)

    assunto = template.assunto
    if assunto:
        assunto = assunto.replace("{nome_responsavel}", lead.nome or "")
        assunto = assunto.replace("{nome_empresa}", lead.nome_empresa or lead.nome or "")
        assunto = assunto.replace("{dias_sem_contato}", str(dias_sem_contato))
        assunto = assunto.replace("{score}", score_str)
        assunto = assunto.replace("{etapa}", etapa_str)
        assunto = assunto.replace("{valor}", valor_str)

    return TenantTemplatePreview(
        assunto=assunto,
        conteudo=conteudo,
        dias_sem_contato=dias_sem_contato,
        score=score_str,
        etapa=lead.status_pipeline,
        valor=float(lead.valor_estimado) if lead.valor_estimado else None,
        anexo_url=template.anexo_arquivo_path,
        anexo_nome_original=template.anexo_nome_original,
        anexo_mime_type=template.anexo_mime_type,
        anexo_tamanho_bytes=template.anexo_tamanho_bytes,
    )
