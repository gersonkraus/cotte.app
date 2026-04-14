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
_TENANT_SCOPE_RE = re.compile(r"\bempresa_id\s*=\s*:empresa_id\b", flags=re.IGNORECASE)
_OR_TRUE_RE = re.compile(r"\bor\s+1\s*=\s*1\b", flags=re.IGNORECASE)
_COMMENT_RE = re.compile(r"(--[^\n]*|/\*[\s\S]*?\*/)")
_STRING_RE = re.compile(r"'(?:''|[^'])*'")
_IN_SUBQUERY_RE = re.compile(r"\b(in|exists)\s*\(\s*select\b", flags=re.IGNORECASE)
_UNION_RE = re.compile(r"\bunion\b", flags=re.IGNORECASE)


def _strip_literals_and_comments(sql: str) -> str:
    without_comments = _COMMENT_RE.sub(" ", sql or "")
    return _STRING_RE.sub("'?'", without_comments)


def _balanced_parentheses(sql: str) -> bool:
    depth = 0
    for char in sql or "":
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if depth < 0:
            return False
    return depth == 0


def _allowed_sources() -> set[str]:
    raw = os.getenv(
        "ANALYTICS_SQL_ALLOWED_SOURCES",
        "orcamentos,clientes,movimentacoes_caixa,contas_financeiras,agendamentos,tool_call_log,tool_call_logs",
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
    risk_score: int = 0
    complexity: Optional[dict[str, int]] = None


def _build_complexity(sql: str) -> dict[str, int]:
    cleaned = _strip_literals_and_comments(sql)
    return {
        "joins": len(re.findall(r"\bjoin\b", cleaned, flags=re.IGNORECASE)),
        "group_by": len(re.findall(r"\bgroup\s+by\b", cleaned, flags=re.IGNORECASE)),
        "order_by": len(re.findall(r"\border\s+by\b", cleaned, flags=re.IGNORECASE)),
        "subqueries": len(re.findall(r"\(\s*select\b", cleaned, flags=re.IGNORECASE)),
        "unions": len(re.findall(r"\bunion\b", cleaned, flags=re.IGNORECASE)),
    }


def _risk_score(complexity: dict[str, int]) -> int:
    return int(
        complexity.get("joins", 0) * 2
        + complexity.get("group_by", 0)
        + complexity.get("order_by", 0)
        + complexity.get("subqueries", 0) * 3
        + complexity.get("unions", 0) * 4
    )


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
    if not _balanced_parentheses(raw):
        return SqlValidationResult(
            ok=False,
            error="SQL com parênteses desbalanceados.",
            code="sql_unbalanced_parentheses",
        )
    if _OR_TRUE_RE.search(_strip_literals_and_comments(raw)):
        return SqlValidationResult(
            ok=False,
            error="Padrão de bypass detectado (OR 1=1).",
            code="sql_tenant_bypass_pattern",
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
    if _UNION_RE.search(raw):
        return SqlValidationResult(
            ok=False,
            error="UNION não é permitido no SQL Agent analítico.",
            code="sql_union_blocked",
        )
    if _IN_SUBQUERY_RE.search(raw):
        return SqlValidationResult(
            ok=False,
            error="Subquery IN/EXISTS não permitida nesta fase do SQL Agent.",
            code="sql_subquery_blocked",
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
    if not _TENANT_SCOPE_RE.search(raw):
        return SqlValidationResult(
            ok=False,
            error="SQL analítico deve filtrar por empresa_id usando :empresa_id.",
            code="sql_missing_tenant_scope",
        )
    complexity = _build_complexity(raw)
    score = _risk_score(complexity)
    max_risk = int(os.getenv("ANALYTICS_SQL_MAX_RISK_SCORE", "20"))
    if score > max_risk:
        return SqlValidationResult(
            ok=False,
            error="Consulta excede limite de complexidade permitido para SQL Agent.",
            code="sql_complexity_exceeded",
            risk_score=score,
            complexity=complexity,
        )
    return SqlValidationResult(ok=True, sql=raw, risk_score=score, complexity=complexity)
