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

    if not empresa_id:
        reasons.append("Usuário sem escopo de empresa para execução semântica.")

    if not is_engine_available_for_user(
        resolved_engine,
        is_superadmin=is_superadmin,
        is_gestor=is_gestor,
    ):
        reasons.append("Engine indisponível para este usuário/contexto.")

    if plan.capability in {"GenerateAnalyticsReport", "GeneratePrintableDocument"}:
        if resolved_engine != ENGINE_ANALYTICS:
            reasons.append("Relatórios semânticos exigem engine analytics (read-only).")
        if not is_sql_agent_enabled():
            reasons.append("SQL Agent analítico desabilitado por flag.")
    elif plan.capability in {
        "PrepareQuotePackage",
        "DeliverQuoteMultiChannel",
        "CreateCommercialProposal",
        "ExecuteCompositeWorkflow",
    }:
        if resolved_engine != ENGINE_OPERATIONAL:
            reasons.append("Capability transacional/documental exige engine operational.")

    if plan.capability == "UnknownCapability":
        reasons.append("Intenção fora das capabilities semânticas ativas.")

    return PolicyDecision(
        allowed=not reasons,
        reasons=reasons,
        risk_level="medium" if reasons else "low",
        limits={"max_rows": 200, "max_period_days": 365},
    )
