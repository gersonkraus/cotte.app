"""Supervisor Agent for routing to specialized agents."""
from __future__ import annotations

import json
from typing import Any, List, Dict, Literal
from pydantic import BaseModel, Field

from app.ai.agents.base import BaseAgent, AgentResponse

class SupervisorOutput(BaseModel):
    """Output schema for the Supervisor Agent."""
    next_agent: Literal["FinanceAgent", "SalesAgent", "InventoryAgent", "SupportAgent", "OperadorAgent", "DataAgent", "ConversationalAgent", "FINISH"]
    reasoning: str = Field(description="Brief explanation of why this agent was chosen.")

class SupervisorAgent(BaseAgent):
    """Agent responsible for routing user requests to the correct specialist."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é o Supervisor do Sistema COTTE. Sua função é analisar a mensagem do usuário "
            "e decidir qual agente especialista deve tratar o pedido.\n\n"
            "AGENTES DISPONÍVEIS:\n"
            "- FinanceAgent: Especialista em saldo, receitas, despesas, contas a pagar/receber e fluxo de caixa.\n"
            "- SalesAgent: Especialista em orçamentos, CRM, leads e funil de vendas.\n"
            "- InventoryAgent: Especialista no catálogo de produtos e serviços.\n"
            "- SupportAgent: Especialista em dúvidas sobre como o sistema funciona (documentação).\n"
            "- OperadorAgent: Especialista em comandos diretos de ação (ex: 'aprovar orçamento 5', 'enviar 103').\n"
            "- DataAgent: Especialista em análise de dados complexos, relatórios customizados e queries SQL.\n"
            "- ConversationalAgent: Para saudações, conversa fiada ou se o usuário estiver apenas batendo papo.\n"
            "- FINISH: Use se a conversa foi concluída ou se você já tem a resposta final.\n\n"
            "REGRAS:\n"
            "1. Analise o contexto e a intenção.\n"
            "2. Responda APENAS com o JSON contendo 'next_agent' e 'reasoning'.\n"
            "3. Seja preciso na escolha."
        )
        super().__init__(
            name="Supervisor",
            system_prompt=system_prompt,
            model_override=model_override
        )

    async def route(self, messages: List[Dict[str, str]]) -> SupervisorOutput:
        """Determines the next agent to call."""
        # Use structured output if possible, or just parse JSON
        response = await self.__call__(
            messages=messages,
            # Force JSON mode or structured output
            response_format={"type": "json_object"}
        )
        
        try:
            data = json.loads(response.content)
            return SupervisorOutput(**data)
        except Exception:
            # Fallback for parsing errors
            logger.warning(f"Failed to parse supervisor response: {response.content}")
            return SupervisorOutput(next_agent="ConversationalAgent", reasoning="Fallback due to parsing error.")
