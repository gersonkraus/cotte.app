"""Default de agendamento_modo no POST /orcamentos/ quando omitido no body."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.models import ModoAgendamentoOrcamento
from app.routers.orcamentos import _resolver_agendamento_modo_criacao
from app.schemas.schemas import ItemOrcamentoCreate, OrcamentoCreate


class TestResolverAgendamentoModoCriacao:
    def test_explicit_prevalece_sobre_empresa(self):
        emp = MagicMock()
        emp.agendamento_modo_padrao = ModoAgendamentoOrcamento.OPCIONAL
        emp.agendamento_escolha_obrigatoria = False
        assert (
            _resolver_agendamento_modo_criacao(
                ModoAgendamentoOrcamento.OBRIGATORIO, emp
            )
            == ModoAgendamentoOrcamento.OBRIGATORIO
        )

    def test_explicit_prevalece_mesmo_com_escolha_obrigatoria(self):
        emp = MagicMock()
        emp.agendamento_escolha_obrigatoria = True
        assert (
            _resolver_agendamento_modo_criacao(
                ModoAgendamentoOrcamento.NAO_USA, emp
            )
            == ModoAgendamentoOrcamento.NAO_USA
        )

    def test_omitido_usa_padrao_empresa(self):
        emp = MagicMock()
        emp.agendamento_modo_padrao = ModoAgendamentoOrcamento.OPCIONAL
        emp.agendamento_escolha_obrigatoria = False
        assert (
            _resolver_agendamento_modo_criacao(None, emp)
            == ModoAgendamentoOrcamento.OPCIONAL
        )

    def test_omitido_com_escolha_obrigatoria_levanta(self):
        emp = MagicMock()
        emp.agendamento_escolha_obrigatoria = True
        with pytest.raises(HTTPException) as exc:
            _resolver_agendamento_modo_criacao(None, emp)
        assert exc.value.status_code == 400

    def test_omitido_sem_empresa_cai_em_nao_usa(self):
        assert (
            _resolver_agendamento_modo_criacao(None, None)
            == ModoAgendamentoOrcamento.NAO_USA
        )


def test_orcamento_create_sem_agendamento_modo_valida():
    """Body sem a chave agendamento_modo deve parsear com None."""
    m = OrcamentoCreate(
        cliente_id=1,
        itens=[
            ItemOrcamentoCreate(
                descricao="Teste", quantidade=1, valor_unit=100
            )
        ],
    )
    assert m.agendamento_modo is None


def test_orcamento_create_itens_obrigatorios():
    with pytest.raises(ValidationError):
        OrcamentoCreate(cliente_id=1, itens=[])
