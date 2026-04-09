import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.notifications import SendResult
from app.services import quote_notification_service as qns


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDB:
    def __init__(self, query_results=None):
        self.query_results = list(query_results or [])
        self.query_calls = 0
        self.added = []
        self.commits = 0

    def query(self, *args, **kwargs):
        if self.query_calls < len(self.query_results):
            result = self.query_results[self.query_calls]
        else:
            result = None
        self.query_calls += 1
        return _FakeQuery(result)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def flush(self):
        pass

    def begin_nested(self):
        return MagicMock(__enter__=lambda x: x, __exit__=lambda x, y, z, w: None)


def _make_quote():
    empresa = SimpleNamespace(id=10, telefone_operador="(48) 99999-0000", telefone=None)
    cliente = SimpleNamespace(nome="Cliente Teste")
    criado_por = SimpleNamespace(id=7, ativo=True, nome="Atendente", telefone="(48) 98888-7777")
    return SimpleNamespace(
        id=99,
        empresa_id=10,
        empresa=empresa,
        cliente=cliente,
        criado_por=criado_por,
        criado_por_id=7,
        numero="ORC-99-26",
        total=1299.9,
        aceite_em=datetime.now(timezone.utc),
        approved_notification_sent_at=None,
        contas_receber_geradas_em=None,
        regra_entrada_percentual=0,
        regra_saldo_percentual=0,
        regra_entrada_metodo=None,
        regra_saldo_metodo=None,
        regra_pagamento_id=None,
    )


def test_notify_quote_approved_envia_whatsapp_quando_telefone_valido(monkeypatch):
    db = _FakeDB()
    quote = _make_quote()
    calls = {"count": 0}

    async def _fake_send(*args, **kwargs):
        calls["count"] += 1
        return SendResult(success=True)

    monkeypatch.setattr(qns, "send_internal_quote_approved_whatsapp", _fake_send)

    asyncio.run(qns.notify_quote_approved(db, quote, source="test"))

    assert calls["count"] == 1
    assert quote.approved_notification_sent_at is not None
    assert db.commits == 1


def test_notify_quote_approved_nao_envia_sem_responsavel(monkeypatch):
    db = _FakeDB(query_results=[None, None])
    quote = _make_quote()
    quote.criado_por = None
    quote.criado_por_id = None
    called = {"value": False}

    async def _fake_send(*args, **kwargs):
        called["value"] = True
        return SendResult(success=True)

    monkeypatch.setattr(qns, "send_internal_quote_approved_whatsapp", _fake_send)

    asyncio.run(qns.notify_quote_approved(db, quote, source="test"))

    assert called["value"] is False
    assert quote.approved_notification_sent_at is None
    assert db.commits == 0


def test_notify_quote_approved_nao_envia_com_telefone_invalido(monkeypatch):
    db = _FakeDB()
    quote = _make_quote()
    quote.criado_por.telefone = "123"
    quote.empresa.telefone_operador = ""
    called = {"value": False}

    async def _fake_send(*args, **kwargs):
        called["value"] = True
        return SendResult(success=True)

    monkeypatch.setattr(qns, "send_internal_quote_approved_whatsapp", _fake_send)

    asyncio.run(qns.notify_quote_approved(db, quote, source="test"))

    assert called["value"] is False
    assert quote.approved_notification_sent_at is None


def test_notify_quote_approved_nao_duplica_envio(monkeypatch):
    db = _FakeDB()
    quote = _make_quote()
    quote.approved_notification_sent_at = datetime.now(timezone.utc)
    called = {"value": False}

    async def _fake_send(*args, **kwargs):
        called["value"] = True
        return SendResult(success=True)

    monkeypatch.setattr(qns, "send_internal_quote_approved_whatsapp", _fake_send)

    asyncio.run(qns.notify_quote_approved(db, quote, source="test"))

    assert called["value"] is False
    assert db.commits == 0


def test_notify_quote_approved_falha_whatsapp_nao_quebra_fluxo(monkeypatch):
    db = _FakeDB()
    quote = _make_quote()

    async def _fake_send(*args, **kwargs):
        return SendResult(success=False, error="timeout")

    monkeypatch.setattr(qns, "send_internal_quote_approved_whatsapp", _fake_send)

    asyncio.run(qns.notify_quote_approved(db, quote, source="test"))

    assert quote.approved_notification_sent_at is None
    assert db.commits == 0


def test_resolve_quote_responsible_user_fallback_para_gestor():
    quote = _make_quote()
    quote.criado_por = None
    quote.criado_por_id = None
    gestor = SimpleNamespace(id=20, ativo=True, is_gestor=True, nome="Gestor")
    db = _FakeDB(query_results=[gestor])

    resolved = qns.resolve_quote_responsible_user(db, quote)

    assert resolved is gestor


def test_handle_quote_status_changed_expirado_sem_disparo():
    db = _FakeDB()
    quote = _make_quote()

    asyncio.run(
        qns.handle_quote_status_changed(
            db=db,
            quote=quote,
            old_status=SimpleNamespace(value="enviado"),
            new_status=qns.StatusOrcamento.EXPIRADO,
            source="test",
        )
    )

    assert quote.approved_notification_sent_at is None
    # Cria notificação in-app mas NÃO envia WhatsApp
    assert db.commits == 1
    assert len(db.added) == 1
    assert db.added[0].tipo == "expirado"
