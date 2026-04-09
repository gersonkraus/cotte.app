"""Registry de ferramentas (Tool Use / function calling) do assistente COTTE.

Único ponto de verdade sobre quais tools existem. O `tool_executor` consulta
`REGISTRY[name]` para validar input, checar permissões e chamar o handler.

Uso típico no loop do assistente_unificado_v2:

    from app.services.ai_tools import REGISTRY, openai_tools_payload
    tools = openai_tools_payload()
    response = await ia_service.chat(messages, tools=tools)
"""
from __future__ import annotations

from typing import Any

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

# Ordem importa apenas para introspecção/debug.
_ALL_TOOLS: list[ToolSpec] = [
    # leitura
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


__all__ = [
    "REGISTRY",
    "ToolSpec",
    "openai_tools_payload",
]
