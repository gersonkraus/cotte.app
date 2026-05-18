"""Orquestração Multi-Agente via LangGraph (v2.1) para o assistente COTTE."""

from __future__ import annotations

import os
import logging
import json
import time
import asyncio
from typing import Any, Awaitable, Callable, TypedDict, Annotated, List, Optional, AsyncGenerator, Literal
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    HAS_POSTGRES_SAVER = True
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    HAS_POSTGRES_SAVER = False

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import ToolCallLog

# Agentes
from app.ai.agents.supervisor import SupervisorAgent, SupervisorOutput
from app.ai.agents.finance_agent import FinanceAgent
from app.ai.agents.sales_agent import SalesAgent
from app.ai.agents.inventory_agent import InventoryAgent
from app.ai.agents.support_agent import SupportAgent
from app.ai.agents.operador_agent import OperadorAgent
from app.ai.agents.data_agent import DataAgent
from app.ai.agents.conversational_agent import ConversationalAgent
from app.ai.agents.tool_runner import run_agent_with_tools
from app.ai.orchestrator.service import direct_agents_enabled

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# ESTADO DO ASSISTENTE
# ─────────────────────────────────────────────────────────────────────────────

class AssistantState(TypedDict):
    """Estado persistente da conversa e execução do assistente."""
    messages: Annotated[List[BaseMessage], add_messages]
    empresa_id: int
    usuario_id: int
    sessao_id: str
    
    # Roteamento
    next_agent: Optional[str]
    reasoning: Optional[str]
    
    # Resultados
    payload: Optional[dict[str, Any]]
    result: Optional[dict[str, Any]]
    errors: List[str]
    node_trace: List[dict[str, Any]]


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def langgraph_enabled() -> bool:
    """Verifica se a orquestração via LangGraph deve ser utilizada."""
    return _env_flag("V2_LANGGRAPH_ORCHESTRATION") or _env_flag("USE_LANGGRAPH_ASSISTANT")


def _messages_for_agent(messages: list[Any]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, dict):
            converted.append({"role": message.get("role"), "content": message.get("content", "")})
            continue

        role = getattr(message, "role", None)
        if role is None:
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                role = getattr(message, "type", "user")

        converted.append({"role": role, "content": getattr(message, "content", "")})
    return converted


