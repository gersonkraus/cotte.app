"""Guardrails de segurança para SQL Agent analítico v2.

Política: bloqueia DML/DDL e tabelas de sistema. SELECT livre com tenant
isolation via parâmetro :empresa_id. Sem whitelist de tabelas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


_DML_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|vacuum)\b",
    flags=re.IGNORECASE,
)
_SYSTEM_TABLE_RE = re.compile(
    r"\b(pg_\w+|information_schema\b|alembic_version)\b",
    flags=re.IGNORECASE,
)
_COMMENT_RE = re.compile(r"(--[^\n]*|/\*[\s\S]*?\*/)")
_STRING_RE = re.compile(r"'(?:''|[^'])*'")
_OR_TRUE_RE = re.compile(r"\bor\s+1\s*=\s*1\b", re.IGNORECASE)
_TENANT_PARAM_RE = re.compile(r":empresa_id\b", re.IGNORECASE)


def _strip_literals_and_comments(sql: str) -> str:
    without_comments = _COMMENT_RE.sub(" ", sql or "")
    return _STRING_RE.sub("'?'", without_comments)


def _balanced_parentheses(sql: str) -> bool:
    depth = 0
    for ch in sql or "":
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            return False
    return depth == 0


@dataclass(frozen=True)
class SqlValidationResult:
    ok: bool
    sql: Optional[str] = None
    error: Optional[str] = None
    code: Optional[str] = None
    # Mantidos por compatibilidade com callers existentes (sql_analytics_tools.py)
    risk_score: int = 0
    complexity: Optional[dict] = field(default=None)


def validate_analytics_sql(sql: str, *, allow_cross_tenant: bool = False) -> SqlValidationResult:
    """Valida SQL garantindo read-only e tenant isolation.

    allow_cross_tenant=True permite omitir :empresa_id (uso exclusivo de superadmin).
    """
    raw = (sql or "").strip()

    if not raw:
        return SqlValidationResult(ok=False, error="SQL vazio.", code="invalid_input")

    if len(raw) > 8000:
        return SqlValidationResult(
            ok=False, error="SQL excede limite de 8000 caracteres.", code="invalid_input"
        )

    if not _balanced_parentheses(raw):
        return SqlValidationResult(
            ok=False,
            error="SQL com parênteses desbalanceados.",
            code="sql_unbalanced_parentheses",
        )

    cleaned = _strip_literals_and_comments(raw)

    if ";" in cleaned:
        return SqlValidationResult(
            ok=False,
            error="SQL com múltiplas instruções não é permitido.",
            code="sql_multi_statement_blocked",
        )

    if _OR_TRUE_RE.search(cleaned):
        return SqlValidationResult(
            ok=False,
            error="Padrão de bypass detectado (OR 1=1).",
            code="sql_tenant_bypass_pattern",
        )

    lowered = raw.lower().lstrip()
    if not (
        lowered.startswith("select ")
        or lowered.startswith("select\n")
        or lowered.startswith("select\t")
        or lowered.startswith("with ")
    ):
        return SqlValidationResult(
            ok=False,
            error="SQL Agent permite apenas SELECT/CTE read-only.",
            code="sql_not_read_only",
        )

    if _DML_RE.search(cleaned):
        return SqlValidationResult(
            ok=False,
            error="Comando SQL bloqueado por política de segurança (DML/DDL).",
            code="sql_blocked_keyword",
        )

    if _SYSTEM_TABLE_RE.search(cleaned):
        return SqlValidationResult(
            ok=False,
            error="Acesso a tabelas de sistema (pg_*, alembic_*) não é permitido.",
            code="sql_system_table_blocked",
        )

    if not allow_cross_tenant and not _TENANT_PARAM_RE.search(cleaned):
        return SqlValidationResult(
            ok=False,
            error=(
                "SQL analítico deve filtrar por empresa usando :empresa_id como parâmetro. "
                "Exemplo: WHERE empresa_id = :empresa_id"
            ),
            code="sql_missing_tenant_scope",
        )

    return SqlValidationResult(ok=True, sql=raw, risk_score=0, complexity={})
