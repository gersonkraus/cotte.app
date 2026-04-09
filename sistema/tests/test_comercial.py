"""
Testes do módulo Comercial (CRM interno).

Cobre:
- CRUD Segmentos
- CRUD Origens (LeadSources)
- CRUD Templates
- CRUD Leads (criar, atualizar, listar, buscar, filtrar)
- Pipeline: atualizar status com histórico
- Interações: observações, histórico
- WhatsApp e Email (mocked)
- Lembretes: criar, concluir
- Dashboard métricas
- Config: ler e atualizar
- Acesso restrito a superadmin
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.auth import get_superadmin
from app.core.database import get_db
from app.models.models import (
    CommercialLead, CommercialInteraction, CommercialSegment,
    CommercialLeadSource, CommercialTemplate, CommercialReminder,
    CommercialConfig, StatusPipeline, Usuario,
)
from tests.conftest import (
    TestingSessionLocal, override_get_db, make_empresa, make_usuario,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _superadmin_user():
    """Retorna um objeto que simula superadmin para override de dependência."""
    u = MagicMock(spec=Usuario)
    u.id = 999
    u.is_superadmin = True
    u.nome = "Admin Teste"
    u.email = "admin@teste.com"
    return u


def _non_admin_user():
    u = MagicMock(spec=Usuario)
    u.id = 1
    u.is_superadmin = False
    return u


@pytest.fixture
def admin_client(mock_services):
    """TestClient autenticado como superadmin."""
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_superadmin] = lambda: _superadmin_user()

    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def nonadmin_client(mock_services):
    """TestClient sem permissão de superadmin (dependência não substituída)."""
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    # NÃO override get_superadmin — vai exigir token real

    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def make_segmento(db, nome="Instalador de Ar", ativo=True):
    s = CommercialSegment(nome=nome, ativo=ativo)
    db.add(s)
    db.flush()
    return s


def make_origem(db, nome="Site", ativo=True):
    o = CommercialLeadSource(nome=nome, ativo=ativo)
    db.add(o)
    db.flush()
    return o


def make_lead(db, segmento=None, origem=None, **overrides):
    defaults = dict(
        nome_responsavel="João Silva",
        nome_empresa="Empresa ABC",
        whatsapp="5548999990001",
        email="joao@abc.com",
        cidade="Florianópolis",
        status_pipeline=StatusPipeline.NOVO,
        ativo=True,
    )
    defaults.update(overrides)
    if segmento:
        defaults["segmento_id"] = segmento.id
    if origem:
        defaults["origem_lead_id"] = origem.id
    lead = CommercialLead(**defaults)
    db.add(lead)
    db.flush()
    db.commit()
    return lead


def make_template(db, **overrides):
    defaults = dict(
        nome="Template Teste",
        tipo="mensagem_inicial",
        canal="whatsapp",
        conteudo="Olá {{nome}}, tudo bem?",
        ativo=True,
    )
    defaults.update(overrides)
    t = CommercialTemplate(**defaults)
    db.add(t)
    db.flush()
    return t


# ═══════════════════════════════════════════════════════════════════════════════
# SEGMENTOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSegmentos:
    def test_criar_segmento(self, admin_client):
        r = admin_client.post("/api/v1/comercial/segmentos", json={"nome": "Eletricista"})
        assert r.status_code == 201
        assert r.json()["nome"] == "Eletricista"
        assert r.json()["ativo"] is True

    def test_listar_segmentos(self, admin_client, db):
        make_segmento(db, "Pintor")
        make_segmento(db, "Encanador")
        db.commit()
        r = admin_client.get("/api/v1/comercial/segmentos")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_atualizar_segmento(self, admin_client, db):
        s = make_segmento(db, "Antigo")
        db.commit()
        r = admin_client.patch(f"/api/v1/comercial/segmentos/{s.id}", json={"nome": "Novo Nome"})
        assert r.status_code == 200
        assert r.json()["nome"] == "Novo Nome"

    def test_desativar_segmento(self, admin_client, db):
        s = make_segmento(db, "Temp")
        db.commit()
        r = admin_client.patch(f"/api/v1/comercial/segmentos/{s.id}", json={"ativo": False})
        assert r.status_code == 200
        assert r.json()["ativo"] is False

    def test_segmento_duplicado_retorna_erro(self, admin_client, db):
        make_segmento(db, "Único")
        db.commit()
        r = admin_client.post("/api/v1/comercial/segmentos", json={"nome": "Único"})
        assert r.status_code in (400, 409)


# ═══════════════════════════════════════════════════════════════════════════════
# ORIGENS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrigens:
    def test_criar_origem(self, admin_client):
        r = admin_client.post("/api/v1/comercial/origens", json={"nome": "Google Ads"})
        assert r.status_code == 201
        assert r.json()["nome"] == "Google Ads"

    def test_listar_origens(self, admin_client, db):
        make_origem(db, "Indicação")
        db.commit()
        r = admin_client.get("/api/v1/comercial/origens")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_atualizar_origem(self, admin_client, db):
        o = make_origem(db, "Velho")
        db.commit()
        r = admin_client.patch(f"/api/v1/comercial/origens/{o.id}", json={"nome": "Atualizado"})
        assert r.status_code == 200
        assert r.json()["nome"] == "Atualizado"


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplates:
    def test_criar_template(self, admin_client):
        r = admin_client.post("/api/v1/comercial/templates", json={
            "nome": "Boas-vindas",
            "tipo": "mensagem_inicial",
            "canal": "whatsapp",
            "conteudo": "Olá {{nome}}, bem-vindo!",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nome"] == "Boas-vindas"
        assert data["ativo"] is True

    def test_listar_templates(self, admin_client, db):
        make_template(db)
        db.commit()
        r = admin_client.get("/api/v1/comercial/templates")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_atualizar_template(self, admin_client, db):
        t = make_template(db)
        db.commit()
        r = admin_client.patch(f"/api/v1/comercial/templates/{t.id}", json={"nome": "Renomeado"})
        assert r.status_code == 200
        assert r.json()["nome"] == "Renomeado"

    def test_excluir_template(self, admin_client, db):
        t = make_template(db, nome="Para Excluir")
        db.commit()
        r = admin_client.delete(f"/api/v1/comercial/templates/{t.id}")
        assert r.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# LEADS CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestLeadsCRUD:
    def test_criar_lead(self, admin_client, db):
        seg = make_segmento(db, "Ar Condicionado")
        ori = make_origem(db, "Site")
        db.commit()
        r = admin_client.post("/api/v1/comercial/leads", json={
            "nome_responsavel": "Maria Costa",
            "nome_empresa": "Cool Ar",
            "whatsapp": "5548999001234",
            "email": "maria@coolar.com",
            "segmento_id": seg.id,
            "origem_lead_id": ori.id,
            "interesse_plano": "pro",
            "valor_proposto": 299.90,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nome_empresa"] == "Cool Ar"
        assert data["status_pipeline"] == "novo"

    def test_criar_lead_sem_contato_retorna_erro(self, admin_client):
        r = admin_client.post("/api/v1/comercial/leads", json={
            "nome_responsavel": "Sem Contato",
            "nome_empresa": "Empresa X",
        })
        assert r.status_code == 400

    def test_listar_leads(self, admin_client, db):
        make_lead(db)
        r = admin_client.get("/api/v1/comercial/leads")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data or isinstance(data, list)

    def test_buscar_lead_por_nome(self, admin_client, db):
        make_lead(db, nome_empresa="Busca Especial")
        r = admin_client.get("/api/v1/comercial/leads?search=Busca+Especial")
        assert r.status_code == 200
        data = r.json()
        items = data.get("items", data)
        assert any("Busca Especial" in l.get("nome_empresa", "") for l in items)

    def test_filtrar_leads_por_status(self, admin_client, db):
        make_lead(db, nome_empresa="Lead Novo", status_pipeline=StatusPipeline.NOVO)
        make_lead(db, nome_empresa="Lead Ganho", status_pipeline=StatusPipeline.FECHADO_GANHO)
        r = admin_client.get("/api/v1/comercial/leads?status=novo")
        assert r.status_code == 200
        items = r.json().get("items", r.json())
        for l in items:
            assert l["status_pipeline"] == "novo"

    def test_filtrar_leads_follow_up_hoje(self, admin_client, db):
        from datetime import datetime, timedelta, timezone

        passado = datetime.now(timezone.utc) - timedelta(days=1)
        futuro = datetime.now(timezone.utc) + timedelta(days=7)
        make_lead(
            db,
            nome_empresa="FU Vencido",
            status_pipeline=StatusPipeline.NEGOCIACAO,
            proximo_contato_em=passado,
        )
        make_lead(
            db,
            nome_empresa="FU Futuro",
            status_pipeline=StatusPipeline.NEGOCIACAO,
            proximo_contato_em=futuro,
        )
        make_lead(
            db,
            nome_empresa="FU Ganho",
            status_pipeline=StatusPipeline.FECHADO_GANHO,
            proximo_contato_em=passado,
        )
        r = admin_client.get("/api/v1/comercial/leads?follow_up_hoje=true")
        assert r.status_code == 200
        items = r.json()["items"]
        nomes = {l["nome_empresa"] for l in items}
        assert "FU Vencido" in nomes
        assert "FU Futuro" not in nomes
        assert "FU Ganho" not in nomes

    def test_obter_lead_individual(self, admin_client, db):
        lead = make_lead(db)
        r = admin_client.get(f"/api/v1/comercial/leads/{lead.id}")
        assert r.status_code == 200
        assert r.json()["id"] == lead.id

    def test_atualizar_lead(self, admin_client, db):
        lead = make_lead(db)
        r = admin_client.patch(f"/api/v1/comercial/leads/{lead.id}", json={
            "nome_empresa": "Novo Nome Corp",
            "cidade": "São Paulo",
        })
        assert r.status_code == 200
        assert r.json()["nome_empresa"] == "Novo Nome Corp"

    def test_lead_inexistente_retorna_404(self, admin_client):
        r = admin_client.get("/api/v1/comercial/leads/99999")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipeline:
    def test_atualizar_status(self, admin_client, db):
        lead = make_lead(db, status_pipeline=StatusPipeline.NOVO)
        r = admin_client.patch(f"/api/v1/comercial/leads/{lead.id}/status", json={
            "status": "contato_iniciado"
        })
        assert r.status_code == 200
        assert r.json()["status_pipeline"] == "contato_iniciado"

    def test_mudanca_status_cria_interacao(self, admin_client, db):
        lead = make_lead(db, status_pipeline=StatusPipeline.NOVO)
        admin_client.patch(f"/api/v1/comercial/leads/{lead.id}/status", json={
            "status": "proposta_enviada"
        })
        r = admin_client.get(f"/api/v1/comercial/leads/{lead.id}/interactions")
        assert r.status_code == 200
        interacoes = r.json()
        assert any("status" in (i.get("tipo", "") or "").lower() for i in interacoes)


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVAÇÕES E INTERAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservacoes:
    def test_adicionar_observacao(self, admin_client, db):
        lead = make_lead(db)
        r = admin_client.post(f"/api/v1/comercial/leads/{lead.id}/observacao", json={
            "conteudo": "Lead muito interessado no plano Pro"
        })
        assert r.status_code == 200

    def test_listar_interacoes(self, admin_client, db):
        lead = make_lead(db)
        admin_client.post(f"/api/v1/comercial/leads/{lead.id}/observacao", json={
            "conteudo": "Primeira observação"
        })
        r = admin_client.get(f"/api/v1/comercial/leads/{lead.id}/interactions")
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# WHATSAPP E EMAIL (mocked)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMensagens:
    @patch(
        "app.routers.comercial_interacoes.enviar_mensagem_texto",
        new_callable=AsyncMock,
        return_value=True,
    )
    def test_enviar_whatsapp(self, mock_wa, admin_client, db):
        lead = make_lead(db, whatsapp="5548999990001")
        r = admin_client.post(f"/api/v1/comercial/leads/{lead.id}/whatsapp", json={
            "mensagem": "Olá, tudo bem?"
        })
        assert r.status_code == 200

    @patch(
        "app.routers.comercial_interacoes.enviar_mensagem_texto",
        new_callable=AsyncMock,
        return_value=True,
    )
    def test_enviar_whatsapp_sem_numero_retorna_erro(self, mock_wa, admin_client, db):
        lead = make_lead(db, whatsapp=None)
        r = admin_client.post(f"/api/v1/comercial/leads/{lead.id}/whatsapp", json={
            "mensagem": "Olá"
        })
        assert r.status_code == 400

    @patch(
        "app.routers.comercial_interacoes.send_email_simples", return_value=True
    )
    def test_enviar_email(self, mock_email, admin_client, db):
        lead = make_lead(db, email="teste@example.com")
        r = admin_client.post(f"/api/v1/comercial/leads/{lead.id}/email", json={
            "assunto": "Proposta Comercial",
            "mensagem": "Segue nossa proposta."
        })
        assert r.status_code == 200

    @patch(
        "app.routers.comercial_interacoes.send_email_simples", return_value=False
    )
    def test_enviar_email_falha_transporte_retorna_503(self, mock_email, admin_client, db):
        lead = make_lead(db, email="teste@example.com")
        r = admin_client.post(f"/api/v1/comercial/leads/{lead.id}/email", json={
            "assunto": "Teste",
            "mensagem": "Corpo"
        })
        assert r.status_code == 503

    @patch(
        "app.routers.comercial_interacoes.send_email_simples", return_value=True
    )
    def test_enviar_email_sem_email_retorna_erro(self, mock_email, admin_client, db):
        lead = make_lead(db, email=None)
        r = admin_client.post(f"/api/v1/comercial/leads/{lead.id}/email", json={
            "assunto": "Teste",
            "mensagem": "Teste"
        })
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# LEMBRETES
# ═══════════════════════════════════════════════════════════════════════════════

class TestLembretes:
    def test_criar_lembrete(self, admin_client, db):
        lead = make_lead(db)
        r = admin_client.post("/api/v1/comercial/lembretes", json={
            "lead_id": lead.id,
            "titulo": "Ligar amanhã",
            "data_hora": "2025-12-01T10:00:00",
            "canal_sugerido": "whatsapp",
        })
        assert r.status_code == 201
        assert r.json()["titulo"] == "Ligar amanhã"

    def test_listar_lembretes(self, admin_client, db):
        lead = make_lead(db)
        admin_client.post("/api/v1/comercial/lembretes", json={
            "lead_id": lead.id,
            "titulo": "Acompanhar",
            "data_hora": "2025-12-15T09:00:00",
        })
        r = admin_client.get("/api/v1/comercial/lembretes")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_concluir_lembrete(self, admin_client, db):
        lead = make_lead(db)
        resp = admin_client.post("/api/v1/comercial/lembretes", json={
            "lead_id": lead.id,
            "titulo": "Para concluir",
            "data_hora": "2025-11-01T08:00:00",
        })
        lemb_id = resp.json()["id"]
        r = admin_client.post(f"/api/v1/comercial/lembretes/{lemb_id}/concluir")
        assert r.status_code == 200
        assert r.json()["status"] in ("concluido", "CONCLUIDO")


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboard:
    def test_dashboard_retorna_metricas(self, admin_client, db):
        make_lead(db, status_pipeline=StatusPipeline.NOVO)
        make_lead(db, nome_empresa="Outra", status_pipeline=StatusPipeline.FECHADO_GANHO)
        r = admin_client.get("/api/v1/comercial/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "novos" in data
        assert "fechados_ganho" in data
        assert "follow_ups_hoje" in data
        assert "empresas_em_trial" in data

    def test_leads_recentes(self, admin_client, db):
        make_lead(db)
        r = admin_client.get("/api/v1/comercial/leads/recentes?limit=3")
        assert r.status_code == 200

    def test_follow_ups_hoje(self, admin_client, db):
        r = admin_client.get("/api/v1/comercial/leads/follow-ups-hoje")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_obter_config(self, admin_client):
        r = admin_client.get("/api/v1/comercial/config")
        assert r.status_code == 200

    def test_atualizar_config(self, admin_client):
        r = admin_client.patch("/api/v1/comercial/config", json={
            "link_demo": "https://demo.cotte.app",
            "canal_preferencial": "whatsapp",
        })
        assert r.status_code == 200
        assert r.json()["link_demo"] == "https://demo.cotte.app"


# ═══════════════════════════════════════════════════════════════════════════════
# ACESSO RESTRITO
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcessoRestrito:
    def test_sem_token_retorna_401(self, nonadmin_client):
        r = nonadmin_client.get("/api/v1/comercial/dashboard")
        assert r.status_code in (401, 403)

    def test_sem_token_leads_retorna_401(self, nonadmin_client):
        r = nonadmin_client.get("/api/v1/comercial/leads")
        assert r.status_code in (401, 403)

    def test_sem_token_config_retorna_401(self, nonadmin_client):
        r = nonadmin_client.get("/api/v1/comercial/config")
        assert r.status_code in (401, 403)
