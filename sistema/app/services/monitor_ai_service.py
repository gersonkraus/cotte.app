import os
import logging
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.services.monitor_ai_tools import (
    get_sql_toolkit,
    get_custom_tools,
    log_reader_tool,
    schema_inspector_tool,
    code_rag_tool,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_llm() -> ChatOpenAI:
    """Configura e retorna o LLM apontando para o OpenRouter."""
    api_key = getattr(settings, "AI_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning(
            "AI_API_KEY ou OPENROUTER_API_KEY não configurada. Usando fake para testes."
        )
        api_key = "dummy"

    model_name = os.getenv("MODEL_NAME", "google/gemini-2.5-pro")

    return ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model=model_name,
        temperature=0,
        max_tokens=2048,
    )


def create_agent_executor():
    """Cria e configura o Agent (LangGraph) com as tools necessárias e o prompt do Superadmin."""
    llm = get_llm()

    # Prepara as tools
    sql_toolkit = get_sql_toolkit(llm)
    tools = sql_toolkit.get_tools() + get_custom_tools()

    # Prompt do Agente
    prompt = (
        "Você é o Monitor AI, um assistente especializado de nível Superadmin do sistema Cotte.\n"
        "Você tem acesso a ferramentas poderosas para consultar o banco de dados SQL, "
        "ler logs de execução e buscar trechos de código-fonte (RAG).\n\n"
        "Regras críticas de segurança:\n"
        "1. Você só deve realizar consultas (SELECT) no banco de dados. Nunca execute INSERT, UPDATE, DELETE ou DROP.\n"
        "2. Nunca revele senhas, tokens, variáveis de ambiente ou segredos encontrados nos logs ou schemas.\n"
        "3. Responda sempre em português do Brasil, de forma técnica, direta e clara.\n"
        "4. Mostre sempre o raciocínio ou as ferramentas que utilizou para chegar à resposta."
    )

    # Cria o agente usando LangGraph
    agent = create_react_agent(llm, tools, prompt=prompt)
    return agent


def process_monitor_query(
    query: str, history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Processa a query do usuário através do agente LangGraph e retorna o resultado."""
    if history is None:
        history = []

    chat_history = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            chat_history.append(HumanMessage(content=content))
        elif role in ["assistant", "ai"]:
            chat_history.append(AIMessage(content=content))

    chat_history.append(HumanMessage(content=query))

    executor = create_agent_executor()

    try:
        result = executor.invoke({"messages": chat_history})

        # Extrair mensagens do estado final do LangGraph
        messages = result.get("messages", [])

        # A última mensagem é a resposta do agente
        output = ""
        if messages and isinstance(messages[-1], AIMessage):
            output = messages[-1].content

        # Extrair uso de tokens do último AIMessage
        input_tokens = 0
        output_tokens = 0
        last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        if last_ai:
            _meta = getattr(last_ai, "response_metadata", {}) or {}
            _usage = _meta.get("token_usage") or _meta.get("usage") or {}
            input_tokens = int(_usage.get("prompt_tokens", 0) or _usage.get("input_tokens", 0) or 0)
            output_tokens = int(_usage.get("completion_tokens", 0) or _usage.get("output_tokens", 0) or 0)

        # Processar os tool calls como intermediate_steps
        steps = []
        for msg in messages:
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                for call in msg.tool_calls:
                    steps.append(
                        {
                            "tool": call.get("name", "unknown_tool"),
                            "tool_input": call.get("args", {}),
                            "log": "Calling tool...",
                            "observation": "",
                        }
                    )
            elif isinstance(msg, ToolMessage):
                # Associa a resposta da tool ao step correspondente (o mais recente que não tem observação)
                for step in reversed(steps):
                    if step["tool"] == msg.name and step["observation"] == "":
                        step["observation"] = str(msg.content)[:2000]
                        break

        # Persiste resumo de tokens no ToolCallLog para observabilidade
        if input_tokens > 0 or output_tokens > 0:
            try:
                from app.core.database import get_db as _get_db
                from app.models.models import ToolCallLog as _ToolCallLog
                _db = next(_get_db())
                try:
                    _token_row = _ToolCallLog(
                        tool="llm_turn",
                        args_json={"_meta": {"engine": "monitor"}},
                        resultado_json=None,
                        status="ok",
                        input_tokens=int(input_tokens),
                        output_tokens=int(output_tokens),
                    )
                    _db.add(_token_row)
                    _db.commit()
                finally:
                    _db.close()
            except Exception:
                pass  # não bloqueia resposta se falhar

        return {
            "success": True,
            "answer": output or "Sem resposta gerada.",
            "intermediate_steps": steps,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    except Exception as e:
        logger.error(f"Erro ao processar query no Monitor AI: {e}", exc_info=True)
        return {
            "success": False,
            "answer": f"Ocorreu um erro interno no agente: {str(e)}",
            "intermediate_steps": [],
        }
