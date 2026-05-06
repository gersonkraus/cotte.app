# Modelos Com Anexos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que o cadastro de modelos em `tenant-comercial.html` aceite um anexo opcional (PDF ou imagem), persistindo os metadados no tenant comercial e usando o anexo de forma funcional no envio por e-mail, com fallback explicito por link no WhatsApp.

**Architecture:** A menor mudanca segura é separar o upload do arquivo do salvamento textual do template. O tenant ganha schemas proprios para nao contaminar o modulo comercial global, um endpoint dedicado de upload devolve metadados do anexo, e os endpoints JSON existentes de template passam a aceitar campos opcionais de anexo. No envio, e-mail anexa o arquivo real; WhatsApp reaproveita a URL publica do upload e adiciona o link ao corpo da mensagem.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Alembic, frontend HTML/CSS/JavaScript vanilla, R2 via `documentos_service`, pytest.

---

## Estrutura de arquivos

- Criar: `sistema/alembic/versions/tc008_add_anexo_to_tenant_templates.py`
- Criar: `sistema/app/schemas/tenant_comercial_templates.py`
- Criar: `sistema/app/services/template_anexos_service.py`
- Modificar: `sistema/app/models/models.py`
- Modificar: `sistema/app/routers/tenant/comercial_templates.py`
- Modificar: `sistema/app/routers/tenant/comercial_leads.py`
- Modificar: `sistema/app/services/email_service.py`
- Modificar: `sistema/cotte-frontend/tenant-comercial.html`
- Modificar: `sistema/cotte-frontend/js/tenant-TemplatesManager.js`
- Modificar: `sistema/cotte-frontend/js/tenant-comercial-mensagens.js`
- Modificar: `sistema/cotte-frontend/js/tenant-comercial-core.js`
- Testar: `sistema/tests/test_tenant_comercial.py`
- Consultar como referencia de upload: `sistema/app/services/documentos_service.py`
- Consultar como referencia de templates globais sem tocar no contrato: `sistema/app/routers/comercial_templates.py`

## Decisoes de implementacao

- Escopo inicial de formatos: `application/pdf`, `image/png`, `image/jpeg`, `image/webp`.
- Persistencia somente em `TenantCommercialTemplate`; `CommercialTemplate` global fica inalterado.
- O upload acontece antes do `POST` ou `PUT` do template, via endpoint dedicado do tenant, para preservar o CRUD JSON atual.
- O template passa a expor metadados de anexo opcionais e `anexo_url` para consumo do frontend.
- E-mail passa a usar o anexo do template quando `template_id` vier no payload.
- WhatsApp nao tenta enviar midia binaria; se o template possuir anexo, o backend concatena uma linha com a URL publica do arquivo na mensagem final.

### Task 1: Cobrir o comportamento esperado do tenant com testes falhando primeiro

**Files:**
- Modify: `sistema/tests/test_tenant_comercial.py`
- Consult: `sistema/app/routers/tenant/comercial_templates.py`
- Consult: `sistema/app/routers/tenant/comercial_leads.py`

- [ ] **Step 1: Escrever os testes de templates com metadados de anexo**

Adicionar uma secao nova no final de `sistema/tests/test_tenant_comercial.py` com estes cenarios:

```python
class TestTenantTemplatesComAnexo:
    def test_criar_template_com_anexo(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        payload = comercial_templates.TenantTemplateCreate(
            nome="Proposta com PDF",
            tipo="proposta_comercial",
            canal="email",
            assunto="Segue proposta",
            conteudo="Ola {nome_responsavel}",
            anexo_arquivo_path="https://cdn.exemplo.com/proposta.pdf",
            anexo_nome_original="proposta.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=2048,
        )

        template = asyncio.run(comercial_templates.create_template(payload, db=db, current_user=user))

        assert template.anexo_nome_original == "proposta.pdf"
        assert template.anexo_mime_type == "application/pdf"

    def test_preview_template_retorna_metadados_do_anexo(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, nome="Cliente Preview")
        template = comercial_templates.TenantCommercialTemplate(
            empresa_id=empresa_com_modulo.id,
            nome="Template com imagem",
            tipo="email_comercial",
            canal="ambos",
            conteudo="Ola {nome_responsavel}",
            assunto="Assunto",
            ativo=True,
            anexo_arquivo_path="https://cdn.exemplo.com/flyer.png",
            anexo_nome_original="flyer.png",
            anexo_mime_type="image/png",
            anexo_tamanho_bytes=1024,
        )
        db.add(template)
        db.commit()

        preview = asyncio.run(comercial_templates.preview_template(template.id, lead.id, db=db, current_user=user))

        assert preview.anexo_nome_original == "flyer.png"
        assert preview.anexo_url == "https://cdn.exemplo.com/flyer.png"
```

