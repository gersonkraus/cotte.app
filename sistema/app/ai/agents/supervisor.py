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
Você é o Supervisor do Sistema COTTE. Analise a mensagem do usuário e o histórico \
da conversa para decidir qual agente especialista deve tratar o pedido.

AGENTES DISPONÍVEIS:
- FinanceAgent: saldo de caixa, receitas, despesas simples, resumo financeiro.
- SalesAgent: criar/editar/enviar orçamentos, CRM, leads, funil de vendas.
- InventoryAgent: catálogo de produtos e serviços, materiais.
- SupportAgent: dúvidas sobre como o sistema funciona (ajuda/documentação).
- OperadorAgent: ações diretas com verbo + ID explícito (ex: "aprovar 5", "enviar 103", \
"excluir cliente 7"). Não use para consultas de dados.
- DataAgent: USE PARA qualquer consulta que retorne, filtre ou consolide dados: \
rankings, top N, contas de um cliente, tabelas de registros, agrupamentos por período, \
ticket médio, crescimento, comparativos, cruzamento entre tabelas, relatórios, \
inadimplência, histórico de transações, extrato. Este agente gera SQL read-only.
- ConversationalAgent: saudações, conversa livre, perguntas fora do escopo do sistema.
- FINISH: se a conversa foi concluída ou já há resposta final.

REGRAS (em ordem de prioridade):
1. Se a mensagem pede para VER, LISTAR, MOSTRAR, FILTRAR ou ANALISAR dados → DataAgent.
2. Se a mensagem é follow-up de uma resposta de dados anterior (ex: "id 1" depois de \
uma lista) → DataAgent (o usuário quer detalhar os dados, não editar).
3. Use OperadorAgent SOMENTE para ações com verbo imperativo + ID (aprovar, enviar, \
excluir, recusar). Nunca para consultas.
4. Responda APENAS com JSON válido contendo 'next_agent' e 'reasoning'.
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
