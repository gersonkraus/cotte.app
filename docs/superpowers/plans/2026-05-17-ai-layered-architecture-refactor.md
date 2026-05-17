# AI Layered Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refatorar amplamente o assistente IA para uma arquitetura em camadas, mantendo contratos públicos e reduzindo risco por flags, testes de contrato e migração incremental.

**Architecture:** A refatoração preserva os endpoints atuais e cria camadas internas explícitas para canal, orquestração, agentes, execução de tools e observabilidade. O fluxo legado em `sistema/app/services/cotte_ai_hub.py` continua como fallback até que cada domínio prove equivalência por testes.

**Tech Stack:** FastAPI, SQLAlchemy, LiteLLM, LangGraph, pgvector, pytest, JavaScript Vanilla, SSE via `StreamingResponse`.

---

## Baseline Observado

Worktree: `/home/gk/Projeto-izi/.worktrees/refactor-ai-layered-architecture`

Ambiente Python local criado em `sistema/.venv` porque o sistema global bloqueia `pip install` por PEP 668.

Comando executado:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_assistant_langgraph.py tests/test_code_rag_service.py -q
```

Resultado atual:

```text
1 failed, 4 passed
FAILED tests/test_assistant_langgraph.py::test_langgraph_enabled_por_flag_legada
```

Falha de base: `USE_LANGGRAPH_ASSISTANT=true` não ativa `langgraph_enabled()` quando `V2_LANGGRAPH_ORCHESTRATION` está ausente.

---

## File Structure

Arquivos existentes a modificar:

- `sistema/app/ai/graph/assistant.py`: manter grafo LangGraph, corrigir flags, adicionar opção de execução direta por agente atrás de flag.
- `sistema/app/ai/agents/supervisor.py`: corrigir logger e cobrir fallback de parsing.
- `sistema/app/ai/agents/base.py`: corrigir tipo de `metadata` e manter contrato de resposta dos agentes.
- `sistema/app/routers/ai_hub.py`: manter contratos atuais dos endpoints e usar facade de canal apenas internamente quando flag ativada.
- `sistema/app/routers/whatsapp.py`: manter webhook Evolution e preparar adaptação para contrato de canal sem mudar payload externo.
- `sistema/app/services/cotte_ai_hub.py`: manter fallback legado; reduzir chamadas diretas gradualmente.
- `sistema/app/services/assistant_engine_registry.py`: adicionar flags novas para rollout controlado.

Arquivos novos a criar:

- `sistema/app/ai/channels/__init__.py`: exporta contratos de canal.
- `sistema/app/ai/channels/types.py`: modelos `ChannelKind`, `ChannelMessage`, `ChannelResponse`.
- `sistema/app/ai/channels/web.py`: normalização do chat web atual para `ChannelMessage`.
- `sistema/app/ai/channels/whatsapp.py`: normalização do webhook Evolution para `ChannelMessage`.
- `sistema/app/ai/channels/voice.py`: normalização de áudio web/WhatsApp para `ChannelMessage`.
- `sistema/app/ai/orchestrator/__init__.py`: exporta facade do orquestrador.
- `sistema/app/ai/orchestrator/service.py`: facade `AssistantOrchestrator` que escolhe LangGraph direto ou legado.
- `sistema/app/ai/agents/tool_runner.py`: loop de tool calling por agente usando `tool_executor.execute`.
- `sistema/app/ai/observability/__init__.py`: exporta helpers de eventos.
- `sistema/app/ai/observability/events.py`: eventos padronizados para SSE e logs.

Testes a criar/modificar:

- `sistema/tests/test_assistant_langgraph.py`: flags, supervisor e roteamento básico.
- `sistema/tests/test_ai_channels_contract.py`: contrato dos canais.
- `sistema/tests/test_ai_agent_tool_runner.py`: execução de tool calls por agente sem chamar LLM real.
- `sistema/tests/test_ai_orchestrator_facade.py`: fallback legado e flag de execução direta.
- `sistema/tests/test_assistente_unificado_v2.py`: regressão do fluxo legado.
- `sistema/tests/test_ai_tool_routing.py`: obrigatório se descrições de tools/gatilhos forem alteradas.

---

### Task 1: Corrigir Baseline LangGraph E Supervisor

**Files:**
- Modify: `sistema/app/ai/graph/assistant.py:62-65`
- Modify: `sistema/app/ai/agents/supervisor.py:1-56`
- Modify: `sistema/tests/test_assistant_langgraph.py:1-19`

- [ ] **Step 1: Escrever teste para fallback de parsing do supervisor**

Adicionar a `sistema/tests/test_assistant_langgraph.py`:

```python
import pytest