- [ ] **Step 2: Escrever os testes de envio por e-mail e WhatsApp com template anexado**

Adicionar os dois cenarios abaixo no mesmo arquivo:

```python
    @patch("app.routers.tenant.comercial_leads.send_email_simples")
    def test_enviar_email_com_template_anexado(self, send_email_mock, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, email="cliente@teste.com")
        template = comercial_templates.TenantCommercialTemplate(
            empresa_id=empresa_com_modulo.id,
            nome="Template Email",
            tipo="email_comercial",
            canal="email",
            conteudo="Mensagem",
            assunto="Assunto",
            ativo=True,
            anexo_arquivo_path="https://cdn.exemplo.com/proposta.pdf",
            anexo_nome_original="proposta.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=2048,
        )
        db.add(template)
        db.commit()
        send_email_mock.return_value = True

        body = comercial_leads.EmailBody(assunto="Assunto", mensagem="Mensagem", template_id=template.id)
        response = comercial_leads.enviar_email(lead.id, body=body, db=db, usuario=user)

        assert response["success"] is True
        kwargs = send_email_mock.call_args.kwargs
        assert kwargs["attachments"][0]["name"] == "proposta.pdf"

    @patch("app.routers.tenant.comercial_leads.enviar_mensagem_texto", new_callable=AsyncMock)
    def test_enviar_whatsapp_com_link_do_anexo(self, whatsapp_mock, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, telefone="48999990001")
        template = comercial_templates.TenantCommercialTemplate(
            empresa_id=empresa_com_modulo.id,
            nome="Template WhatsApp",
            tipo="mensagem_inicial",
            canal="ambos",
            conteudo="Mensagem",
            ativo=True,
            anexo_arquivo_path="https://cdn.exemplo.com/flyer.png",
            anexo_nome_original="flyer.png",
            anexo_mime_type="image/png",
            anexo_tamanho_bytes=1024,
        )
        db.add(template)
        db.commit()
        whatsapp_mock.return_value = True

        body = comercial_leads.MensagemBody(mensagem="Mensagem", template_id=template.id)
        response = asyncio.run(comercial_leads.enviar_whatsapp(lead.id, body=body, db=db, usuario=user))

        assert response["success"] is True
        mensagem_enviada = whatsapp_mock.call_args.args[1]
        assert "https://cdn.exemplo.com/flyer.png" in mensagem_enviada
```

- [ ] **Step 3: Rodar os testes novos para confirmar que falham**

Run: `pytest sistema/tests/test_tenant_comercial.py -k "anexo or template" -v`
Expected: falhas por classes e campos ainda inexistentes, como `TenantTemplateCreate`, `template_id` e colunas de anexo.

- [ ] **Step 4: Commit**

```bash
git add sistema/tests/test_tenant_comercial.py
git commit -m "test(comercial): cover tenant templates with attachments"
```

### Task 2: Isolar o contrato do tenant e persistir metadados do anexo

**Files:**
- Create: `sistema/alembic/versions/tc008_add_anexo_to_tenant_templates.py`
- Create: `sistema/app/schemas/tenant_comercial_templates.py`
- Modify: `sistema/app/models/models.py`
- Modify: `sistema/app/routers/tenant/comercial_templates.py`

- [ ] **Step 1: Criar a migration apenas para a tabela tenant**

Criar `sistema/alembic/versions/tc008_add_anexo_to_tenant_templates.py` com este corpo:

```python
"""add anexo fields to tenant templates

Revision ID: tc008_add_anexo_to_tenant_templates
Revises: tc007_add_full_address_fields_to_tenant_leads
Create Date: 2026-05-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "tc008_add_anexo_to_tenant_templates"
down_revision = "tc007_add_full_address_fields_to_tenant_leads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant_commercial_templates", sa.Column("anexo_arquivo_path", sa.String(length=500), nullable=True))
    op.add_column("tenant_commercial_templates", sa.Column("anexo_nome_original", sa.String(length=255), nullable=True))
    op.add_column("tenant_commercial_templates", sa.Column("anexo_mime_type", sa.String(length=120), nullable=True))
    op.add_column("tenant_commercial_templates", sa.Column("anexo_tamanho_bytes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_commercial_templates", "anexo_tamanho_bytes")
    op.drop_column("tenant_commercial_templates", "anexo_mime_type")
    op.drop_column("tenant_commercial_templates", "anexo_nome_original")
    op.drop_column("tenant_commercial_templates", "anexo_arquivo_path")
```

- [ ] **Step 2: Adicionar os campos no modelo SQLAlchemy do tenant**

Inserir somente em `TenantCommercialTemplate` este bloco:

```python
anexo_arquivo_path = Column(String(500), nullable=True)
anexo_nome_original = Column(String(255), nullable=True)
anexo_mime_type = Column(String(120), nullable=True)
anexo_tamanho_bytes = Column(Integer, nullable=True)
```

Nao alterar `CommercialTemplate` global.

- [ ] **Step 3: Criar schemas proprios do tenant para evitar impacto no modulo global**

Criar `sistema/app/schemas/tenant_comercial_templates.py` com o minimo abaixo:

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_serializer

from app.models.models import CanalTemplate, TipoTemplate


class TenantTemplateCreate(BaseModel):
    nome: str
    tipo: TipoTemplate
    canal: CanalTemplate
    assunto: Optional[str] = None
    conteudo: str
    anexo_arquivo_path: Optional[str] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None


class TenantTemplateUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[TipoTemplate] = None
    canal: Optional[CanalTemplate] = None
    assunto: Optional[str] = None
    conteudo: Optional[str] = None
    ativo: Optional[bool] = None
    anexo_arquivo_path: Optional[str] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None
    remover_anexo: Optional[bool] = None


class TenantTemplateOut(BaseModel):
    id: int
    nome: str
    tipo: TipoTemplate
    canal: CanalTemplate
    assunto: Optional[str] = None
    conteudo: str
    ativo: bool
    anexo_arquivo_path: Optional[str] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None
    anexo_url: Optional[str] = None
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    @field_serializer("canal", "tipo")
    def serialize_enum(self, v):
        return v.value if hasattr(v, "value") else str(v)

    class Config:
        from_attributes = True


class TenantTemplatePreview(BaseModel):
    assunto: Optional[str] = None
    conteudo: str
    dias_sem_contato: int = 0
    score: Optional[str] = None
    etapa: Optional[str] = None
    valor: Optional[float] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None
    anexo_url: Optional[str] = None
```

- [ ] **Step 4: Ajustar o router tenant para usar os schemas novos e limpar anexo removido**

Trocar os imports e a logica principal de `sistema/app/routers/tenant/comercial_templates.py` por algo neste formato:

```python
from app.schemas.tenant_comercial_templates import (
    TenantTemplateCreate,
    TenantTemplateOut,
    TenantTemplatePreview,
    TenantTemplateUpdate,
)


def _limpar_anexo_template(template: TenantCommercialTemplate) -> None:
    template.anexo_arquivo_path = None
    template.anexo_nome_original = None
    template.anexo_mime_type = None
    template.anexo_tamanho_bytes = None


