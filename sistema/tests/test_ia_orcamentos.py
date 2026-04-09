import pytest
from unittest.mock import patch, MagicMock
from app.services.ia_service import interpretar_mensagem, interpretar_comando_operador
from app.schemas.schemas import IAInterpretacaoOut
from app.services.cotte_ai_hub import AIResponse

@pytest.mark.asyncio
async def test_interpretar_mensagem_sucesso():
    """Testa a extração de dados de orçamento de uma mensagem em linguagem natural."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"cliente_nome":"João da Silva","servico":"Pintura de sala","valor":800.0,"desconto":10.0,"desconto_tipo":"percentual","observacoes":"Urgent","confianca":0.95}')]
    
    with patch("app.services.ia_service.client.messages.create", return_value=mock_response):
        resultado = await interpretar_mensagem("Pintura de sala para João da Silva por 800 reais com 10% de desconto urgente")
        
        assert isinstance(resultado, IAInterpretacaoOut)
        assert resultado.cliente_nome == "João da Silva"
        assert resultado.servico == "Pintura de sala"
        assert resultado.valor == 800.0
        assert resultado.desconto == 10.0
        assert resultado.desconto_tipo == "percentual"
        assert resultado.confianca == 0.95

@pytest.mark.asyncio
async def test_interpretar_comando_operador_ver_orcamento():
    """Testa a interpretação de um comando do operador para ver um orçamento."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"acao":"VER","orcamento_id":5,"valor":null,"desconto_tipo":"percentual","descricao":null,"num_item":null,"confianca":1.0}')]
    
    with patch("app.services.ia_service.client.messages.create", return_value=mock_response):
        resultado = await interpretar_comando_operador("ver orçamento 5")
        
        assert resultado["acao"] == "VER"
        assert resultado["orcamento_id"] == 5

@pytest.mark.asyncio
async def test_route_interpretar_orcamento_sucesso(client, admin_token):
    """Testa o endpoint /ai/orcamento/interpretar."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"cliente_nome":"João da Silva","servico":"Pintura de sala","valor":800.0,"desconto":10.0,"desconto_tipo":"percentual","observacoes":"Urgent","confianca":0.95}')]
    
    # Patch both instances of the client
    with patch("app.services.ia_service.client.messages.create", return_value=mock_response), \
         patch("app.services.cotte_ai_hub.client.messages.create", return_value=mock_response):
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.post("/api/v1/ai/orcamento/interpretar?mensagem=Pintura+de+sala+para+João", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["sucesso"] is True
        assert data["tipo_resposta"] == "orcamento_rascunho"
        assert data["dados"]["cliente_nome"] == "João da Silva"

@pytest.mark.asyncio
async def test_route_comando_operador_sucesso(client, admin_token):
    """Testa o endpoint /ai/operador/comando."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"acao":"VER","orcamento_id":5,"valor":null,"desconto_tipo":"percentual","descricao":null,"num_item":null,"confianca":1.0}')]

    # Patch both instances of the client
    with patch("app.services.ia_service.client.messages.create", return_value=mock_response), \
         patch("app.services.cotte_ai_hub.client.messages.create", return_value=mock_response):
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.post("/api/v1/ai/operador/comando?mensagem=ver+orcamento+5", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["sucesso"] is True
        assert data["tipo_resposta"] == "comando_operador"
        assert data["dados"]["acao"] == "VER"
        assert data["dados"]["orcamento_id"] == 5
