"""
Testes do módulo comercial tenant (CRM por empresa).

Valida:
- CRUD de leads
- Etapas do pipeline
- Propostas
- Dashboard
- Isolamento entre empresas
- Permissões e módulo habilitado
"""

import asyncio
import io
import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import FastAPI, HTTPException

from app.core.auth import criar_token
from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import (
    CanalInteracao,
    CanalTemplate,
    Empresa,
    ModuloSistema,
    Papel,
    Plano,
    PlanoModulo,
    TenantCommercialInteraction,
    TenantCommercialTemplate,
    TenantCommercialLead,
    TenantPipelineEtapa,
    TenantProposta,
    TipoInteracao,
    TipoTemplate,
    Usuario,
)
from app.routers.tenant import (
    comercial_campaigns,
    comercial_dashboard,
    comercial_import,
    comercial_interacoes,
    comercial_leads,
    comercial_pipeline,
    comercial_propostas,
    comercial_propostas_publicas,
    comercial_templates,
)
from app.services import email_service
from app.schemas.schemas import TemplateCreate as SharedTemplateCreate
from tests.asgi_client import SyncASGIClient
from tests.conftest import make_empresa, make_usuario, override_get_db


def _auth_headers(usuario) -> dict[str, str]:
    token = criar_token({"sub": str(usuario.id), "v": int(usuario.token_versao or 1)})
    return {"Authorization": f"Bearer {token}"}


def _tenant_user(empresa, permissoes_papel=None, is_gestor=False):
    user = MagicMock(spec=Usuario)
    user.id = 100
    user.is_superadmin = False
    user.empresa_id = empresa.id
    user.nome = "Vendedor Teste"
    user.email = "vendedor@teste.com"
    user.is_gestor = is_gestor
    user.empresa = empresa
    user.permissoes = {}

    papel = MagicMock(spec=Papel)
    papel.id = 1
    papel.nome = "Papel Teste"
    papel.permissoes = permissoes_papel or ["comercial:leitura", "comercial:escrita"]
    user.papel = papel
    user.papel_id = papel.id
    return user


def _tenant_admin_user(empresa):
    return _tenant_user(
        empresa,
        ["comercial:leitura", "comercial:escrita", "comercial:exclusao", "comercial:admin"],
        is_gestor=True,
    )


def _tenant_readonly_user(empresa):
    return _tenant_user(empresa, ["comercial:leitura"])


@pytest.fixture
def tenant_comercial_http_client(mock_services, setup_database, clean_tables):
    app = FastAPI()
    app.include_router(comercial_templates.router, prefix="/api/v1/tenant/comercial")

    app.dependency_overrides[get_db] = override_get_db

    yield SyncASGIClient(app, raise_app_exceptions=False)

    app.dependency_overrides.clear()


