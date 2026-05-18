"""DataAgent — especialista em SQL analítico com schema-awareness."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.ai.agents.base import BaseAgent, AgentResponse
from app.ai.tools.sql_analytics_tools import executar_sql_analitico
from app.ai.rag.schema_registry import SchemaRegistry

logger = logging.getLogger(__name__)

_BASE_SYSTEM_PROMPT = """\
Você é o Agente de Dados do Sistema COTTE. Sua especialidade é realizar consultas \
SQL analíticas nos dados da empresa para responder perguntas de negócio.

DIRETRIZES:
1. Use a ferramenta 'executar_sql_analitico' para buscar dados quando necessário.
2. SEMPRE inclua `empresa_id = :empresa_id` no WHERE ou JOIN — o executor fará o bind.
3. Para rankings: use ORDER BY + LIMIT. Para totais: use SUM/COUNT com GROUP BY.
4. Explique os resultados de forma clara, com tabela quando houver múltiplas linhas.
5. Se o SQL falhar, leia o erro e tente novamente com a correção.

REGRAS DE NEGÓCIO DO COTTE:
- Orçamentos: status = 'rascunho' | 'enviado' | 'aprovado' | 'recusado'
- Movimentações: tipo = 'entrada' | 'saida', status = 'confirmado' | 'pendente'
- Sempre filtre por empresa_id para isolar dados do tenant correto.
"""


class DataAgent(BaseAgent):
    """Agente de dados com acesso ao schema do banco via SchemaRegistry."""

    def __init__(self, model_override: Optional[str] = None):
        tools = [executar_sql_analitico.openai_schema()]
        super().__init__(
            name="DataAgent",
            system_prompt=_BASE_SYSTEM_PROMPT,
            tools=tools,
            model_override=model_override,
        )
        self._db: Any = None

    def set_db_context(self, *, db: Any) -> None:
        """Injeta db para busca de schema. Chamado por run_agent_with_tools."""
        self._db = db

    async def __call__(self, messages: List[Dict[str, Any]], **kwargs) -> AgentResponse:
        """Enriquece o system prompt com schema relevante antes de chamar o LLM."""
        system_prompt = _BASE_SYSTEM_PROMPT

        if self._db is not None:
            try:
                user_query = next(
                    (m["content"] for m in reversed(messages) if m.get("role") == "user"),
                    "",
                )
                tables = await SchemaRegistry.get_relevant_tables(
                    user_query, top_k=6, db=self._db
                )
                schema_ctx = SchemaRegistry.format_schema_context(tables)
                if schema_ctx:
                    system_prompt = _BASE_SYSTEM_PROMPT + "\n\n" + schema_ctx
            except Exception as exc:
                logger.warning("[DataAgent] Falha ao carregar schema: %s", exc)

        original = self.system_prompt
        self.system_prompt = system_prompt
        try:
            return await super().__call__(messages, **kwargs)
        finally:
            self.system_prompt = original
