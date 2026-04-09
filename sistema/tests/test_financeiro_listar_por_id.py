"""
Testes para a correção de filtro por ID em contas e despesas.

Este teste valida que o parâmetro 'id' funciona corretamente nos endpoints:
- GET /financeiro/contas?id=X
- GET /financeiro/despesas?id=X

O problema original: o frontend chama Financeiro.listarDespesas({ id: contaId })
mas o backend ignorava o parâmetro id e retornava todas as despesas.

A solução: adicionar suporte ao parâmetro id em:
- router listar_contas() e listar_despesas()
- service listar_contas() e listar_despesas()
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import date, timedelta

from app.models.models import (
    ContaFinanceira, TipoConta, StatusConta, OrigemRegistro
)
from app.core.config import settings


@pytest_asyncio.fixture
async def contas_para_teste(db_session: AsyncSession, empresa_id: int) -> dict:
    """Cria 3 contas a receber e 3 despesas para testar o filtro por ID"""
    contas = []
    despesas = []
    
    # Criar 3 contas a receber
    for i in range(1, 4):
        conta = ContaFinanceira(
            empresa_id=empresa_id,
            tipo=TipoConta.RECEBER,
            descricao=f"Conta a receber {i}",
            valor=Decimal(f"{i * 100}.00"),
            status=StatusConta.PENDENTE,
            data_vencimento=date.today() + timedelta(days=i),
            origem=OrigemRegistro.SISTEMA,
            data_criacao=date.today()
        )
        db_session.add(conta)
        contas.append(conta)
    
    # Criar 3 despesas
    for i in range(1, 4):
        despesa = ContaFinanceira(
            empresa_id=empresa_id,
            tipo=TipoConta.PAGAR,
            descricao=f"Despesa {i}",
            valor=Decimal(f"{i * 50}.00"),
            status=StatusConta.PENDENTE,
            data_vencimento=date.today() + timedelta(days=i),
            origem=OrigemRegistro.SISTEMA,
            favorecido=f"Fornecedor {i}",
            data_criacao=date.today()
        )
        db_session.add(despesa)
        despesas.append(despesa)
    
    await db_session.commit()
    
    # Refresh para obter IDs
    for c in contas + despesas:
        await db_session.refresh(c)
    
    return {
        "contas": contas,
        "despesas": despesas,
        "empresa_id": empresa_id
    }


@pytest.mark.asyncio
async def test_listar_contas_com_filtro_id(client: AsyncClient, admin_token: str, contas_para_teste: dict):
    """Testa que GET /financeiro/contas?id=X retorna apenas a conta com ID X"""
    conta_selecionada = contas_para_teste["contas"][1]  # Segunda conta (id = ...)
    conta_id = conta_selecionada.id
    
    # Listar com filtro por ID
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/contas",
        params={"id": conta_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200, f"Erro: {response.json()}"
    data = response.json()
    
    # Deve retornar exatamente 1 conta
    assert len(data) == 1, f"Esperava 1 conta, receive {len(data)}"
    assert data[0]["id"] == conta_id
    assert data[0]["descricao"] == conta_selecionada.descricao
    assert data[0]["valor"] == float(conta_selecionada.valor)


@pytest.mark.asyncio
async def test_listar_despesas_com_filtro_id(client: AsyncClient, admin_token: str, contas_para_teste: dict):
    """Testa que GET /financeiro/despesas?id=X retorna apenas a despesa com ID X"""
    despesa_selecionada = contas_para_teste["despesas"][2]  # Terceira despesa
    despesa_id = despesa_selecionada.id
    
    # Listar com filtro por ID
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/despesas",
        params={"id": despesa_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200, f"Erro: {response.json()}"
    data = response.json()
    
    # Deve retornar exatamente 1 despesa
    assert len(data) == 1, f"Esperava 1 despesa, receive {len(data)}"
    assert data[0]["id"] == despesa_id
    assert data[0]["descricao"] == despesa_selecionada.descricao
    assert float(data[0]["valor"]) == float(despesa_selecionada.valor)
    assert data[0]["favorecido"] == despesa_selecionada.favorecido


@pytest.mark.asyncio
async def test_listar_contas_sem_filtro_retorna_todas(client: AsyncClient, admin_token: str, contas_para_teste: dict):
    """Testa que GET /financeiro/contas sem filtro retorna todas as contas"""
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/contas",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Deve retornar pelo menos as 3 contas criadas
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_listar_despesas_sem_filtro_retorna_todas(client: AsyncClient, admin_token: str, contas_para_teste: dict):
    """Testa que GET /financeiro/despesas sem filtro retorna todas as despesas"""
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/despesas",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Deve retornar pelo menos as 3 despesas criadas
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_listar_contas_id_inexistente(client: AsyncClient, admin_token: str):
    """Testa filtro por ID inexistente retorna lista vazia"""
    id_inexistente = 999999
    
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/contas",
        params={"id": id_inexistente},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_listar_despesas_id_inexistente(client: AsyncClient, admin_token: str):
    """Testa filtro por ID inexistente retorna lista vazia"""
    id_inexistente = 999999
    
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/despesas",
        params={"id": id_inexistente},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_listar_contas_com_id_e_outros_filtros(client: AsyncClient, admin_token: str, contas_para_teste: dict):
    """Testa que filtro por ID funciona combinado com outros filtros"""
    conta_selecionada = contas_para_teste["contas"][0]
    conta_id = conta_selecionada.id
    
    # Deve funcionar mesmo com outros parâmetros (que serão ignorados se não combináveis)
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/contas",
        params={"id": conta_id, "tipo": "receber"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == conta_id
    assert data[0]["tipo"] == "receber"
