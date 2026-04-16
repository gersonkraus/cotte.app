import pytest
from unittest.mock import patch
from sqlalchemy import select
from app.services.ia_service import interpretar_mensagem, interpretar_comando_operador
from app.schemas.schemas import IAInterpretacaoOut
from app.models.models import ItemOrcamento, Servico


def _fake_chat_response(content: str) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

@pytest.mark.asyncio
async def test_interpretar_mensagem_sucesso():
    """Testa a extração de dados de orçamento de uma mensagem em linguagem natural."""

    async def fake_chat(*args, **kwargs):
        return _fake_chat_response(
            '{"cliente_nome":"João da Silva","servico":"Pintura de sala","valor":800.0,"desconto":10.0,"desconto_tipo":"percentual","observacoes":"Urgent","confianca":0.95}'
        )

    with patch("app.services.ia_service.ia_service.chat", side_effect=fake_chat):
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

    async def fake_chat(*args, **kwargs):
        return _fake_chat_response(
            '{"acao":"VER","orcamento_id":5,"valor":null,"desconto_tipo":"percentual","descricao":null,"num_item":null,"confianca":1.0}'
        )

    with patch("app.services.ia_service.ia_service.chat", side_effect=fake_chat):
        resultado = await interpretar_comando_operador("ver orçamento 5")
        
        assert resultado["acao"] == "VER"
        assert resultado["orcamento_id"] == 5

@pytest.mark.asyncio
async def test_route_interpretar_orcamento_sucesso(client, admin_token):
    """Testa o endpoint /ai/orcamento/interpretar."""

    async def fake_chat(*args, **kwargs):
        return _fake_chat_response(
            '{"cliente_nome":"João da Silva","servico":"Pintura de sala","valor":800.0,"desconto":10.0,"desconto_tipo":"percentual","observacoes":"Urgent","confianca":0.95}'
        )

    with patch("app.services.ia_service.ia_service.chat", side_effect=fake_chat):
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

    async def fake_chat(*args, **kwargs):
        return _fake_chat_response(
            '{"acao":"VER","orcamento_id":5,"valor":null,"desconto_tipo":"percentual","descricao":null,"num_item":null,"confianca":1.0}'
        )

    with patch("app.services.ia_service.ia_service.chat", side_effect=fake_chat):
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.post("/api/v1/ai/operador/comando?mensagem=ver+orcamento+5", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["sucesso"] is True
        assert data["tipo_resposta"] == "comando_operador"
        assert data["dados"]["acao"] == "VER"
        assert data["dados"]["orcamento_id"] == 5


@pytest.mark.asyncio
async def test_confirmar_orcamento_vincula_servico_existente_catalogo(
    client,
    admin_token,
    db_session,
    empresa_id,
):
    servico = Servico(
        empresa_id=empresa_id,
        nome="Carrinho do toreto",
        preco_padrao=123.0,
        ativo=True,
    )
    db_session.add(servico)
    await db_session.commit()
    await db_session.refresh(servico)

    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "cliente_nome": "Nicollas da silva",
        "servico": "carrinho do toreto",
        "valor": 123.0,
        "desconto": 0.0,
        "desconto_tipo": "percentual",
        "observacoes": "teste integração catálogo",
        "cadastrar_materiais_novos": False,
    }
    response = await client.post(
        "/api/v1/ai/orcamento/confirmar",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sucesso"] is True
    assert body["tipo_resposta"] == "orcamento_criado"
    orcamento_id = int(body["dados"]["id"])

    item_q = await db_session.execute(
        select(ItemOrcamento).where(ItemOrcamento.orcamento_id == orcamento_id)
    )
    item = item_q.scalar_one()
    assert item.servico_id == servico.id
