"""Specialized agent for direct operator commands."""
from __future__ import annotations

from typing import List, Dict, Any
from app.ai.agents.base import BaseAgent
from app.ai.tools.orcamento_tools import (
    obter_orcamento,
    aprovar_orcamento,
    recusar_orcamento,
    enviar_orcamento_whatsapp,
    enviar_orcamento_email
)
from app.ai.tools.financeiro_tools import (
    marcar_despesa_paga,
    registrar_pagamento_recebivel
)

class OperadorAgent(BaseAgent):
    """Agent focused on executing direct commands from the operator."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é o Agente Operador do Sistema COTTE. Sua função é executar comandos de ação direta "
            "com rapidez e precisão.\n\n"
            "DIRETRIZES:\n"
            "1. Foque na execução da tarefa (aprovar, enviar, pagar).\n"
            "2. Se o ID não estiver claro, use 'obter_orcamento' para validar antes de agir.\n"
            "3. Lembre-se: toda ação de escrita exige confirmação."
        )
        
        # Collect tools
        tools_specs = [
            obter_orcamento,
            aprovar_orcamento,
            recusar_orcamento,
            enviar_orcamento_whatsapp,
            enviar_orcamento_email,
            marcar_despesa_paga,
            registrar_pagamento_recebivel
        ]
        
        tools = [spec.openai_schema() for spec in tools_specs]
        
        super().__init__(
            name="OperadorAgent",
            system_prompt=system_prompt,
            tools=tools,
            model_override=model_override
        )