def _message_content(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content") or "")
    return str(getattr(message, "content", "") or "")


# ─────────────────────────────────────────────────────────────────────────────
# TELEMETRIA
# ─────────────────────────────────────────────────────────────────────────────

def _log_node_telemetry(state: AssistantState, node_name: str, latency_ms: int, status: str = "ok", error: str | None = None):
    db = SessionLocal()
    try:
        log = ToolCallLog(
            empresa_id=state["empresa_id"],
            usuario_id=state["usuario_id"],
            sessao_id=state["sessao_id"],
            tool=f"agent_node:{node_name}",
            args_json={"reasoning": state.get("reasoning"), "_meta": {"engine": "langgraph_v2.1"}},
            resultado_json={"error": error},
            status=status,
            latencia_ms=latency_ms,
            user_input=state["messages"][-1].content if state["messages"] else None
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"[LangGraph Telemetry] Erro no log do nó {node_name}: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# NODES DO GRAFO
# ─────────────────────────────────────────────────────────────────────────────

async def supervisor_node(state: AssistantState) -> dict[str, Any]:
    """Roteia a mensagem para o agente especialista correto."""
    start_time = time.perf_counter()
    supervisor = SupervisorAgent()
    
    # Converte BaseMessages para o formato simples esperado pelo BaseAgent
    conv_messages = []
    for m in state["messages"][-5:]: # Janela curta para o supervisor
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        conv_messages.append({"role": role, "content": m.content})
        
    try:
        route_out = await supervisor.route(conv_messages)
        logger.info(f"[Supervisor] Roteando para {route_out.next_agent}. Motivo: {route_out.reasoning}")
        return {
            "next_agent": route_out.next_agent,
            "reasoning": route_out.reasoning
        }
    except Exception as e:
        logger.error(f"[Supervisor] Falha no roteamento: {e}")
        return {"next_agent": "ConversationalAgent", "reasoning": "Fallback devido a erro."}
    finally:
        latency = int((time.perf_counter() - start_time) * 1000)
        _log_node_telemetry(state, "supervisor", latency)


async def specialist_agent_node(
    state: AssistantState, 
    agent_name: str,
    agent_class: Any,
    legacy_runner: Callable[[dict[str, Any]], Awaitable[Any]]
) -> dict[str, Any]:
    """Nó genérico para executar qualquer agente especialista."""
    start_time = time.perf_counter()
    logger.info(f"[LangGraph] Executando especialista: {agent_name}")
    
    # Para manter compatibilidade com o loop de tool-use legado e visualizações ricas,
    # por enquanto delegamos a execução real para o legacy_runner injetado,
    # mas passando a intenção/contexto do agente.
    
    payload = state.get("payload") or {}
    payload["agent_name"] = agent_name
    payload["empresa_id"] = state["empresa_id"]
    payload["usuario_id"] = state["usuario_id"]
    payload["mensagem"] = _message_content(state["messages"][-1]) if state["messages"] else ""
    errors = list(state.get("errors") or [])
    node_trace = list(state.get("node_trace") or [])

    meta = payload.get("metadata", {})
    db = payload.get("db") or meta.get("db")
    current_user = payload.get("current_user") or meta.get("current_user")
    
    if direct_agents_enabled() and db is not None and current_user is not None:
        try:
            agent = agent_class()
            response = await run_agent_with_tools(
                agent,
                messages=_messages_for_agent(state.get("messages") or []),
                db=db,
                current_user=current_user,
                sessao_id=state.get("sessao_id") or payload.get("sessao_id"),
                engine=payload.get("engine", "operational"),
            )
            result = {"final_text": response.content, "content": response.content}
            if response.metadata:
                result["metadata"] = response.metadata

            updates = {
                "result": result,
                "next_agent": "FINISH",
                "payload": payload,
                "node_trace": node_trace + [{"agent": agent_name, "mode": "direct"}],
            }
            if response.content:
                updates["messages"] = [AIMessage(content=response.content)]
            return updates
        except Exception as e:
            logger.error(f"[Specialist {agent_name}] Erro no agente direto, usando legado: {e}")
            errors.append(str(e))
            node_trace.append({"agent": agent_name, "mode": "direct", "error": str(e)})
     
    try:
        # No futuro, aqui usaremos agent_class() diretamente.
        # Por enquanto, o legacy_runner em cotte_ai_hub ainda é o maestro das ferramentas.
        result = await legacy_runner(payload)
         
        updates = {"result": result, "next_agent": "FINISH"}
        if errors:
            updates["errors"] = errors
        if node_trace:
            updates["node_trace"] = node_trace
        if result and result.get("final_text"):
            updates["messages"] = [AIMessage(content=result["final_text"])]
            
        return updates
    except Exception as e:
        logger.error(f"[Specialist {agent_name}] Erro: {e}")
        return {"next_agent": "FINISH", "errors": [str(e)]}
    finally:
        latency = int((time.perf_counter() - start_time) * 1000)
        _log_node_telemetry(state, agent_name, latency)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUTOR DO GRAFO
# ─────────────────────────────────────────────────────────────────────────────

async def get_assistant_app(legacy_runner: Callable[[dict[str, Any]], Awaitable[Any]]):
    workflow = StateGraph(AssistantState)
    
    # Registro de Nós
    workflow.add_node("supervisor", supervisor_node)
    
    # Especialistas
    agents = {
        "FinanceAgent": (FinanceAgent, "financeiro"),
        "SalesAgent": (SalesAgent, "vendas"),
        "InventoryAgent": (InventoryAgent, "catalogo"),
        "SupportAgent": (SupportAgent, "suporte"),
        "OperadorAgent": (OperadorAgent, "operador"),
        "DataAgent": (DataAgent, "dados"),
        "ConversationalAgent": (ConversationalAgent, "conversa"),
    }
    
    for name, (cls, _) in agents.items():
        # Wrapper para passar argumentos extras para o nó
        async def _node_func(state: AssistantState, n=name, c=cls):
            return await specialist_agent_node(state, agent_name=n, agent_class=c, legacy_runner=legacy_runner)
        workflow.add_node(name, _node_func)

    # Fluxo
    workflow.add_edge(START, "supervisor")
    
    # Edges Condicionais (Roteamento)
    def route_decision(state: AssistantState):
        return state.get("next_agent", "ConversationalAgent")

    workflow.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "FinanceAgent": "FinanceAgent",
            "SalesAgent": "SalesAgent",
            "InventoryAgent": "InventoryAgent",
            "SupportAgent": "SupportAgent",
            "OperadorAgent": "OperadorAgent",
            "DataAgent": "DataAgent",
            "ConversationalAgent": "ConversationalAgent",
            "FINISH": END
        }
    )
    
    # Todos os especialistas terminam o fluxo nesta iteração
    for name in agents.keys():
        workflow.add_edge(name, END)
    
    # Persistência
    if HAS_POSTGRES_SAVER:
        from app.ai.graph.assistant import _get_async_db_url # Reuso da lógica de URL
        checkpointer = AsyncPostgresSaver.from_conn_string(_get_async_db_url())
    else:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
        
    return workflow.compile(checkpointer=checkpointer)


