"""Telemetria e auditoria da execução semântica."""

from __future__ import annotations

from typing import Any

from app.services.assistant_autonomy.contracts import ExecutionResult, SemanticPlan
from app.services.audit_service import registrar_auditoria


def record_semantic_audit(
    *,
    db: Any,
    current_user: Any,
    request_id: str | None,
    sessao_id: str | None,
    plan: SemanticPlan,
    execution: ExecutionResult,
    policy_decision: Any | None = None,
) -> None:
    try:
        policy_payload = {
            "allowed": bool(getattr(policy_decision, "allowed", False)),
            "risk_level": getattr(policy_decision, "risk_level", "low"),
            "requires_confirmation": bool(
                getattr(policy_decision, "requires_confirmation", False)
            ),
            "governance_mode": getattr(policy_decision, "governance_mode", "read_only"),
            "recommended_engine": getattr(policy_decision, "recommended_engine", None),
            "allowed_export_formats": list(
                getattr(policy_decision, "allowed_export_formats", []) or []
            ),
            "limits": dict(getattr(policy_decision, "limits", {}) or {}),
        }
        registrar_auditoria(
            db=db,
            usuario=current_user,
            acao="assistente_autonomia_semantica",
            recurso="assistente_ia",
            recurso_id=str(getattr(current_user, "empresa_id", "")),
            detalhes={
                "request_id": request_id,
                "sessao_id": sessao_id,
                "capability": plan.capability,
                "domain": plan.request.domain,
                "metrics": plan.request.metrics,
                "comparison_mode": plan.request.comparison_mode,
                "filters": plan.request.entity_filters,
                "success": execution.success,
                "code": execution.code,
                "pending_confirmation": bool(execution.pending_action),
                "policy": policy_payload,
                "slo": {
                    "total_duration_ms": execution.metrics.get("total_duration_ms"),
                    "total_steps": execution.metrics.get("total_steps"),
                    "tools_total": execution.metrics.get("tools_total"),
                    "tools_ok": execution.metrics.get("tools_ok"),
                    "tools_failed": execution.metrics.get("tools_failed"),
                    "tools_pending": execution.metrics.get("tools_pending"),
                    "generated_at": execution.metrics.get("generated_at"),
                },
                "quality": {
                    "rows_total": execution.metrics.get("rows_total"),
                    "cache_hit": execution.metrics.get("cache_hit"),
                },
            },
        )
    except Exception:
        # Não interrompe fluxo do assistente por erro de auditoria
        return
