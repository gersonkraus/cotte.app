"""Catálogo semântico de métricas e dimensões do assistente."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    description: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class DimensionDefinition:
    key: str
    label: str
    aliases: tuple[str, ...]


METRICS_CATALOG: dict[str, MetricDefinition] = {
    "revenue_total": MetricDefinition(
        key="revenue_total",
        label="Faturamento total",
        description="Soma de receitas no período filtrado.",
        aliases=("faturamento", "vendas", "receita", "total vendido"),
    ),
    "overdue_receivables": MetricDefinition(
        key="overdue_receivables",
        label="Contas a receber vencidas",
        description="Total de contas a receber com vencimento anterior a hoje.",
        aliases=("vencidas", "inadimplencia", "contas vencidas", "a receber vencidas"),
    ),
    "top_customers": MetricDefinition(
        key="top_customers",
        label="Top clientes",
        description="Clientes com maior volume financeiro no período.",
        aliases=("clientes que mais compraram", "top clientes", "melhores clientes"),
    ),
    "seller_performance": MetricDefinition(
        key="seller_performance",
        label="Performance de vendedores",
        description="Indicadores agregados por vendedor/responsável comercial.",
        aliases=("vendedores", "performance vendedor", "ranking vendedores"),
    ),
    "quote_conversion": MetricDefinition(
        key="quote_conversion",
        label="Conversão de orçamentos",
        description="Taxa de aprovação/conversão de orçamentos.",
        aliases=("conversao", "taxa de aprovacao", "orcamentos aprovados"),
    ),
    "operations_productivity": MetricDefinition(
        key="operations_productivity",
        label="Produtividade operacional",
        description="Volume de agendamentos e execução operacional no período.",
        aliases=("produtividade", "agendamentos", "operacao", "operação"),
    ),
    "commercial_funnel": MetricDefinition(
        key="commercial_funnel",
        label="Funil comercial",
        description="Distribuição de leads por etapa e status de ganho/perda.",
        aliases=("funil", "pipeline", "leads", "etapa comercial"),
    ),
    "seller_commission": MetricDefinition(
        key="seller_commission",
        label="Comissão de vendedores",
        description="Estimativa de comissão por vendedor com base em percentual informado.",
        aliases=("comissao", "comissão", "percentual", "8%", "10%"),
    ),
    "document_generation": MetricDefinition(
        key="document_generation",
        label="Geração de documento",
        description="Pedido de conteúdo formal para impressão/PDF.",
        aliases=("imprimir", "imprimível", "pdf", "documento"),
    ),
}


DIMENSIONS_CATALOG: dict[str, DimensionDefinition] = {
    "time_month": DimensionDefinition(
        key="time_month",
        label="Mês",
        aliases=("mes", "mês", "mensal", "por mes", "por mês"),
    ),
    "time_quarter": DimensionDefinition(
        key="time_quarter",
        label="Trimestre",
        aliases=("trimestre", "trimestral"),
    ),
    "customer": DimensionDefinition(
        key="customer",
        label="Cliente",
        aliases=("cliente", "clientes"),
    ),
    "seller": DimensionDefinition(
        key="seller",
        label="Vendedor",
        aliases=("vendedor", "vendedores", "responsavel"),
    ),
    "channel": DimensionDefinition(
        key="channel",
        label="Canal",
        aliases=("canal", "whatsapp", "email"),
    ),
    "stage": DimensionDefinition(
        key="stage",
        label="Etapa",
        aliases=("etapa", "stage", "pipeline"),
    ),
    "status": DimensionDefinition(
        key="status",
        label="Status",
        aliases=("status", "situação", "situacao"),
    ),
    "category": DimensionDefinition(
        key="category",
        label="Categoria",
        aliases=("categoria", "categorias", "classe"),
    ),
}


def detect_metrics(text: str) -> list[str]:
    normalized = (text or "").lower()
    selected: list[str] = []
    for metric_key, metric in METRICS_CATALOG.items():
        if any(alias in normalized for alias in metric.aliases):
            selected.append(metric_key)
    if not selected and any(word in normalized for word in ("relatorio", "resumo", "desempenho")):
        selected.append("revenue_total")
    return selected


def detect_dimensions(text: str) -> list[str]:
    normalized = (text or "").lower()
    selected: list[str] = []
    for dim_key, dim in DIMENSIONS_CATALOG.items():
        if any(alias in normalized for alias in dim.aliases):
            selected.append(dim_key)
    return selected
