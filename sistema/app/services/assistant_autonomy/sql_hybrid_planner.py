"""Planejador SQL híbrido para autonomia analítica."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.assistant_autonomy.contracts import SemanticPlan


@dataclass(frozen=True)
class SqlPlanningOutput:
    sql: str
    rationale: str
    source: str


def _sql_customer_ranking_month_over_month() -> str:
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


def _sql_operations_productivity(period_days: int) -> str:
    return (
        "SELECT DATE_TRUNC('day', a.data_agendada) AS dia, "
        "COUNT(a.id) AS total_agendamentos, "
        "COUNT(*) FILTER (WHERE a.status IN ('concluido', 'confirmado')) AS concluidos_confirmados "
        "FROM agendamentos a "
        "WHERE a.empresa_id = :empresa_id "
        f"AND a.data_agendada >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        "GROUP BY DATE_TRUNC('day', a.data_agendada) "
        "ORDER BY dia ASC"
    )


def _sql_funnel_commercial(period_days: int) -> str:
    return (
        "SELECT COALESCE(l.stage_slug, 'sem_stage') AS etapa, "
        "COUNT(l.id) AS total_leads, "
        "COUNT(*) FILTER (WHERE l.status = 'ganho') AS ganhos, "
        "COUNT(*) FILTER (WHERE l.status = 'perdido') AS perdidos "
        "FROM commercial_leads l "
        "WHERE l.empresa_id = :empresa_id "
        f"AND l.criado_em >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        "GROUP BY COALESCE(l.stage_slug, 'sem_stage') "
        "ORDER BY total_leads DESC"
    )


def _sql_receivables_aging() -> str:
    return (
        "SELECT "
        "CASE "
        "WHEN (CURRENT_DATE - c.vencimento) BETWEEN 1 AND 7 THEN '1-7 dias' "
        "WHEN (CURRENT_DATE - c.vencimento) BETWEEN 8 AND 30 THEN '8-30 dias' "
        "WHEN (CURRENT_DATE - c.vencimento) > 30 THEN '31+ dias' "
        "ELSE 'em dia' END AS faixa_atraso, "
        "COUNT(c.id) AS total_titulos, "
        "COALESCE(SUM(c.valor - COALESCE(c.valor_pago,0)),0) AS valor_pendente "
        "FROM contas_financeiras c "
        "WHERE c.empresa_id = :empresa_id "
        "AND c.tipo = 'RECEBER' "
        "AND c.status = 'PENDENTE' "
        "GROUP BY faixa_atraso "
        "ORDER BY total_titulos DESC"
    )


def plan_sql_hybrid(plan: SemanticPlan) -> SqlPlanningOutput:
    text = (plan.request.raw_message or "").lower()
    period_days = max(1, min(365, int(plan.request.period_days or 30)))

    if "ranking" in text and "cliente" in text and "faturamento" in text:
        return SqlPlanningOutput(
            sql=_sql_customer_ranking_month_over_month(),
            rationale="Template determinístico para ranking de clientes MoM.",
            source="deterministic_template",
        )
    if "funil" in text or "lead" in text:
        return SqlPlanningOutput(
            sql=_sql_funnel_commercial(period_days),
            rationale="Template determinístico para funil comercial por etapa.",
            source="deterministic_template",
        )
    if "agendamento" in text or "produtividade" in text:
        return SqlPlanningOutput(
            sql=_sql_operations_productivity(period_days),
            rationale="Template determinístico para produtividade operacional.",
            source="deterministic_template",
        )
    if "inadimpl" in text or ("receber" in text and "venc" in text):
        return SqlPlanningOutput(
            sql=_sql_receivables_aging(),
            rationale="Template determinístico para aging de contas a receber.",
            source="deterministic_template",
        )

    # Fallback híbrido: SQL composto por heurística em torno de receita por período.
    sql = (
        "SELECT DATE_TRUNC('day', o.aprovado_em) AS dia, "
        "COALESCE(SUM(o.total),0) AS receita_total, "
        "COUNT(o.id) AS total_orcamentos "
        "FROM orcamentos o "
        "WHERE o.empresa_id = :empresa_id "
        f"AND o.aprovado_em >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        "GROUP BY DATE_TRUNC('day', o.aprovado_em) "
        "ORDER BY dia ASC"
    )
    return SqlPlanningOutput(
        sql=sql,
        rationale="Fallback híbrido para série temporal de receita e volume de orçamentos.",
        source="hybrid_fallback",
    )
