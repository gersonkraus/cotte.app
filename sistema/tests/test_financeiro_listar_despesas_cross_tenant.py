from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.models import ContaFinanceira, StatusConta, TipoConta, Usuario
from app.services.ai_tools.financeiro_tools import ListarDespesasInput, _listar_despesas
from tests.conftest import make_empresa, make_usuario


@pytest.mark.asyncio
async def test_listar_despesas_bloqueia_empresa_id_filtro_para_nao_superadmin(db):
    empresa = make_empresa(db, nome="Origem")
    outra_empresa = make_empresa(db, nome="Destino")
    user = make_usuario(db, empresa, email="gestor-cross-tenant@teste.com")
    db.commit()

    out = await _listar_despesas(
        ListarDespesasInput(empresa_id_filtro=outra_empresa.id),
        db=db,
        current_user=user,
    )

    assert out["code"] == "forbidden_cross_tenant"
    assert "não possui permissão" in out["error"].lower()


@pytest.mark.asyncio
async def test_listar_despesas_superadmin_consulta_empresa_id_filtro(db):
    empresa_origem = make_empresa(db, nome="Origem Superadmin")
    empresa_alvo = make_empresa(db, nome="Empresa 5")
    superadmin = Usuario(
        empresa_id=empresa_origem.id,
        nome="Super Admin",
        email="superadmin-cross-tenant@teste.com",
        senha_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehash12",
        ativo=True,
        is_gestor=True,
        is_superadmin=True,
        permissoes={},
    )
    db.add(superadmin)
    db.flush()

    despesa = ContaFinanceira(
        empresa_id=empresa_alvo.id,
        tipo=TipoConta.PAGAR,
        descricao="Hospedagem dedicada",
        valor=Decimal("199.90"),
        valor_pago=Decimal("0.00"),
        status=StatusConta.PENDENTE,
        data_vencimento=date.today() + timedelta(days=3),
        origem="sistema",
        favorecido="Fornecedor Cloud",
    )
    db.add(despesa)
    db.commit()

    out = await _listar_despesas(
        ListarDespesasInput(empresa_id_filtro=empresa_alvo.id, busca="Hospedagem"),
        db=db,
        current_user=superadmin,
    )

    assert out["total"] == 1
    assert out["despesas"][0]["descricao"] == "Hospedagem dedicada"
    assert out["despesas"][0]["favorecido"] == "Fornecedor Cloud"
