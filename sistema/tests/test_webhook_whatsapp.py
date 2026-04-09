"""
Testes do webhook WhatsApp — endpoints mais críticos do COTTE.

Cobre:
- Ignorar mensagens próprias, grupos e sem texto
- Aprovação de orçamento via "ACEITO"
- Recusa de orçamento via "RECUSO"/"NÃO"
- Cenários de cliente/orçamento não encontrado
- Diferença de payload Z-API vs Evolution
- Rate limiting no webhook e no /interpretar
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.models import StatusOrcamento
from app.services.rate_limit_service import RateLimitResult
from tests.conftest import make_cliente, make_empresa, make_orcamento, make_usuario

ZAPI_HEADERS = {"Client-Token": "test-zapi-client-token"}
EVOLUTION_HEADERS = {"apikey": "test-evolution-api-key"}


# ── Payloads Z-API ────────────────────────────────────────────────────────

def zapi_payload(phone: str, text: str, from_me=False, is_group=False):
    return {
        "phone": phone,
        "isGroup": is_group,
        "isNewsletter": False,
        "fromMe": from_me,
        "text": {"message": text},
        "type": "ReceivedCallback",
    }


# ── Payloads Evolution ────────────────────────────────────────────────────

def evolution_payload(phone: str, text: str, from_me=False, is_group=False):
    return {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": from_me, "remoteJid": f"{phone}@s.whatsapp.net"},
            "messageType": "conversation",
            "message": {"conversation": text},
        },
    }


# ── Testes de filtragem (mensagens ignoradas) ─────────────────────────────

class TestWebhookFiltragem:
    def test_ignora_mensagem_propria_zapi(self, http_client):
        r = http_client.post("/whatsapp/webhook", json=zapi_payload("5511999990001", "teste", from_me=True), headers=ZAPI_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"

    def test_ignora_grupo_zapi(self, http_client):
        r = http_client.post("/whatsapp/webhook", json=zapi_payload("5511999990001", "teste", is_group=True), headers=ZAPI_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"

    def test_ignora_mensagem_vazia_zapi(self, http_client):
        payload = zapi_payload("5511999990001", "")
        payload["text"] = {}  # sem texto
        r = http_client.post("/whatsapp/webhook", json=payload, headers=ZAPI_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"

    def test_rejeita_webhook_zapi_sem_token(self, http_client):
        r = http_client.post("/whatsapp/webhook", json=zapi_payload("5511999990001", "teste"))
        assert r.status_code == 401

    def test_ignora_evento_desconhecido_evolution(self, http_client):
        from unittest.mock import patch
        with patch("app.routers.whatsapp.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "evolution"
            mock_settings.EVOLUTION_API_KEY = "test-evolution-api-key"
            r = http_client.post("/whatsapp/webhook", json={
                "event": "connection.update",
                "data": {},
            }, headers=EVOLUTION_HEADERS)
        assert r.status_code == 200
        # sem instance → connection.update sem empresa → status ok
        data = r.json()
        assert data.get("status") in ("ok", "ignored")

    def test_ignora_from_me_evolution(self, http_client):
        from unittest.mock import patch
        with patch("app.routers.whatsapp.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "evolution"
            mock_settings.EVOLUTION_API_KEY = "test-evolution-api-key"
            r = http_client.post(
                "/whatsapp/webhook?instance=qualquer",
                json=evolution_payload("5511999990001", "teste", from_me=True),
                headers=EVOLUTION_HEADERS,
            )
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"


# ── Testes de aprovação ───────────────────────────────────────────────────

class TestAprovacaoOrcamento:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.emp = make_empresa(db, telefone_operador="5511000000001")
        self.usr = make_usuario(db, self.emp)
        self.cli = make_cliente(db, self.emp, telefone="5511988880001")
        self.orc = make_orcamento(db, self.emp, self.cli, self.usr,
                                   status=StatusOrcamento.ENVIADO)
        self.db = db

    def test_aceito_confirmacao_depois_sim_aprova(self, http_client, db):
        """Fluxo em 2 etapas: ACEITO envia confirmação; SIM confirma e aprova."""
        r1 = http_client.post("/whatsapp/webhook", json=zapi_payload("5511988880001", "ACEITO"), headers=ZAPI_HEADERS)
        assert r1.status_code == 200
        assert r1.json()["status"] == "ok"
        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.ENVIADO  # ainda não aprovado

        r2 = http_client.post("/whatsapp/webhook", json=zapi_payload("5511988880001", "SIM"), headers=ZAPI_HEADERS)
        assert r2.status_code == 200
        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.APROVADO

    def test_aceito_com_ponto_depois_sim_aprova(self, http_client, db):
        r1 = http_client.post("/whatsapp/webhook", json=zapi_payload("5511988880001", "Aceito."), headers=ZAPI_HEADERS)
        assert r1.status_code == 200
        r2 = http_client.post("/whatsapp/webhook", json=zapi_payload("5511988880001", "SIM"), headers=ZAPI_HEADERS)
        assert r2.status_code == 200
        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.APROVADO

    def test_sim_sem_pendente_envia_confirmacao_depois_sim_aprova(self, http_client, db):
        """Primeiro SIM envia confirmação; segundo SIM confirma e aprova."""
        r1 = http_client.post("/whatsapp/webhook", json=zapi_payload("5511988880001", "SIM"), headers=ZAPI_HEADERS)
        assert r1.status_code == 200
        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.ENVIADO
        r2 = http_client.post("/whatsapp/webhook", json=zapi_payload("5511988880001", "SIM"), headers=ZAPI_HEADERS)
        assert r2.status_code == 200
        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.APROVADO

    def test_aceito_cliente_inexistente_retorna_ok(self, http_client):
        """Webhook retorna ok mesmo quando cliente não existe (processado em background)."""
        r = http_client.post("/whatsapp/webhook", json=zapi_payload("5599000000000", "ACEITO"), headers=ZAPI_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_aceito_sem_orcamento_enviado_retorna_ok(self, http_client, db):
        """Cliente existe mas não tem orçamento ENVIADO — webhook retorna ok."""
        self.orc.status = StatusOrcamento.RASCUNHO
        db.commit()

        r = http_client.post("/whatsapp/webhook", json=zapi_payload("5511988880001", "ACEITO"), headers=ZAPI_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ── Testes de recusa ──────────────────────────────────────────────────────

class TestRecusaOrcamento:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.emp = make_empresa(db)
        self.usr = make_usuario(db, self.emp)
        self.cli = make_cliente(db, self.emp, telefone="5511977770001")
        self.orc = make_orcamento(db, self.emp, self.cli, self.usr,
                                   status=StatusOrcamento.ENVIADO)
        self.db = db

    def test_recuso_recusa_orcamento(self, http_client, db):
        r = http_client.post("/whatsapp/webhook", json=zapi_payload("5511977770001", "RECUSO"), headers=ZAPI_HEADERS)
        assert r.status_code == 200

        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.RECUSADO

    def test_nao_quero_recusa(self, http_client, db):
        r = http_client.post("/whatsapp/webhook", json=zapi_payload("5511977770001", "NAO QUERO"), headers=ZAPI_HEADERS)
        assert r.status_code == 200

        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.RECUSADO


# ── Testes payload Evolution ──────────────────────────────────────────────

class TestWebhookEvolution:
    def test_evolution_messages_upsert_aceito(self, http_client, db):
        from unittest.mock import patch
        emp = make_empresa(db)
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp, telefone="5511966660001")
        orc = make_orcamento(db, emp, cli, usr, status=StatusOrcamento.ENVIADO)

        with patch("app.routers.whatsapp.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "evolution"
            mock_settings.EVOLUTION_API_KEY = "test-evolution-api-key"
            r1 = http_client.post(
                "/whatsapp/webhook",
                json=evolution_payload("5511966660001", "ACEITO"),
                headers=EVOLUTION_HEADERS,
            )
        assert r1.status_code == 200
        assert r1.json()["status"] == "ok"
        with patch("app.routers.whatsapp.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "evolution"
            mock_settings.EVOLUTION_API_KEY = "test-evolution-api-key"
            r2 = http_client.post(
                "/whatsapp/webhook",
                json=evolution_payload("5511966660001", "SIM"),
                headers=EVOLUTION_HEADERS,
            )
        assert r2.status_code == 200
        db.expire_all()
        from app.models.models import Orcamento
        updated = db.get(Orcamento, orc.id)
        assert updated.status == StatusOrcamento.APROVADO

    def test_evolution_evento_nao_mensagem_ignorado(self, http_client):
        from unittest.mock import patch
        with patch("app.routers.whatsapp.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "evolution"
            mock_settings.EVOLUTION_API_KEY = "test-evolution-api-key"
            r = http_client.post("/whatsapp/webhook", json={
                "event": "qrcode.updated",
                "data": {},
            }, headers=EVOLUTION_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"


# ── Rate Limiting ─────────────────────────────────────────────────────────

class TestRateLimitingWebhook:
    """Garante que o webhook retorna 429 quando o rate limiter bloqueia."""

    def test_webhook_retorna_429_quando_bloqueado(self, http_client):
        bloqueado = RateLimitResult(allowed=False, retry_after_seconds=60)
        with patch("app.routers.whatsapp.webhook_rate_limiter") as mock_rl:
            mock_rl.check.return_value = bloqueado
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511999990001", "OI"),
                headers=ZAPI_HEADERS,
            )
        assert r.status_code == 429
        assert r.headers.get("retry-after") == "60"

    def test_webhook_passa_quando_nao_bloqueado(self, http_client):
        permitido = RateLimitResult(allowed=True, retry_after_seconds=0)
        with patch("app.routers.whatsapp.webhook_rate_limiter") as mock_rl:
            mock_rl.check.return_value = permitido
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511999990001", "OI"),
                headers=ZAPI_HEADERS,
            )
        # Qualquer 2xx é aceitável — o importante é não ser 429
        assert r.status_code != 429


class TestEnviarExigeOperador:
    def test_enviar_id_por_cliente_nao_envia_orcamento(self, http_client, db):
        emp = make_empresa(db, telefone_operador="5511000000001")
        usr = make_usuario(db, emp)
        cli = make_cliente(db, emp, telefone="5511988880001")
        orc = make_orcamento(db, emp, cli, usr, status=StatusOrcamento.RASCUNHO)

        with patch("app.services.whatsapp_bot_service.enviar_orcamento_completo", new_callable=MagicMock) as mock_envio:
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511988880001", f"ENVIAR {orc.id}"),
                headers=ZAPI_HEADERS,
            )

        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        mock_envio.assert_not_called()


class TestRateLimitingInterpretar:
    """Garante que /interpretar retorna 429 quando o rate limiter bloqueia."""

    def test_interpretar_retorna_429_quando_bloqueado(self, http_client):
        bloqueado = RateLimitResult(allowed=False, retry_after_seconds=600)
        with patch("app.routers.whatsapp.ia_interpretar_rate_limiter") as mock_rl:
            mock_rl.check.return_value = bloqueado
            r = http_client.post(
                "/whatsapp/interpretar",
                json={"mensagem": "preciso de um orçamento"},
            )
        assert r.status_code == 429
        assert r.headers.get("retry-after") == "600"

    def test_interpretar_passa_quando_nao_bloqueado(self, http_client):
        permitido = RateLimitResult(allowed=True, retry_after_seconds=0)
        with patch("app.routers.whatsapp.ia_interpretar_rate_limiter") as mock_rl:
            mock_rl.check.return_value = permitido
            r = http_client.post(
                "/whatsapp/interpretar",
                json={"mensagem": "preciso de um orçamento"},
            )
        assert r.status_code != 429


# ── Testes: ação operacional sem ID nunca cria orçamento ─────────────────────

class TestAcaoOperacionalSemID:
    """
    Garante que comandos como "aprovar", "ver", "recusar" SEM número de orçamento
    NÃO caem no fallback de criação — em vez disso, pedem o número.
    """

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.emp = make_empresa(db, telefone_operador="5511000000001")
        self.usr = make_usuario(db, self.emp)
        self.cli = make_cliente(db, self.emp, telefone="5511988880001")
        self.orc = make_orcamento(db, self.emp, self.cli, self.usr,
                                   status=StatusOrcamento.ENVIADO, numero="ORC-5-26")
        self.db = db

    def test_aprovar_sem_id_nao_cria_orcamento(self, http_client, db):
        """'aprovar' sozinho deve pedir o número, não criar orçamento fantasma."""
        mock_interpretar = AsyncMock(return_value={"acao": "APROVAR", "orcamento_id": None})
        with patch("app.services.whatsapp_bot_service.enviar_mensagem_texto", new_callable=AsyncMock) as mock_msg, \
             patch("app.services.whatsapp_bot_service.interpretar_comando_operador", mock_interpretar):
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511000000001", "aprovar"),
                headers=ZAPI_HEADERS,
            )
        assert r.status_code == 200
        # Verifica que enviou mensagem pedindo o número
        mock_msg.assert_called()
        args = mock_msg.call_args
        texto = args[0][1] if args else ""
        assert "aprovar" in texto.lower() or "qual" in texto.lower()
        # Confirma que NÃO criou orçamento
        db.expire_all()
        orcs = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).filter(
            __import__("app.models.models", fromlist=["Orcamento"]).Orcamento.cliente_id == self.cli.id
        ).all()
        # Deve existir apenas o original ORC-5-26
        assert len(orcs) == 1

    def test_ver_sem_id_nao_cria_orcamento(self, http_client, db):
        """'ver' sozinho deve pedir o número, não criar orçamento fantasma."""
        mock_interpretar = AsyncMock(return_value={"acao": "VER", "orcamento_id": None})
        with patch("app.services.whatsapp_bot_service.enviar_mensagem_texto", new_callable=AsyncMock) as mock_msg, \
             patch("app.services.whatsapp_bot_service.interpretar_comando_operador", mock_interpretar):
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511000000001", "ver"),
                headers=ZAPI_HEADERS,
            )
        assert r.status_code == 200
        mock_msg.assert_called()
        db.expire_all()
        orcs = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).filter(
            __import__("app.models.models", fromlist=["Orcamento"]).Orcamento.cliente_id == self.cli.id
        ).all()
        assert len(orcs) == 1

    def test_recusar_sem_id_nao_cria_orcamento(self, http_client, db):
        """'recusar' sozinho deve pedir o número, não criar orçamento fantasma."""
        mock_interpretar = AsyncMock(return_value={"acao": "RECUSAR", "orcamento_id": None})
        with patch("app.services.whatsapp_bot_service.enviar_mensagem_texto", new_callable=AsyncMock) as mock_msg, \
             patch("app.services.whatsapp_bot_service.interpretar_comando_operador", mock_interpretar):
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511000000001", "recusar"),
                headers=ZAPI_HEADERS,
            )
        assert r.status_code == 200
        mock_msg.assert_called()

    def test_aprovar_orcamento_sem_numero_nao_cria(self, http_client, db):
        """'aprovar orçamento' (sem número) deve pedir ID, não criar."""
        mock_interpretar = AsyncMock(return_value={"acao": "APROVAR", "orcamento_id": None})
        with patch("app.services.whatsapp_bot_service.enviar_mensagem_texto", new_callable=AsyncMock) as mock_msg, \
             patch("app.services.whatsapp_bot_service.interpretar_comando_operador", mock_interpretar):
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511000000001", "aprovar orçamento"),
                headers=ZAPI_HEADERS,
            )
        assert r.status_code == 200
        mock_msg.assert_called()
        db.expire_all()
        orcs = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).filter(
            __import__("app.models.models", fromlist=["Orcamento"]).Orcamento.cliente_id == self.cli.id
        ).all()
        assert len(orcs) == 1

    def test_aprovar_com_id_aprova_normalmente(self, http_client, db):
        """'aprovar 5' (com ID) deve aprovar o orçamento, não pedir número."""
        mock_interpretar = AsyncMock(return_value={"acao": "APROVAR", "orcamento_id": self.orc.id})
        with patch("app.services.whatsapp_bot_service.enviar_mensagem_texto", new_callable=AsyncMock), \
             patch("app.services.whatsapp_bot_service.interpretar_comando_operador", mock_interpretar), \
             patch("app.services.whatsapp_bot_service.handle_quote_status_changed", new_callable=AsyncMock):
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511000000001", f"aprovar {self.orc.id}"),
                headers=ZAPI_HEADERS,
            )
        assert r.status_code == 200
        db.expire_all()
        orc = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).get(self.orc.id)
        assert orc.status == StatusOrcamento.APROVADO

    def test_enviar_sem_id_nao_cria_orcamento(self, http_client, db):
        """'enviar' sozinho deve pedir o número, não criar."""
        mock_interpretar = AsyncMock(return_value={"acao": "ENVIAR", "orcamento_id": None})
        with patch("app.services.whatsapp_bot_service.enviar_mensagem_texto", new_callable=AsyncMock) as mock_msg, \
             patch("app.services.whatsapp_bot_service.interpretar_comando_operador", mock_interpretar):
            r = http_client.post(
                "/whatsapp/webhook",
                json=zapi_payload("5511000000001", "enviar"),
                headers=ZAPI_HEADERS,
            )
        assert r.status_code == 200
        mock_msg.assert_called()
        db.expire_all()
        orcs = db.query(__import__("app.models.models", fromlist=["Orcamento"]).Orcamento).filter(
            __import__("app.models.models", fromlist=["Orcamento"]).Orcamento.cliente_id == self.cli.id
        ).all()
        assert len(orcs) == 1
