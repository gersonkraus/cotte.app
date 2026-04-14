"""Heurísticas do assistente para listar_orcamentos (autopaginação)."""

from app.services.cotte_ai_hub import _wants_all_orcamentos


def test_wants_all_orcamentos_todos_e_lista_completa():
    assert _wants_all_orcamentos("mostre todos os orçamentos de ontem") is True
    assert _wants_all_orcamentos("lista completa de orçamentos aprovados") is True
    assert _wants_all_orcamentos("sem limite, quero ver orçamentos") is True
    assert _wants_all_orcamentos("todos os orcamentos do mês") is True


def test_wants_all_orcamentos_lista_simples_nao_dispara():
    assert _wants_all_orcamentos("me mostre a lista dos orçamentos de hoje") is False
    assert _wants_all_orcamentos("lista de orçamentos aprovados ontem") is False


def test_wants_all_orcamentos_sem_escopo_orcamento():
    assert _wants_all_orcamentos("qual o faturamento") is False
    assert _wants_all_orcamentos("lista completa de clientes") is False
