"""Specialized agent for financial operations."""
from __future__ import annotations

from typing import List, Dict, Any
from app.ai.agents.base import BaseAgent
from app.ai.tools.financeiro_tools import (
    obter_saldo_caixa,
    listar_movimentacoes_financeiras,
    criar_movimentacao_financeira,
    registrar_pagamento_recebivel,
    listar_despesas,
    criar_despesa,
    marcar_despesa_paga,
    criar_parcelamento,
    gerar_relatorio_vendas,
    gerar_relatorio_contas_a_receber
)

class FinanceAgent(BaseAgent):
    """Agent focused on financial queries and operations."""
    def __init__(self, model_override: str | None = None):
        system_prompt = (
            "Você é o Agente Financeiro do Sistema COTTE. Sua especialidade é gerenciar o caixa, "
            "contas a pagar, contas a receber e gerar relatórios financeiros.\n\n"
            "DIRETRIZES:\n"
            "1. Sempre verifique o saldo antes de sugerir pagamentos.\n"
            "2. Ao listar despesas ou movimentações, apresente os dados de forma organizada.\n"
            "3. Se o usuário quiser criar uma movimentação ou pagar algo, use as ferramentas de escrita "
            "e lembre-se que elas exigem confirmação.\n"
            "4. Não invente números. Use apenas o que as ferramentas retornarem.\n"
            "5. Se precisar de uma data e ela não foi informada, use o contexto temporal atual."
        )
        
        # Collect tools
        tools_specs = [
            obter_saldo_caixa,
            listar_movimentacoes_financeiras,
            criar_movimentacao_financeira,
            registrar_pagamento_recebivel,
            listar_despesas,
            criar_despesa,
            marcar_despesa_paga,
            criar_parcelamento,
            gerar_relatorio_vendas,
            gerar_relatorio_contas_a_receber
        ]
        
        tools = [spec.openai_schema() for spec in tools_specs]
        
        super().__init__(
            name="FinanceAgent",
            system_prompt=system_prompt,
            tools=tools,
            model_override=model_override
        )