@pytest.fixture
def empresa_com_modulo(db):
    modulo = db.query(ModuloSistema).filter(ModuloSistema.slug == "comercial").first()
    if modulo is None:
        modulo = ModuloSistema(
            nome="Comercial",
            slug="comercial",
            descricao="CRM tenant",
            acoes=["leitura", "escrita", "exclusao", "admin"],
        )
        db.add(modulo)
        db.flush()
    plano = Plano(nome="Plano Comercial", preco_mensal=99.90, ativo=True)
    db.add(plano)
    db.flush()
    if (
        db.query(PlanoModulo)
        .filter(
            PlanoModulo.plano_id == plano.id,
            PlanoModulo.modulo_id == modulo.id,
        )
        .first()
        is None
    ):
        db.add(PlanoModulo(plano_id=plano.id, modulo_id=modulo.id))
    empresa = Empresa(
        nome="Empresa Comercial",
        telefone_operador="5511999990001",
        ativo=True,
        plano_id=plano.id,
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


@pytest.fixture
def empresa_sem_modulo(db):
    plano = Plano(nome="Plano Básico", preco_mensal=19.90, ativo=True)
    empresa = Empresa(
        nome="Empresa sem Comercial",
        telefone_operador="5511999990002",
        ativo=True,
    )
    db.add_all([plano, empresa])
    db.flush()
    empresa.plano_id = plano.id
    db.commit()
    db.refresh(empresa)
    return empresa


def make_tenant_etapa(db, empresa_id, nome="Novo", ordem=1, cor="#3498db"):
    etapa = TenantPipelineEtapa(
        nome=nome,
        empresa_id=empresa_id,
        ordem=ordem,
        cor=cor,
        ativo=True,
    )
    db.add(etapa)
    db.flush()
    return etapa


def make_tenant_lead(db, empresa_id, responsavel_id=None, **overrides):
    if responsavel_id is None:
        email_r = f"lead_resp_{empresa_id}@test.com"
        existente = db.query(Usuario).filter(Usuario.email == email_r).first()
        if existente:
            responsavel_id = existente.id
        else:
            empresa = db.query(Empresa).filter_by(id=empresa_id).first()
            usuario = make_usuario(
                db,
                empresa,
                nome="Lead Responsavel",
                email=email_r,
                is_gestor=False,
                permissoes={"comercial": "escrita"},
            )
            responsavel_id = usuario.id

    etapa = (
        db.query(TenantPipelineEtapa)
        .filter_by(empresa_id=empresa_id, nome="Novo")
        .first()
    )
    if etapa is None:
        etapa = make_tenant_etapa(db, empresa_id=empresa_id, nome="Novo", ordem=1)

    payload = {
        "nome": "Lead Teste",
        "email": "lead@teste.com",
        "telefone": "48999990001",
        "empresa_id": empresa_id,
        "etapa_pipeline_id": etapa.id,
        "ativo": True,
        "responsavel_id": responsavel_id,
    }
    payload.update(overrides)

    lead = TenantCommercialLead(**payload)
    db.add(lead)
    db.flush()
    return lead


def make_tenant_proposta(db, lead_id, empresa_id, **overrides):
    payload = {
        "titulo": "Proposta Teste",
        "lead_id": lead_id,
        "empresa_id": empresa_id,
        "valor_total": 1000.00,
        "status": "rascunho",
    }
    payload.update(overrides)
    proposta = TenantProposta(**payload)
    db.add(proposta)
    db.flush()
    return proposta


def make_tenant_template(db, empresa_id, **overrides):
    payload = {
        "nome": "Template Tenant",
        "empresa_id": empresa_id,
        "tipo": TipoTemplate.EMAIL_COMERCIAL,
        "canal": CanalTemplate.EMAIL,
        "assunto": "Assunto base",
        "conteudo": "Ola {nome_responsavel}",
        "ativo": True,
    }
    payload.update(overrides)

    template = TenantCommercialTemplate(**payload)
    db.add(template)
    db.flush()
    return template


class TestPermissoes:
    def test_exigir_modulo_liberado(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        assert exigir_modulo("comercial")(current_user=user, db=db) == user

    def test_exigir_modulo_bloqueia_sem_recurso(self, db, empresa_sem_modulo):
        user = _tenant_user(empresa_sem_modulo, [])
        with pytest.raises(HTTPException) as exc:
            exigir_modulo("comercial")(current_user=user, db=db)
        assert exc.value.status_code == 403

    def test_exigir_permissao_bloqueia_readonly_em_escrita(self, empresa_com_modulo):
        user = _tenant_readonly_user(empresa_com_modulo)
        with pytest.raises(HTTPException) as exc:
            exigir_permissao("comercial", "escrita")(usuario=user)
        assert exc.value.status_code == 403


class TestTenantLeadsCRUD:
    def test_criar_lead_sucesso(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        payload = comercial_leads.LeadCreate(
            nome="Novo Lead",
            email="novo@lead.com",
            telefone="48999990002",
        )
        lead = comercial_leads.create_lead(payload, db=db, usuario=user)
        assert lead.nome == "Novo Lead"
        assert lead.empresa_id == empresa_com_modulo.id

    def test_listar_leads(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        make_tenant_lead(db, empresa_com_modulo.id, nome="Lead 1")
        make_tenant_lead(db, empresa_com_modulo.id, nome="Lead 2")
        db.commit()
        data = comercial_leads.list_leads(db=db, usuario=user)
        assert data["total"] >= 2

    def test_atualizar_lead(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, nome="Lead Original")
        db.commit()
        updated = comercial_leads.update_lead(
            lead.id,
            comercial_leads.LeadUpdate(nome="Lead Atualizado"),
            db=db,
            usuario=user,
        )
        assert updated.nome == "Lead Atualizado"

    def test_deletar_lead_soft_delete(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, nome="Lead para Deletar")
        db.commit()
        comercial_leads.delete_lead(lead.id, db=db, usuario=user)
        db.refresh(lead)
        assert lead.ativo is False

    def test_mover_lead_entre_etapas(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        etapa1 = make_tenant_etapa(db, empresa_com_modulo.id, nome="Etapa 1", ordem=1)
        etapa2 = make_tenant_etapa(db, empresa_com_modulo.id, nome="Etapa 2", ordem=2)
        lead = make_tenant_lead(db, empresa_com_modulo.id, etapa_pipeline_id=etapa1.id)
        db.commit()
        moved = comercial_leads.move_lead_stage(
            lead.id,
            comercial_leads.MoveEtapaRequest(etapa_id=etapa2.id),
            db=db,
            usuario=user,
        )
        assert moved.etapa_pipeline_id == etapa2.id


class TestTenantPipeline:
    def test_listar_etapas_vazio_cria_padrao(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        etapas = comercial_pipeline.list_etapas(db=db, usuario=user)
        assert len(etapas) >= 1

    def test_criar_etapa(self, db, empresa_com_modulo):
        user = _tenant_admin_user(empresa_com_modulo)
        etapa = comercial_pipeline.create_etapa(
            comercial_pipeline.EtapaCreate(nome="Qualificado", cor="#2ecc71", ordem=5),
            db=db,
            usuario=user,
        )
        assert etapa.nome == "Qualificado"
        assert etapa.empresa_id == empresa_com_modulo.id

    def test_nao_admin_nao_cria_etapa(self, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        with pytest.raises(HTTPException):
            exigir_permissao("comercial", "admin")(usuario=user)


class TestTenantPropostas:
    def test_criar_proposta(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, nome="Lead para Proposta")
        db.commit()
        proposta = comercial_propostas.create_proposta(
            comercial_propostas.PropostaCreate(
                titulo="Proposta Comercial",
                lead_id=lead.id,
                valor_total=5000.00,
                descricao="Proposta de serviços",
            ),
            db=db,
            usuario=user,
        )
        assert proposta.titulo == "Proposta Comercial"
        assert proposta.lead_id == lead.id

    def test_listar_propostas(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id)
        make_tenant_proposta(db, lead.id, empresa_com_modulo.id, titulo="Prop 1")
        make_tenant_proposta(db, lead.id, empresa_com_modulo.id, titulo="Prop 2")
        db.commit()
        data = comercial_propostas.list_propostas(db=db, usuario=user)
        assert data["total"] >= 2

    @pytest.mark.parametrize("canal", ["whatsapp", "email", "ambos"])
    def test_enviar_proposta(self, db, empresa_com_modulo, canal):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id)
        proposta = make_tenant_proposta(db, lead.id, empresa_com_modulo.id)
        db.commit()

        with patch("app.routers.tenant.comercial_propostas.enviar_mensagem_texto", new_callable=MagicMock) as mock_whatsapp:
            with patch("app.routers.tenant.comercial_propostas.send_email_simples", new_callable=MagicMock) as mock_email:
                result = asyncio.run(
                    comercial_propostas.enviar_proposta(
                        proposta.id,
                        comercial_propostas.PropostaEnvioRequest(canal=canal),
                        db=db,
                        usuario=user,
                    )
                )
                assert result["status"] == "enviada"
                if canal in {"whatsapp", "ambos"}:
                    mock_whatsapp.assert_called_once()
                if canal in {"email", "ambos"}:
                    mock_email.assert_called_once()


class TestTenantTemplatesComAnexos:
    @pytest.fixture(autouse=True)
    def _mock_r2_disponivel(self):
        from app.services.template_anexos_service import r2_service as anexo_r2
        with patch.object(anexo_r2, "client", True, create=True):
            yield
    @pytest.mark.parametrize(
        ("filename", "mime_type"),
        [
            ("catalogo.pdf", "application/pdf"),
            ("flyer.png", "image/png"),
        ],
    )
    def test_salvar_upload_template_aceita_pdf_e_imagem(self, empresa_com_modulo, filename, mime_type):
        try:
            from app.services import template_anexos_service
        except ModuleNotFoundError as exc:
            pytest.fail(f"Serviço de anexo de template ausente: {exc}")

        file = SimpleNamespace(
            filename=filename,
            content_type=mime_type,
            file=io.BytesIO(b"anexo-binario"),
        )

        with patch.object(
            template_anexos_service.r2_service,
            "upload_file",
            return_value=f"https://cdn.exemplo.com/{filename}",
        ) as upload_mock:
            meta = template_anexos_service.salvar_upload_template_anexo(
                empresa_com_modulo.id,
                file,
            )

        assert meta == {
            "arquivo_path": f"https://cdn.exemplo.com/{filename}",
            "arquivo_nome_original": filename,
            "mime_type": mime_type,
            "tamanho_bytes": len(b"anexo-binario"),
        }
        assert upload_mock.call_args.kwargs["tipo"] == "templates-anexos"

    def test_salvar_upload_template_sem_content_type_infere_por_extensao(self, empresa_com_modulo):
        from app.services import template_anexos_service

        file = SimpleNamespace(
            filename="banner.png",
            content_type=None,
            file=io.BytesIO(b"conteudo-imagem"),
        )

        with patch.object(
            template_anexos_service.r2_service,
            "upload_file",
            return_value="https://cdn.exemplo.com/banner.png",
        ) as upload_mock:
            meta = template_anexos_service.salvar_upload_template_anexo(
                empresa_com_modulo.id,
                file,
            )

        assert meta == {
            "arquivo_path": "https://cdn.exemplo.com/banner.png",
            "arquivo_nome_original": "banner.png",
            "mime_type": "image/png",
            "tamanho_bytes": len(b"conteudo-imagem"),
        }
        assert upload_mock.call_args.kwargs["content_type"] == "image/png"

    def test_salvar_upload_template_rejeita_content_type_invalido(self, empresa_com_modulo):
        from app.services import template_anexos_service

        file = SimpleNamespace(
            filename="banner.png",
            content_type="application/octet-stream",
            file=io.BytesIO(b"conteudo-imagem"),
        )

        with pytest.raises(HTTPException) as exc:
            template_anexos_service.salvar_upload_template_anexo(empresa_com_modulo.id, file)

        assert exc.value.status_code == 400
        assert "Tipo de arquivo não permitido" in exc.value.detail

    def test_upload_anexo_template_retorna_metadados_via_http(self, tenant_comercial_http_client, db, empresa_com_modulo):
        usuario = make_usuario(
            db,
            empresa_com_modulo,
            email="template-upload-http@teste.com",
            is_gestor=False,
            permissoes={"comercial": "escrita"},
        )
        usuario.token_versao = 1
        db.commit()

        with patch(
            "app.services.template_anexos_service.r2_service.upload_file",
            return_value="https://cdn.exemplo.com/banner.png",
        ) as upload_mock:
            response = tenant_comercial_http_client.post(
                "/api/v1/tenant/comercial/templates/upload-anexo",
                headers=_auth_headers(usuario),
                files={"file": ("banner.png", b"conteudo-imagem", "image/png")},
            )

        assert response.status_code == 200, response.text
        assert response.json() == {
            "arquivo_path": "https://cdn.exemplo.com/banner.png",
            "arquivo_nome_original": "banner.png",
            "mime_type": "image/png",
            "tamanho_bytes": len(b"conteudo-imagem"),
        }
        assert upload_mock.call_args.kwargs["content_type"] == "image/png"

    def test_criar_template_com_metadados_de_anexo(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        request_model = inspect.signature(comercial_templates.create_template).parameters[
            "request"
        ].annotation
        required_fields = {
            "anexo_arquivo_path",
            "anexo_nome_original",
            "anexo_mime_type",
            "anexo_tamanho_bytes",
        }
        assert request_model is not SharedTemplateCreate
        assert required_fields.issubset(request_model.model_fields)

        payload = request_model(
            nome="Template com anexo",
            tipo=TipoTemplate.EMAIL_COMERCIAL,
            canal=CanalTemplate.EMAIL,
            assunto="Proposta comercial",
            conteudo="Segue a proposta em anexo.",
            anexo_arquivo_path=(
                f"https://cdn.exemplo.com/empresas/{empresa_com_modulo.id}/"
                "templates-anexos/proposta.pdf"
            ),
            anexo_nome_original="proposta.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=204800,
        )

        with patch("app.services.template_anexos_service.r2_service.public_url", "https://cdn.exemplo.com"):
            template = asyncio.run(
                comercial_templates.create_template(payload, db=db, current_user=user)
            )

        assert getattr(template, "anexo_arquivo_path", None) == (
            f"https://cdn.exemplo.com/empresas/{empresa_com_modulo.id}/"
            "templates-anexos/proposta.pdf"
        )
        assert getattr(template, "anexo_nome_original", None) == "proposta.pdf"
        assert getattr(template, "anexo_mime_type", None) == "application/pdf"
        assert getattr(template, "anexo_tamanho_bytes", None) == 204800

    def test_criar_template_rejeita_anexo_fora_do_prefixo_esperado(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        request_model = inspect.signature(comercial_templates.create_template).parameters[
            "request"
        ].annotation
        payload = request_model(
            nome="Template com anexo inválido",
            tipo=TipoTemplate.EMAIL_COMERCIAL,
            canal=CanalTemplate.EMAIL,
            assunto="Proposta comercial",
            conteudo="Segue a proposta em anexo.",
            anexo_arquivo_path="/etc/passwd",
            anexo_nome_original="proposta.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=204800,
        )

        with patch("app.services.template_anexos_service.r2_service.public_url", "https://cdn.exemplo.com"):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(comercial_templates.create_template(payload, db=db, current_user=user))

        assert exc.value.status_code == 400
        assert "Anexo inválido" in exc.value.detail

    def test_atualizar_template_com_remover_anexo_limpa_metadados(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        template = make_tenant_template(
            db,
            empresa_com_modulo.id,
            nome="Template com anexo",
            assunto="Proposta comercial",
            conteudo="Segue a proposta em anexo.",
            anexo_arquivo_path=(
                f"https://cdn.exemplo.com/empresas/{empresa_com_modulo.id}/"
                "templates-anexos/proposta.pdf"
            ),
            anexo_nome_original="proposta.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=204800,
        )
        db.commit()

        payload = comercial_templates.TenantTemplateUpdate(
            nome="Template sem anexo",
            remover_anexo=True,
        )

        atualizado = asyncio.run(
            comercial_templates.update_template(template.id, payload, db=db, current_user=user)
        )

        assert atualizado.nome == "Template sem anexo"
        assert atualizado.anexo_arquivo_path is None
        assert atualizado.anexo_nome_original is None
        assert atualizado.anexo_mime_type is None
        assert atualizado.anexo_tamanho_bytes is None

        db.refresh(template)
        assert template.anexo_arquivo_path is None
        assert template.anexo_nome_original is None
        assert template.anexo_mime_type is None
        assert template.anexo_tamanho_bytes is None

    def test_atualizar_template_rejeita_anexo_fora_do_prefixo_esperado(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        template = make_tenant_template(db, empresa_com_modulo.id)
        db.commit()

        payload = comercial_templates.TenantTemplateUpdate(
            anexo_arquivo_path="https://interna.local/segredo.pdf",
            anexo_nome_original="segredo.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=123,
        )

        with patch("app.services.template_anexos_service.r2_service.public_url", "https://cdn.exemplo.com"):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(
                    comercial_templates.update_template(template.id, payload, db=db, current_user=user)
                )

        assert exc.value.status_code == 400
        assert "Anexo inválido" in exc.value.detail

    def test_preview_template_retorna_metadados_do_anexo(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        empresa_id = empresa_com_modulo.id
        lead = make_tenant_lead(
            db,
            empresa_id,
            nome="Maria",
            email="maria@teste.com",
        )
        template = make_tenant_template(
            db,
            empresa_id,
            nome="Template com anexo",
            conteudo="Ola {nome_responsavel}",
        )
        db.commit()
        template_id = template.id
        lead_id = lead.id
        db.expunge_all()

        template_com_anexo = SimpleNamespace(
            id=template_id,
            empresa_id=empresa_id,
            nome="Template com anexo",
            tipo=TipoTemplate.EMAIL_COMERCIAL,
            canal=CanalTemplate.EMAIL,
            assunto="Assunto base",
            conteudo="Ola {nome_responsavel}",
            ativo=True,
            anexo_arquivo_path=(
                f"https://cdn.exemplo.com/empresas/{empresa_id}/templates-anexos/catalogo.pdf"
            ),
            anexo_nome_original="catalogo.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=512000,
        )
        real_query = db.query

        def query_with_template(model):
            if model is TenantCommercialTemplate:
                query = MagicMock()
                query.filter.return_value.first.return_value = template_com_anexo
                return query
            return real_query(model)

        with patch.object(db, "query", side_effect=query_with_template):
            preview = asyncio.run(
                comercial_templates.preview_template(
                    template_id,
                    lead_id,
                    db=db,
                    current_user=user,
                )
            )

        assert "anexo_arquivo_path" not in preview.model_dump()
        assert getattr(preview, "anexo_url", None) == (
            f"https://cdn.exemplo.com/empresas/{empresa_id}/templates-anexos/catalogo.pdf"
        )
        assert getattr(preview, "anexo_nome_original", None) == "catalogo.pdf"
        assert getattr(preview, "anexo_mime_type", None) == "application/pdf"
        assert getattr(preview, "anexo_tamanho_bytes", None) == 512000

    def test_preview_template_http_aceita_lead_id_via_json(
        self,
        tenant_comercial_http_client,
        db,
        empresa_com_modulo,
    ):
        usuario = make_usuario(
            db,
            empresa_com_modulo,
            email="template-preview-http@teste.com",
            is_gestor=False,
            permissoes={"comercial": "escrita"},
        )
        usuario.token_versao = 1
        lead = make_tenant_lead(db, empresa_com_modulo.id, nome="Maria")
        template = make_tenant_template(
            db,
            empresa_com_modulo.id,
            assunto="Oi {nome_responsavel}",
            conteudo="Corpo {nome_responsavel}",
        )
        db.commit()

        response = tenant_comercial_http_client.post(
            f"/api/v1/tenant/comercial/templates/{template.id}/preview",
            headers=_auth_headers(usuario),
            json={"lead_id": lead.id},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["assunto"] == "Oi Maria"
        assert data["conteudo"] == "Corpo Maria"

    def test_enviar_email_com_template_anexado_repassa_attachments(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        empresa_id = empresa_com_modulo.id
        assert "template_id" in comercial_leads.EmailBody.model_fields

        lead = make_tenant_lead(
            db,
            empresa_id,
            nome="Maria",
            email="maria@teste.com",
        )
        template = make_tenant_template(
            db,
            empresa_id,
            nome="Template email com anexo",
        )
        db.commit()
        lead_id = lead.id
        template_id = template.id
        db.expunge_all()

        lead = db.query(TenantCommercialLead).filter_by(id=lead_id).first()
        template_com_anexo = SimpleNamespace(
            id=template_id,
            empresa_id=empresa_id,
            nome="Template email com anexo",
            tipo=TipoTemplate.EMAIL_COMERCIAL,
            canal=CanalTemplate.EMAIL,
            assunto="Assunto base",
            conteudo="Segue a proposta em anexo.",
            ativo=True,
            anexo_arquivo_path=(
                f"https://cdn.exemplo.com/empresas/{empresa_id}/templates-anexos/proposta.pdf"
            ),
            anexo_nome_original="proposta.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=204800,
        )
        real_query = db.query

        def query_with_template(model):
            if model is TenantCommercialTemplate:
                query = MagicMock()
                query.filter.return_value.first.return_value = template_com_anexo
                return query
            return real_query(model)

        body = comercial_leads.EmailBody.model_construct(
            assunto="Proposta comercial",
            mensagem="Segue a proposta em anexo.",
            template_id=template_id,
        )
        assert "template_id" in comercial_leads.EmailBody.model_fields
        assert getattr(body, "template_id", None) == template_id

        with patch(
            "app.routers.tenant.comercial_leads.send_email_simples",
            new_callable=MagicMock,
        ) as mock_email, patch.object(
            comercial_leads, "validar_template_anexo_path", side_effect=lambda path, _: path
        ):
            mock_email.return_value = True

            with patch.object(db, "query", side_effect=query_with_template):
                result = comercial_leads.enviar_email(lead.id, body, db=db, usuario=user)

        assert result["ok"] is True
        assert result["success"] is True
        attachments = mock_email.call_args.kwargs.get("attachments") or []
        assert attachments
        assert any(
            a.get("path")
            == f"https://cdn.exemplo.com/empresas/{empresa_id}/templates-anexos/proposta.pdf"
            for a in attachments
        )
        assert any(a.get("name") == "proposta.pdf" for a in attachments)
        assert any(a.get("mime_type") == "application/pdf" for a in attachments)
        assert any(a.get("size_bytes") == 204800 for a in attachments)

    def test_enviar_email_rejeita_template_legado_com_anexo_invalido(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        empresa_id = empresa_com_modulo.id

        lead = make_tenant_lead(
            db,
            empresa_id,
            nome="Maria",
            email="maria@teste.com",
        )
        template = make_tenant_template(
            db,
            empresa_id,
            nome="Template legado com anexo inválido",
        )
        db.commit()
        lead_id = lead.id
        template_id = template.id
        db.expunge_all()

        lead = db.query(TenantCommercialLead).filter_by(id=lead_id).first()
        template_legado = SimpleNamespace(
            id=template_id,
            empresa_id=empresa_id,
            nome="Template legado com anexo inválido",
            tipo=TipoTemplate.EMAIL_COMERCIAL,
            canal=CanalTemplate.EMAIL,
            assunto="Assunto base",
            conteudo="Segue a proposta em anexo.",
            ativo=True,
            anexo_arquivo_path="/etc/passwd",
            anexo_nome_original="proposta.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=204800,
        )
        real_query = db.query

        def query_with_template(model):
            if model is TenantCommercialTemplate:
                query = MagicMock()
                query.filter.return_value.first.return_value = template_legado
                return query
            return real_query(model)

        body = comercial_leads.EmailBody.model_construct(
            assunto="Proposta comercial",
            mensagem="Segue a proposta em anexo.",
            template_id=template_id,
        )

        with patch(
            "app.routers.tenant.comercial_leads.send_email_simples",
            new_callable=MagicMock,
        ) as mock_email:
            with patch.object(db, "query", side_effect=query_with_template):
                with pytest.raises(HTTPException) as exc:
                    comercial_leads.enviar_email(lead.id, body, db=db, usuario=user)

        assert exc.value.status_code == 400
        assert "Anexo inválido" in exc.value.detail
        mock_email.assert_not_called()

    def test_send_email_simples_aceita_anexo_por_url_publica(self):
        response = httpx.Response(
            200,
            content=b"pdf-content",
            headers={"Content-Type": "application/pdf"},
            request=httpx.Request("GET", "https://cdn.exemplo.com/proposta.pdf"),
        )

        with patch.object(email_service, "email_habilitado", return_value=True), patch.object(
            email_service, "brevo_api_habilitado", return_value=True
        ), patch.object(email_service.httpx, "get", return_value=response) as mock_get, patch.object(
            email_service, "_enviar_via_brevo_api", return_value=(True, None)
        ) as mock_brevo:
            result = email_service.send_email_simples(
                "maria@teste.com",
                "Proposta comercial",
                "Segue em anexo.",
                attachments=[
                    {
                        "path": "https://cdn.exemplo.com/proposta.pdf",
                        "name": "proposta.pdf",
                        "mime_type": "application/pdf",
                    }
                ],
            )

        assert result is True
        mock_get.assert_called_once_with("https://cdn.exemplo.com/proposta.pdf", timeout=30.0)
        attachments = mock_brevo.call_args.kwargs.get("attachments") or []
        assert attachments == [
            {
                "name": "proposta.pdf",
                "content": "cGRmLWNvbnRlbnQ=",
            }
        ]

    def test_send_email_simples_falha_quando_anexo_remoto_nao_pode_ser_baixado(self):
        with patch.object(email_service, "email_habilitado", return_value=True), patch.object(
            email_service, "brevo_api_habilitado", return_value=True
        ), patch.object(
            email_service.httpx,
            "get",
            side_effect=httpx.ConnectError(
                "falha download",
                request=httpx.Request("GET", "https://cdn.exemplo.com/proposta.pdf"),
            ),
        ) as mock_get, patch.object(
            email_service, "_enviar_via_brevo_api", return_value=(True, None)
        ) as mock_brevo:
            result = email_service.send_email_simples(
                "maria@teste.com",
                "Proposta comercial",
                "Segue em anexo.",
                attachments=[
                    {
                        "path": "https://cdn.exemplo.com/proposta.pdf",
                        "name": "proposta.pdf",
                        "mime_type": "application/pdf",
                    }
                ],
            )

        assert result is False
        mock_get.assert_called_once_with("https://cdn.exemplo.com/proposta.pdf", timeout=30.0)
        mock_brevo.assert_not_called()

    def test_enviar_whatsapp_com_template_anexado_inclui_url_na_mensagem(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        empresa_id = empresa_com_modulo.id
        assert "template_id" in comercial_leads.MensagemBody.model_fields

        lead = make_tenant_lead(
            db,
            empresa_id,
            nome="Maria",
            telefone="5511999990001",
        )
        template = make_tenant_template(
            db,
            empresa_id,
            nome="Template whatsapp com anexo",
            tipo=TipoTemplate.MENSAGEM_INICIAL,
            canal=CanalTemplate.WHATSAPP,
        )
        db.commit()
        lead_id = lead.id
        template_id = template.id
        db.expunge_all()

        lead = db.query(TenantCommercialLead).filter_by(id=lead_id).first()
        template_com_anexo = SimpleNamespace(
            id=template_id,
            empresa_id=empresa_id,
            nome="Template whatsapp com anexo",
            tipo=TipoTemplate.MENSAGEM_INICIAL,
            canal=CanalTemplate.WHATSAPP,
            assunto=None,
            conteudo="Segue nosso catalogo.",
            ativo=True,
            anexo_arquivo_path="/media/templates/catalogo.pdf",
            anexo_nome_original="catalogo.pdf",
            anexo_mime_type="application/pdf",
            anexo_tamanho_bytes=512000,
        )
        real_query = db.query

        def query_with_template(model):
            if model is TenantCommercialTemplate:
                query = MagicMock()
                query.filter.return_value.first.return_value = template_com_anexo
                return query
            return real_query(model)

        body = comercial_leads.MensagemBody.model_construct(
            mensagem="Segue nosso catalogo.",
            template_id=template_id,
        )
        assert "template_id" in comercial_leads.MensagemBody.model_fields
        assert getattr(body, "template_id", None) == template_id

        with patch(
            "app.routers.tenant.comercial_leads.enviar_mensagem_texto",
            new_callable=AsyncMock,
        ) as mock_whatsapp:
            mock_whatsapp.return_value = True

            with patch.object(db, "query", side_effect=query_with_template):
                result = asyncio.run(
                    comercial_leads.enviar_whatsapp(lead.id, body, db=db, usuario=user)
                )

        assert result["ok"] is True
        assert result["success"] is True
        assert mock_whatsapp.call_args.args[0] == lead.telefone
        mensagem_final = mock_whatsapp.call_args.args[1]
        assert "Segue nosso catalogo." in mensagem_final
        assert template_com_anexo.anexo_arquivo_path in mensagem_final


class TestTenantDashboard:
    def test_dashboard_retorna_metricas(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        make_tenant_lead(db, empresa_com_modulo.id, nome="Lead 1")
        make_tenant_lead(db, empresa_com_modulo.id, nome="Lead 2")
        db.commit()
        data = comercial_dashboard.get_dashboard(db=db, usuario=user)
        assert data.total_leads >= 2
        assert data.novos >= 0
        assert data.propostas_enviadas >= 0
        assert data.follow_ups_hoje >= 0


class TestTenantIsolation:
    def test_lead_empresa_a_nao_visivel_empresa_b(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        empresa_b = make_empresa(db, nome="Empresa B", plano="pro")
        db.commit()

        lead_a = make_tenant_lead(db, empresa_com_modulo.id, nome="Lead Empresa A")
        lead_b = make_tenant_lead(db, empresa_b.id, nome="Lead Empresa B")
        db.commit()

        data = comercial_leads.list_leads(db=db, usuario=user)
        assert any(item["id"] == lead_a.id for item in data["items"])
        assert all(item["id"] != lead_b.id for item in data["items"])

        with pytest.raises(HTTPException) as exc:
            comercial_leads.get_lead(lead_b.id, db=db, usuario=user)
        assert exc.value.status_code == 404

    def test_etapa_empresa_a_nao_visivel_empresa_b(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        empresa_b = make_empresa(db, nome="Empresa B Etapa", plano="pro")
        db.commit()

        etapa_a = make_tenant_etapa(db, empresa_com_modulo.id, nome="Etapa A")
        etapa_b = make_tenant_etapa(db, empresa_b.id, nome="Etapa B")
        db.commit()

        etapas = comercial_pipeline.list_etapas(db=db, usuario=user)
        assert any(item.id == etapa_a.id for item in etapas)
        assert all(item.id != etapa_b.id for item in etapas)


class TestTenantGuardrails:
    def test_tenant_nao_cria_empresa_do_lead(self):
        with pytest.raises(HTTPException) as exc:
            comercial_leads.tenant_forbidden_criar_empresa(1)
        assert exc.value.status_code == 403

    def test_tenant_nao_reenvia_senha_do_lead(self):
        with pytest.raises(HTTPException) as exc:
            comercial_leads.tenant_forbidden_reenviar_senha(1)
        assert exc.value.status_code == 403


class TestTenantImportacaoLeads:
    def test_importar_lead_salva_endereco_estruturado(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        payload = {
            "metodo": "ia",
            "leads": [
                {
                    "nome_responsavel": "Maria Souza",
                    "nome_empresa": "MS Reformas",
                    "whatsapp": "(11) 99888-7777",
                    "email": "maria@ms.com",
                    "endereco": "Rua A, 123 - Centro",
                }
            ],
        }

        asyncio.run(comercial_leads.importar_leads_tenant(payload, db=db, usuario=user))

        lead = (
            db.query(TenantCommercialLead)
            .filter(TenantCommercialLead.empresa_id == empresa_com_modulo.id)
            .order_by(TenantCommercialLead.id.desc())
            .first()
        )
        assert lead is not None
        assert lead.endereco == "Rua A, 123 - Centro"

    def test_analisar_importacao_normaliza_telefone_br_com_ddi(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        existing = make_tenant_lead(
            db,
            empresa_com_modulo.id,
            telefone="5511998887777",
            email="duplicado@teste.com",
        )
        db.commit()

        fake_response = {
            "items": [
                {
                    "nome_responsavel": "Duplicado",
                    "nome_empresa": "Empresa D",
                    "whatsapp": "+55 (11) 99888-7777",
                    "email": "novo@teste.com",
                }
            ]
        }

        with patch(
            "app.routers.tenant.comercial_leads.analisar_leads",
            new=AsyncMock(return_value=fake_response),
        ):
            result = asyncio.run(
                comercial_leads.analisar_importacao_tenant(
                    {"texto": "Lead para importar"},
                    db=db,
                    usuario=user,
                )
            )

        assert result["items"][0]["whatsapp"] == "5511998887777"
        assert result["items"][0]["duplicado"] is True
        assert existing.id is not None


class TestNovaRespostaWhatsappBadge:
    def test_listagem_nova_resposta_whatsapp_true(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, telefone="5511887766555")
        db.flush()
        lead.whatsapp_conversa_vista_em = datetime.now(timezone.utc) - timedelta(hours=3)
        db.add(
            TenantCommercialInteraction(
                empresa_id=empresa_com_modulo.id,
                lead_id=lead.id,
                tipo=TipoInteracao.WHATSAPP,
                canal=CanalInteracao.WHATSAPP,
                conteudo="Resposta do cliente",
                direcao="recebido",
                criado_em=datetime.now(timezone.utc) - timedelta(minutes=10),
            )
        )
        db.commit()

        data = comercial_leads.list_leads(db=db, usuario=user)
        row = next((x for x in data["items"] if x["id"] == lead.id), None)
        assert row is not None
        assert row.get("nova_resposta_whatsapp") is True

    def test_post_marcar_conversa_lida_zera_badge(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        read_only = _tenant_readonly_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, telefone="5511998877665")
        db.flush()
        lead.whatsapp_conversa_vista_em = datetime.now(timezone.utc) - timedelta(days=1)
        db.add(
            TenantCommercialInteraction(
                empresa_id=empresa_com_modulo.id,
                lead_id=lead.id,
                tipo=TipoInteracao.WHATSAPP,
                canal=CanalInteracao.WHATSAPP,
                conteudo="Nova msg",
                direcao="recebido",
                criado_em=datetime.now(timezone.utc) - timedelta(seconds=30),
            )
        )
        db.commit()

        items = comercial_leads.list_leads(db=db, usuario=user)["items"]
        row_before = next((x for x in items if x["id"] == lead.id), None)
        assert row_before is not None
        assert row_before.get("nova_resposta_whatsapp") is True

        comercial_leads.marcar_whatsapp_conversa_lida(lead.id, db=db, usuario=read_only)
        db.expire_all()

        row = next(
            (x for x in comercial_leads.list_leads(db=db, usuario=user)["items"] if x["id"] == lead.id),
            None,
        )
        assert row is not None
        assert row.get("nova_resposta_whatsapp") is False

    def test_sem_interacao_recebida_flag_false(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, nome="Sem WA recebido")
        db.commit()
        data = comercial_leads.list_leads(db=db, usuario=user)
        row = next((x for x in data["items"] if x["id"] == lead.id), None)
        assert row is not None
        assert row.get("nova_resposta_whatsapp") is False

    def test_vista_nula_com_primeira_resposta_true(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        lead = make_tenant_lead(db, empresa_com_modulo.id, nome="Primeira resposta")
        assert getattr(lead, "whatsapp_conversa_vista_em", None) is None
        db.add(
            TenantCommercialInteraction(
                empresa_id=empresa_com_modulo.id,
                lead_id=lead.id,
                tipo=TipoInteracao.WHATSAPP,
                canal=CanalInteracao.WHATSAPP,
                conteudo="Primeiro oi",
                direcao="recebido",
                criado_em=datetime.now(timezone.utc),
            )
        )
        db.commit()
        data = comercial_leads.list_leads(db=db, usuario=user)
        row = next((x for x in data["items"] if x["id"] == lead.id), None)
        assert row is not None
        assert row.get("nova_resposta_whatsapp") is True