from app.ai.agents.supervisor import SupervisorAgent


@pytest.mark.asyncio
async def test_supervisor_fallback_quando_modelo_retorna_json_invalido(monkeypatch):
    async def fake_call(self, messages, **kwargs):
        class FakeResponse:
            content = "nao eh json"

        return FakeResponse()

    monkeypatch.setattr(SupervisorAgent, "__call__", fake_call)

    result = await SupervisorAgent().route([{"role": "user", "content": "ola"}])

    assert result.next_agent == "ConversationalAgent"
    assert "Fallback" in result.reasoning
```

- [ ] **Step 2: Rodar teste para confirmar falha atual**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_assistant_langgraph.py -q
```

Expected: falha em `test_langgraph_enabled_por_flag_legada` e/ou erro de `logger` quando o teste de fallback executar.

- [ ] **Step 3: Implementar correção mínima de flags**

Alterar `sistema/app/ai/graph/assistant.py`:

```python
def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def langgraph_enabled() -> bool:
    """Verifica se a orquestração via LangGraph deve ser utilizada."""
    return _env_flag("V2_LANGGRAPH_ORCHESTRATION") or _env_flag("USE_LANGGRAPH_ASSISTANT")
```

- [ ] **Step 4: Implementar logger no supervisor**

Alterar início de `sistema/app/ai/agents/supervisor.py`:

```python
"""Supervisor Agent for routing to specialized agents."""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Literal

from pydantic import BaseModel, Field

from app.ai.agents.base import BaseAgent


logger = logging.getLogger(__name__)
```

Manter o restante da classe e remover imports não usados `Any` e `AgentResponse`.

- [ ] **Step 5: Rodar testes focados**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_assistant_langgraph.py tests/test_code_rag_service.py -q
```

Expected: `5 passed` ou mais, conforme os testes adicionados.

- [ ] **Step 6: Commit de checkpoint, se autorizado pelo usuário**

Run:

```bash
git add sistema/app/ai/graph/assistant.py sistema/app/ai/agents/supervisor.py sistema/tests/test_assistant_langgraph.py
git commit -m "test: harden langgraph supervisor baseline"
```

---

### Task 2: Criar Contrato Interno De Canais

**Files:**
- Create: `sistema/app/ai/channels/__init__.py`
- Create: `sistema/app/ai/channels/types.py`
- Create: `sistema/tests/test_ai_channels_contract.py`

- [ ] **Step 1: Escrever testes do contrato de canal**

Criar `sistema/tests/test_ai_channels_contract.py`:

```python
from app.ai.channels.types import ChannelMessage, ChannelResponse


def test_channel_message_web_minimo():
    msg = ChannelMessage(
        channel="web",
        text="quanto vendi hoje?",
        empresa_id=10,
        usuario_id=20,
        sessao_id="sess-1",
    )

    assert msg.channel == "web"
    assert msg.text == "quanto vendi hoje?"
    assert msg.metadata == {}
    assert msg.attachments == []


def test_channel_response_preserva_eventos_e_metadata():
    response = ChannelResponse(
        text="Resposta final",
        events=[{"type": "agent", "agent": "FinanceAgent"}],
        metadata={"engine": "langgraph"},
    )

    assert response.text == "Resposta final"
    assert response.events[0]["agent"] == "FinanceAgent"
    assert response.metadata["engine"] == "langgraph"
```

- [ ] **Step 2: Rodar teste para confirmar falha por módulo ausente**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_channels_contract.py -q
```

Expected: `ModuleNotFoundError: No module named 'app.ai.channels'`.

- [ ] **Step 3: Criar tipos de canal**

Criar `sistema/app/ai/channels/types.py`:

```python
"""Contratos internos para entrada e saída dos canais do assistente IA."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChannelKind = Literal["web", "whatsapp", "voice", "internal"]


class ChannelMessage(BaseModel):
    channel: ChannelKind
    text: str
    empresa_id: int
    usuario_id: int | None = None
    sessao_id: str | None = None
    external_id: str | None = None
    phone: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelResponse(BaseModel):
    text: str
    events: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Criar `sistema/app/ai/channels/__init__.py`:

```python
"""Camada de canais do assistente IA."""

