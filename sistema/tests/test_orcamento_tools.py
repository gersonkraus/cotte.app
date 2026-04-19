from unittest.mock import Mock, MagicMock
from app.services.ai_tools.orcamento_tools import _resolver_itens, CriarOrcamentoInput

def test_item_orcamento_input_allows_zero_value():
    from app.services.ai_tools.orcamento_tools import ItemOrcamentoInput
    item = ItemOrcamentoInput(descricao="Serviço vazio", quantidade=1.0, valor_unit=0.0)
    assert item.valor_unit == 0.0

def test_item_orcamento_input_rejects_negative_value():
    import pytest
    from pydantic import ValidationError
    from app.services.ai_tools.orcamento_tools import ItemOrcamentoInput
    with pytest.raises(ValidationError):
        ItemOrcamentoInput(descricao="Erro", quantidade=1.0, valor_unit=-1.0)

def test_resolver_itens_permite_valor_zero():
    mock_db = MagicMock()
    # Emular db.query().filter().limit().all() retornando vazio
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    mock_limit = mock_filter.limit.return_value
    mock_limit.all.return_value = []
    
    mock_user = Mock()
    mock_user.empresa_id = 1
    
    inp = CriarOrcamentoInput(
        cliente_nome="Ana Julia",
        itens=[{"descricao": "Serviço", "quantidade": 1.0, "valor_unit": 0.0}]
    )
    
    itens_resolvidos, materiais_novos, err = _resolver_itens(inp, mock_db, mock_user)
    
    assert err is None, f"Erro inesperado: {err}"
    assert len(itens_resolvidos) == 1
    assert itens_resolvidos[0]["valor_unit"] == 0.0
