"""Supervisor Agent — roteia mensagens para o agente especialista correto."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.ai.agents.base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class SupervisorOutput(BaseModel):
    next_agent: Literal[
        "FinanceAgent", "SalesAgent", "InventoryAgent", "SupportAgent",
        "OperadorAgent", "DataAgent", "ConversationalAgent", "FINISH"
    ]
    reasoning: str = Field(description="Motivo curto da escolha.")


_SUPERVISOR_SYSTEM_PROMPT = """\
Você é o Supervisor do Sistema COTTE. Analise a mensagem do usuário e decida qual \
agente especialista deve tratar o pedido.

AGENTES DISPONÍVEIS:
- FinanceAgent: saldo de caixa, receitas, despesas simples, contas a pagar/receber.
- SalesAgent: criar/editar/enviar orçamentos, CRM, leads, funil de vendas.
- InventoryAgent: catálogo de produtos e serviços, materiais.
- SupportAgent: dúvidas sobre como o sistema funciona (ajuda/documentação).
- OperadorAgent: comandos diretos com ID explícito (ex: "aprovar 5", "enviar 103").
- DataAgent: USE PARA rankings, top N clientes/serviços, agrupamentos por período, \
ticket médio, crescimento, comparativos, cruzamento de dados entre tabelas, \
relatórios complexos, inadimplência, histórico. Este agente tem acesso a SQL read-only.
- ConversationalAgent: saudações, conversa livre, perguntas fora do escopo do sistema.
- FINISH: se a conversa foi concluída ou já há resposta final.

REGRAS:
1. Prefira DataAgent para qualquer pergunta que exija cruzar dados ou calcular métricas.
2. Prefira OperadorAgent quando há um número de ID explícito na mensagem.
3. Responda APENAS com JSON válido contendo 'next_agent' e 'reasoning'.
"""


class SupervisorAgent(BaseAgent):
    def __init__(self, model_override: Optional[str] = None):
        super().__init__(
            name="Supervisor",
            system_prompt=_SUPERVISOR_SYSTEM_PROMPT,
            model_override=model_override,
        )

    async def route(
        self,
        messages: List[Dict[str, str]],
        *,
        schema_context: str = "",
    ) -> SupervisorOutput:
        """Determina o próximo agente. schema_context é injetado quando disponível."""
        routing_messages = list(messages)

        if schema_context:
            routing_messages = [
                {"role": "system", "content": f"Schema disponível para DataAgent:\n{schema_context}"},
                *routing_messages,
            ]

        response = await self.__call__(
            routing_messages,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response.content)
            return SupervisorOutput(**data)
        except Exception:
            logger.warning("[Supervisor] Falha ao parsear resposta: %s", response.content)
            return SupervisorOutput(
                next_agent="ConversationalAgent",
                reasoning="Fallback por erro de parsing.",
            )