def _get_async_db_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgres://"): url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"): url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url.split("?")[0] if "?" in url else url


# ─────────────────────────────────────────────────────────────────────────────
# ENTRYPOINTS
# ─────────────────────────────────────────────────────────────────────────────

async def run_assistant_v2_graph_stream(
    *,
    message: str,
    empresa_id: int,
    usuario_id: int,
    thread_id: str,
    payload: dict[str, Any],
    legacy_runner: Callable[[dict[str, Any]], Awaitable[Any]],
) -> AsyncGenerator[dict[str, Any], None]:
    try:
        app = await get_assistant_app(legacy_runner)
        if HAS_POSTGRES_SAVER and hasattr(app.checkpointer, "setup"):
            async with app.checkpointer as saver: await saver.setup()

        config = {"configurable": {"thread_id": thread_id}}
        initial_input = {
            "messages": [HumanMessage(content=message)],
            "empresa_id": empresa_id,
            "usuario_id": usuario_id,
            "sessao_id": thread_id,
            "payload": payload,
            "errors": [],
            "node_trace": []
        }
        
        async for chunk in app.astream(initial_input, config=config, stream_mode="updates"):
            for node_name, updates in chunk.items():
                label_map = {
                    "supervisor": "Analisando pedido",
                    "FinanceAgent": "Consultando financeiro",
                    "SalesAgent": "Verificando vendas",
                    "InventoryAgent": "Consultando catálogo",
                    "SupportAgent": "Buscando documentação",
                    "OperadorAgent": "Executando ação",
                    "DataAgent": "Analisando dados",
                    "ConversationalAgent": "Preparando resposta",
                }
                yield {"phase": "langgraph_step", "node": node_name, "status": "done", "step_label": label_map.get(node_name, "Processando")}
            
            # Resultado final
            for node_name in chunk:
                if node_name in ["FinanceAgent", "SalesAgent", "InventoryAgent", "SupportAgent", "OperadorAgent", "DataAgent", "ConversationalAgent"]:
                    yield {"is_final": True, "result": chunk[node_name].get("result")}

    except Exception as e:
        logger.exception(f"Erro no LangGraph: {e}")
        res = await legacy_runner(payload)
        yield {"is_final": True, "result": res}