from app.ai.channels.types import ChannelKind, ChannelMessage, ChannelResponse

__all__ = ["ChannelKind", "ChannelMessage", "ChannelResponse"]
```

- [ ] **Step 4: Rodar testes do contrato**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_channels_contract.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit de checkpoint, se autorizado pelo usuário**

Run:

```bash
git add sistema/app/ai/channels sistema/tests/test_ai_channels_contract.py
git commit -m "feat: add assistant channel contracts"
```

---

### Task 3: Criar Eventos Padronizados De Observabilidade/SSE

**Files:**
- Create: `sistema/app/ai/observability/__init__.py`
- Create: `sistema/app/ai/observability/events.py`
- Create: `sistema/tests/test_ai_observability_events.py`

- [ ] **Step 1: Escrever testes de eventos**

Criar `sistema/tests/test_ai_observability_events.py`:

```python
from app.ai.observability.events import agent_event, final_event, tool_event


def test_agent_event_padronizado():
    event = agent_event("FinanceAgent", "Consultando financeiro")

    assert event["type"] == "agent_step"
    assert event["agent"] == "FinanceAgent"
    assert event["message"] == "Consultando financeiro"


def test_tool_event_nao_expoe_args_por_padrao():
    event = tool_event("listar_orcamentos", status="ok")


    assert event == {"type": "tool_step", "tool": "listar_orcamentos", "status": "ok"}


def test_final_event_preserva_metadata():
    event = final_event("ok", metadata={"engine": "langgraph"})


    assert event["type"] == "final"
    assert event["text"] == "ok"
    assert event["metadata"]["engine"] == "langgraph"
```

- [ ] **Step 2: Rodar teste para confirmar falha por módulo ausente**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_observability_events.py -q
```

Expected: `ModuleNotFoundError: No module named 'app.ai.observability'`.

- [ ] **Step 3: Criar helpers de eventos**

Criar `sistema/app/ai/observability/events.py`:

```python
"""Eventos internos padronizados para streaming, logs e UI do assistente."""
from __future__ import annotations

from typing import Any


def agent_event(agent: str, message: str) -> dict[str, Any]:
    return {"type": "agent_step", "agent": agent, "message": message}


def tool_event(tool: str, *, status: str) -> dict[str, Any]:
    return {"type": "tool_step", "tool": tool, "status": status}


def final_event(text: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "final", "text": text, "metadata": metadata or {}}
```

Criar `sistema/app/ai/observability/__init__.py`:

```python
"""Observabilidade interna do assistente IA."""

from app.ai.observability.events import agent_event, final_event, tool_event
__all__ = ["agent_event", "final_event", "tool_event"]
```

- [ ] **Step 4: Rodar testes de eventos**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_observability_events.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit de checkpoint, se autorizado pelo usuário**

Run:

```bash
git add sistema/app/ai/observability sistema/tests/test_ai_observability_events.py
git commit -m "feat: add assistant observability events"
```

---

### Task 4: Criar Runner De Agente Com Tool Executor

**Files:**
- Modify: `sistema/app/ai/agents/base.py:12-17`
- Create: `sistema/app/ai/agents/tool_runner.py`
- Create: `sistema/tests/test_ai_agent_tool_runner.py`

- [ ] **Step 1: Escrever teste sem LLM real para tool runner**

Criar `sistema/tests/test_ai_agent_tool_runner.py`:

```python
from types import SimpleNamespace

import pytest

from app.ai.agents.base import AgentResponse, BaseAgent
from app.ai.agents.tool_runner import run_agent_with_tools


class FakeAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="FakeAgent", system_prompt="fake")
        self.calls = 0

    async def __call__(self, messages, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return AgentResponse(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "obter_saldo_caixa", "arguments": "{}"},
                    }
                ],
                metadata={},
            )
        return AgentResponse(content="Saldo consultado.", tool_calls=[], metadata={})


@pytest.mark.asyncio
async def test_tool_runner_executa_tool_call_e_retorna_texto(monkeypatch):
    async def fake_execute(name, args, *, db, current_user, sessao_id=None, request_id=None, confirmation_token=None, engine=None):
        assert name == "obter_saldo_caixa"

        class FakeResult:
            status = "ok"
            data = {"saldo": 100}
            error = None

            def to_llm_payload(self):
                return {"status": "ok", "data": self.data}

        return FakeResult()

    monkeypatch.setattr("app.ai.agents.tool_runner.execute", fake_execute)

    result = await run_agent_with_tools(
        FakeAgent(),
        messages=[{"role": "user", "content": "qual meu saldo?"}],
        db=object(),
        current_user=SimpleNamespace(id=1, empresa_id=2),
        sessao_id="sess-1",
        engine="operational",
    )

    assert result.content == "Saldo consultado."
    assert result.metadata["tool_results"][0]["tool"] == "obter_saldo_caixa"
```

