import pytest
from fastapi.testclient import TestClient


def test_assistente_stream_endpoint_uses_orchestrator(monkeypatch):
    from app.main import app
    from app.services.cotte_ai_hub import assistente_unificado_stream
    
    # We will test if the orchestrator structure is built inside the endpoint
    called = False
    async def mock_orchestrator_stream(*args, **kwargs):
        nonlocal called
        called = True
        yield "data: ok\n\n"
        
    from app.ai.orchestrator.service import AssistantOrchestrator
    monkeypatch.setattr(AssistantOrchestrator, "run_stream", mock_orchestrator_stream)
    
    # Needs valid auth mock if the router is protected
    from app.core.auth import get_usuario_atual
    from app.models.models import Usuario, Empresa
    app.dependency_overrides[get_usuario_atual] = lambda: Usuario(id=1, empresa_id=1, empresa=Empresa(id=1), is_superadmin=True)
    
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/assistente/stream", json={"mensagem": "teste", "sessao_id": "123", "engine": "operational"})
    
        assert response.status_code == 200
        assert called is True


def test_assistente_endpoint_uses_orchestrator(monkeypatch):
    from app.main import app
    
    called = False
    async def mock_orchestrator_run(*args, **kwargs):
        nonlocal called
        called = True
        from app.ai.channels.types import ChannelResponse
        return ChannelResponse(text="resposta mock", metadata={"debug": "test"})
        
    from app.ai.orchestrator.service import AssistantOrchestrator
    monkeypatch.setattr(AssistantOrchestrator, "run", mock_orchestrator_run)
    
    from app.core.auth import get_usuario_atual
    from app.models.models import Usuario, Empresa
    app.dependency_overrides[get_usuario_atual] = lambda: Usuario(id=1, empresa_id=1, empresa=Empresa(id=1), is_superadmin=True)
    
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/assistente", json={"mensagem": "teste", "sessao_id": "123", "engine": "operational"})
    
        assert response.status_code == 200
        assert called is True
        assert "resposta mock" in response.text
