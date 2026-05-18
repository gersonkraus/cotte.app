"""Tool SQL analítica read-only com guardrails de segurança."""

from __future__ import annotations

from typing import Any, Optional

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
    empresa_id_filtro: Optional[int] = Field(
        default=None,
        description="ID da empresa para filtrar (apenas superadmin). Se None, usa empresa do usuário.",
    )


def _ensure_limit(sql: str, limit: int) -> str:
    return f"SELECT * FROM ({sql.rstrip()}) AS analytics_scoped_result LIMIT :_agent_limit"


async def _executar_sql_analitico(
    inp: ExecutarSqlAnaliticoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    is_superadmin = bool(getattr(current_user, "is_superadmin", False))
    empresa_id_alvo: int

    if inp.empresa_id_filtro is not None:
        if not is_superadmin:
            return {
                "error": (
                    "O usuário autenticado não possui permissão para consultar outra empresa. "
                    "Apenas superadmin pode usar empresa_id_filtro."
                ),
                "code": "forbidden_cross_tenant"
            }
        empresa_id_alvo = inp.empresa_id_filtro
    else:
        if not getattr(current_user, "empresa_id", None):
            return {"error": "Usuário sem escopo de empresa.", "code": "tenant_scope_required"}
        empresa_id_alvo = int(current_user.empresa_id)

    allow_cross_tenant = is_superadmin and inp.empresa_id_filtro is not None
    validation = validate_analytics_sql(inp.sql, allow_cross_tenant=allow_cross_tenant)
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
                "empresa_id": empresa_id_alvo,
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
        recurso_id=str(empresa_id_alvo),
        detalhes={
            "sql_original": inp.sql,
            "sql_final": sql_final,
            "row_count": len(rows),
            "limit": inp.limit,
            "risk_score": validation.risk_score,
            "complexity": validation.complexity or {},
            "tenant_scope": {
                "empresa_id_param": empresa_id_alvo,
                "empresa_id_filtro": inp.empresa_id_filtro,
                "is_cross_tenant": inp.empresa_id_filtro is not None and inp.empresa_id_filtro != current_user.empresa_id,
            },
        },
    )
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "sql_final": sql_final,
        "risk_score": validation.risk_score,
        "complexity": validation.complexity or {},
        "empresa_id_consultado": empresa_id_alvo,
    }


executar_sql_analitico = ToolSpec(
    name="executar_sql_analitico",
    description=(
        "Ferramenta principal para responder a perguntas analíticas e de negócio do usuário usando o banco de dados. "
        "USE ESTA FERRAMENTA para: criar rankings (ex: os 5 melhores clientes, piores pagadores, mais vendidos), "
        "obter contagens (quantos orçamentos aprovados), estatísticas, valores médios, tickets médios, "
        "faturamento, agrupamentos (vendas por mês/dia/vendedor) e cruzar dados de diferentes tabelas. "
        "Executa SQL em modo read-only bloqueado contra DML/DDL. Aceita apenas SELECT/CTE."
    ),
    input_model=ExecutarSqlAnaliticoInput,
    handler=_executar_sql_analitico,
    destrutiva=False,
    permissao_recurso="ia",
    permissao_acao="leitura",
)