- [ ] **Step 2: Rodar teste para confirmar falha por módulo ausente**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_agent_tool_runner.py -q
```

Expected: `ModuleNotFoundError: No module named 'app.ai.agents.tool_runner'`.

- [ ] **Step 3: Corrigir tipo de metadata em AgentResponse**

Alterar `sistema/app/ai/agents/base.py`:

```python
class AgentResponse(BaseModel):
    """Standardized response from an agent."""
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Criar runner de tools por agente**

Criar `sistema/app/ai/agents/tool_runner.py`:

```python
"""Execução controlada de tool calls emitidas por agentes especializados."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.ai.agents.base import AgentResponse, BaseAgent
from app.models.models import Usuario
from app.services.tool_executor import execute


logger = logging.getLogger(__name__)


def _tool_call_name_and_args(tool_call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    function = tool_call.get("function") or {}
    name = str(function.get("name") or "").strip()
    raw_args = function.get("arguments") or "{}"
    if isinstance(raw_args, str):
        args = json.loads(raw_args or "{}")
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        args = {}
    return name, args


async def run_agent_with_tools(
    agent: BaseAgent,
    *,
    messages: list[dict[str, str]],
    db: Session,
    current_user: Usuario,
    sessao_id: str | None,
    engine: str | None,
    max_steps: int = 4,
) -> AgentResponse:
    tool_results: list[dict[str, Any]] = []
    working_messages = list(messages)

    for _ in range(max_steps):
        response = await agent(working_messages)
        if not response.tool_calls:
            response.metadata = dict(response.metadata or {})
            response.metadata["tool_results"] = tool_results
            return response

        for tool_call in response.tool_calls:
            name, args = _tool_call_name_and_args(tool_call)
            if not name:
                continue
            result = await execute(
                name,
                args,
                db=db,
                current_user=current_user,
                sessao_id=sessao_id,
                engine=engine,
            )
            payload = result.to_llm_payload()
            tool_results.append({"tool": name, "status": result.status, "payload": payload})
            working_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": name,
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            )

    logger.warning("Agent %s reached max tool steps", agent.name)
    return AgentResponse(
        content="Não consegui concluir a ação dentro do limite seguro de etapas.",
        metadata={"tool_results": tool_results, "max_steps_reached": True},
    )
```

- [ ] **Step 5: Rodar teste do runner**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_agent_tool_runner.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Rodar regressão obrigatória se tool routing for tocado**

Run somente se descrições de tools, registry ou gatilhos forem alterados:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_tool_routing.py -q
```

Expected: todos verdes.

- [ ] **Step 7: Commit de checkpoint, se autorizado pelo usuário**

Run:

```bash
git add sistema/app/ai/agents/base.py sistema/app/ai/agents/tool_runner.py sistema/tests/test_ai_agent_tool_runner.py
git commit -m "feat: add direct agent tool runner"
```

---

### Task 5: Adicionar Facade De Orquestração Com Fallback Legado

**Files:**
- Create: `sistema/app/ai/orchestrator/__init__.py`
- Create: `sistema/app/ai/orchestrator/service.py`
- Modify: `sistema/app/services/assistant_engine_registry.py:156-167`
- Create: `sistema/tests/test_ai_orchestrator_facade.py`

- [ ] **Step 1: Escrever teste de fallback legado**

Criar `sistema/tests/test_ai_orchestrator_facade.py`:

```python
import pytest

