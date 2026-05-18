import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from app.ai.rag.schema_registry import SchemaRegistry, TableSchema


def test_table_schema_to_prompt_line():
    t = TableSchema(table="orcamentos", columns=["id", "empresa_id", "valor_total"], description="Tabela de orçamentos")
    line = t.to_prompt_line()
    assert "orcamentos" in line
    assert "id" in line
    assert "valor_total" in line


def test_format_schema_context_vazio():
    result = SchemaRegistry.format_schema_context([])
    assert result == ""


def test_format_schema_context_com_tabelas():
    tables = [
        TableSchema(table="orcamentos", columns=["id", "empresa_id"], description="Orçamentos"),
        TableSchema(table="clientes", columns=["id", "nome"], description="Clientes"),
    ]
    ctx = SchemaRegistry.format_schema_context(tables)
    assert "orcamentos" in ctx
    assert "clientes" in ctx
    assert ":empresa_id" in ctx


@pytest.mark.asyncio
async def test_get_relevant_tables_sem_db():
    result = await SchemaRegistry.get_relevant_tables("ranking clientes", db=None)
    assert result == []


@pytest.mark.asyncio
async def test_get_relevant_tables_com_falha_retorna_lista_vazia():
    """Testa que exceptions no search_schema retornam []."""
    db = MagicMock()

    # Usar monkeypatch via patch do módulo importado
    with patch("app.ai.rag.service.SemanticRAGService.search_schema", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = Exception("pgvector indisponível")
        result = await SchemaRegistry.get_relevant_tables("ranking", db=db)
        assert result == []


@pytest.mark.asyncio
async def test_get_relevant_tables_mapeia_resultado():
    """Testa mapeamento correto de resultados do search_schema."""
    db = MagicMock()

    mock_idx = MagicMock()
    mock_idx.table_name = "orcamentos"
    mock_idx.description = "Tabela de orçamentos"
    mock_idx.schema_json = {"columns": [{"name": "id"}, {"name": "empresa_id"}]}

    with patch("app.ai.rag.service.SemanticRAGService.search_schema", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [mock_idx]
        result = await SchemaRegistry.get_relevant_tables("orçamentos", db=db)

        assert len(result) == 1
        assert result[0].table == "orcamentos"
        assert "id" in result[0].columns
        assert "empresa_id" in result[0].columns
