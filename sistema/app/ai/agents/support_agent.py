"""Specialized agent for support and system documentation."""
from __future__ import annotations

from typing import List, Dict, Any
from app.ai.agents.base import BaseAgent
from app.ai.tools.rag_tools import buscar_conhecimento

class SupportAgent(BaseAgent):
    """Agent focused on helping the user understand the system."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é o Agente de Suporte do Sistema COTTE. Sua função é responder dúvidas sobre "
            "o funcionamento da plataforma, regras de negócio e ajudar o usuário a navegar.\n\n"
            "DIRETRIZES:\n"
            "1. Use a ferramenta 'buscar_conhecimento' para encontrar informações nos manuais da empresa.\n"
            "2. Seja didático e amigável.\n"
            "3. Se você não souber a resposta com base no contexto recuperado, oriente o usuário a procurar "
            "o suporte humano ou consultar o manual principal.\n"
            "4. Não invente funcionalidades que não existem."
        )
        
        # Support agent primarily uses RAG
        tools_specs = [
            buscar_conhecimento
        ]
        
        tools = [spec.openai_schema() for spec in tools_specs]
        
        super().__init__(
            name="SupportAgent",
            system_prompt=system_prompt,
            tools=tools,
            model_override=model_override
        )