from app.ai.channels.types import ChannelMessage
from app.ai.orchestrator.service import AssistantOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_usa_legacy_runner_quando_direct_agents_desligado(monkeypatch):
    monkeypatch.delenv("V2_LANGGRAPH_DIRECT_AGENTS", raising=False)

    async def fake_legacy(payload):
        assert payload["mensagem"] == "oi"
        return {"final_text": "resposta legado"}

    orchestrator = AssistantOrchestrator(legacy_runner=fake_legacy)
    response = await orchestrator.run(
        ChannelMessage(channel="web", text="oi", empresa_id=1, usuario_id=2, sessao_id="s1")
    )

    assert response.text == "resposta legado"
    assert response.metadata["mode"] == "legacy"
```

- [ ] **Step 2: Rodar teste para confirmar falha por módulo ausente**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_orchestrator_facade.py -q
```

Expected: `ModuleNotFoundError: No module named 'app.ai.orchestrator'`.

- [ ] **Step 3: Adicionar capability flag de execução direta**

Alterar `sistema/app/services/assistant_engine_registry.py`:

```python
CAPABILITY_FLAGS = {
    "assistente_operacional": "V2_OPERATIONS_ENGINE",
    "engine_analitica": "V2_ANALYTICS_ENGINE",
    "engine_documental": "V2_DOCUMENT_ENGINE",
    "copiloto_interno": "V2_INTERNAL_COPILOT",
    "copiloto_interno_autonomia": "V2_INTERNAL_COPILOT_AUTONOMY",
    "copiloto_interno_autonomia_shadow": "V2_INTERNAL_COPILOT_AUTONOMY_SHADOW",
    "code_rag_tecnico": "V2_CODE_RAG",
    "sql_agent": "V2_SQL_AGENT",
    "langgraph_orchestration": "V2_LANGGRAPH_ORCHESTRATION",
    "langgraph_direct_agents": "V2_LANGGRAPH_DIRECT_AGENTS",
    "semantic_autonomy": "V2_SEMANTIC_AUTONOMY",
}
```

- [ ] **Step 4: Criar facade do orquestrador**

Criar `sistema/app/ai/orchestrator/service.py`:

```python
"""Facade interna para orquestrar mensagens do assistente IA."""
from __future__ import annotations

import os
from typing import Any, Awaitable, Callable

from app.ai.channels.types import ChannelMessage, ChannelResponse


def direct_agents_enabled() -> bool:
    raw = os.getenv("V2_LANGGRAPH_DIRECT_AGENTS")
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


class AssistantOrchestrator:
    def __init__(self, legacy_runner: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]):
        self.legacy_runner = legacy_runner

    async def run(self, message: ChannelMessage) -> ChannelResponse:
        payload = {
            "mensagem": message.text,
            "empresa_id": message.empresa_id,
            "usuario_id": message.usuario_id,
            "sessao_id": message.sessao_id,
            "channel": message.channel,
            "metadata": message.metadata,
        }

        if direct_agents_enabled():
            payload["orchestrator_mode"] = "direct_agents"
        result = await self.legacy_runner(payload)
        return ChannelResponse(
            text=str((result or {}).get("final_text") or ""),
            events=(result or {}).get("events") or [],
            metadata={"mode": "direct_agents" if direct_agents_enabled() else "legacy", "raw": result or {}},
        )
```

Criar `sistema/app/ai/orchestrator/__init__.py`:

```python
"""Facade de orquestração do assistente IA."""

from app.ai.orchestrator.service import AssistantOrchestrator, direct_agents_enabled
__all__ = ["AssistantOrchestrator", "direct_agents_enabled"]
```

- [ ] **Step 5: Rodar teste da facade**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_orchestrator_facade.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit de checkpoint, se autorizado pelo usuário**

Run:

```bash
git add sistema/app/ai/orchestrator sistema/app/services/assistant_engine_registry.py sistema/tests/test_ai_orchestrator_facade.py
git commit -m "feat: add assistant orchestrator facade"
```

---

### Task 6: Ligar Execução Direta Ao LangGraph Atrás De Flag

**Files:**
- Modify: `sistema/app/ai/graph/assistant.py:123-158`
- Modify: `sistema/tests/test_assistant_langgraph.py`

- [ ] **Step 1: Escrever teste de specialist node com execução direta desligada**

Adicionar a `sistema/tests/test_assistant_langgraph.py`:

