# Orquestrador LangGraph Endpoint Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the layered AI architecture (channels, orchestrator, direct agents) directly into the public endpoints (`ai_hub.py` and `whatsapp.py`).

**Architecture:** Extend `AssistantOrchestrator` to support streaming with `run_stream` and wire the FastApi endpoints up to correctly use `app.ai.channels` adpaters and the `AssistantOrchestrator` instead of direct calls to legacy models. Legacy stream functionality will be preserved as a fallback path in the orchestrator.

**Tech Stack:** FastAPI, Pydantic, Python Async Generators, Pytest

---

### Task 1: Extend AssistantOrchestrator with Streaming Support

**Files:**
- Modify: `sistema/app/ai/orchestrator/service.py`
- Modify: `sistema/tests/test_ai_orchestrator_facade.py`

- [x] **Step 1: Write the failing test**

```python
import pytest
from typing import AsyncGenerator
from app.ai.channels.types import ChannelMessage
from app.ai.orchestrator.service import AssistantOrchestrator

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
```

- [x] **Step 2: Run test to verify it fails**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_orchestrator_facade.py::test_assistant_orchestrator_run_stream_uses_legacy_stream_when_direct_disabled -v -q'`
Expected: FAIL with TypeError related to missing `legacy_stream_runner` argument.

- [x] **Step 3: Write minimal implementation**

```python
# Modify `__init__` in `sistema/app/ai/orchestrator/service.py`:
    def __init__(
        self, 
        legacy_runner: Callable[[dict[str, Any]], Any],
        legacy_stream_runner: Callable[[dict[str, Any]], Any] | None = None
    ) -> None:
        self.legacy_runner = legacy_runner
        self.legacy_stream_runner = legacy_stream_runner

# Add `run_stream` method to `AssistantOrchestrator`:
    async def run_stream(self, message: ChannelMessage) -> Any: # Returns AsyncGenerator
        from app.ai.graph.assistant import langgraph_enabled

        if direct_agents_enabled() and langgraph_enabled():
            # Future expansion for direct LangGraph stream execution
            # Fallback to legacy stream for now to satisfy this test step
            if self.legacy_stream_runner:
                 async for chunk in self.legacy_stream_runner(self._legacy_payload(message)):
                     yield chunk
        else:
            if self.legacy_stream_runner:
                async for chunk in self.legacy_stream_runner(self._legacy_payload(message)):
                    yield chunk
            else:
                yield "Streaming not supported by legacy runner configuration."

```

