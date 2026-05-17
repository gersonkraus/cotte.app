import pytest
from typing import AsyncGenerator

from app.ai.channels.types import ChannelMessage, ChannelResponse
from app.ai.orchestrator import AssistantOrchestrator, direct_agents_enabled


def test_direct_agents_enabled_false_por_default(monkeypatch):
    monkeypatch.delenv("V2_LANGGRAPH_DIRECT_AGENTS", raising=False)

    assert direct_agents_enabled() is False


def test_direct_agents_enabled_true_com_env_truthy(monkeypatch):
    for value in ("1", "true", "yes", "on"):
        monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", value)

        assert direct_agents_enabled() is True


def test_direct_agents_enabled_false_com_env_falsey(monkeypatch):
    for value in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", value)

        assert direct_agents_enabled() is False


def test_orchestrator_run_chama_legado_com_payload_correto():
    chamadas = []

    def legacy_runner(payload):
        chamadas.append(payload)
        return "ok"

    message = ChannelMessage(
        channel="whatsapp",
        text="listar orcamentos",
        empresa_id=5,
        usuario_id=7,
        sessao_id="sess-123",
        external_id="msg-456",
        phone="5511999999999",
        attachments=[{"type": "image", "url": "https://example.test/a.png"}],
        metadata={"source": "evolution"},
    )

    response = AssistantOrchestrator(legacy_runner).run(message)

    assert response.text == "ok"
    assert chamadas == [
        {
            "mensagem": "listar orcamentos",
            "empresa_id": 5,
            "usuario_id": 7,
            "sessao_id": "sess-123",
            "channel": "whatsapp",
            "external_id": "msg-456",
            "phone": "5511999999999",
            "attachments": [{"type": "image", "url": "https://example.test/a.png"}],
            "metadata": {"source": "evolution"},
        }
    ]


def test_orchestrator_run_isola_payload_legado_de_mutacoes_aninhadas():
    def legacy_runner(payload):
        payload["attachments"][0]["meta"]["size"] = 99
        payload["metadata"]["context"]["step"] = "mutado"
        return "ok"

    message = ChannelMessage(
        channel="web",
        text="oi",
        empresa_id=1,
        attachments=[{"name": "a.png", "meta": {"size": 10}}],
        metadata={"context": {"step": "original"}},
    )

    AssistantOrchestrator(legacy_runner).run(message)

    assert message.attachments == [{"name": "a.png", "meta": {"size": 10}}]
    assert message.metadata == {"context": {"step": "original"}}


def test_orchestrator_run_converte_dict_para_channel_response():
    def legacy_runner(_payload):
        return {"resposta": "texto legado", "metadata": {"engine": "legacy"}}

    message = ChannelMessage(channel="web", text="oi", empresa_id=1)

    response = AssistantOrchestrator(legacy_runner).run(message)

    assert isinstance(response, ChannelResponse)
    assert response.text == "texto legado"
    assert response.metadata == {"engine": "legacy"}


def test_orchestrator_run_isola_metadata_do_retorno_legado_de_mutacoes_aninhadas():
    legacy_result = {"text": "ok", "metadata": {"context": {"step": "original"}}}

    def legacy_runner(_payload):
        return legacy_result

    message = ChannelMessage(channel="web", text="oi", empresa_id=1)

    response = AssistantOrchestrator(legacy_runner).run(message)
    legacy_result["metadata"]["context"]["step"] = "mutado"

    assert response.metadata == {"context": {"step": "original"}}


@pytest.mark.parametrize(
    ("legacy_result", "expected_text"),
    [
        (
            {
                "text": "texto principal",
                "resposta": "resposta legado",
                "content": "conteudo legado",
                "message": "mensagem legado",
            },
            "texto principal",
        ),
        (
            {
                "resposta": "resposta legado",
                "content": "conteudo legado",
                "message": "mensagem legado",
            },
            "resposta legado",
        ),
        (
            {"content": "conteudo legado", "message": "mensagem legado"},
            "conteudo legado",
        ),
        ({"message": "mensagem legado"}, "mensagem legado"),
    ],
)
def test_orchestrator_run_respeita_precedencia_de_texto_em_dict_legado(
    legacy_result,
    expected_text,
):
    def legacy_runner(_payload):
        return legacy_result

    message = ChannelMessage(channel="web", text="oi", empresa_id=1)

    response = AssistantOrchestrator(legacy_runner).run(message)

    assert response.text == expected_text


@pytest.mark.parametrize("metadata", ["x", ["invalid"]])
def test_orchestrator_run_ignora_metadata_legado_nao_dict(metadata):
    def legacy_runner(_payload):
        return {"text": "ok", "metadata": metadata}

    message = ChannelMessage(channel="web", text="oi", empresa_id=1)

    response = AssistantOrchestrator(legacy_runner).run(message)

    assert response.metadata == {}


def test_orchestrator_run_preserva_channel_response():
    expected = ChannelResponse(text="pronto", metadata={"source": "test"})

    def legacy_runner(_payload):
        return expected

    message = ChannelMessage(channel="web", text="oi", empresa_id=1)

    response = AssistantOrchestrator(legacy_runner).run(message)

    assert response is expected


@pytest.mark.asyncio
async def test_assistant_orchestrator_run_stream_uses_legacy_stream_when_direct_disabled(monkeypatch):
    monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", "0")

    async def mock_legacy_stream(payload: dict) -> AsyncGenerator[str, None]:
        yield f"legacy stream: {payload['mensagem']}"

    orchestrator = AssistantOrchestrator(
        legacy_runner=lambda p: None,
        legacy_stream_runner=mock_legacy_stream
    )
    message = ChannelMessage(channel="web", text="teste stream", empresa_id=1, usuario_id=1, sessao_id="123")
    
    chunks = []
    async for chunk in orchestrator.run_stream(message):
        chunks.append(chunk)
        
    assert chunks == ["legacy stream: teste stream"]

@pytest.mark.asyncio
async def test_assistant_orchestrator_run_stream_uses_direct_langgraph_stream_when_enabled(monkeypatch):
    monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", "1")
    monkeypatch.setenv("V2_LANGGRAPH_ORCHESTRATION", "1")

    async def mock_langgraph_stream(*args, **kwargs):
        yield {"final_text": "langgraph stream"}

    import sys
    from unittest.mock import MagicMock
    mock_module = MagicMock()
    mock_module.langgraph_enabled.return_value = True
    mock_module.run_assistant_v2_graph_stream = mock_langgraph_stream
    monkeypatch.setitem(sys.modules, "app.ai.graph.assistant", mock_module)

    import app.ai.orchestrator.service

    orchestrator = AssistantOrchestrator(
        legacy_runner=lambda p: None,
        legacy_stream_runner=lambda p: None
    )
    message = ChannelMessage(channel="web", text="teste stream", empresa_id=1, usuario_id=1, sessao_id="123")
    
    chunks = []
    async for chunk in orchestrator.run_stream(message):
        chunks.append(chunk)
        
    assert chunks == [{"final_text": "langgraph stream"}]
