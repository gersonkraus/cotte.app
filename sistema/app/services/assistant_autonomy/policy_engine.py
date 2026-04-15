"""Policy engine central para execução semântica."""

from __future__ import annotations

from typing import Any

from app.services.assistant_autonomy.contracts import PolicyDecision, SemanticPlan
from app.services.assistant_engine_registry import (
    ENGINE_ANALYTICS,
    ENGINE_OPERATIONAL,
    is_engine_available_for_user,
    is_sql_agent_enabled,
    resolve_engine,
)


_ANALYTICS_CAPABILITIES = {"GenerateAnalyticsReport", "GeneratePrintableDocument"}
_TRANSACTIONAL_CAPABILITIES = {
    "PrepareQuotePackage",
    "DeliverQuoteMultiChannel",
    "ExecuteCompositeWorkflow",
}
_LOW_RISK_CAPABILITIES = {"GenerateAnalyticsReport", "GeneratePrintableDocument"}
_MEDIUM_RISK_CAPABILITIES = {"PrepareQuotePackage", "CreateCommercialProposal"}
_HIGH_RISK_CAPABILITIES = {"DeliverQuoteMultiChannel", "ExecuteCompositeWorkflow"}


def _resolve_risk_level(plan: SemanticPlan) -> str:
    if plan.capability in _HIGH_RISK_CAPABILITIES:
        return "high"
    if plan.capability in _MEDIUM_RISK_CAPABILITIES:
        return "medium"
    return "low"


def _resolve_limits(plan: SemanticPlan) -> dict[str, Any]:
    if plan.capability in _ANALYTICS_CAPABILITIES:
        return {
            "max_rows": 200,
            "max_period_days": 365,
            "max_export_rows": 500,
            "max_chart_points": 24,
        }
    return {
        "max_rows": 50,
        "max_period_days": 180,
        "max_export_rows": 100,
        "max_chart_points": 12,
    }


def evaluate_policy(
    *,
    plan: SemanticPlan,
    current_user: Any,
    engine: str | None,
) -> PolicyDecision:
    reasons: list[str] = []
    resolved_engine = resolve_engine(engine)
    is_superadmin = bool(getattr(current_user, "is_superadmin", False))
    is_gestor = bool(getattr(current_user, "is_gestor", False))
    empresa_id = getattr(current_user, "empresa_id", None)
    risk_level = _resolve_risk_level(plan)
    limits = _resolve_limits(plan)
    governance_mode = (
        "read_only" if plan.capability in _ANALYTICS_CAPABILITIES else "mixed_by_risk"
    )
    recommended_engine = (
        ENGINE_ANALYTICS
        if plan.capability in _ANALYTICS_CAPABILITIES
        else ENGINE_OPERATIONAL
    )
    allowed_export_formats = (
        ["csv", "txt", "html", "pdf"]
        if plan.capability in _ANALYTICS_CAPABILITIES
        else []
    )
    requires_confirmation = plan.capability in _TRANSACTIONAL_CAPABILITIES

    if not empresa_id:
        reasons.append("Usuário sem escopo de empresa para execução semântica.")

    if not is_engine_available_for_user(
        resolved_engine,
        is_superadmin=is_superadmin,
        is_gestor=is_gestor,
    ):
        reasons.append("Engine indisponível para este usuário/contexto.")

    if plan.capability in _ANALYTICS_CAPABILITIES:
        if resolved_engine != ENGINE_ANALYTICS:
            reasons.append("Relatórios semânticos exigem engine analytics (read-only).")
        if not is_sql_agent_enabled():
            reasons.append("SQL Agent analítico desabilitado por flag.")
    elif plan.capability in (
        _TRANSACTIONAL_CAPABILITIES | {"CreateCommercialProposal"}
    ):
        if resolved_engine != ENGINE_OPERATIONAL:
            reasons.append("Capability transacional/documental exige engine operational.")

    if plan.capability == "UnknownCapability":
        reasons.append("Intenção fora das capabilities semânticas ativas.")

    if int(plan.request.period_days or 0) > int(limits.get("max_period_days") or 365):
        reasons.append("Janela solicitada acima do limite operacional da capability.")

    return PolicyDecision(
        allowed=not reasons,
        reasons=reasons,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        governance_mode=governance_mode,
        recommended_engine=recommended_engine,
        allowed_export_formats=allowed_export_formats,
        limits=limits,
    )
