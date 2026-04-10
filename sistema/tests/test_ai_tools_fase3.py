"""Testes E2E das tools da Fase 3 — handlers diretos (happy path + erros)."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.ai_tools.catalogo_tools import (
    CadastrarMaterialInput,
    _cadastrar_material,
)
from app.services.ai_tools.cliente_tools import (
    EditarClienteInput,
    _editar_cliente,
)
from app.services.ai_tools.financeiro_tools import (
    CriarDespesaInput,
    CriarParcelamentoInput,
    ListarDespesasInput,
    MarcarDespesaPagaInput,
    _criar_despesa,
    _criar_parcelamento,
    _listar_despesas,
    _marcar_despesa_paga,
)
from app.services.ai_tools.orcamento_tools import (
    DuplicarOrcamentoInput,
    EditarOrcamentoInput,
    ListarOrcamentosInput,
    _duplicar_orcamento,
    _editar_orcamento,
    _listar_orcamentos,
)
from app.models.models import StatusOrcamento
from tests.conftest import (
    make_cliente,
    make_empresa,
    make_orcamento,
    make_usuario,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Cadastro de material ─────────────────────────────────────────────────
def test_cadastrar_material_gera_id(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    inp = CadastrarMaterialInput(nome="Tomada dupla", preco_padrao=Decimal("12.50"))
    res = _run(_cadastrar_material(inp, db=db, current_user=user))
    assert res["criado"] is True
    assert res["id"] > 0
    assert res["nome"] == "Tomada dupla"


# ── Editar cliente ───────────────────────────────────────────────────────
def test_editar_cliente_atualiza_campos(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Ana", telefone="5511900001111")
    inp = EditarClienteInput(cliente_id=cli.id, nome="Ana Souza", email="ana@x.com")
    res = _run(_editar_cliente(inp, db=db, current_user=user))
    assert res["atualizado"] is True
    assert res["nome"] == "Ana Souza"
    assert res["email"] == "ana@x.com"


def test_editar_cliente_sem_campos(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp)
    inp = EditarClienteInput(cliente_id=cli.id)
    res = _run(_editar_cliente(inp, db=db, current_user=user))
    assert res.get("code") == "invalid_input"


# ── Duplicar orçamento ───────────────────────────────────────────────────
@pytest.mark.skip(reason="gerar_numero usa split_part (PostgreSQL-only) — testado em integração")
def test_duplicar_orcamento_cria_rascunho_novo(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp)
    orc = make_orcamento(db, emp, cli, user, status=StatusOrcamento.APROVADO, total=200)
    res = _run(
        _duplicar_orcamento(
            DuplicarOrcamentoInput(orcamento_id=orc.id), db=db, current_user=user
        )
    )
    assert res["criado"] is True
    assert res["id"] != orc.id
    assert res["duplicado_de"] == orc.id
    assert res["total"] == 200.0


def test_duplicar_orcamento_not_found(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    res = _run(
        _duplicar_orcamento(
            DuplicarOrcamentoInput(orcamento_id=99999), db=db, current_user=user
        )
    )
    assert res.get("code") == "not_found"


# ── Editar orçamento ─────────────────────────────────────────────────────
def test_editar_orcamento_rascunho_ok(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp)
    orc = make_orcamento(db, emp, cli, user, status=StatusOrcamento.RASCUNHO)
    res = _run(
        _editar_orcamento(
            EditarOrcamentoInput(orcamento_id=orc.id, observacoes="nova obs"),
            db=db,
            current_user=user,
        )
    )
    assert res["atualizado"] is True
    assert res["observacoes"] == "nova obs"


def test_editar_orcamento_nao_rascunho_bloqueia(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp)
    orc = make_orcamento(db, emp, cli, user, status=StatusOrcamento.APROVADO)
    res = _run(
        _editar_orcamento(
            EditarOrcamentoInput(orcamento_id=orc.id, observacoes="x"),
            db=db,
            current_user=user,
        )
    )
    assert res.get("code") == "invalid_state"


@pytest.mark.parametrize(
    "status_input",
    ["ENVIADO", "PENDENTE", "EM_ABERTO", "A_RECEBER", "RECEBER"],
)
def test_listar_orcamentos_status_semantico(db, status_input):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Ana Júlia")

    make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.ENVIADO,
        total=150.0,
        numero="ORC-100-26",
    )
    make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=300.0,
        numero="ORC-101-26",
    )

    res = _run(
        _listar_orcamentos(
            ListarOrcamentosInput(status=status_input, dias=365, limit=20),
            db=db,
            current_user=user,
        )
    )

    expected_status = (
        StatusOrcamento.APROVADO.value
        if status_input in ("A_RECEBER", "RECEBER")
        else StatusOrcamento.ENVIADO.value
    )
    assert res["total"] == 1
    assert len(res["orcamentos"]) == 1
    assert res["orcamentos"][0]["status"] == expected_status


# ── Criar + marcar despesa paga (ciclo completo) ─────────────────────────
def test_despesa_ciclo_completo(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    venc = (date.today() + timedelta(days=5)).isoformat()

    criar = _run(
        _criar_despesa(
            CriarDespesaInput(
                descricao="Energia", valor=Decimal("150.00"), data_vencimento=venc
            ),
            db=db,
            current_user=user,
        )
    )
    assert criar["criado"] is True
    conta_id = criar["id"]

    listado = _run(
        _listar_despesas(ListarDespesasInput(busca="Energia"), db=db, current_user=user)
    )
    assert listado["total"] >= 1
    assert any(d["id"] == conta_id for d in listado["despesas"])

    pago = _run(
        _marcar_despesa_paga(
            MarcarDespesaPagaInput(conta_id=conta_id), db=db, current_user=user
        )
    )
    assert pago["criado"] is True
    assert pago["valor"] == 150.0


def test_marcar_despesa_paga_not_found(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    res = _run(
        _marcar_despesa_paga(
            MarcarDespesaPagaInput(conta_id=99999), db=db, current_user=user
        )
    )
    assert res.get("code") == "not_found"


# ── Parcelamento (pagar) ─────────────────────────────────────────────────
def test_criar_parcelamento_pagar(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    res = _run(
        _criar_parcelamento(
            CriarParcelamentoInput(
                tipo="pagar",
                descricao="Aluguel",
                valor_total=Decimal("3000"),
                parcelas=3,
                primeira_data=date.today().isoformat(),
                favorecido="Imobiliária",
            ),
            db=db,
            current_user=user,
        )
    )
    assert res["criado"] is True
    assert res["parcelas_criadas"] == 3
    assert len(res["contas_ids"]) == 3
    assert res["valor_parcela"] == 1000.0
