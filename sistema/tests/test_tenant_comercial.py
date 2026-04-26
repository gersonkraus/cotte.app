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
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.auth import exigir_modulo, exigir_permissao
from app.models.models import (
    Empresa,
    ModuloSistema,
    Papel,
    Plano,
    PlanoModulo,
    TenantCommercialLead,
    TenantPipelineEtapa,
    TenantProposta,
    Usuario,
)
from app.routers.tenant import comercial_dashboard, comercial_leads, comercial_pipeline, comercial_propostas
from tests.conftest import make_empresa, make_usuario


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
def empresa_com_modulo(db):
    modulo = ModuloSistema(
        nome="Comercial",
        slug="comercial",
        descricao="CRM tenant",
        acoes=["leitura", "escrita", "exclusao", "admin"],
    )
    plano = Plano(nome="Plano Comercial", preco_mensal=99.90, ativo=True)
    db.add_all([modulo, plano])
    db.flush()
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
        empresa = db.query(Empresa).filter_by(id=empresa_id).first()
        usuario = make_usuario(
            db,
            empresa,
            nome="Lead Responsavel",
            email=f"lead_resp_{empresa_id}@test.com",
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


class TestTenantDashboard:
    def test_dashboard_retorna_metricas(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        make_tenant_lead(db, empresa_com_modulo.id, nome="Lead 1")
        make_tenant_lead(db, empresa_com_modulo.id, nome="Lead 2")
        db.commit()
        data = comercial_dashboard.get_dashboard(db=db, usuario=user)
        assert data["total_leads"] >= 2
        assert "leads_por_etapa" in data
        assert "leads_novos_hoje" in data
        assert "leads_recentes" in data


class TestTenantIsolation:
    def test_lead_empresa_a_nao_visivel_empresa_b(self, db, empresa_com_modulo):
        user = _tenant_user(empresa_com_modulo)
        empresa_b = make_empresa(db, nome="Empresa B", plano="pro")
        db.commit()

        lead_a = make_tenant_lead(db, empresa_com_modulo.id, nome="Lead Empresa A")
        lead_b = make_tenant_lead(db, empresa_b.id, nome="Lead Empresa B")
        db.commit()

        data = comercial_leads.list_leads(db=db, usuario=user)
        assert any(item.id == lead_a.id for item in data["items"])
        assert all(item.id != lead_b.id for item in data["items"])

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
