"""Capabilities semânticas compostas sobre adapters existentes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

from app.services.assistant_autonomy.contracts import SemanticPlan
from app.services.assistant_autonomy.sql_hybrid_planner import plan_sql_hybrid


@dataclass
class ToolCallSpec:
    name: str
    args: dict[str, Any]


def _escape_sql_literal(value: str) -> str:
    return (value or "").replace("'", "''")


def _clamp_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        val = int(value)
        return max(min_value, min(max_value, val))
    except Exception:
        return default


def _analytics_sql_top_customers(period_days: int) -> str:
    return (
        "SELECT c.id, c.nome, COALESCE(SUM(o.total),0) AS total_comprado, "
        "COUNT(o.id) AS total_orcamentos "
        "FROM clientes c "
        "JOIN orcamentos o ON o.cliente_id = c.id "
        "WHERE c.empresa_id = :empresa_id "
        "AND o.empresa_id = :empresa_id "
        f"AND o.aprovado_em >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        "GROUP BY c.id, c.nome "
        "ORDER BY total_comprado DESC"
    )


def _analytics_sql_overdue_receivables() -> str:
    return (
        "SELECT COUNT(*) AS total_titulos, COALESCE(SUM(valor),0) AS total_vencido "
        "FROM contas_financeiras "
        "WHERE empresa_id = :empresa_id "
        "AND tipo = 'RECEBER' "
        "AND status = 'PENDENTE' "
        "AND vencimento < CURRENT_DATE"
    )


def _analytics_sql_month_comparison(period_days: int) -> str:
    days = max(60, period_days)
    return (
        "SELECT DATE_TRUNC('month', aprovado_em) AS mes, "
        "COALESCE(SUM(total),0) AS total_vendas "
        "FROM orcamentos "
        "WHERE empresa_id = :empresa_id "
        f"AND aprovado_em >= (CURRENT_DATE - INTERVAL '{days} days') "
        "GROUP BY DATE_TRUNC('month', aprovado_em) "
        "ORDER BY mes ASC"
    )


def _analytics_sql_seller_ranking(period_days: int, seller_name: str | None = None) -> str:
    seller_filter = ""
    if seller_name:
        seller_filter = f" AND u.nome ILIKE '%{_escape_sql_literal(seller_name)}%' "
    return (
        "SELECT COALESCE(u.nome, 'Sem vendedor') AS vendedor, "
        "COUNT(o.id) AS total_orcamentos, "
        "COALESCE(SUM(o.total),0) AS total_vendas "
        "FROM orcamentos o "
        "LEFT JOIN usuarios u ON u.id = o.criado_por_id "
        "WHERE o.empresa_id = :empresa_id "
        f"AND o.aprovado_em >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        f"{seller_filter}"
        "GROUP BY COALESCE(u.nome, 'Sem vendedor') "
        "ORDER BY total_vendas DESC"
    )


def _analytics_sql_commission_report(period_days: int, commission_pct: float, seller_name: str | None = None) -> str:
    pct = max(0.0, min(100.0, float(commission_pct or 0.0)))
    seller_filter = ""
    if seller_name:
        seller_filter = f" AND u.nome ILIKE '%{_escape_sql_literal(seller_name)}%' "
    return (
        "SELECT COALESCE(u.nome, 'Sem vendedor') AS vendedor, "
        "COALESCE(SUM(o.total),0) AS total_vendas, "
        f"ROUND(COALESCE(SUM(o.total),0) * ({pct} / 100.0), 2) AS comissao_estimada, "
        f"{pct}::numeric AS percentual_comissao "
        "FROM orcamentos o "
        "LEFT JOIN usuarios u ON u.id = o.criado_por_id "
        "WHERE o.empresa_id = :empresa_id "
        f"AND o.aprovado_em >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        f"{seller_filter}"
        "GROUP BY COALESCE(u.nome, 'Sem vendedor') "
        "ORDER BY comissao_estimada DESC"
    )


def _analytics_sql_by_categories(period_days: int, categories: list[str]) -> str:
    values = ",".join(f"'{_escape_sql_literal(cat)}'" for cat in categories)
    return (
        "SELECT i.descricao AS categoria, "
        "COALESCE(SUM(i.total),0) AS total_categoria, "
        "COUNT(DISTINCT o.id) AS total_orcamentos "
        "FROM itens_orcamento i "
        "JOIN orcamentos o ON o.id = i.orcamento_id "
        "WHERE o.empresa_id = :empresa_id "
        f"AND o.aprovado_em >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        f"AND i.descricao IN ({values}) "
        "GROUP BY i.descricao "
        "ORDER BY total_categoria DESC"
    )


def _analytics_sql_default(period_days: int) -> str:
    return (
        "SELECT DATE_TRUNC('day', criado_em) AS dia, "
        "COALESCE(SUM(valor),0) AS total_movimentado "
        "FROM movimentacoes_caixa "
        "WHERE empresa_id = :empresa_id "
        f"AND criado_em >= (CURRENT_DATE - INTERVAL '{period_days} days') "
        "GROUP BY DATE_TRUNC('day', criado_em) "
        "ORDER BY dia ASC"
    )


def _analytics_sql_from_plan(plan: SemanticPlan) -> str:
    req = plan.request
    text = req.raw_message.lower()
    period_days = _clamp_int(req.period_days, 30, 1, 365)
    filters = req.entity_filters or {}
    seller_name = filters.get("seller_name")
    commission_pct = filters.get("commission_pct")
    categories = filters.get("categories") or []

    if categories:
        return _analytics_sql_by_categories(period_days, categories)
    if "clientes" in text and "compr" in text:
        return _analytics_sql_top_customers(period_days)
    if "vencid" in text and "receber" in text:
        return _analytics_sql_overdue_receivables()
    if "comiss" in text or commission_pct is not None:
        return _analytics_sql_commission_report(period_days, commission_pct or 0.0, seller_name)
    if "vendedor" in text or "ranking" in text:
        return _analytics_sql_seller_ranking(period_days, seller_name)
    if "compar" in text and ("mes" in text or "mês" in text or "trimestre" in text):
        return _analytics_sql_month_comparison(period_days)
    hybrid = plan_sql_hybrid(plan)
    return hybrid.sql


def _parse_quote_args_from_message(message: str) -> dict[str, Any]:
    text = (message or "")
    normalized = text.replace(",", ".")
    cliente_nome = None
    cliente_match = re.search(r"cliente\s+([A-ZÀ-ÿ][\wÀ-ÿ'’-]*(?:\s+[A-ZÀ-ÿ][\wÀ-ÿ'’-]*){0,2})", text, flags=re.IGNORECASE)
    if cliente_match:
        cliente_nome = cliente_match.group(1).strip()

    servico = "Serviço personalizado"
    servico_match = re.search(r"itens?\s+(.+?)(?:\s+com|\s+e\s+condi|$)", text, flags=re.IGNORECASE)
    if servico_match:
        servico = servico_match.group(1).strip(" .")

    valor = 0.0
    valor_match = re.search(r"(?:r\$|valor\s+de?\s*)(\d+(?:\.\d{1,2})?)", normalized, flags=re.IGNORECASE)
    if valor_match:
        valor = float(valor_match.group(1))
    if valor <= 0:
        valor = 100.0

    item = {"descricao": servico, "quantidade": 1, "valor_unit": valor}
    args = {"cliente_nome": cliente_nome or "Cliente a confirmar", "itens": [item]}
    return args


def _parse_delivery_args_from_message(plan: SemanticPlan) -> dict[str, Any]:
    raw = plan.request.raw_message or ""
    filters = plan.request.entity_filters or {}
    quote_identifier = filters.get("quote_identifier")
    channels = (filters.get("channels") or {})
    send_whatsapp = channels.get("whatsapp") or "whatsapp" in raw.lower()
    send_email = channels.get("email") or "email" in raw.lower() or "e-mail" in raw.lower()
    if not quote_identifier:
        quote_identifier = "ultimo"
    out: dict[str, Any] = {}
    if send_whatsapp:
        out["send_whatsapp"] = {"orcamento_id": quote_identifier}
    if send_email:
        out["send_email"] = {"orcamento_id": quote_identifier}
    return out


def build_tool_calls_for_plan(plan: SemanticPlan, override_args: dict[str, Any] | None = None) -> list[ToolCallSpec]:
    if plan.capability == "GenerateAnalyticsReport":
        sql = str((override_args or {}).get("sql_candidate") or "").strip() or _analytics_sql_from_plan(plan)
        limit = _clamp_int((override_args or {}).get("sql_limit"), 120, 1, 200)
        hybrid = plan_sql_hybrid(plan)
        return [
            ToolCallSpec(
                name="executar_sql_analitico",
                args={
                    "sql": sql,
                    "limit": limit,
                    "_meta": {
                        "planner_source": hybrid.source,
                        "planner_rationale": hybrid.rationale,
                    },
                },
            )
        ]

    if plan.capability == "GeneratePrintableDocument":
        sql = str((override_args or {}).get("sql_candidate") or "").strip() or _analytics_sql_from_plan(plan)
        limit = _clamp_int((override_args or {}).get("sql_limit"), 120, 1, 200)
        hybrid = plan_sql_hybrid(plan)
        return [
            ToolCallSpec(
                name="executar_sql_analitico",
                args={
                    "sql": sql,
                    "limit": limit,
                    "_meta": {
                        "planner_source": hybrid.source,
                        "planner_rationale": hybrid.rationale,
                    },
                },
            )
        ]

    if plan.capability == "PrepareQuotePackage":
        args = dict(override_args or {})
        if not args:
            args = _parse_quote_args_from_message(plan.request.raw_message)
        if not args:
            return []
        return [ToolCallSpec(name="criar_orcamento", args=args)]

    if plan.capability == "DeliverQuoteMultiChannel":
        args = dict(override_args or {})
        if not args:
            args = _parse_delivery_args_from_message(plan)
        out: list[ToolCallSpec] = []
        if args.get("send_whatsapp"):
            out.append(ToolCallSpec(name="enviar_orcamento_whatsapp", args=args["send_whatsapp"]))
        if args.get("send_email"):
            out.append(ToolCallSpec(name="enviar_orcamento_email", args=args["send_email"]))
        return out

    if plan.capability == "ExecuteCompositeWorkflow":
        chain: list[ToolCallSpec] = []
        base_quote_args = dict(override_args or {}).get("quote") or {}
        if not base_quote_args:
            base_quote_args = _parse_quote_args_from_message(plan.request.raw_message)
        if base_quote_args:
            chain.append(ToolCallSpec(name="criar_orcamento", args=base_quote_args))
        delivery_args = dict(override_args or {}).get("delivery") or _parse_delivery_args_from_message(plan)
        if delivery_args.get("send_whatsapp"):
            chain.append(ToolCallSpec(name="enviar_orcamento_whatsapp", args=delivery_args["send_whatsapp"]))
        if delivery_args.get("send_email"):
            chain.append(ToolCallSpec(name="enviar_orcamento_email", args=delivery_args["send_email"]))
        return chain

    # CreateCommercialProposal e outras capabilities sem side-effect imediato
    return []
