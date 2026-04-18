"""Ferramentas de relatórios financeiros especializados e seguros."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Usuario
from app.services.audit_service import registrar_auditoria

from ._base import ToolSpec


def _sql_customer_ranking_month_over_month() -> str:
    """Query SQL pré-definida e segura para ranking de clientes."""
    return (
        "WITH curr AS ( "
        "SELECT c.id AS cliente_id, c.nome AS cliente_nome, "
        "COALESCE(SUM(o.total),0) AS faturamento_mes_atual, "
        "COUNT(o.id) AS pedidos_mes_atual "
        "FROM clientes c "
        "JOIN orcamentos o ON o.cliente_id = c.id "
        "WHERE c.empresa_id = :empresa_id "
        "AND o.empresa_id = :empresa_id "
        "AND o.aprovado_em >= DATE_TRUNC('month', CURRENT_DATE) "
        "AND o.aprovado_em < (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month') "
        "GROUP BY c.id, c.nome "
        "), prev AS ( "
        "SELECT o.cliente_id, COALESCE(SUM(o.total),0) AS faturamento_mes_anterior "
        "FROM orcamentos o "
        "WHERE o.empresa_id = :empresa_id "
        "AND o.aprovado_em >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month') "
        "AND o.aprovado_em < DATE_TRUNC('month', CURRENT_DATE) "
        "GROUP BY o.cliente_id "
        ") "
        "SELECT curr.cliente_id, curr.cliente_nome, curr.faturamento_mes_atual, "
        "CASE WHEN curr.pedidos_mes_atual > 0 "
        "THEN ROUND(curr.faturamento_mes_atual / curr.pedidos_mes_atual, 2) "
        "ELSE 0 END AS ticket_medio, "
        "COALESCE(prev.faturamento_mes_anterior, 0) AS faturamento_mes_anterior, "
        "CASE "
        "WHEN COALESCE(prev.faturamento_mes_anterior, 0) = 0 THEN NULL "
        "ELSE ROUND(((curr.faturamento_mes_atual - prev.faturamento_mes_anterior) / "
        "prev.faturamento_mes_anterior) * 100.0, 2) END AS variacao_percentual "
        "FROM curr "
        "LEFT JOIN prev ON prev.cliente_id = curr.cliente_id "
        "ORDER BY curr.faturamento_mes_atual DESC "
        "LIMIT 10"
    )


class GerarRelatorioRankingClientesInput(BaseModel):
    """Não requer input, o período é fixo (mês atual vs anterior)."""

    pass


async def _gerar_relatorio_ranking_clientes(
    inp: GerarRelatorioRankingClientesInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    """Handler que executa a query de ranking de clientes."""
    if not getattr(current_user, "empresa_id", None):
        return {
            "error": "Usuário sem escopo de empresa.",
            "code": "tenant_scope_required",
        }

    sql = _sql_customer_ranking_month_over_month()
    try:
        result = db.execute(
            text(sql),
            {"empresa_id": int(current_user.empresa_id)},
        )
        rows = [dict(row) for row in result.mappings().all()]
        columns = list(rows[0].keys()) if rows else []
    except Exception as exc:
        return {
            "error": f"Falha ao executar relatório: {exc}",
            "code": "report_execution_error",
        }

    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="report_ranking_clientes",
        recurso="relatorios",
        recurso_id=str(current_user.empresa_id),
        detalhes={"row_count": len(rows)},
    )
    return {
        "titulo": "Ranking de Clientes (Mês Atual vs. Anterior)",
        "descricao": "Clientes com maior faturamento em orçamentos aprovados no mês corrente, com comparação ao mês anterior.",
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


gerar_relatorio_ranking_clientes = ToolSpec(
    name="gerar_relatorio_ranking_clientes",
    description=(
        "Gera um relatório com o ranking dos clientes por faturamento no mês atual, "
        "comparando com o faturamento do mês anterior. Ideal para perguntas como 'quais os melhores clientes este mês?' "
        "ou 'ranking de clientes por faturamento'."
    ),
    input_model=GerarRelatorioRankingClientesInput,
    handler=_gerar_relatorio_ranking_clientes,
    destrutiva=False,
    permissao_recurso="financeiro",
    permissao_acao="leitura",
)
