"""Guardrails de segurança para SQL Agent analítico (read-only)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional


_DANGEROUS_SQL_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|comment|copy|vacuum|analyze)\b",
    flags=re.IGNORECASE,
)
_SOURCE_RE = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w\.]*)", flags=re.IGNORECASE)


def _allowed_sources() -> set[str]:
    raw = os.getenv(
        "ANALYTICS_SQL_ALLOWED_SOURCES",
        "orcamentos,clientes,movimentacoes_caixa,contas_financeiras,agendamentos,tool_call_logs",
    )
    return {
        part.strip().lower()
        for part in str(raw).split(",")
        if part and part.strip()
    }


@dataclass(frozen=True)
class SqlValidationResult:
    ok: bool
    sql: Optional[str] = None
    error: Optional[str] = None
    code: Optional[str] = None


def validate_analytics_sql(sql: str) -> SqlValidationResult:
    raw = (sql or "").strip()
    if not raw:
        return SqlValidationResult(ok=False, error="SQL vazio.", code="invalid_input")
    if len(raw) > 4000:
        return SqlValidationResult(ok=False, error="SQL excede limite de tamanho.", code="invalid_input")
    if ";" in raw:
        return SqlValidationResult(
            ok=False,
            error="SQL com múltiplas instruções não é permitido.",
            code="sql_multi_statement_blocked",
        )
    lowered = raw.lower()
    if not (lowered.startswith("select ") or lowered.startswith("with ")):
        return SqlValidationResult(
            ok=False,
            error="SQL Agent permite apenas SELECT/CTE read-only.",
            code="sql_not_read_only",
        )
    if _DANGEROUS_SQL_RE.search(raw):
        return SqlValidationResult(
            ok=False,
            error="Comando SQL bloqueado por política de segurança.",
            code="sql_blocked_keyword",
        )

    allowed = _allowed_sources()
    sources = [m.group(1).split(".")[-1].lower() for m in _SOURCE_RE.finditer(raw)]
    for source in sources:
        if source not in allowed:
            return SqlValidationResult(
                ok=False,
                error=f"Fonte SQL não permitida: {source}",
                code="sql_not_allowed_source",
            )
    return SqlValidationResult(ok=True, sql=raw)
