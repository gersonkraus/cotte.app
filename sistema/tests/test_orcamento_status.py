"""Testes da máquina de estados compartilhada (API + bot)."""

from app.models.models import StatusOrcamento
from app.utils.orcamento_status import transicao_permitida


def test_transicao_rascunho_para_enviado():
    assert transicao_permitida(StatusOrcamento.RASCUNHO, StatusOrcamento.ENVIADO)


def test_transicao_enviado_para_aprovado():
    assert transicao_permitida(StatusOrcamento.ENVIADO, StatusOrcamento.APROVADO)


def test_transicao_rascunho_para_aprovado():
    assert transicao_permitida(StatusOrcamento.RASCUNHO, StatusOrcamento.APROVADO)


def test_idempotente_mesmo_status():
    assert transicao_permitida(StatusOrcamento.ENVIADO, StatusOrcamento.ENVIADO)


def test_transicao_enviado_para_recusado():
    assert transicao_permitida(StatusOrcamento.ENVIADO, StatusOrcamento.RECUSADO)
