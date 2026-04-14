"""Registry das engines da Sprint 3.

Centraliza:
- tipos de engine permitidos
- flags de capability/rollout
- mapeamento de tools permitidas por engine
- guardrails de contexto
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from app.services.ai_tools import openai_tools_payload

ENGINE_OPERATIONAL = "operational"
ENGINE_ANALYTICS = "analytics"
ENGINE_DOCUMENTAL = "documental"
ENGINE_INTERNAL_COPILOT = "internal_copilot"

DEFAULT_ENGINE = ENGINE_OPERATIONAL


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EnginePolicy:
    key: str
    label: str
    description: str
    allowed_tools: tuple[str, ...]
    allow_tenant_rag: bool
    allow_business_context: bool
    allow_code_context: bool


ENGINE_POLICIES: dict[str, EnginePolicy] = {
    ENGINE_OPERATIONAL: EnginePolicy(
        key=ENGINE_OPERATIONAL,
        label="Assistente Operacional",
        description="Fluxos operacionais do produto para empresa usuária.",
        allowed_tools=(
            "obter_saldo_caixa",
            "listar_movimentacoes_financeiras",
            "listar_orcamentos",
            "obter_orcamento",
            "listar_clientes",
            "listar_materiais",
            "listar_despesas",
            "listar_agendamentos",
            "criar_movimentacao_financeira",
            "registrar_pagamento_recebivel",
            "criar_despesa",
            "marcar_despesa_paga",
            "criar_cliente",
            "editar_cliente",
            "excluir_cliente",
            "criar_orcamento",
            "duplicar_orcamento",
            "editar_orcamento",
            "editar_item_orcamento",
            "aprovar_orcamento",
            "recusar_orcamento",
            "enviar_orcamento_whatsapp",
            "enviar_orcamento_email",
            "cadastrar_material",
            "criar_agendamento",
            "cancelar_agendamento",
            "remarcar_agendamento",
            "criar_parcelamento",
            "anexar_documento_orcamento",
        ),
        allow_tenant_rag=True,
        allow_business_context=True,
        allow_code_context=False,
    ),
    ENGINE_ANALYTICS: EnginePolicy(
        key=ENGINE_ANALYTICS,
        label="Engine Analitica",
        description="Leitura e analise de dados de negocio sem mutacoes.",
        allowed_tools=(
            "obter_saldo_caixa",
            "listar_movimentacoes_financeiras",
            "listar_orcamentos",
            "obter_orcamento",
            "listar_clientes",
            "listar_despesas",
            "listar_agendamentos",
            "analisar_tool_logs",
            "executar_sql_analitico",
        ),
        allow_tenant_rag=False,
        allow_business_context=True,
        allow_code_context=False,
    ),
    ENGINE_DOCUMENTAL: EnginePolicy(
        key=ENGINE_DOCUMENTAL,
        label="Engine Documental",
        description="Consultas e apoio em documentos empresariais.",
        allowed_tools=(
            "obter_orcamento",
            "listar_orcamentos",
            "listar_clientes",
            "anexar_documento_orcamento",
        ),
        allow_tenant_rag=True,
        allow_business_context=True,
        allow_code_context=False,
    ),
    ENGINE_INTERNAL_COPILOT: EnginePolicy(
        key=ENGINE_INTERNAL_COPILOT,
        label="Copiloto Tecnico Interno",
        description="Canal interno tecnico, separado do assistente operacional.",
        allowed_tools=("analisar_tool_logs", "executar_sql_analitico"),
        allow_tenant_rag=False,
        allow_business_context=False,
        allow_code_context=True,
    ),
}


CAPABILITY_FLAGS = {
    "assistente_operacional": "V2_OPERATIONS_ENGINE",
    "engine_analitica": "V2_ANALYTICS_ENGINE",
    "engine_documental": "V2_DOCUMENT_ENGINE",
    "copiloto_interno": "V2_INTERNAL_COPILOT",
    "code_rag_tecnico": "V2_CODE_RAG",
    "sql_agent": "V2_SQL_AGENT",
    "langgraph_orchestration": "V2_LANGGRAPH_ORCHESTRATION",
    "semantic_autonomy": "V2_SEMANTIC_AUTONOMY",
}

COMPONENT_CAPABILITIES = {
    "nav.assistente_operacional": "assistente_operacional",
    "nav.copiloto_interno": "copiloto_interno",
    "screen.assistente_operacional": "assistente_operacional",
    "screen.copiloto_interno": "copiloto_interno",
    "engine.analytics": "engine_analitica",
    "engine.documental": "engine_documental",
    "engine.sql_agent": "sql_agent",
    "engine.code_rag_tecnico": "code_rag_tecnico",
    "engine.semantic_autonomy": "semantic_autonomy",
}


def resolve_engine(engine: str | None) -> str:
    normalized = (engine or DEFAULT_ENGINE).strip().lower()
    if normalized in ENGINE_POLICIES:
        return normalized
    return DEFAULT_ENGINE


def get_engine_policy(engine: str | None) -> EnginePolicy:
    return ENGINE_POLICIES[resolve_engine(engine)]


def list_capabilities() -> dict[str, Any]:
    flags = {
        capability: _env_flag(flag_name, default=(capability == "assistente_operacional"))
        for capability, flag_name in CAPABILITY_FLAGS.items()
    }
    engines = {
        key: {
            "label": policy.label,
            "description": policy.description,
            "tools_count": len(policy.allowed_tools),
            "allow_tenant_rag": policy.allow_tenant_rag,
            "allow_business_context": policy.allow_business_context,
            "allow_code_context": policy.allow_code_context,
        }
        for key, policy in ENGINE_POLICIES.items()
    }
    components = {
        comp: bool(flags.get(capability, False))
        for comp, capability in COMPONENT_CAPABILITIES.items()
    }
    return {"flags": flags, "engines": engines, "components": components}


def is_internal_copilot_enabled() -> bool:
    return _env_flag(CAPABILITY_FLAGS["copiloto_interno"], default=False)


def is_sql_agent_enabled() -> bool:
    return _env_flag(CAPABILITY_FLAGS["sql_agent"], default=False)


def is_code_rag_enabled() -> bool:
    return _env_flag(CAPABILITY_FLAGS["code_rag_tecnico"], default=False)


def tools_payload_for_engine(engine: str | None) -> list[dict[str, Any]]:
    policy = ENGINE_POLICIES[resolve_engine(engine)]
    allowed = set(policy.allowed_tools)
    payload: list[dict[str, Any]] = []
    for item in openai_tools_payload():
        name = ((item.get("function") or {}).get("name") or "").strip()
        if name == "executar_sql_analitico" and not is_sql_agent_enabled():
            continue
        if (
            resolve_engine(engine) == ENGINE_INTERNAL_COPILOT
            and name == "executar_sql_analitico"
            and not is_sql_agent_enabled()
        ):
            continue
        if name and name in allowed:
            payload.append(item)
    return payload


def build_engine_guardrails(engine: str | None) -> str:
    policy = ENGINE_POLICIES[resolve_engine(engine)]
    lines: list[str] = [
        "## Guardrails da engine ativa",
        f"- Engine ativa: {policy.label} ({policy.key})",
        f"- Escopo: {policy.description}",
        "- NUNCA execute tool fora da lista permitida.",
        "- Em caso de duvida sobre escopo, responda pedindo contexto adicional sem inventar.",
    ]
    if not policy.allow_code_context:
        lines.append("- Proibido usar ou inferir contexto tecnico de codebase interna.")
    if not policy.allow_tenant_rag:
        lines.append("- Nao use RAG documental da empresa nesta engine.")
    if not policy.allow_business_context:
        lines.append("- Nao use dados operacionais de empresa de cliente final.")
    if policy.key == ENGINE_ANALYTICS and not is_sql_agent_enabled():
        lines.append("- SQL Agent analítico desabilitado por flag de ambiente.")
    if policy.key == ENGINE_INTERNAL_COPILOT:
        if not is_code_rag_enabled():
            lines.append("- Code RAG técnico desabilitado por flag de ambiente.")
        if not is_sql_agent_enabled():
            lines.append("- SQL Agent técnico desabilitado por flag de ambiente.")
    return "\n".join(lines)


def is_engine_available_for_user(
    engine: str | None,
    *,
    is_superadmin: bool,
    is_gestor: bool,
) -> bool:
    resolved = resolve_engine(engine)
    caps = list_capabilities()["flags"]
    if resolved == ENGINE_OPERATIONAL:
        return bool(caps.get("assistente_operacional"))
    if resolved == ENGINE_ANALYTICS:
        return bool(caps.get("engine_analitica"))
    if resolved == ENGINE_DOCUMENTAL:
        return bool(caps.get("engine_documental"))
    if resolved == ENGINE_INTERNAL_COPILOT:
        return bool(caps.get("copiloto_interno")) and bool(is_superadmin or is_gestor)
    return False
