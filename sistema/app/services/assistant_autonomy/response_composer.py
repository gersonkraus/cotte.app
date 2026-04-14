"""Compositor de resposta multiformato para execução semântica."""

from __future__ import annotations

from typing import Any

from app.services.assistant_autonomy.action_advisor import suggest_actions
from app.services.assistant_autonomy.contracts import ExecutionResult, ResponseContract, SemanticPlan
from app.services.assistant_autonomy.insight_engine import build_structured_insights


def _extract_rows(execution: ExecutionResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in execution.outputs.get("tools") or []:
        data = item.get("data")
        if isinstance(data, dict):
            possible = data.get("rows")
            if isinstance(possible, list):
                rows.extend([row for row in possible if isinstance(row, dict)])
    return rows


def compose_response_contract(plan: SemanticPlan, execution: ExecutionResult) -> ResponseContract:
    rows = _extract_rows(execution)
    truncated = len(rows) > 100
    summary = (
        "Execução semântica concluída com sucesso."
        if execution.success
        else "Não foi possível concluir a execução semântica."
    )
    data_sources = [
        item.get("name")
        for item in (execution.outputs.get("tools") or [])
        if isinstance(item, dict) and item.get("name")
    ]
    chart_payload = None
    if "chart" in plan.request.output_formats and rows:
        keys = list(rows[0].keys())
        if len(keys) >= 2:
            chart_payload = {
                "type": "bar",
                "labels": [str(row.get(keys[0], "")) for row in rows[:20]],
                "datasets": [{"label": keys[1], "data": [row.get(keys[1], 0) for row in rows[:20]]}],
            }

    printable_payload = None
    if "printable" in plan.request.output_formats:
        printable_payload = {
            "title": f"Relatório {plan.capability}",
            "summary": summary,
            "period_days": plan.request.period_days,
            "filters": plan.request.entity_filters,
            "rows": rows[:100],
            "generated_at": execution.metrics.get("generated_at"),
        }

    metadata = {
        "capability": plan.capability,
        "domain": plan.request.domain,
        "period_days": plan.request.period_days,
        "metrics": plan.request.metrics,
        "dimensions": plan.request.dimensions,
        "filters": plan.request.entity_filters,
        "comparison_mode": plan.request.comparison_mode,
        "data_sources": data_sources,
        "confidence_hint": 0.86 if execution.success else 0.45,
        "execution_metrics": execution.metrics,
        "truncated": truncated,
        "rows_total": len(rows),
        "rows_returned": min(100, len(rows)),
    }
    insights = build_structured_insights(rows=rows[:100], capability=plan.capability)
    suggested_actions = suggest_actions(capability=plan.capability, metadata=metadata)

    return ResponseContract(
        summary=summary,
        data_table=rows[:100],
        chart_payload=chart_payload,
        printable_payload=printable_payload,
        insights=insights,
        suggested_actions=suggested_actions,
        metadata=metadata,
    )


def to_ai_response_payload(
    *,
    contract: ResponseContract,
    execution: ExecutionResult,
) -> dict[str, Any]:
    if not execution.success:
        return {
            "sucesso": False,
            "resposta": execution.error or "Falha na execução semântica.",
            "confianca": 0.45,
            "modulo_origem": "assistente_autonomia",
            "erros": [execution.error or "semantic_execution_error"],
            "dados": {
                "code": execution.code,
                "semantic_contract": {
                    "summary": execution.error or "Falha na execução semântica.",
                    "table": [],
                    "chart": None,
                    "printable": None,
                    "insights": [],
                    "suggested_actions": [],
                    "metadata": {
                        "capability": execution.capability,
                        "confidence_hint": 0.45,
                        "execution_metrics": execution.metrics,
                    },
                },
                "trace": [item.__dict__ for item in execution.trace],
                "metrics": execution.metrics,
            },
        }

    return {
        "sucesso": True,
        "resposta": contract.summary,
        "confianca": 0.86,
        "modulo_origem": "assistente_autonomia",
        "dados": {
            "semantic_contract": {
                "summary": contract.summary,
                "table": contract.data_table,
                "chart": contract.chart_payload,
                "printable": contract.printable_payload,
                "insights": contract.insights,
                "suggested_actions": contract.suggested_actions,
                "metadata": contract.metadata,
            },
            "trace": [item.__dict__ for item in execution.trace],
            "metrics": execution.metrics,
        },
    }
