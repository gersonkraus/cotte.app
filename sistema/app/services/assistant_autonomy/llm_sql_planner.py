"""Planejador opcional de SQL via LLM para modo híbrido."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from app.services.ia_service import ia_service


@dataclass(frozen=True)
class LLMSqlPlan:
    sql: str | None
    rationale: str
    used: bool


def llm_sql_planner_enabled() -> bool:
    return str(os.getenv("V2_LLM_SQL_PLANNER", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def try_generate_sql_from_llm(message: str, *, period_days: int, historico: str = "") -> LLMSqlPlan:
    if not llm_sql_planner_enabled():
        return LLMSqlPlan(sql=None, rationale="LLM SQL planner desabilitado.", used=False)
    prompt = (
        "Gere APENAS SQL PostgreSQL read-only (SELECT/CTE), com filtro obrigatório "
        "empresa_id = :empresa_id, sem ; no final, sem UNION e sem subqueries EXISTS/IN. "
        f"Período padrão: {period_days} dias. Histórico da conversa (se houver): {historico!r}. Pedido do usuário: {message!r}. "
        "Retorne JSON: {\"sql\": \"...\", \"rationale\": \"...\"}."
    )
    try:
        resp = await ia_service.chat(
            messages=[{"role": "system", "content": "Você gera SQL seguro para analytics."}, {"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=450,
        )
        choices = (resp or {}).get("choices") or []
        content = (((choices[0] or {}).get("message") or {}).get("content") or "") if choices else ""
        data = json.loads(content) if content else {}
        sql = str(data.get("sql") or "").strip() or None
        rationale = str(data.get("rationale") or "LLM SQL planner")
        return LLMSqlPlan(sql=sql, rationale=rationale, used=bool(sql))
    except Exception as exc:
        return LLMSqlPlan(sql=None, rationale=f"Falha no LLM SQL planner: {exc}", used=False)
