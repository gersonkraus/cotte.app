from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.models import SaldoCaixaConfig
from app.services import ai_intention_classifier, cotte_ai_hub, financeiro_service


class _FakeQuery:
    def __init__(self, *, scalar_result=0, first_result=None, all_result=None):
        self._scalar_result = scalar_result
        self._first_result = first_result
        self._all_result = all_result if all_result is not None else []

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def group_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def scalar(self):
        return self._scalar_result

    def first(self):
        return self._first_result

    def all(self):
        return self._all_result

    def count(self):
        return 0


class _FakeDB:
    def query(self, *args, **kwargs):
        if len(args) == 1 and args[0] is SaldoCaixaConfig:
            return _FakeQuery(first_result=SimpleNamespace(saldo_inicial=Decimal("50")))
        return _FakeQuery()


def test_calcular_resumo_usa_fonte_unica_saldo(monkeypatch):
    monkeypatch.setattr(
        financeiro_service,
        "calcular_saldo_caixa_kpi",
        lambda empresa_id, db: Decimal("1234.56"),
    )
    monkeypatch.setattr(financeiro_service, "_receita_ultimos_meses", lambda *a, **k: [])
    monkeypatch.setattr(financeiro_service, "_receita_por_meio", lambda *a, **k: [])

    resumo = financeiro_service.calcular_resumo(empresa_id=1, db=_FakeDB())

    assert resumo["saldo_caixa"] == Decimal("1234.56")


@pytest.mark.asyncio
async def test_buscar_dados_financeiros_alinha_saldo_com_kpi(monkeypatch):
    monkeypatch.setattr(
        financeiro_service,
        "calcular_saldo_caixa_kpi",
        lambda empresa_id, db: Decimal("999.99"),
    )

    dados = await cotte_ai_hub._buscar_dados_financeiros(db=_FakeDB(), empresa_id=1)

    assert dados["saldo"]["atual"] == 999.99
    assert "Mesmo valor do KPI 'Saldo em Caixa'" in dados["saldo"]["definicao"]


@pytest.mark.asyncio
async def test_saldo_rapido_ia_usa_mesmo_valor_do_kpi(monkeypatch):
    monkeypatch.setattr(
        financeiro_service,
        "calcular_saldo_caixa_kpi",
        lambda empresa_id, db: Decimal("777.70"),
    )

    resposta = await ai_intention_classifier.saldo_rapido_ia(db=_FakeDB(), empresa_id=1)

    assert resposta.sucesso is True
    assert resposta.dados["saldo_atual"] == 777.70
    assert "Caixa operacional" in resposta.dados["definicao"]


@pytest.mark.asyncio
async def test_assistente_unificado_roteia_saldo_rapido_sem_llm(monkeypatch):
    class _DummyIntent:
        class _IntentValue:
            value = "SALDO_RAPIDO"

        intencao = _IntentValue()

    chamada = {"saldo_rapido": False}

    async def _fake_detectar(mensagem):
        return _DummyIntent()

    async def _fake_saldo_rapido(db=None, empresa_id=None):
        chamada["saldo_rapido"] = True
        return SimpleNamespace(sucesso=True, resposta="ok", tipo_resposta="saldo_caixa", dados={})

    monkeypatch.setattr(cotte_ai_hub, "detectar_intencao_assistente_async", _fake_detectar)
    monkeypatch.setattr(ai_intention_classifier, "saldo_rapido_ia", _fake_saldo_rapido)

    resposta = await cotte_ai_hub.assistente_unificado(
        mensagem="qual o saldo do caixa?",
        sessao_id="sessao-teste",
        db=_FakeDB(),
        empresa_id=1,
        usuario_id=1,
        is_gestor=True  # Bypass permission check
    )

    assert chamada["saldo_rapido"] is True
    assert resposta.tipo_resposta == "saldo_caixa"


@pytest.mark.asyncio
async def test_classificador_async_saldo_usa_regex_sem_llm():
    resultado = await ai_intention_classifier.detectar_intencao_assistente_async(
        "qual o saldo do caixa?"
    )

    assert resultado.intencao.value == "SALDO_RAPIDO"
    assert resultado.metodo == "regex"
