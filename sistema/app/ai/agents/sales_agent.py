"""Specialized agent for sales, quotes, and CRM operations."""
from __future__ import annotations

from typing import List, Dict, Any
from app.ai.agents.base import BaseAgent
from app.ai.tools.orcamento_tools import (
    listar_orcamentos,
    gerar_relatorio_orcamentos,
    obter_orcamento,
    criar_orcamento,
    aprovar_orcamento,
    recusar_orcamento,
    enviar_orcamento_whatsapp,
    enviar_orcamento_email,
    duplicar_orcamento,
    editar_orcamento,
    editar_item_orcamento,
    anexar_documento_orcamento
)
from app.ai.tools.cliente_tools import (
    listar_clientes,
    obter_cliente,
    criar_cliente,
    editar_cliente
)

class SalesAgent(BaseAgent):
    """Agent focused on sales, quotes, and client management."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é o Agente Comercial do Sistema COTTE. Sua especialidade é gerenciar orçamentos, "
            "clientes (CRM), leads e fechar negócios.\n\n"
            "DIRETRIZES:\n"
            "1. Sempre tente identificar o cliente antes de criar um orçamento.\n"
            "2. Ao listar orçamentos, use filtros de status para ser mais relevante.\n"
            "3. Se o usuário quiser criar ou aprovar um orçamento, lembre-se que essas ações "
            "exigem confirmação do usuário (são destrutivas/críticas).\n"
            "4. Forneça detalhes claros sobre os orçamentos quando solicitado.\n"
            "5. Se um orçamento estiver pendente há muito tempo, sugira proativamente o reenvio por WhatsApp."
        )
        
        # Collect tools
        tools_specs = [
            listar_orcamentos,
            gerar_relatorio_orcamentos,
            obter_orcamento,
            criar_orcamento,
            aprovar_orcamento,
            recusar_orcamento,
            enviar_orcamento_whatsapp,
            enviar_orcamento_email,
            duplicar_orcamento,
            editar_orcamento,
            editar_item_orcamento,
            anexar_documento_orcamento,
            listar_clientes,
            obter_cliente,
            criar_cliente,
            editar_cliente
        ]
        
        tools = [spec.openai_schema() for spec in tools_specs]
        
        super().__init__(
            name="SalesAgent",
            system_prompt=system_prompt,
            tools=tools,
            model_override=model_override
        )
