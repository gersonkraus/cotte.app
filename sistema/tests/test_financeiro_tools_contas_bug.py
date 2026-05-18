import pytest
from app.ai.tools.financeiro_tools import _gerar_relatorio_contas_a_receber, GerarRelatorioContasAReceberInput
from app.models.models import ContaFinanceira, TipoConta, StatusConta, Cliente, Empresa, Usuario, Orcamento, StatusOrcamento

@pytest.mark.asyncio
async def test_gerar_relatorio_contas_a_receber(db):
    # Setup test data
    empresa = Empresa(nome="Test Corp")
    db.add(empresa)
    db.commit()
    
    usuario = Usuario(nome="Test User", email="test@test.com", senha_hash="xyz", empresa_id=empresa.id)
    db.add(usuario)
    db.commit()
    
    cliente = Cliente(nome="John Doe", empresa_id=empresa.id)
    db.add(cliente)
    db.commit()
    
    orcamento = Orcamento(
        numero="O-001",
        empresa_id=empresa.id,
        cliente_id=cliente.id,
        criado_por_id=usuario.id,
        status=StatusOrcamento.APROVADO
    )
    db.add(orcamento)
    db.commit()
    
    conta = ContaFinanceira(
        descricao="Teste",
        valor=100.0,
        valor_pago=0.0,
        tipo=TipoConta.RECEBER,
        status=StatusConta.PENDENTE,
        empresa_id=empresa.id,
        orcamento_id=orcamento.id,
        origem="sistema"
    )
    db.add(conta)
    db.commit()
    
    # Test 1: Sem agrupar
    inp = GerarRelatorioContasAReceberInput(limit=50)
    res = await _gerar_relatorio_contas_a_receber(inp, db=db, current_user=usuario)
    assert res is not None
    assert res["quantidade_contas"] == 1
    assert res["total_devido"] == 100.0
    assert res["detalhes"][0]["cliente"] == "John Doe"

    # Test 2: Com agrupar_por = cliente
    inp_agrupado = GerarRelatorioContasAReceberInput(limit=50, agrupar_por="cliente")
    res_agrupado = await _gerar_relatorio_contas_a_receber(inp_agrupado, db=db, current_user=usuario)
    assert res_agrupado["quantidade_contas"] == 1
    assert res_agrupado["total_devido"] == 100.0
    assert res_agrupado["detalhes"][0]["cliente"] == "John Doe"

