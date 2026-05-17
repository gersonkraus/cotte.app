"""Specialized agent for data analysis and direct SQL queries (read-only)."""
from __future__ import annotations

from typing import List, Dict, Any
from app.ai.agents.base import BaseAgent
from app.ai.tools.sql_analytics_tools import executar_sql_analitico

class DataAgent(BaseAgent):
    """Agent focused on data extraction and complex queries."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é o Agente de Dados do Sistema COTTE. Sua especialidade é realizar consultas "
            "complexas e análises sobre os dados da empresa.\n\n"
            "DIRETRIZES:\n"
            "1. Use a ferramenta 'executar_sql_analitico' para buscar dados brutos quando necessário.\n"
            "2. Explique os resultados de forma clara e visual.\n"
            "3. Você tem acesso apenas a dados de LEITURA da empresa do usuário atual.\n"
            "4. Se o esquema da tabela não estiver claro, peça ajuda ao Supervisor."
        )
        
        # Collect tools
        tools_specs = [
            executar_sql_analitico
        ]
        
        tools = [spec.openai_schema() for spec in tools_specs]
        
        super().__init__(
            name="DataAgent",
            system_prompt=system_prompt,
            tools=tools,
            model_override=model_override
        )
