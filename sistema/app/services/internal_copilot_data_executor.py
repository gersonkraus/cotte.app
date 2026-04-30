"""Adaptador de dados do copiloto interno via autonomia semântica."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.services.assistant_autonomy.runtime import try_handle_semantic_autonomy
from app.services.assistant_engine_registry import ENGINE_ANALYTICS
from app.services.internal_copilot_agents import LogicalAgentRunResult


def _is_short_follow_up(message: str) -> bool:
    normalized = (message or "").strip()
    return bool(normalized) and len(normalized.split()) <= 4


def _build_message_seed(agent_run: LogicalAgentRunResult) -> str:
    original = (agent_run.context.mensagem_original or "").strip()
    objective = (agent_run.context.decision.objetivo_ativo or "").strip()
    if agent_run.context.decision.continuidade_aplicada and objective and _is_short_follow_up(original):
        return objective
    return original


def _apply_output_hint(message: str, preferred_output: str) -> str:
    lowered = (message or "").lower()
    if preferred_output == "table" and "tabela" not in lowered:
        return f"{message} em formato de tabela"
    if preferred_output == "chart" and not any(token in lowered for token in ("grafico", "gráfico")):
        return f"{message} com gráfico"
    if preferred_output == "summary" and not any(
        token in lowered for token in ("resumo", "sumario", "sumário", "executivo")
    ):
        return f"{message} em formato de resumo executivo"
    return message


def _build_semantic_message(agent_run: LogicalAgentRunResult) -> str:
    business_data = agent_run.business_data
    seed = _build_message_seed(agent_run)
    if business_data is not None:
        seed = _apply_output_hint(seed, business_data.preferred_output)
    return seed


def _build_override_args(agent_run: LogicalAgentRunResult) -> dict[str, Any]:
    business_data = agent_run.business_data
    if business_data is None:
        return {}
    preferred_output = business_data.preferred_output
    if preferred_output == "table":
        return {"preferencias": {"preferencia_visualizacao_usuario": {"formato_preferido": "tabela"}}}
    if preferred_output == "summary":
        return {"preferencias": {"preferencia_visualizacao_usuario": {"formato_preferido": "resumo"}}}
    return {}


def _build_artifact_patch(
    agent_run: LogicalAgentRunResult,
    semantic_payload: dict[str, Any],
) -> dict[str, Any] | None:
    business_data = agent_run.business_data
    if business_data is None:
        return None

    semantic_contract = ((semantic_payload.get("dados") or {}).get("semantic_contract"))
    if not isinstance(semantic_contract, dict):
        return None

    metadata = dict(semantic_contract.get("metadata") or {})
    metadata.setdefault("preferred_output", business_data.preferred_output)
    if business_data.artifact_action:
        metadata.setdefault("artifact_action", business_data.artifact_action)

    table_data = semantic_contract.get("table")
    if not isinstance(table_data, (list, dict)):
        table_data = []

    chart_data = semantic_contract.get("chart")
    if not isinstance(chart_data, dict):
        chart_data = {}

    insights_data = semantic_contract.get("insights")
    if not isinstance(insights_data, list):
        insights_data = []

    suggested_actions_data = semantic_contract.get("suggested_actions")
    if not isinstance(suggested_actions_data, list):
        suggested_actions_data = []

    patch = {
        "artifact_type": business_data.target_artifact_type or "report",
        "title": (
            metadata.get("report_title")
            or agent_run.context.artefato_ativo.title
            or agent_run.context.decision.objetivo_ativo
            or "Relatório do copiloto"
        ),
        "summary": semantic_contract.get("summary"),
        "table": table_data,
        "chart": chart_data,
        "insights": insights_data,
        "suggested_actions": suggested_actions_data,
        "metadata": metadata,
        "status": "completed" if semantic_payload.get("sucesso") else "error",
    }
    if business_data.artifact_action == "update_report" and agent_run.context.artefato_ativo.artifact_id:
        patch["artifact_id"] = agent_run.context.artefato_ativo.artifact_id
    return patch


class SemanticDataExecutionResult(BaseModel):
    executed: bool
    used_engine: str | None = None
    semantic_message: str | None = None
    semantic_payload: dict[str, Any] | None = None
    artifact_patch: dict[str, Any] | None = None
    skip_reason: str | None = None


class InternalCopilotDataExecutor:
    @staticmethod
    async def execute(
        *,
        agent_run: LogicalAgentRunResult,
        db: Any,
        current_user: Any,
        sessao_id: str,
        request_id: str | None,
    ) -> SemanticDataExecutionResult:
        business_data = agent_run.business_data
        if business_data is None or not business_data.needs_business_data:
            return SemanticDataExecutionResult(
                executed=False,
                skip_reason="no_business_data_plan",
            )

        semantic_message = _build_semantic_message(agent_run)
        override_args = _build_override_args(agent_run)
        try:
            semantic_payload = await try_handle_semantic_autonomy(
                mensagem=semantic_message,
                sessao_id=sessao_id,
                db=db,
                current_user=current_user,
                engine=ENGINE_ANALYTICS,
                request_id=request_id,
                confirmation_token=None,
                override_args=override_args,
            )
        except Exception as e:
            logger.warning(f"[DataExecutor] Falha na autonomia semântica analítica: {e}")
            semantic_payload = None

        if not isinstance(semantic_payload, dict) or semantic_payload.get("handled") is False:
            return SemanticDataExecutionResult(
                executed=False,
                used_engine=ENGINE_ANALYTICS,
                semantic_message=semantic_message,
                skip_reason="semantic_runtime_unavailable" if not semantic_payload else "handled_false",
                artifact_patch=None
            )

        return SemanticDataExecutionResult(
            executed=True,
            used_engine=ENGINE_ANALYTICS,
            semantic_message=semantic_message,
            semantic_payload=semantic_payload,
            artifact_patch=_build_artifact_patch(agent_run, semantic_payload),
        )