@router.post("/", response_model=TenantTemplateOut)
async def create_template(
    request: TenantTemplateCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    template = TenantCommercialTemplate(empresa_id=current_user.empresa_id, **request.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
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
        raise HTTPException(status_code=404, detail="Template nao encontrado")
    data = request.model_dump(exclude_unset=True)
    remover_anexo = data.pop("remover_anexo", False)
    for field, value in data.items():
        setattr(template, field, value)
    if remover_anexo:
        _limpar_anexo_template(template)
    db.commit()
    db.refresh(template)
    return template
```

- [ ] **Step 5: Rodar os testes de template para validar persistencia**

Run: `pytest sistema/tests/test_tenant_comercial.py -k "template and anexo" -v`
Expected: os testes de criacao e preview passam; os de envio ainda falham porque `template_id` nao existe em `EmailBody` e `MensagemBody`.

- [ ] **Step 6: Commit**

```bash
git add sistema/alembic/versions/tc008_add_anexo_to_tenant_templates.py sistema/app/models/models.py sistema/app/schemas/tenant_comercial_templates.py sistema/app/routers/tenant/comercial_templates.py
git commit -m "feat(comercial): persist attachments on tenant templates"
```

### Task 3: Reaproveitar o upload existente com whitelist de anexos de template

**Files:**
- Create: `sistema/app/services/template_anexos_service.py`
- Modify: `sistema/app/routers/tenant/comercial_templates.py`
- Consult: `sistema/app/services/documentos_service.py`

- [ ] **Step 1: Escrever o teste do upload aceitando PDF e imagens**

Adicionar ao mesmo arquivo de testes um cenario direto contra o helper:

```python
def test_upload_anexo_template_aceita_pdf_e_imagem(monkeypatch, empresa_com_modulo):
    from io import BytesIO
    from fastapi import UploadFile
    from app.services import template_anexos_service

    monkeypatch.setattr(
        template_anexos_service.r2_service,
        "upload_file",
        lambda **kwargs: "https://cdn.exemplo.com/template/flyer.png",
    )

    file = UploadFile(filename="flyer.png", file=BytesIO(b"conteudo"), headers={"content-type": "image/png"})
    file.content_type = "image/png"

    result = template_anexos_service.salvar_upload_template_anexo(empresa_com_modulo.id, file)

    assert result["arquivo_nome_original"] == "flyer.png"
    assert result["mime_type"] == "image/png"
```

- [ ] **Step 2: Criar o service especializado sem afrouxar o upload global de documentos**

Criar `sistema/app/services/template_anexos_service.py` com base em `documentos_service.py`, mas com whitelist propria:

```python
from fastapi import HTTPException, UploadFile

from app.services.r2_service import r2_service
from app.services.documentos_service import _extensao_do_nome


MAX_TEMPLATE_ANEXO_BYTES = 15 * 1024 * 1024
MIME_PERMITIDOS_TEMPLATE = {"application/pdf", "image/png", "image/jpeg", "image/webp"}
EXTENSOES_PERMITIDAS_TEMPLATE = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def salvar_upload_template_anexo(empresa_id: int, file: UploadFile) -> dict:
    original = (file.filename or "").strip()
    if not original:
        raise HTTPException(status_code=400, detail="Arquivo invalido")

    ext = _extensao_do_nome(original)
    if ext not in EXTENSOES_PERMITIDAS_TEMPLATE:
        raise HTTPException(status_code=400, detail="Formato nao permitido para anexo de modelo")

    mime = (file.content_type or "").strip().lower()
    if mime and mime not in MIME_PERMITIDOS_TEMPLATE:
        raise HTTPException(status_code=400, detail="Tipo de arquivo nao permitido para anexo de modelo")

    file.file.seek(0, 2)
    tamanho = file.file.tell()
    file.file.seek(0)
    if tamanho == 0 or tamanho > MAX_TEMPLATE_ANEXO_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo invalido")

    file_url = r2_service.upload_file(
        file_obj=file.file,
        empresa_id=empresa_id,
        tipo="templates",
        extensao=ext,
        content_type=mime or "application/octet-stream",
    )
    return {
        "arquivo_path": file_url,
        "arquivo_nome_original": original,
        "mime_type": mime or "application/octet-stream",
        "tamanho_bytes": int(tamanho),
    }
```

- [ ] **Step 3: Expor o endpoint de upload do tenant comercial**

Adicionar em `sistema/app/routers/tenant/comercial_templates.py` este endpoint:

```python
from fastapi import File, UploadFile
from app.services.template_anexos_service import salvar_upload_template_anexo


@router.post("/upload-anexo")
async def upload_template_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    del db
    result = salvar_upload_template_anexo(current_user.empresa_id, file)
    return {
        "arquivo_path": result["arquivo_path"],
        "arquivo_nome_original": result["arquivo_nome_original"],
        "mime_type": result["mime_type"],
        "tamanho_bytes": result["tamanho_bytes"],
    }
```

- [ ] **Step 4: Rodar os testes do helper e do router de template**

Run: `pytest sistema/tests/test_tenant_comercial.py -k "upload_anexo_template or template and anexo" -v`
Expected: helper de upload passa; envio por e-mail e WhatsApp continua falhando ate o proximo passo.

- [ ] **Step 5: Commit**

```bash
git add sistema/app/services/template_anexos_service.py sistema/app/routers/tenant/comercial_templates.py sistema/tests/test_tenant_comercial.py
git commit -m "feat(comercial): add tenant template attachment upload"
```

### Task 4: Tornar o envio de mensagens consciente do anexo do template

**Files:**
- Modify: `sistema/app/routers/tenant/comercial_leads.py`
- Modify: `sistema/app/routers/tenant/comercial_templates.py`
- Modify: `sistema/app/services/email_service.py`
- Test: `sistema/tests/test_tenant_comercial.py`

- [ ] **Step 1: Estender os payloads de envio com `template_id` opcional**

Alterar somente os models locais em `sistema/app/routers/tenant/comercial_leads.py`:

```python
class MensagemBody(BaseModel):
    mensagem: str
    template_id: Optional[int] = None


class EmailBody(BaseModel):
    assunto: str
    mensagem: str
    template_id: Optional[int] = None
```

- [ ] **Step 2: Criar helper local para buscar template ativo da empresa**

Adicionar perto de `_buscar_lead`:

```python
def _buscar_template_ativo(db: Session, empresa_id: int, template_id: Optional[int]) -> Optional[TenantCommercialTemplate]:
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
        raise HTTPException(status_code=404, detail="Template nao encontrado")
    return template
```

- [ ] **Step 3: Anexar o arquivo no envio por e-mail**

Trocar o trecho central de `enviar_email` por este fluxo:

```python
template = _buscar_template_ativo(db, usuario.empresa_id, body.template_id)
attachments = None
if template and template.anexo_arquivo_path:
    attachments = [{
        "url": template.anexo_arquivo_path,
        "name": template.anexo_nome_original or "anexo",
        "contentType": template.anexo_mime_type or "application/octet-stream",
    }]

sucesso = send_email_simples(
    lead.email,
    body.assunto,
    body.mensagem,
    attachments=attachments,
)
```

Se `send_email_simples` ainda nao aceitar `attachments`, ajustar sua assinatura para:

```python
def send_email_simples(destinatario: str, assunto: str, mensagem: str, attachments: list[dict] | None = None) -> bool:
```

e propagar o parametro ate o ponto que ja chama `_enviar_via_brevo_api`.

- [ ] **Step 4: Aplicar fallback por link no WhatsApp**

Trocar o trecho central de `enviar_whatsapp` por este fluxo:

```python
template = _buscar_template_ativo(db, usuario.empresa_id, body.template_id)
mensagem_final = body.mensagem
if template and template.anexo_arquivo_path:
    mensagem_final = f"{mensagem_final}\n\nAnexo do modelo: {template.anexo_arquivo_path}"

sucesso = await enviar_mensagem_texto(lead.telefone, mensagem_final, empresa=empresa)
```

- [ ] **Step 5: Incluir metadados de anexo no preview do template**

Fazer `preview_template` retornar tambem:

```python
return TenantTemplatePreview(
    assunto=assunto,
    conteudo=conteudo,
    dias_sem_contato=dias_sem_contato,
    score=score_str,
    etapa=lead.status_pipeline,
    valor=float(lead.valor_estimado) if lead.valor_estimado else None,
    anexo_nome_original=template.anexo_nome_original,
    anexo_mime_type=template.anexo_mime_type,
    anexo_tamanho_bytes=template.anexo_tamanho_bytes,
    anexo_url=template.anexo_arquivo_path,
)
```

- [ ] **Step 6: Rodar os testes do backend fim a fim do tenant**

Run: `pytest sistema/tests/test_tenant_comercial.py -k "anexo or template or email or whatsapp" -v`
Expected: todos os cenarios novos passam, inclusive envio com anexo por e-mail e fallback por link no WhatsApp.

- [ ] **Step 7: Commit**

```bash
git add sistema/app/routers/tenant/comercial_leads.py sistema/app/routers/tenant/comercial_templates.py sistema/app/services/email_service.py sistema/tests/test_tenant_comercial.py
git commit -m "feat(comercial): send tenant template attachments by channel"
```

### Task 5: Expor o anexo no modal de Modelos e usar o template no envio

**Files:**
- Modify: `sistema/cotte-frontend/tenant-comercial.html`
- Modify: `sistema/cotte-frontend/js/tenant-TemplatesManager.js`
- Modify: `sistema/cotte-frontend/js/tenant-comercial-mensagens.js`
- Modify: `sistema/cotte-frontend/js/tenant-comercial-core.js`

- [ ] **Step 1: Adicionar UI minima de anexo no modal de template**

Inserir no form de `#modal-template` um bloco como este, logo abaixo de `#tpl-conteudo`:

```html
<div class="form-group">
  <label for="tpl-anexo">Anexo opcional</label>
  <input type="file" id="tpl-anexo" accept=".pdf,image/png,image/jpeg,image/webp">
  <input type="hidden" id="tpl-anexo-path">
  <input type="hidden" id="tpl-anexo-nome">
  <input type="hidden" id="tpl-anexo-mime">
  <input type="hidden" id="tpl-anexo-tamanho">
  <div id="tpl-anexo-atual" class="muted small"></div>
  <button type="button" class="btn btn-secondary btn-sm" id="tpl-anexo-remover" style="display:none">Remover anexo</button>
  <small class="muted">Formatos: PDF, PNG, JPG, WEBP. Maximo de 15 MB.</small>
</div>
```

- [ ] **Step 2: Fazer upload assicrono do arquivo antes de salvar o template**

Adicionar em `sistema/cotte-frontend/js/tenant-TemplatesManager.js` funcoes pequenas neste formato:

```js
async function uploadAnexoTemplate(file) {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/tenant/comercial/templates/upload-anexo', formData, true);
}

function preencherCamposAnexo(meta) {
  document.getElementById('tpl-anexo-path').value = meta?.arquivo_path || '';
  document.getElementById('tpl-anexo-nome').value = meta?.arquivo_nome_original || '';
  document.getElementById('tpl-anexo-mime').value = meta?.mime_type || '';
  document.getElementById('tpl-anexo-tamanho').value = meta?.tamanho_bytes || '';
  document.getElementById('tpl-anexo-atual').textContent = meta?.arquivo_nome_original || 'Nenhum anexo selecionado';
  document.getElementById('tpl-anexo-remover').style.display = meta?.arquivo_path ? 'inline-flex' : 'none';
}
```

No fluxo de `salvarTemplate()`, montar o payload incluindo os campos opcionais:

```js
const payload = {
  nome,
  tipo,
  canal,
  assunto,
  conteudo,
  anexo_arquivo_path: document.getElementById('tpl-anexo-path').value || null,
  anexo_nome_original: document.getElementById('tpl-anexo-nome').value || null,
  anexo_mime_type: document.getElementById('tpl-anexo-mime').value || null,
  anexo_tamanho_bytes: Number(document.getElementById('tpl-anexo-tamanho').value || 0) || null,
  remover_anexo: false,
};
```

- [ ] **Step 3: Reidratar o anexo ao editar e mostrar indicacao na listagem**

Ao abrir um template existente, preencher os campos ocultos a partir do `GET /tenant/comercial/templates/{id}` e mostrar um indicador simples na tabela/cards:

```js
const badgeAnexo = template.anexo_nome_original
  ? '<span class="badge badge-info">Com anexo</span>'
  : '';
```

Usar o badge tanto na renderizacao desktop quanto mobile, sem mexer em layout global.

- [ ] **Step 4: Incluir `template_id` no envio de e-mail e WhatsApp**

Em `sistema/cotte-frontend/js/tenant-comercial-mensagens.js`, manter o fluxo atual de preview e acrescentar o id do template selecionado no envio:

```js
const templateId = Number(document.getElementById(`${prefix}-template`).value || 0) || null;
```

No `POST` de WhatsApp:

```js
await api.post(`/tenant/comercial/leads/${leadAtualId}/whatsapp`, {
  mensagem,
  template_id: templateId,
});
```

No `POST` de e-mail:

```js
await api.post(`/tenant/comercial/leads/${leadAtualId}/email`, {
  assunto,
  mensagem,
  template_id: templateId,
});
```

Quando `aplicarTemplate(prefix)` receber preview com `anexo_nome_original`, mostrar uma observacao discreta no modal de envio:

```js
anexoInfoEl.textContent = preview.anexo_nome_original
  ? `Este modelo enviara o anexo: ${preview.anexo_nome_original}`
  : '';
```

- [ ] **Step 5: Garantir que `templatesCache` propague os metadados novos sem regressao**

Em `sistema/cotte-frontend/js/tenant-comercial-core.js`, nao criar cache paralelo. Apenas validar que o carregamento atual continua:

```js
templatesCache = await api.get('/tenant/comercial/templates?ativo=true');
```

Se o front fizer destructuring seletivo em algum ponto, ampliar para manter `anexo_nome_original` e `anexo_arquivo_path`.

- [ ] **Step 6: Validar manualmente o fluxo completo no navegador**

Checklist manual:

```text
1. Abrir Config > Modelos e criar um modelo de e-mail com PDF anexado.
2. Editar o modelo criado e confirmar que o nome do anexo reaparece no modal.
3. Aplicar esse modelo no modal de e-mail de um lead e confirmar que a UI avisa sobre o anexo.
4. Enviar o e-mail de teste e verificar que o anexo chegou.
5. Aplicar um modelo com imagem no WhatsApp e confirmar que a mensagem final inclui o link do anexo.
6. Reabrir a lista de modelos e verificar o badge `Com anexo`.
```

- [ ] **Step 7: Commit**

```bash
git add sistema/cotte-frontend/tenant-comercial.html sistema/cotte-frontend/js/tenant-TemplatesManager.js sistema/cotte-frontend/js/tenant-comercial-mensagens.js sistema/cotte-frontend/js/tenant-comercial-core.js
git commit -m "feat(comercial): support template attachments in tenant frontend"
```

### Task 6: Fechar validacao, regressao e riscos conhecidos

**Files:**
- Test: `sistema/tests/test_tenant_comercial.py`
- Test manual: fluxo em `tenant-comercial.html`

- [ ] **Step 1: Rodar a suite focada do tenant comercial**

Run: `pytest sistema/tests/test_tenant_comercial.py -v`
Expected: suite tenant verde, incluindo templates, envio e upload de anexos.

- [ ] **Step 2: Rodar a suite do comercial global para garantir isolamento de contrato**

Run: `pytest sistema/tests/test_comercial.py -k "template" -v`
Expected: testes do modulo global continuam verdes sem conhecer os campos de anexo do tenant.

- [ ] **Step 3: Verificar rapidamente se nenhum uso do schema global foi alterado por acidente**

Run: `rg -n "TemplateCreate|TemplateUpdate|TemplateOut" sistema/app/routers sistema/app/schemas`
Expected: `app/routers/comercial_templates.py` continua importando os schemas globais antigos; apenas o tenant comercial usa `tenant_comercial_templates.py`.

- [ ] **Step 4: Commit final de validacao**

```bash
git add sistema/tests/test_tenant_comercial.py sistema/tests/test_comercial.py
git commit -m "test(comercial): validate tenant template attachment rollout"
```

## Riscos que o executor deve observar

- `send_email_simples` pode nao aceitar `attachments` por URL; se o provider exigir base64, adapte o helper para baixar ou carregar o binario uma vez no backend, sem mudar o contrato do frontend.
- Alguns provedores de WhatsApp podem encurtar ou bloquear URLs; manter o fallback por link simples evita quebrar o envio atual, mas merece validacao real com o provider configurado da empresa.
- O frontend do tenant pode usar helper `api.post` com comportamento diferente para `FormData`; validar se o terceiro argumento ja sinaliza multipart. Se nao sinalizar, ajustar somente no helper local usado por `TemplatesManager`.
- Se houver templates antigos com `canal="whatsapp"` e anexo PDF, o comportamento combinado continua texto + link; nao tentar promover isso para envio de PDF nativo nesta entrega.

## Melhor ordem de execucao

1. Testes novos.
2. Persistencia e schemas isolados do tenant.
3. Upload dedicado de anexos.
4. Envio por canal com fallback seguro.
5. Frontend do modal e dos envios.
6. Regressao e validacao manual.
