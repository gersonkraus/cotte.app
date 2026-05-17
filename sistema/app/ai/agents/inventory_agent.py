"""Specialized agent for catalog and inventory operations."""
from __future__ import annotations

from typing import List, Dict, Any
from app.ai.agents.base import BaseAgent
from app.ai.tools.catalogo_tools import (
    listar_materiais,
    cadastrar_material,
    resumo_catalogo
)

class InventoryAgent(BaseAgent):
    """Agent focused on products and services catalog."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é o Agente de Catálogo do Sistema COTTE. Sua especialidade é gerenciar o portfólio "
            "de produtos e serviços da empresa.\n\n"
            "DIRETRIZES:\n"
            "1. Sempre verifique se um item já existe antes de sugerir o cadastro de um novo.\n"
            "2. Ao listar materiais, destaque os preços e unidades de forma clara.\n"
            "3. O resumo do catálogo é útil para dar uma visão geral da precificação da empresa.\n"
            "4. Se o usuário quiser cadastrar algo, peça os detalhes necessários se não estiverem claros."
        )
        
        # Collect tools
        tools_specs = [
            listar_materiais,
            cadastrar_material,
            resumo_catalogo
        ]
        
        tools = [spec.openai_schema() for spec in tools_specs]
        
        super().__init__(
            name="InventoryAgent",
            system_prompt=system_prompt,
            tools=tools,
            model_override=model_override
        )