```python
import pytest

from app.ai.graph.assistant import specialist_agent_node


@pytest.mark.asyncio
async def test_specialist_node_mantem_legacy_runner_por_padrao(monkeypatch):
    monkeypatch.delenv("V2_LANGGRAPH_DIRECT_AGENTS", raising=False)

    async def fake_legacy(payload):
        assert payload["agent_name"] == "FinanceAgent"
        return {"final_text": "ok legado"}

    state = {
        "messages": [],
        "empresa_id": 1,
        "usuario_id": 2,
        "sessao_id": "s1",
        "payload": {"mensagem": "saldo"},
        "errors": [],
        "node_trace": [],
    }

    result = await specialist_agent_node(
        state,
        agent_name="FinanceAgent",
        agent_class=object,
        legacy_runner=fake_legacy,
    )

    assert result["result"]["final_text"] == "ok legado"
```

- [ ] **Step 2: Rodar teste para confirmar estado atual**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_assistant_langgraph.py -q
```

Expected: teste novo passa no modo legado depois da Task 1.

- [ ] **Step 3: Adicionar branch de execução direta sem ativar por padrão**

Alterar `sistema/app/ai/graph/assistant.py` dentro de `specialist_agent_node`, antes do `legacy_runner`:

```python
        from app.ai.orchestrator.service import direct_agents_enabled

        if direct_agents_enabled() and payload.get("db") and payload.get("current_user"):
            from app.ai.agents.tool_runner import run_agent_with_tools

            agent = agent_class()
            response = await run_agent_with_tools(
                agent,
                messages=[{"role": "user", "content": payload.get("mensagem") or ""}],
                db=payload["db"],
                current_user=payload["current_user"],
                sessao_id=state["sessao_id"],
                engine=payload.get("engine"),
            )
            return {
                "result": {"final_text": response.content, "metadata": response.metadata},
                "next_agent": "FINISH",
                "messages": [AIMessage(content=response.content)] if response.content else [],
            }
```

Manter o caminho legado intacto quando a flag estiver desligada ou quando `db/current_user` não estiverem disponíveis.

- [ ] **Step 4: Rodar regressão LangGraph e assistente V2**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_assistant_langgraph.py tests/test_assistente_unificado_v2.py -q
```

Expected: todos verdes ou falhas existentes documentadas antes de prosseguir.

- [ ] **Step 5: Commit de checkpoint, se autorizado pelo usuário**

Run:

```bash
git add sistema/app/ai/graph/assistant.py sistema/tests/test_assistant_langgraph.py
git commit -m "feat: gate direct agent execution in langgraph"
```

---

### Task 7: Adaptadores De Canal Sem Trocar Endpoints Públicos

**Files:**
- Create: `sistema/app/ai/channels/web.py`
- Create: `sistema/app/ai/channels/whatsapp.py`
- Create: `sistema/app/ai/channels/voice.py`
- Modify: `sistema/tests/test_ai_channels_contract.py`

- [ ] **Step 1: Adicionar testes dos adaptadores**

Adicionar a `sistema/tests/test_ai_channels_contract.py`:

```python
from app.ai.channels.web import from_web_payload
from app.ai.channels.whatsapp import from_whatsapp_payload
from app.ai.channels.voice import from_voice_payload


def test_web_adapter_preserva_sessao_e_texto():
    msg = from_web_payload({"mensagem": "saldo", "sessao_id": "abc"}, empresa_id=1, usuario_id=2)

    assert msg.channel == "web"
    assert msg.text == "saldo"
    assert msg.sessao_id == "abc"


def test_whatsapp_adapter_preserva_telefone():
    msg = from_whatsapp_payload(text="oi", telefone="559999", empresa_id=1, external_id="msg-1")

    assert msg.channel == "whatsapp"
    assert msg.phone == "559999"
    assert msg.external_id == "msg-1"


def test_voice_adapter_anexa_formato():
    msg = from_voice_payload(text="emitir relatorio", empresa_id=1, usuario_id=2, audio_format="webm")

    assert msg.channel == "voice"
    assert msg.metadata["audio_format"] == "webm"
```

- [ ] **Step 2: Rodar teste para confirmar falha por módulos ausentes**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_channels_contract.py -q
```

Expected: falha por `ModuleNotFoundError` dos adaptadores.

- [ ] **Step 3: Criar adaptador web**

Criar `sistema/app/ai/channels/web.py`:

```python
"""Adaptador do chat web para o contrato interno de canais."""
from __future__ import annotations

from typing import Any

from app.ai.channels.types import ChannelMessage


