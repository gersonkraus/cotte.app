"""Planner semântico orientado a intenções e contratos."""

from __future__ import annotations

import re
from typing import Any

from app.services.assistant_autonomy.contracts import (
    PlanStep,
    SemanticPlan,
    SemanticRequest,
)
from app.services.assistant_autonomy.intent_router import route_intent
from app.services.assistant_autonomy.semantic_model import detect_dimensions, detect_metrics


def _extract_period_days(message: str) -> int:
    text = (message or "").lower()
    match = re.search(r"(\d{1,3})\s*dias", text)
    if match:
        return max(1, min(365, int(match.group(1))))
    if "trimestre" in text:
        return 90
    if "mes passado" in text or "mês passado" in text:
        return 60
    if "mes" in text or "mês" in text:
        return 30
    if "semana" in text:
        return 7
    if "ano" in text:
        return 365
    return 30


def _extract_output_formats(message: str) -> list[str]:
    text = (message or "").lower()
    formats: list[str] = ["text"]
    if any(token in text for token in ("tabela", "relatorio", "relatório", "resumo", "ranking", "compar")):
        formats.append("table")
    if "grafico" in text or "gráfico" in text:
        formats.append("chart")
    if "imprim" in text or "pdf" in text:
        formats.append("printable")
    return list(dict.fromkeys(formats))


def _extract_comparison_mode(message: str) -> str:
    text = (message or "").lower()
    if "trimestre" in text and ("compar" in text or "compare" in text):
        return "quarter_over_quarter"
    if "compare" in text or "compar" in text:
        return "month_over_month"
    return "none"


def _extract_categories(message: str) -> list[str]:
    text = (message or "")
    lower = text.lower()
    if "categoria" not in lower:
        return []
    m = re.search(r"categorias?\s+(.+?)(?:\s+no\s+periodo|\s+no\s+período|$)", text, flags=re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1).strip(" .")
    parts = re.split(r",| e |/|\|", raw)
    cleaned = [p.strip(" .") for p in parts if p and p.strip(" .")]
    return cleaned[:8]


def _extract_seller_name(message: str) -> str | None:
    text = (message or "")
    m = re.search(
        r"vendedor(?:a)?\s+([A-ZÀ-ÿ][\wÀ-ÿ'’-]*(?:\s+[A-ZÀ-ÿ][\wÀ-ÿ'’-]*){0,2})",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return None


def _extract_commission_pct(message: str) -> float | None:
    text = (message or "").replace(",", ".")
    m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", text)
    if not m:
        return None
    value = float(m.group(1))
    return max(0.0, min(100.0, value))


def _extract_quote_identifier(message: str) -> str | None:
    text = (message or "")
    m = re.search(r"\bORC[-\s]?\d[\w-]*\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(0).replace(" ", "-").upper()
    m2 = re.search(r"\bor[çc]amento\s+#?(\d{1,8})\b", text, flags=re.IGNORECASE)
    if m2:
        return m2.group(1)
    return None


def _extract_channels(message: str) -> dict[str, bool]:
    lower = (message or "").lower()
    return {
        "whatsapp": "whatsapp" in lower,
        "email": ("e-mail" in lower) or ("email" in lower),
    }


def _extract_entity_filters(message: str) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    seller_name = _extract_seller_name(message)
    if seller_name:
        filters["seller_name"] = seller_name

    commission_pct = _extract_commission_pct(message)
    if commission_pct is not None:
        filters["commission_pct"] = commission_pct

    categories = _extract_categories(message)
    if categories:
        filters["categories"] = categories

    quote_identifier = _extract_quote_identifier(message)
    if quote_identifier:
        filters["quote_identifier"] = quote_identifier

    channels = _extract_channels(message)
    if channels["whatsapp"] or channels["email"]:
        filters["channels"] = channels

    return filters


def _resolve_capability(message: str, domain: str) -> str:
    text = (message or "").lower()
    if domain == "analytics":
        return "GenerateAnalyticsReport"
    if domain == "document_ops":
        return "GeneratePrintableDocument"
    if domain == "communication" and "orc" in text:
        return "DeliverQuoteMultiChannel"
    if domain == "quote_ops":
        return "PrepareQuotePackage"
    if domain == "commercial":
        return "CreateCommercialProposal"
    if domain == "composite_ops":
        return "ExecuteCompositeWorkflow"
    return "UnknownCapability"


def build_semantic_plan(message: str) -> SemanticPlan:
    domain = route_intent(message)
    capability = _resolve_capability(message, domain)
    entity_filters = _extract_entity_filters(message)
    request = SemanticRequest(
        raw_message=message,
        domain=domain,
        capability=capability,
        metrics=detect_metrics(message),
        dimensions=detect_dimensions(message),
        period_days=_extract_period_days(message),
        comparison_mode=_extract_comparison_mode(message),
        output_formats=_extract_output_formats(message),
        entity_filters=entity_filters,
    )

    steps = [
        PlanStep(name="resolve_intent", stage="resolve"),
        PlanStep(name="fetch_business_data", stage="fetch"),
        PlanStep(name="aggregate_metrics", stage="aggregate"),
        PlanStep(name="compose_output_contract", stage="compose"),
    ]
    if capability in {"PrepareQuotePackage", "DeliverQuoteMultiChannel", "ExecuteCompositeWorkflow"}:
        steps.append(PlanStep(name="validate_transaction_guard", stage="resolve"))
    if capability == "ExecuteCompositeWorkflow":
        steps.append(PlanStep(name="run_composite_chain", stage="deliver"))
    if "printable" in request.output_formats:
        steps.append(PlanStep(name="prepare_printable_payload", stage="deliver", required=False))

    return SemanticPlan(
        capability=capability,
        request=request,
        steps=steps,
        rationale=(
            "Plano semântico gerado a partir de intenção, métricas e formato de saída "
            "com governança por política central."
        ),
    )
