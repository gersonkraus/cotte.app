"""Tool SQL analítica read-only com guardrails de segurança."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Usuario
from app.services.analytics_sql_guard import validate_analytics_sql
from app.services.audit_service import registrar_auditoria

from ._base import ToolSpec


class ExecutarSqlAnaliticoInput(BaseModel):
    sql: str = Field(min_length=5, max_length=4000)
    limit: int = Field(default=50, ge=1, le=200)


def _ensure_limit(sql: str, limit: int) -> str:
    return f"SELECT * FROM ({sql.rstrip()}) AS analytics_scoped_result LIMIT :_agent_limit"


async def _executar_sql_analitico(
    inp: ExecutarSqlAnaliticoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    if not getattr(current_user, "empresa_id", None):
        return {"error": "Usuário sem escopo de empresa.", "code": "tenant_scope_required"}

    validation = validate_analytics_sql(inp.sql)
    if not validation.ok:
        return {
            "error": validation.error or "SQL inválido",
            "code": validation.code or "invalid_input",
            "risk_score": validation.risk_score,
            "complexity": validation.complexity or {},
        }

    sql_final = _ensure_limit(validation.sql or inp.sql, inp.limit)
    try:
        result = db.execute(
            text(sql_final),
            {
                "empresa_id": int(current_user.empresa_id),
                "_agent_limit": int(inp.limit),
            },
        )
        rows = [dict(row) for row in result.mappings().all()]
        columns = list(rows[0].keys()) if rows else []
    except Exception as exc:
        return {"error": f"Falha ao executar SQL: {exc}", "code": "sql_execution_error"}

    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="analytics_sql_agent_query",
        recurso="analytics_sql",
        recurso_id=str(current_user.empresa_id),
        detalhes={
            "sql_original": inp.sql,
            "sql_final": sql_final,
            "row_count": len(rows),
            "limit": inp.limit,
            "risk_score": validation.risk_score,
            "complexity": validation.complexity or {},
            "tenant_scope": {"empresa_id_param": int(current_user.empresa_id)},
        },
    )
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "sql_final": sql_final,
        "risk_score": validation.risk_score,
        "complexity": validation.complexity or {},
    }


executar_sql_analitico = ToolSpec(
    name="executar_sql_analitico",
    description=(
        "Executa SQL analítico em modo read-only com whitelist de fontes e bloqueio de DML/DDL. "
        "Aceita apenas SELECT/CTE."
    ),
    input_model=ExecutarSqlAnaliticoInput,
    handler=_executar_sql_analitico,
    destrutiva=False,
    permissao_recurso="ia",
    permissao_acao="leitura",
)
