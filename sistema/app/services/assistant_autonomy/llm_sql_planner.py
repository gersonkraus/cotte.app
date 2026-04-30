"""Planejador opcional de SQL via LLM para modo híbrido."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

from app.services.ia_service import ia_service
from app.services.assistant_autonomy.schema_context import get_schema_context_for_llm, resolve_table_name

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Você é um planejador de consultas SQL para um sistema de gestão empresarial.\n"
    "Seu trabalho é ler o pedido do operador e gerar UMA query SELECT que responda exatamente o que foi pedido.\n"
    "Regras:\n"
    "- Gere APENAS SELECT (nunca INSERT, UPDATE, DELETE, ALTER, DROP).\n"
    "- NÃO inclua ; no final da query.\n"
    "- NÃO use UNION, WITH/CTE, EXISTS, IN em subqueries.\n"
    "- O filtro de empresa será adicionado automaticamente. NÃO inclua empresa_id na query.\n"
    "- Use COUNT(*) para contagens, SUM() para somas, AVG() para médias.\n"
    "- Use GROUP BY quando necessário para agrupamentos.\n"
    "- Use ORDER BY para ordenação quando fizer sentido.\n"
    "- Quando o pedido for sobre catálogo, use a tabela servicos (coluna ativo para filtrar ativos).\n"
    "- Quando o pedido for sobre orçamentos, use a tabela orcamentos.\n"
    "- Retorne SOMENTE um JSON válido: {\"sql\": \"...\", \"rationale\": \"...\"}\n"
    "- Em rationale, explique brevemente o que a query faz."
)


@dataclass(frozen=True)
class LLMSqlPlan:
    sql: str | None
    rationale: str
    used: bool
    input_tokens: int = 0
    output_tokens: int = 0


def llm_sql_planner_enabled() -> bool:
    return str(os.getenv("V2_LLM_SQL_PLANNER", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _extract_json_from_response(content: str) -> dict:
    """Extrai JSON da resposta do LLM, tolerando markdown code blocks."""
    if not content:
        return {}
    cleaned = content.strip()
    json_match = re.search(r'\{[^{}]*\}', cleaned)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return {}


async def try_generate_sql_from_llm(message: str, *, period_days: int, historico: str = "") -> LLMSqlPlan:
    if not llm_sql_planner_enabled():
        return LLMSqlPlan(sql=None, rationale="LLM SQL planner desabilitado.", used=False)

    schema_ctx = get_schema_context_for_llm()

    historico_part = f"\nHistorico da conversa: {historico!r}" if historico else ""
    prompt = (
        f"{schema_ctx}\n\n"
        "---\n\n"
        f"Pedido do operador: {message!r}\n"
        f"Periodo padrao (quando aplicavel): {period_days} dias.{historico_part}\n\n"
        "Gere o SQL que responde ao pedido do operador. Retorne JSON: {\"sql\": \"...\", \"rationale\": \"...\"}"
    )
    try:
        resp = await ia_service.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        usage = (resp or {}).get("usage") or {}
        input_t = int(usage.get("prompt_tokens", 0) or 0)
        output_t = int(usage.get("completion_tokens", 0) or 0)
        choices = (resp or {}).get("choices") or []
        content = (((choices[0] or {}).get("message") or {}).get("content") or "") if choices else ""

        if not content:
            logger.warning("[LLM SQL Planner] Resposta vazia do LLM para mensagem: %r", message)
            return LLMSqlPlan(sql=None, rationale="LLM retornou conteudo vazio.", used=False)

        data = _extract_json_from_response(content)
        sql = str(data.get("sql") or "").strip() or None
        rationale = str(data.get("rationale") or "LLM SQL planner")

        if not sql:
            logger.warning(
                "[LLM SQL Planner] Nenhum SQL extraido. Content: %r | Data: %r | Mensagem: %r",
                content[:300], data, message,
            )
            return LLMSqlPlan(sql=None, rationale=f"Nenhum SQL valido extraido da resposta LLM.", used=False)

        if sql.lower().startswith(("insert", "update", "delete", "alter", "drop", "create", "truncate")):
            logger.warning("[LLM SQL Planner] LLM gerou SQL de escrita (bloqueado): %r", sql[:200])
            return LLMSqlPlan(sql=None, rationale="LLM gerou SQL de escrita, apenas SELECT e permitido.", used=False)

        logger.info(
            "[LLM SQL Planner] SQL gerado com sucesso. Rationale: %s | SQL: %s | Tokens: %d/%d",
            rationale, sql[:200], input_t, output_t,
        )
        return LLMSqlPlan(sql=sql, rationale=rationale, used=True, input_tokens=input_t, output_tokens=output_t)

    except Exception as exc:
        logger.error("[LLM SQL Planner] Falha inesperada para mensagem %r: %s", message, exc, exc_info=True)
        return LLMSqlPlan(sql=None, rationale=f"Falha no LLM SQL planner: {exc}", used=False)
