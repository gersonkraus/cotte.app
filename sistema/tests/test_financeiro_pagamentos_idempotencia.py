"""Testes: idempotência, teto por saldo e ordem de parcelas nos pagamentos."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.models import (
    ContaFinanceira,
    Orcamento,
    OrigemRegistro,
    PagamentoFinanceiro,
    StatusConta,
    StatusOrcamento,
    StatusPagamentoFinanceiro,
    TipoConta,
    TipoPagamento,
    Usuario,
)
from app.schemas.financeiro import PagamentoCreate
from app.services import financeiro_service as fin
from fastapi import HTTPException
from tests.conftest import make_cliente, make_empresa, make_orcamento, make_usuario


def _orc_aprovado_com_parcelas(db: Session) -> tuple[Orcamento, Usuario]:
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp)
    orc = make_orcamento(
        db,
        emp,
        cli,
        user,
        status=StatusOrcamento.APROVADO,
        total=100.0,
    )
    # Duas parcelas: 40 + 60 (ordem explícita por numero_parcela)
    db.add(
        ContaFinanceira(
            empresa_id=emp.id,
            orcamento_id=orc.id,
            tipo=TipoConta.RECEBER,
            descricao="1ª parcela",
            valor=Decimal("40.00"),
            valor_pago=Decimal("0"),
            status=StatusConta.PENDENTE,
            numero_parcela=1,
            total_parcelas=2,
        )
    )
    db.add(
        ContaFinanceira(
            empresa_id=emp.id,
            orcamento_id=orc.id,
            tipo=TipoConta.RECEBER,
            descricao="2ª parcela",
            valor=Decimal("60.00"),
            valor_pago=Decimal("0"),
            status=StatusConta.PENDENTE,
            numero_parcela=2,
            total_parcelas=2,
        )
    )
    db.commit()
    db.refresh(orc)
    return orc, user


def test_registrar_pagamento_rejeita_valor_acima_saldo_parcela(db: Session) -> None:
    orc, user = _orc_aprovado_com_parcelas(db)
    dados = PagamentoCreate(
        orcamento_id=orc.id,
        valor=Decimal("50.00"),
        data_pagamento=date.today(),
        idempotency_key=None,
    )
    with pytest.raises(HTTPException) as exc:
        fin.registrar_pagamento(orc.empresa_id, dados, user, db)
    assert exc.value.status_code == 400
    assert "saldo" in exc.value.detail.lower()


def test_registrar_pagamento_respeita_ordem_parcelas(db: Session) -> None:
    orc, user = _orc_aprovado_com_parcelas(db)
    p1 = PagamentoCreate(
        orcamento_id=orc.id,
        valor=Decimal("40.00"),
        data_pagamento=date.today(),
    )
    pay1 = fin.registrar_pagamento(orc.empresa_id, p1, user, db)
    db.commit()
    db.refresh(pay1)
    conta1 = db.query(ContaFinanceira).filter_by(id=pay1.conta_id).one()
    assert conta1.numero_parcela == 1
    assert conta1.status == StatusConta.PAGO

    p2 = PagamentoCreate(
        orcamento_id=orc.id,
        valor=Decimal("60.00"),
        data_pagamento=date.today(),
    )
    pay2 = fin.registrar_pagamento(orc.empresa_id, p2, user, db)
    db.commit()
    conta2 = db.query(ContaFinanceira).filter_by(id=pay2.conta_id).one()
    assert conta2.numero_parcela == 2


def test_idempotencia_retorna_mesmo_pagamento(db: Session) -> None:
    orc, user = _orc_aprovado_com_parcelas(db)
    dados = PagamentoCreate(
        orcamento_id=orc.id,
        valor=Decimal("40.00"),
        data_pagamento=date.today(),
        idempotency_key="idem-teste-001",
    )
    a = fin.registrar_pagamento(orc.empresa_id, dados, user, db)
    db.commit()
    b = fin.registrar_pagamento(orc.empresa_id, dados, user, db)
    assert a.id == b.id


def test_parcela_numero_forca_conta_correta(db: Session) -> None:
    orc, user = _orc_aprovado_com_parcelas(db)
    dados = PagamentoCreate(
        orcamento_id=orc.id,
        valor=Decimal("10.00"),
        data_pagamento=date.today(),
        parcela_numero=2,
    )
    pay = fin.registrar_pagamento(orc.empresa_id, dados, user, db)
    db.commit()
    conta = db.query(ContaFinanceira).filter_by(id=pay.conta_id).one()
    assert conta.numero_parcela == 2


def test_registrar_pagamento_conta_receber_usa_saldo_nao_valor_total(db: Session) -> None:
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    conta = ContaFinanceira(
        empresa_id=emp.id,
        tipo=TipoConta.RECEBER,
        descricao="Avulsa",
        valor=Decimal("100.00"),
        valor_pago=Decimal("0"),
        status=StatusConta.PARCIAL,
    )
    db.add(conta)
    db.commit()
    db.refresh(conta)
    # Pagamento parcial pré-existente de 40
    db.add(
        PagamentoFinanceiro(
            empresa_id=emp.id,
            conta_id=conta.id,
            valor=Decimal("40.00"),
            tipo=TipoPagamento.QUITACAO,
            data_pagamento=date.today(),
            origem=OrigemRegistro.MANUAL,
            status=StatusPagamentoFinanceiro.CONFIRMADO,
        )
    )
    db.commit()
    db.refresh(conta)

    pay = fin.registrar_pagamento_conta_receber(
        conta_id=conta.id,
        empresa_id=emp.id,
        usuario=user,
        db=db,
        valor=None,
    )
    db.commit()
    assert pay.valor == Decimal("60.00")