- [x] **Step 4: Run test to verify it passes**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_orchestrator_facade.py::test_assistant_orchestrator_run_stream_uses_legacy_stream_when_direct_disabled -v -q'`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add sistema/app/ai/orchestrator/service.py sistema/tests/test_ai_orchestrator_facade.py
git commit -m "feat(ai): extend AssistantOrchestrator with run_stream"
```

### Task 2: Implement direct agent LangGraph execution in Orchestrator Stream

**Files:**
- Modify: `sistema/app/ai/orchestrator/service.py`
- Modify: `sistema/tests/test_ai_orchestrator_facade.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_assistant_orchestrator_run_stream_uses_direct_langgraph_stream_when_enabled(monkeypatch):
    monkeypatch.setenv("V2_LANGGRAPH_DIRECT_AGENTS", "1")
    monkeypatch.setenv("V2_LANGGRAPH_ORCHESTRATION", "1")

    async def mock_langgraph_stream(*args, **kwargs):
        yield {"final_text": "langgraph stream"}

    import app.ai.orchestrator.service
    monkeypatch.setattr(app.ai.orchestrator.service, "run_assistant_v2_graph_stream", mock_langgraph_stream, raising=False)

    orchestrator = AssistantOrchestrator(
        legacy_runner=lambda p: None,
        legacy_stream_runner=lambda p: None
    )
    message = ChannelMessage(channel="web", text="teste stream", empresa_id=1, usuario_id=1, sessao_id="123")
    
    chunks = []
    async for chunk in orchestrator.run_stream(message):
        chunks.append(chunk)
        
    # We expect the orchestrator to yield the raw dict directly since it's the raw stream out of the graph
    assert chunks == [{"final_text": "langgraph stream"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_orchestrator_facade.py::test_assistant_orchestrator_run_stream_uses_direct_langgraph_stream_when_enabled -v -q'`
Expected: FAIL, might try to use `legacy_stream_runner` since it falls back currently.

- [ ] **Step 3: Write minimal implementation**

```python
# Add import at top or inside `run_stream`
from app.ai.graph.assistant import run_assistant_v2_graph_stream

# Update `run_stream` in `sistema/app/ai/orchestrator/service.py`:
    async def run_stream(self, message: ChannelMessage) -> Any:
        from app.ai.graph.assistant import langgraph_enabled

        payload = self._legacy_payload(message)
        
        if direct_agents_enabled() and langgraph_enabled():
            try:
                # Graph stream execution
                async for event in run_assistant_v2_graph_stream(
                    message=message.text,
                    empresa_id=message.empresa_id,
                    usuario_id=message.usuario_id,
                    thread_id=message.sessao_id,
                    payload=payload
                ):
                     yield event
                return
            except Exception as e:
                # Fallback on error
                pass

        if self.legacy_stream_runner:
            async for chunk in self.legacy_stream_runner(payload):
                yield chunk
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_orchestrator_facade.py::test_assistant_orchestrator_run_stream_uses_direct_langgraph_stream_when_enabled -v -q'`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sistema/app/ai/orchestrator/service.py sistema/tests/test_ai_orchestrator_facade.py
git commit -m "feat(ai): integrate langgraph stream in orchestrator"
```

### Task 3: Refactor /assistente/stream endpoint

**Files:**
- Modify: `sistema/app/routers/ai_hub.py`
- Modify: `sistema/tests/test_ai_hub_router.py` (Create if missing)

- [ ] **Step 1: Write the failing test**

```python
# in sistema/tests/test_ai_hub_router.py (create file)
import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_assistente_stream_endpoint_uses_orchestrator(monkeypatch):
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
    from app.dependencies import get_current_user_sem_banco
    from app.models.models import Usuario, Empresa
    app.dependency_overrides[get_current_user_sem_banco] = lambda: Usuario(id=1, empresa=Empresa(id=1))
    
    client = TestClient(app)
    response = client.post("/api/v1/ai/assistente/stream", json={"mensagem": "teste", "sessao_id": "123", "engine": "operational"})
    
    assert response.status_code == 200
    assert called is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_hub_router.py -v -q'`
Expected: FAIL, does not use orchestrator.

- [ ] **Step 3: Write minimal implementation**

```python
# In `sistema/app/routers/ai_hub.py` around line 1083
@router.post("/assistente/stream")
async def assistente_universal_stream(
    request: AIAssistenteRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    from app.services.cotte_ai_hub import assistente_unificado_stream, assistente_unificado_v2
    from fastapi.responses import StreamingResponse
    from app.ai.channels.web import from_web_payload
    from app.ai.orchestrator.service import AssistantOrchestrator
    import json

    if current_user.empresa:
        current_user.empresa.total_mensagens_ia = (
            current_user.empresa.total_mensagens_ia or 0
        ) + 1
        db.commit()

    engine = resolve_engine(request.engine)
    if engine == ENGINE_INTERNAL_COPILOT:
        raise HTTPException(status_code=400, detail="Use o endpoint /ai/copiloto-interno para o copiloto técnico.")
    if not is_engine_available_for_user(engine, is_superadmin=bool(getattr(current_user, "is_superadmin", False)), is_gestor=bool(getattr(current_user, "is_gestor", False))):
        raise HTTPException(status_code=403, detail="Engine solicitada indisponível.")

    # Convert request to dict and adapt to channel message
    payload_dict = request.model_dump()
    channel_msg = from_web_payload(payload_dict)
    
    # Ensure dependencies are available in metadata to the legacy payload if needed
    channel_msg.metadata["db"] = db
    channel_msg.metadata["current_user"] = current_user
    channel_msg.metadata["engine"] = engine
    channel_msg.metadata["request_id"] = _request_id_from_http(http_request)
    channel_msg.metadata["confirmation_token"] = getattr(request, "confirmation_token", None)
    channel_msg.metadata["override_args"] = getattr(request, "override_args", None)

    orchestrator = AssistantOrchestrator(
        legacy_runner=assistente_unificado_v2,
        legacy_stream_runner=assistente_unificado_stream
    )

    async def _stream_generator():
        # Wrap the orchestrator stream to yield SSE formatted strings if it yields raw dicts
        # If legacy_stream_runner yields formatted strings already, this will just pass them through
        async for chunk in orchestrator.run_stream(channel_msg):
            if isinstance(chunk, dict):
                 yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
            else:
                 yield chunk

    return StreamingResponse(_stream_generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_hub_router.py -v -q'`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sistema/app/routers/ai_hub.py sistema/tests/test_ai_hub_router.py
git commit -m "refactor(ai): integrate orchestrator into stream endpoint"
```

### Task 4: Refactor /assistente endpoint

**Files:**
- Modify: `sistema/app/routers/ai_hub.py`
- Modify: `sistema/tests/test_ai_hub_router.py`

- [ ] **Step 1: Write the failing test**

```python
# in sistema/tests/test_ai_hub_router.py
@pytest.mark.asyncio
async def test_assistente_endpoint_uses_orchestrator(monkeypatch):
    from app.main import app
    
    called = False
    def mock_orchestrator_run(*args, **kwargs):
        nonlocal called
        called = True
        from app.ai.channels.types import ChannelResponse
        return ChannelResponse(text="resposta mock")
        
    from app.ai.orchestrator.service import AssistantOrchestrator
    monkeypatch.setattr(AssistantOrchestrator, "run", mock_orchestrator_run)
    
    from app.dependencies import get_current_user_sem_banco
    from app.models.models import Usuario, Empresa
    app.dependency_overrides[get_current_user_sem_banco] = lambda: Usuario(id=1, empresa=Empresa(id=1))
    
    client = TestClient(app)
    response = client.post("/api/v1/ai/assistente", json={"mensagem": "teste", "sessao_id": "123", "engine": "operational"})
    
    assert response.status_code == 200
    assert called is True
    assert "resposta mock" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_hub_router.py::test_assistente_endpoint_uses_orchestrator -v -q'`
Expected: FAIL, orchestrator is not used.

- [ ] **Step 3: Write minimal implementation**

```python
# In `sistema/app/routers/ai_hub.py` around line 1130
@router.post("/assistente", response_model=AIResponse)
async def assistente_universal(
    request: AIAssistenteRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("ia", "leitura")),
):
    import os
    from app.services.cotte_ai_hub import assistente_unificado_stream, assistente_unificado_v2
    from app.ai.channels.web import from_web_payload
    from app.ai.orchestrator.service import AssistantOrchestrator

    if current_user.empresa:
        current_user.empresa.total_mensagens_ia = (
            current_user.empresa.total_mensagens_ia or 0
        ) + 1
        db.commit()

    engine = resolve_engine(request.engine)
    if engine == ENGINE_INTERNAL_COPILOT:
        raise HTTPException(status_code=400, detail="Use o endpoint /ai/copiloto-interno.")
    if not is_engine_available_for_user(engine, is_superadmin=bool(getattr(current_user, "is_superadmin", False)), is_gestor=bool(getattr(current_user, "is_gestor", False))):
        raise HTTPException(status_code=403, detail="Engine solicitada indisponível.")

    if os.getenv("USE_TOOL_CALLING", "true").lower() == "false":
        # Legacy old engine compatibility kept intact if flag is off
        from app.services.cotte_ai_hub import assistente_unificado_core
        return await assistente_unificado_core(...) # existing implementation
        
    payload_dict = request.model_dump()
    channel_msg = from_web_payload(payload_dict)
    
    channel_msg.metadata["db"] = db
    channel_msg.metadata["current_user"] = current_user
    channel_msg.metadata["engine"] = engine
    channel_msg.metadata["request_id"] = _request_id_from_http(http_request)

    # Legacy runner mapping handling logic inside the wrapper
    async def legacy_runner_wrapper(payload):
         return await assistente_unificado_v2(
             mensagem=payload["mensagem"],
             sessao_id=payload["sessao_id"],
             db=payload["metadata"]["db"],
             current_user=payload["metadata"]["current_user"],
             engine=payload["metadata"].get("engine", engine),
             request_id=payload["metadata"].get("request_id")
         )

    orchestrator = AssistantOrchestrator(
        legacy_runner=legacy_runner_wrapper,
        legacy_stream_runner=assistente_unificado_stream
    )

    response = await orchestrator.run(channel_msg)
    
    return AIResponse(
        resposta=response.text,
        tipo="assistente_v2",
        dados=response.metadata,
        sugestoes=[]
    )
```
*(Ensure await is added to orchestrator.run() in `service.py` if it uses async `legacy_runner_wrapper`! For simplicity, the `AssistantOrchestrator`'s `run` method must handle async or the `legacy_runner_wrapper` should be synchronous. To fix: update `run` to be `async def run` in `service.py`)*

If changing `run` to `async`:

```python
# Modify `run` in `sistema/app/ai/orchestrator/service.py`:
    async def run(self, message: ChannelMessage) -> ChannelResponse:
        import inspect
        legacy_payload = self._legacy_payload(message)
        if inspect.iscoroutinefunction(self.legacy_runner):
            result = await self.legacy_runner(legacy_payload)
        else:
            result = self.legacy_runner(legacy_payload)
        return self._to_channel_response(result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash -lc 'cd sistema && .venv/bin/python -m pytest tests/test_ai_hub_router.py::test_assistente_endpoint_uses_orchestrator -v -q'`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sistema/app/routers/ai_hub.py sistema/app/ai/orchestrator/service.py sistema/tests/test_ai_hub_router.py
git commit -m "refactor(ai): integrate orchestrator into main assistant endpoint"
```