def from_web_payload(payload: dict[str, Any], *, empresa_id: int, usuario_id: int | None) -> ChannelMessage:
    return ChannelMessage(
        channel="web",
        text=str(payload.get("mensagem") or payload.get("message") or ""),
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        sessao_id=payload.get("sessao_id"),
        metadata={"raw_keys": sorted(payload.keys())},
    )
```

- [ ] **Step 4: Criar adaptador WhatsApp**

Criar `sistema/app/ai/channels/whatsapp.py`:

```python
"""Adaptador do WhatsApp Evolution para o contrato interno de canais."""
from __future__ import annotations

from app.ai.channels.types import ChannelMessage


def from_whatsapp_payload(*, text: str, telefone: str, empresa_id: int, external_id: str | None = None) -> ChannelMessage:
    return ChannelMessage(
        channel="whatsapp",
        text=text,
        empresa_id=empresa_id,
        external_id=external_id,
        phone=telefone,
        metadata={"provider": "evolution"},
    )
```

- [ ] **Step 5: Criar adaptador de voz**

Criar `sistema/app/ai/channels/voice.py`:

```python
"""Adaptador de áudio transcrito para o contrato interno de canais."""
from __future__ import annotations

from app.ai.channels.types import ChannelMessage


def from_voice_payload(*, text: str, empresa_id: int, usuario_id: int | None, audio_format: str) -> ChannelMessage:
    return ChannelMessage(
        channel="voice",
        text=text,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        metadata={"audio_format": audio_format},
    )
```

- [ ] **Step 6: Rodar testes de canais**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_channels_contract.py -q
```

Expected: todos verdes.

- [ ] **Step 7: Commit de checkpoint, se autorizado pelo usuário**

Run:

```bash
git add sistema/app/ai/channels sistema/tests/test_ai_channels_contract.py
git commit -m "feat: add assistant channel adapters"
```

---

### Task 8: Validação Integrada Antes De Ativar Flags

**Files:**
- No code changes expected.

- [ ] **Step 1: Rodar testes focados de IA**

Run:

```bash
cd sistema
.venv/bin/python -m pytest \
  tests/test_assistant_langgraph.py \
  tests/test_ai_channels_contract.py \
  tests/test_ai_observability_events.py \
  tests/test_ai_agent_tool_runner.py \
  tests/test_ai_orchestrator_facade.py \
  tests/test_code_rag_service.py \
  -q
```

Expected: todos verdes.

- [ ] **Step 2: Rodar regressão obrigatória de roteamento se tools/gatilhos foram tocados**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_ai_tool_routing.py -q
```

Expected: todos verdes.

- [ ] **Step 3: Rodar regressão do assistente unificado**

Run:

```bash
cd sistema
.venv/bin/python -m pytest tests/test_assistente_unificado_v2.py -q
```

Expected: todos verdes ou falhas preexistentes documentadas com evidência.

- [ ] **Step 4: Conferir diff final**

Run:

```bash
git status --short
git diff --stat
git diff -- sistema/app/ai sistema/app/services/assistant_engine_registry.py sistema/tests
```

Expected: mudanças restritas à arquitetura IA e testes correspondentes.

---

## Rollout Seguro

Flags iniciais recomendadas:

```env
V2_LANGGRAPH_ORCHESTRATION=false
V2_LANGGRAPH_DIRECT_AGENTS=false
```

Ativação local controlada:

```env
V2_LANGGRAPH_ORCHESTRATION=true
V2_LANGGRAPH_DIRECT_AGENTS=false
```

Ativação experimental apenas após testes verdes:

```env
V2_LANGGRAPH_ORCHESTRATION=true
V2_LANGGRAPH_DIRECT_AGENTS=true
```

Não ativar em produção sem validar chat web, WhatsApp, áudio, RAG e relatórios financeiros.

---

## Self-Review

Spec coverage: o plano cobre baseline, canais, observabilidade, tool runner, facade de orquestração, integração LangGraph e validação.

Placeholder scan: não há seções com `TBD`, `TODO` ou instruções sem comando de validação.

Type consistency: `ChannelMessage`, `ChannelResponse`, `AgentResponse`, `AssistantOrchestrator` e `run_agent_with_tools` são definidos antes do uso integrado.

Risco assumido: a refatoração ampla continua usando fallback legado até que a execução direta por agente esteja verde, evitando troca simultânea de comportamento público.
