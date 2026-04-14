"""Testes E2E das tools da Fase 3 — handlers diretos (happy path + erros)."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

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
    AprovarOrcamentoInput,
    DuplicarOrcamentoInput,
    EditarOrcamentoInput,
    ListarOrcamentosInput,
    _aprovar_orcamento,
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


def test_listar_orcamentos_total_real_com_limit(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Cliente Aprovado")
    ontem = date.today() - timedelta(days=1)

    for i in range(12):
        orc = make_orcamento(
            db,
            emp,
            cli,
            user,
            status=StatusOrcamento.APROVADO,
            total=100 + i,
            numero=f"ORC-APR-{i}-26",
        )
        orc.criado_em = ontem
        db.add(orc)
    db.commit()

    res = _run(
        _listar_orcamentos(
            ListarOrcamentosInput(status="APROVADO", dias=2, limit=10),
            db=db,
            current_user=user,
        )
    )

    assert res["total"] == 12
    assert len(res["orcamentos"]) == 10
    assert res["itens_retornados"] == 10
    assert res["has_more"] is True
    assert isinstance(res["next_cursor"], str) and res["next_cursor"]
    assert res["totais_por_status"][StatusOrcamento.APROVADO.value] == 12


def test_listar_orcamentos_cursor_pagina_sem_duplicar(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Cliente Cursor")
    ontem = date.today() - timedelta(days=1)

    for i in range(12):
        orc = make_orcamento(
            db,
            emp,
            cli,
            user,
            status=StatusOrcamento.APROVADO,
            total=200 + i,
            numero=f"ORC-CUR-{i}-26",
        )
        orc.criado_em = ontem
        db.add(orc)
    db.commit()

    primeira = _run(
        _listar_orcamentos(
            ListarOrcamentosInput(status="APROVADO", dias=2, limit=10),
            db=db,
            current_user=user,
        )
    )
    segunda = _run(
        _listar_orcamentos(
            ListarOrcamentosInput(
                status="APROVADO",
                dias=2,
                limit=10,
                cursor=primeira["next_cursor"],
            ),
            db=db,
            current_user=user,
        )
    )

    assert primeira["has_more"] is True
    assert len(primeira["orcamentos"]) == 10
    assert len(segunda["orcamentos"]) == 2
    assert segunda["has_more"] is False
    ids_primeira = {o["id"] for o in primeira["orcamentos"]}
    ids_segunda = {o["id"] for o in segunda["orcamentos"]}
    assert ids_primeira.isdisjoint(ids_segunda)


def test_listar_orcamentos_filtra_por_data_aprovacao_br(db):
    """Orçamentos aprovados 'ontem' usam aprovado_em, não criado_em."""
    br = ZoneInfo("America/Sao_Paulo")
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Cliente Aprovação")
    ontem = date.today() - timedelta(days=1)

    o_ontem = make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=10.0,
        numero="ORC-APR-ONTEM-26",
    )
    o_ontem.aprovado_em = datetime.combine(ontem, time(14, 30), tzinfo=br)
    o_ontem.criado_em = datetime.combine(
        date.today() - timedelta(days=60), time(9, 0), tzinfo=br
    )

    o_antigo = make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=20.0,
        numero="ORC-APR-VELHO-26",
    )
    o_antigo.aprovado_em = datetime.combine(
        ontem - timedelta(days=5), time(10, 0), tzinfo=br
    )

    o_sem_data = make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=30.0,
        numero="ORC-APR-SEM-26",
    )
    o_sem_data.aprovado_em = None

    db.commit()

    res = _run(
        _listar_orcamentos(
            ListarOrcamentosInput(
                status="APROVADO",
                aprovado_em_de=ontem,
                aprovado_em_ate=ontem,
                limit=20,
            ),
            db=db,
            current_user=user,
        )
    )

    assert res["total"] == 1
    assert len(res["orcamentos"]) == 1
    assert res["orcamentos"][0]["id"] == o_ontem.id
    assert res["orcamentos"][0].get("aprovado_em")


def test_listar_orcamentos_intervalo_ontem_e_hoje_aprovacao(db):
    br = ZoneInfo("America/Sao_Paulo")
    hoje = datetime.now(br).date()
    ontem = hoje - timedelta(days=1)
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Cliente Intervalo")

    o1 = make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=1.0,
        numero="ORC-INT-1-26",
    )
    o1.aprovado_em = datetime.combine(ontem, time(9, 0), tzinfo=br)
    o2 = make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=2.0,
        numero="ORC-INT-2-26",
    )
    o2.aprovado_em = datetime.combine(hoje, time(18, 0), tzinfo=br)
    o3 = make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=3.0,
        numero="ORC-INT-3-26",
    )
    o3.aprovado_em = datetime.combine(ontem - timedelta(days=1), time(12, 0), tzinfo=br)
    db.commit()

    res = _run(
        _listar_orcamentos(
            ListarOrcamentosInput(
                aprovado_em_de=ontem,
                aprovado_em_ate=hoje,
                limit=20,
            ),
            db=db,
            current_user=user,
        )
    )
    ids = {r["id"] for r in res["orcamentos"]}
    assert ids == {o1.id, o2.id}
    assert res["total"] == 2
    assert res["filtros"].get("status_efetivo") == StatusOrcamento.APROVADO.value
    assert res.get("diagnostico", {}).get("filtro_por_data_aprovacao") is True
    assert res.get("diagnostico", {}).get("aprovados_sem_data") == 0


def test_aprovar_orcamento_preenche_aprovado_em(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Cliente Aprovação Tool")
    orc = make_orcamento(db, emp, cli, user, status=StatusOrcamento.ENVIADO)

    monkeypatch.setattr(
        "app.services.financeiro_service.criar_contas_receber_aprovacao",
        lambda *_args, **_kwargs: None,
    )

    async def _noop_handle_quote_status_changed(**_kwargs):
        return None

    monkeypatch.setattr(
        "app.services.quote_notification_service.handle_quote_status_changed",
        _noop_handle_quote_status_changed,
    )

    res = _run(
        _aprovar_orcamento(
            AprovarOrcamentoInput(orcamento_id=orc.id),
            db=db,
            current_user=user,
        )
    )
    assert res["status"] == "aprovado"
    db.refresh(orc)
    assert orc.aprovado_em is not None
    assert orc.aprovado_canal == "assistente_tool"


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
