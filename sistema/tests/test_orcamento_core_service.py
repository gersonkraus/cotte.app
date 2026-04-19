import pytest
from unittest.mock import Mock, MagicMock
from decimal import Decimal

def test_criar_orcamento_core_aceita_item_com_valor_zero(monkeypatch):
    # RED: testar que o fluxo core do orçamento aceita valor unitario ZERO (0.0)
    
    # Previne quebra por validações de BD ou limite de plano durante o teste unitário
    monkeypatch.setattr("app.services.orcamento_core_service.checar_limite_orcamentos", Mock())
    monkeypatch.setattr("app.services.orcamento_core_service.gerar_numero", Mock(return_value=("O-100", 100)))
    monkeypatch.setattr("app.services.orcamento_core_service._resolver_agendamento_modo_criacao", Mock(return_value="NAO_USA"))
    
    from app.services.orcamento_core_service import criar_orcamento_core

    mock_db = MagicMock()
    mock_db.flush.return_value = None # Evita o loop infinito / erros do banco
    
    mock_empresa = Mock()
    mock_empresa.id = 1
    mock_empresa.proximo_numero_orcamento = 100
    mock_empresa.texto_observacoes = ""
    mock_empresa.validade_orcamento_dias = 7
    mock_empresa.agendamento_escolha_obrigatoria = False
    mock_user = Mock()
    
    monkeypatch.setattr("app.services.financeiro_service.aplicar_regra_no_orcamento", Mock())
    mock_user.id = 1
    
    # Faz com que o mock do cliente seja resolvido corretamente
    mock_cliente = Mock()
    mock_cliente.id = 1
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_cliente

    itens = [
        {
            "descricao": "Serviço sem preço",
            "quantidade": Decimal("1.0"),
            "valor_unit": Decimal("0.0"),
            "servico_id": None
        }
    ]
    
    # Executa o core
    try:
        orcamento = criar_orcamento_core(
            db=mock_db,
            empresa=mock_empresa,
            usuario_criador=mock_user,
            cliente_id=1,
            itens=itens
        )
        assert orcamento is not None
        
        # Pega os argumentos que foram passados pro mock_db.add (ItemOrcamento está lá no meio)
        added_objects = [call[0][0] for call in mock_db.add.call_args_list]
        from app.models.models import ItemOrcamento
        item_added = next((obj for obj in added_objects if isinstance(obj, ItemOrcamento)), None)
        assert item_added is not None
        assert item_added.valor_unit == Decimal("0.0")
        assert item_added.total == Decimal("0.0")
        
    except Exception as e:
        pytest.fail(f"Criar orçamento core falhou inesperadamente: {e}")
