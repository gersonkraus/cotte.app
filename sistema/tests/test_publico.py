"""
Testes dos endpoints públicos (sem autenticação).

Cobre:
- GET /o/{link} — visualizar orçamento
- POST /o/{link}/aceitar — aceite digital
- POST /o/{link}/recusar — recusa digital
- POST /o/{link}/ajuste  — solicitação de ajuste
- Bloqueio de ações em status finais (já aprovado, já recusado, expirado)
- Criação de notificações in-app para cada evento
"""
import pytest
from app.models.models import Notificacao, StatusOrcamento
from tests.conftest import make_cliente, make_empresa, make_orcamento, make_usuario


class TestVerOrcamentoPublico:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp)
        self.orc = make_orcamento(db, emp, cli, usr, status=StatusOrcamento.ENVIADO,
                                   link_publico="link-teste-abc123")
        self.db = db

    def test_retorna_dados_do_orcamento(self, http_client):
        r = http_client.get("/o/link-teste-abc123")
        assert r.status_code == 200
        data = r.json()
        assert float(data["total"]) == 500.0
        assert data["numero"] == "ORC-1-26"
        assert data["status"] == "enviado"

    def test_link_invalido_retorna_404(self, http_client):
        r = http_client.get("/o/link-que-nao-existe")
        assert r.status_code == 404

    def test_incrementa_visualizacoes(self, http_client, db):
        http_client.get("/o/link-teste-abc123")
        http_client.get("/o/link-teste-abc123")

        db.expire_all()
        from app.models.models import Orcamento
        orc = db.query(Orcamento).get(self.orc.id)
        assert orc.visualizacoes == 2

    def test_registra_primeira_visualizacao(self, http_client, db):
        assert self.orc.visualizado_em is None

        http_client.get("/o/link-teste-abc123")

        db.expire_all()
        from app.models.models import Orcamento
        orc = db.query(Orcamento).get(self.orc.id)
        assert orc.visualizado_em is not None


class TestAceitarOrcamento:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp)
        self.orc_enviado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.ENVIADO,
            link_publico="link-aceite-001",
        )
        self.orc_aprovado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.APROVADO,
            link_publico="link-ja-aprovado",
            numero="ORC-2-26",
        )
        self.orc_recusado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.RECUSADO,
            link_publico="link-ja-recusado",
            numero="ORC-3-26",
        )
        self.orc_expirado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.EXPIRADO,
            link_publico="link-expirado",
            numero="ORC-4-26",
        )

    def test_aceite_com_nome_aprova(self, http_client, db):
        r = http_client.post("/o/link-aceite-001/aceitar", json={"nome": "João Silva"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "aprovado"
        assert data["aceite_nome"] == "João Silva"

    def test_aceite_sem_nome_retorna_400(self, http_client):
        r = http_client.post("/o/link-aceite-001/aceitar", json={"nome": "   "})
        assert r.status_code == 400

    def test_aceite_com_mensagem_opcional(self, http_client):
        r = http_client.post("/o/link-aceite-001/aceitar",
                        json={"nome": "Maria", "mensagem": "Pode começar na segunda"})
        assert r.status_code == 200
        assert r.json()["aceite_mensagem"] == "Pode começar na segunda"

    def test_nao_pode_aceitar_ja_aprovado(self, http_client):
        r = http_client.post("/o/link-ja-aprovado/aceitar", json={"nome": "João"})
        assert r.status_code == 400
        assert "aceito" in r.json()["detail"].lower()

    def test_nao_pode_aceitar_ja_recusado(self, http_client):
        r = http_client.post("/o/link-ja-recusado/aceitar", json={"nome": "João"})
        assert r.status_code == 400
        assert "recusado" in r.json()["detail"].lower()

    def test_nao_pode_aceitar_expirado(self, http_client):
        r = http_client.post("/o/link-expirado/aceitar", json={"nome": "João"})
        assert r.status_code == 400
        assert "expirado" in r.json()["detail"].lower()

    def test_link_invalido_retorna_404(self, http_client):
        r = http_client.post("/o/link-nao-existe/aceitar", json={"nome": "João"})
        assert r.status_code == 404


class TestRecusarOrcamento:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp)
        self.orc = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.ENVIADO,
            link_publico="link-recusa-001",
        )
        self.orc_aprovado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.APROVADO,
            link_publico="link-recusa-ja-aprovado",
            numero="ORC-2-26",
        )

    def test_recusa_sem_motivo(self, http_client, db):
        r = http_client.post("/o/link-recusa-001/recusar", json={})
        assert r.status_code == 200
        assert r.json()["status"] == "recusado"

    def test_recusa_com_motivo(self, http_client, db):
        r = http_client.post("/o/link-recusa-001/recusar", json={"motivo": "Preço alto"})
        assert r.status_code == 200
        assert r.json()["recusa_motivo"] == "Preço alto"

    def test_nao_pode_recusar_ja_aprovado(self, http_client):
        r = http_client.post("/o/link-recusa-ja-aprovado/recusar", json={})
        assert r.status_code == 400

    def test_link_invalido_retorna_404(self, http_client):
        r = http_client.post("/o/link-nao-existe/recusar", json={})
        assert r.status_code == 404


