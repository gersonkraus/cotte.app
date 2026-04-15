"""Registry de ferramentas (Tool Use / function calling) do assistente COTTE.

Único ponto de verdade sobre quais tools existem. O `tool_executor` consulta
`REGISTRY[name]` para validar input, checar permissões e chamar o handler.

Uso típico no loop do assistente_unificado_v2:

    from app.services.ai_tools import REGISTRY, openai_tools_payload
    tools = openai_tools_payload()
    response = await ia_service.chat(messages, tools=tools)
"""
from __future__ import annotations

from typing import Any, Iterable

from ._base import ToolSpec
from .agendamento_tools import (
    cancelar_agendamento,
    criar_agendamento,
    listar_agendamentos,
    remarcar_agendamento,
)
from .catalogo_tools import cadastrar_material, listar_materiais
from .cliente_tools import (
    criar_cliente,
    editar_cliente,
    excluir_cliente,
    listar_clientes,
)
from .financeiro_tools import (
    criar_despesa,
    criar_movimentacao_financeira,
    criar_parcelamento,
    listar_despesas,
    listar_movimentacoes_financeiras,
    marcar_despesa_paga,
    obter_saldo_caixa,
    registrar_pagamento_recebivel,
)
from .log_tools import analisar_tool_logs
from .sql_analytics_tools import executar_sql_analitico
from .code_tools import ler_arquivo_repositorio, buscar_codigo_repositorio, analisar_estrutura_html
from .orcamento_tools import (
    anexar_documento_orcamento,
    aprovar_orcamento,
    criar_orcamento,
    duplicar_orcamento,
    editar_item_orcamento,
    editar_orcamento,
    enviar_orcamento_email,
    enviar_orcamento_whatsapp,
    listar_orcamentos,
    obter_orcamento,
    recusar_orcamento,
)

TOOL_DOMAIN_MAP: dict[str, str] = {
    # orcamentos
    "listar_orcamentos": "orcamentos",
    "obter_orcamento": "orcamentos",
    "criar_orcamento": "orcamentos",
    "duplicar_orcamento": "orcamentos",
    "editar_orcamento": "orcamentos",
    "editar_item_orcamento": "orcamentos",
    "aprovar_orcamento": "orcamentos",
    "recusar_orcamento": "orcamentos",
    "enviar_orcamento_whatsapp": "orcamentos",
    "enviar_orcamento_email": "orcamentos",
    "anexar_documento_orcamento": "orcamentos",
    # financeiro
    "obter_saldo_caixa": "financeiro",
    "listar_movimentacoes_financeiras": "financeiro",
    "criar_movimentacao_financeira": "financeiro",
    "registrar_pagamento_recebivel": "financeiro",
    "listar_despesas": "financeiro",
    "criar_despesa": "financeiro",
    "marcar_despesa_paga": "financeiro",
    "criar_parcelamento": "financeiro",
    # clientes
    "listar_clientes": "clientes",
    "criar_cliente": "clientes",
    "editar_cliente": "clientes",
    "excluir_cliente": "clientes",
    # catalogo
    "listar_materiais": "catalogo",
    "cadastrar_material": "catalogo",
    # agendamentos
    "listar_agendamentos": "agendamentos",
    "criar_agendamento": "agendamentos",
    "cancelar_agendamento": "agendamentos",
    "remarcar_agendamento": "agendamentos",
    # auditoria
    "analisar_tool_logs": "auditoria",
    # analitica
    "executar_sql_analitico": "analitica",
    # code
    "ler_arquivo_repositorio": "code",
    "buscar_codigo_repositorio": "code",
    "analisar_estrutura_html": "code",
}

# Ordem importa apenas para introspecção/debug.
_ALL_TOOLS: list[ToolSpec] = [
    # leitura
    ler_arquivo_repositorio,
    buscar_codigo_repositorio,
    analisar_estrutura_html,
    analisar_tool_logs,
    executar_sql_analitico,
    obter_saldo_caixa,
    listar_movimentacoes_financeiras,
    listar_orcamentos,
    obter_orcamento,
    listar_clientes,
    listar_materiais,
    listar_despesas,
    listar_agendamentos,
    # destrutivas
    criar_movimentacao_financeira,
    registrar_pagamento_recebivel,
    criar_despesa,
    marcar_despesa_paga,
    criar_cliente,
    editar_cliente,
    excluir_cliente,
    criar_orcamento,
    duplicar_orcamento,
    editar_orcamento,
    editar_item_orcamento,
    aprovar_orcamento,
    recusar_orcamento,
    enviar_orcamento_whatsapp,
    enviar_orcamento_email,
    cadastrar_material,
    criar_agendamento,
    cancelar_agendamento,
    remarcar_agendamento,
    criar_parcelamento,
    anexar_documento_orcamento,
]

REGISTRY: dict[str, ToolSpec] = {t.name: t for t in _ALL_TOOLS}


def openai_tools_payload() -> list[dict[str, Any]]:
    """Payload pronto para `ia_service.chat(..., tools=...)` (formato OpenAI/LiteLLM)."""
    return [t.openai_schema() for t in _ALL_TOOLS]


def operational_tool_catalog(
    *, allowed_tools: Iterable[str] | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Agrupa tools por domínio operacional para catálogo auditável.

    Quando `allowed_tools` é informado, limita o catálogo a esse subconjunto.
    """
    allowed = {name for name in (allowed_tools or []) if name}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for tool in _ALL_TOOLS:
        if allowed and tool.name not in allowed:
            continue
        domain = TOOL_DOMAIN_MAP.get(tool.name, "outros")
        grouped.setdefault(domain, []).append(
            {
                "name": tool.name,
                "description": tool.description,
                "destrutiva": bool(tool.destrutiva),
                "permissao_recurso": tool.permissao_recurso,
                "permissao_acao": tool.permissao_acao,
            }
        )
    return grouped


__all__ = [
    "REGISTRY",
    "ToolSpec",
    "openai_tools_payload",
    "operational_tool_catalog",
    "TOOL_DOMAIN_MAP",
]
