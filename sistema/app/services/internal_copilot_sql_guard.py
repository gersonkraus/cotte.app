from __future__ import annotations

import re
from collections.abc import Mapping

from app.services.internal_copilot_autonomy_models import CopilotSafetyDecision


_WRITE_PREFIXES = ("insert ", "update ", "delete ")
_BLOCKED_PREFIXES = ("alter ", "drop ", "with ")
_FROM_PATTERN = re.compile(r"\bfrom\s+([a-zA-Z_][\w]*)", re.IGNORECASE)
_LIMIT_PATTERN = re.compile(r"\blimit\b", re.IGNORECASE)
_WHERE_PATTERN = re.compile(r"\bwhere\b", re.IGNORECASE)
_UNSUPPORTED_SELECT_PATTERN = re.compile(r"\bunion\b", re.IGNORECASE)


def validate_sql_query(*, sql: str, empresa_id: int, allowed_tables: Mapping[str, Mapping[str, str]]) -> CopilotSafetyDecision:
    normalized = " ".join((sql or "").strip().split())
    lowered = normalized.lower()

    if ";" in normalized:
        return CopilotSafetyDecision(allowed=False, mode="blocked", reason="multiple_statements")

    if lowered.startswith(_WRITE_PREFIXES):
        return CopilotSafetyDecision(
            allowed=False,
            mode="confirmation_required",
            needs_confirmation=True,
            reason="write_requires_confirmation",
        )

    if lowered.startswith(_BLOCKED_PREFIXES) or not lowered.startswith("select "):
        return CopilotSafetyDecision(allowed=False, mode="blocked", reason="blocked_statement")

    match = _FROM_PATTERN.search(normalized)
    if not match:
        return CopilotSafetyDecision(allowed=False, mode="blocked", reason="blocked_statement")

    if _has_unsupported_select_shape(normalized, match.end()):
        return CopilotSafetyDecision(allowed=False, mode="blocked", reason="unsupported_select_shape")

    table_name = match.group(1)
    table_config = allowed_tables.get(table_name)
    if not table_config or not table_config.get("empresa_column"):
        return CopilotSafetyDecision(allowed=False, mode="blocked", reason="table_not_allowed")

    scoped_sql = _inject_empresa_filter(normalized, table_name, table_config["empresa_column"], empresa_id)
    rewritten_sql = _ensure_limit(scoped_sql)
    return CopilotSafetyDecision(allowed=True, mode="read_only", rewritten_sql=rewritten_sql)


def _inject_empresa_filter(sql: str, table_name: str, empresa_column: str, empresa_id: int) -> str:
    tenant_filter = f"{table_name}.{empresa_column} = {empresa_id}"
    if tenant_filter.lower() in sql.lower():
        return sql

    if _LIMIT_PATTERN.search(sql):
        limit_match = _LIMIT_PATTERN.search(sql)
        assert limit_match is not None
        prefix = sql[: limit_match.start()].rstrip()
        suffix = sql[limit_match.start() :]
        if _WHERE_PATTERN.search(prefix):
            return f"{prefix} AND {tenant_filter} {suffix}"
        return f"{prefix} WHERE {tenant_filter} {suffix}"

    if _WHERE_PATTERN.search(sql):
        return f"{sql} AND {tenant_filter}"

    return f"{sql} WHERE {tenant_filter}"


def _ensure_limit(sql: str) -> str:
    if _LIMIT_PATTERN.search(sql):
        return sql
    return f"{sql} LIMIT 100"


def _has_unsupported_select_shape(sql: str, from_end: int) -> bool:
    if _UNSUPPORTED_SELECT_PATTERN.search(sql):
        return True

    remainder = sql[from_end:].lstrip()
    if not remainder:
        return False

    lowered = remainder.lower()
    return not (lowered.startswith("where ") or lowered.startswith("limit "))