class TestNotificacoesInApp:
    """Verifica que cada evento público cria a Notificacao correta no banco."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp)
        self.orc_aceite = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.ENVIADO,
            link_publico="notif-aceite-link",
            numero="ORC-10-26",
        )
        self.orc_recusa = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.ENVIADO,
            link_publico="notif-recusa-link",
            numero="ORC-11-26",
        )
        self.orc_ajuste = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.ENVIADO,
            link_publico="notif-ajuste-link",
            numero="ORC-12-26",
        )
        self.db = db

    def test_aceite_cria_notificacao_aprovado(self, http_client, db):
        http_client.post("/o/notif-aceite-link/aceitar", json={"nome": "Carlos"})
        notif = db.query(Notificacao).filter(
            Notificacao.orcamento_id == self.orc_aceite.id,
            Notificacao.tipo == "aprovado",
        ).first()
        assert notif is not None
        assert "Carlos" in notif.mensagem

    def test_recusa_cria_notificacao_recusado(self, http_client, db):
        http_client.post("/o/notif-recusa-link/recusar", json={"motivo": "Preço alto"})
        notif = db.query(Notificacao).filter(
            Notificacao.orcamento_id == self.orc_recusa.id,
            Notificacao.tipo == "recusado",
        ).first()
        assert notif is not None
        assert "Preço alto" in notif.mensagem

    def test_ajuste_cria_notificacao_ajuste(self, http_client, db):
        http_client.post("/o/notif-ajuste-link/ajuste", json={"mensagem": "Quero 3 unidades"})
        notif = db.query(Notificacao).filter(
            Notificacao.orcamento_id == self.orc_ajuste.id,
            Notificacao.tipo == "ajuste",
        ).first()
        assert notif is not None
        assert "Quero 3 unidades" in notif.mensagem


class TestSolicitarAjuste:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp)
        self.orc = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.ENVIADO,
            link_publico="link-ajuste-001",
        )
        self.orc_aprovado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.APROVADO,
            link_publico="link-ajuste-aprovado",
            numero="ORC-2-26",
        )
        self.orc_recusado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.RECUSADO,
            link_publico="link-ajuste-recusado",
            numero="ORC-3-26",
        )
        self.orc_expirado = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.EXPIRADO,
            link_publico="link-ajuste-expirado",
            numero="ORC-4-26",
        )
        self.orc_rascunho = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.RASCUNHO,
            link_publico="link-ajuste-rascunho",
            numero="ORC-5-26",
        )

    def test_ajuste_retorna_ok(self, http_client):
        r = http_client.post("/o/link-ajuste-001/ajuste", json={"mensagem": "Quero mais 2 unidades"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_mensagem_vazia_retorna_400(self, http_client):
        r = http_client.post("/o/link-ajuste-001/ajuste", json={"mensagem": "   "})
        assert r.status_code == 400

    def test_nao_pode_ajustar_aprovado(self, http_client):
        r = http_client.post("/o/link-ajuste-aprovado/ajuste", json={"mensagem": "Quero mudar"})
        assert r.status_code == 400

    def test_nao_pode_ajustar_recusado(self, http_client):
        r = http_client.post("/o/link-ajuste-recusado/ajuste", json={"mensagem": "Mudei de ideia"})
        assert r.status_code == 400

    def test_nao_pode_ajustar_expirado(self, http_client):
        r = http_client.post("/o/link-ajuste-expirado/ajuste", json={"mensagem": "Pode aceitar?"})
        assert r.status_code == 400

    def test_pode_ajustar_rascunho(self, http_client):
        r = http_client.post("/o/link-ajuste-rascunho/ajuste", json={"mensagem": "Ajuste no rascunho"})
        assert r.status_code == 200

    def test_link_invalido_retorna_404(self, http_client):
        r = http_client.post("/o/link-nao-existe/ajuste", json={"mensagem": "teste"})
        assert r.status_code == 404


class TestRateLimiting:
    """SEC-02: endpoints públicos de escrita devem retornar 429 após exceder o limite."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp)
        make_orcamento(db, emp, cli, usr, status=StatusOrcamento.ENVIADO,
                       link_publico="rl-link-001", numero="ORC-RL-1")
        make_orcamento(db, emp, cli, usr, status=StatusOrcamento.ENVIADO,
                       link_publico="rl-link-002", numero="ORC-RL-2")
        make_orcamento(db, emp, cli, usr, status=StatusOrcamento.ENVIADO,
                       link_publico="rl-link-003", numero="ORC-RL-3")

    def _exhaust_limit(self, http_client, url, body, limit=10):
        """Dispara `limit` requisições para esgotar o rate limit."""
        for _ in range(limit):
            http_client.post(url, json=body)

    def test_aceitar_retorna_429_apos_limite(self, http_client):
        from app.services import rate_limit_service
        from unittest.mock import patch

        call_count = 0

        def fake_check(key):
            nonlocal call_count
            call_count += 1
            from app.services.rate_limit_service import RateLimitResult
            # Bloqueia a partir da 11ª chamada
            if call_count > 10:
                return RateLimitResult(allowed=False, retry_after_seconds=300)
            return RateLimitResult(allowed=True)

        with patch.object(rate_limit_service.public_endpoint_rate_limiter, "check", side_effect=fake_check):
            responses = [
                http_client.post("/o/rl-link-001/aceitar", json={"nome": f"User{i}"})
                for i in range(12)
            ]

        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes, "Deve retornar 429 após exceder o limite"

    def test_ajuste_retorna_429_apos_limite(self, http_client):
        from app.services import rate_limit_service
        from unittest.mock import patch
        from app.services.rate_limit_service import RateLimitResult

        with patch.object(
            rate_limit_service.public_endpoint_rate_limiter, "check",
            return_value=RateLimitResult(allowed=False, retry_after_seconds=300),
        ):
            r = http_client.post("/o/rl-link-002/ajuste", json={"mensagem": "teste"})

        assert r.status_code == 429
        assert "Retry-After" in r.headers

    def test_recusar_retorna_429_apos_limite(self, http_client):
        from app.services import rate_limit_service
        from unittest.mock import patch
        from app.services.rate_limit_service import RateLimitResult

        with patch.object(
            rate_limit_service.public_endpoint_rate_limiter, "check",
            return_value=RateLimitResult(allowed=False, retry_after_seconds=300),
        ):
            r = http_client.post("/o/rl-link-003/recusar", json={})

        assert r.status_code == 429
        assert "Muitas tentativas" in r.json()["detail"]

    def test_get_nao_tem_rate_limit(self, http_client):
        """Leitura pública (GET) não deve ser bloqueada por rate limit."""
        from app.services import rate_limit_service
        from unittest.mock import patch
        from app.services.rate_limit_service import RateLimitResult

        # Mesmo que o limiter bloqueie, o GET não deve ser afetado (não chama o limiter)
        with patch.object(
            rate_limit_service.public_endpoint_rate_limiter, "check",
            return_value=RateLimitResult(allowed=False, retry_after_seconds=300),
        ):
            r = http_client.get("/o/rl-link-001")

        assert r.status_code == 200


class TestBaixarPDFPublico:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp)
        self.orc = make_orcamento(
            db, emp, cli, usr,
            status=StatusOrcamento.ENVIADO,
            link_publico="link-pdf-001",
        )

    def test_retorna_pdf(self, http_client):
        from unittest.mock import patch
        with patch("app.routers.publico.gerar_pdf_orcamento", return_value=b"%PDF-fake"):
            r = http_client.get("/o/link-pdf-001/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    def test_pdf_link_invalido_retorna_404(self, http_client):
        r = http_client.get("/o/link-nao-existe/pdf")
        assert r.status_code == 404
