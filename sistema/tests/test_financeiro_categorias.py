import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import CategoriaFinanceira
from app.schemas.financeiro import CategoriaFinanceiraCreate, TipoCategoria
from app.core.config import settings


@pytest_asyncio.fixture
async def categoria_ativa_existente(db_session: AsyncSession, empresa_id: int) -> CategoriaFinanceira:
    categoria = CategoriaFinanceira(
        empresa_id=empresa_id,
        nome="Categoria Teste Ativa",
        tipo="despesa",
        ativo=True,
        icone="💰",
        cor="#000000"
    )
    db_session.add(categoria)
    await db_session.commit()
    await db_session.refresh(categoria)
    return categoria

@pytest_asyncio.fixture
async def categoria_inativa_existente(db_session: AsyncSession, empresa_id: int) -> CategoriaFinanceira:
    categoria = CategoriaFinanceira(
        empresa_id=empresa_id,
        nome="Categoria Teste Inativa",
        tipo="despesa",
        ativo=False,
        icone="💰",
        cor="#000000"
    )
    db_session.add(categoria)
    await db_session.commit()
    await db_session.refresh(categoria)
    return categoria

@pytest.mark.asyncio
async def test_criar_categoria_financeira_sucesso(client: AsyncClient, admin_token: str, empresa_id: int):
    response = await client.post(
        f"{settings.API_V1_STR}/financeiro/categorias",
        json={
            "nome": "Nova Categoria",
            "tipo": "receita",
            "cor": "#FFFFFF",
            "icone": "💸",
            "ordem": 1
        },
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Nova Categoria"
    assert data["tipo"] == "receita"
    assert data["empresa_id"] == empresa_id
    assert data["ativo"] is True

@pytest.mark.asyncio
async def test_criar_categoria_financeira_duplicada(client: AsyncClient, admin_token: str, categoria_ativa_existente: CategoriaFinanceira):
    response = await client.post(
        f"{settings.API_V1_STR}/financeiro/categorias",
        json={
            "nome": categoria_ativa_existente.nome,
            "tipo": categoria_ativa_existente.tipo,
            "cor": "#FFFFFF",
            "icone": "💸",
            "ordem": 1
        },
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data, f"Expected error in: {data}"
    assert "Já existe uma categoria ativa com o mesmo nome e tipo." in data["error"]["message"]

@pytest.mark.asyncio
async def test_criar_categoria_financeira_duplicada_com_inativa_permite(client: AsyncClient, admin_token: str, categoria_inativa_existente: CategoriaFinanceira, empresa_id: int):
    # Deve permitir criar uma categoria com mesmo nome/tipo se a existente estiver inativa
    response = await client.post(
        f"{settings.API_V1_STR}/financeiro/categorias",
        json={
            "nome": categoria_inativa_existente.nome,
            "tipo": categoria_inativa_existente.tipo,
            "cor": "#FFFFFF",
            "icone": "💸",
            "ordem": 1
        },
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == categoria_inativa_existente.nome
    assert data["tipo"] == categoria_inativa_existente.tipo
    assert data["empresa_id"] == empresa_id
    assert data["ativo"] is True

@pytest.mark.asyncio
async def test_listar_categorias_financeiras(client: AsyncClient, admin_token: str, categoria_ativa_existente: CategoriaFinanceira):
    response = await client.get(
        f"{settings.API_V1_STR}/financeiro/categorias",
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(c["nome"] == categoria_ativa_existente.nome for c in data)

@pytest.mark.asyncio
async def test_atualizar_categoria_financeira_sucesso(client: AsyncClient, admin_token: str, categoria_ativa_existente: CategoriaFinanceira):
    response = await client.patch(
        f"{settings.API_V1_STR}/financeiro/categorias/{categoria_ativa_existente.id}",
        json={
            "nome": "Nome Atualizado",
            "icone": "📈"
        },
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "Nome Atualizado"
    assert data["icone"] == "📈"

@pytest.mark.asyncio
async def test_atualizar_categoria_financeira_para_duplicada(client: AsyncClient, admin_token: str, db_session: AsyncSession, empresa_id: int, categoria_ativa_existente: CategoriaFinanceira):
    # Cria uma segunda categoria ativa para forçar duplicidade na atualização da primeira
    nome_outra = "Outra Categoria"
    tipo_outra = "despesa"
    outra_categoria = CategoriaFinanceira(
        empresa_id=empresa_id,
        nome=nome_outra,
        tipo=tipo_outra,
        ativo=True,
        icone="💸",
        cor="#FF0000"
    )
    db_session.add(outra_categoria)
    target_id = categoria_ativa_existente.id
    await db_session.commit()

    response = await client.patch(
        f"{settings.API_V1_STR}/financeiro/categorias/{target_id}",
        json={
            "nome": nome_outra,  # Tenta atualizar para um nome já existente e ativo
            "tipo": tipo_outra
        },
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data, f"Expected error in: {data}"
    assert "Já existe uma categoria ativa com o mesmo nome e tipo." in data["error"]["message"]

@pytest.mark.asyncio
async def test_excluir_categoria_financeira_sucesso(client: AsyncClient, admin_token: str, categoria_ativa_existente: CategoriaFinanceira):
    response = await client.delete(
        f"{settings.API_V1_STR}/financeiro/categorias/{categoria_ativa_existente.id}",
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 204

    # Verifica se a categoria foi desativada (soft delete)
    response_get = await client.get(
        f"{settings.API_V1_STR}/financeiro/categorias?ativas=false", # buscar por inativas
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response_get.status_code == 200
    data = response_get.json()
    assert any(c["id"] == categoria_ativa_existente.id and c["ativo"] is False for c in data)

@pytest.mark.asyncio
async def test_excluir_categoria_financeira_nao_encontrada(client: AsyncClient, admin_token: str):
    response = await client.delete(
        f"{settings.API_V1_STR}/financeiro/categorias/99999",
        headers={
            "Authorization": f"Bearer {admin_token}"
        }
    )
    assert response.status_code == 404
    data = response.json()
    assert "error" in data, f"Expected error in: {data}"
    assert "Categoria não encontrada." in data["error"]["message"]
