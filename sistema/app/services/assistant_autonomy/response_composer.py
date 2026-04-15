"""Compositor de resposta multiformato para execução semântica."""

from __future__ import annotations

from typing import Any

from app.services.assistant_autonomy.action_advisor import suggest_actions
from app.services.assistant_autonomy.contracts import (
    ExecutionResult,
    ResponseContract,
    SemanticPlan,
)
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


def _human_capability_title(plan: SemanticPlan) -> str:
    filters = plan.request.entity_filters or {}
    seller_name = filters.get("seller_name")
    if plan.capability == "GeneratePrintableDocument":
        if seller_name:
            return f"Relatório imprimível de vendas - {seller_name}"
        return "Relatório imprimível do assistente"
    if plan.capability == "GenerateAnalyticsReport":
        if seller_name and "seller_commission" in (plan.request.metrics or []):
            return f"Comissão de vendas - {seller_name}"
        return "Relatório analítico do assistente"
    return "Resultado do assistente"


def _build_theme(plan: SemanticPlan) -> dict[str, Any]:
    filters = plan.request.entity_filters or {}
    layout = filters.get("layout_preferences")
    layout = layout if isinstance(layout, dict) else {}
    accent = str(layout.get("accent_color") or "").strip() or "#0f766e"
    variant = str(layout.get("variant") or "").strip() or "professional"
    if variant == "executive":
        accent_soft = "#eff6ff" if accent == "#1d4ed8" else "#ecfdf5"
    else:
        accent_soft = "#f8fafc"
    return {
        "variant": variant,
        "accent_color": accent,
        "accent_soft": accent_soft,
        "text_color": "#111827",
        "muted_color": "#4b5563",
        "surface_color": "#f8fafc",
        "border_color": "#d1d5db",
        "brand_name": "Assistente COTTE",
    }


def _build_period_label(plan: SemanticPlan) -> str:
    period_days = int(plan.request.period_days or 0)
    if period_days <= 0:
        return "Período não informado"
    if period_days == 7:
        return "Últimos 7 dias"
    if period_days == 30:
        return "Últimos 30 dias"
    if period_days == 90:
        return "Último trimestre"
    if period_days == 365:
        return "Últimos 12 meses"
    return f"Últimos {period_days} dias"


def _format_number(value: Any) -> str:
    try:
        num = float(value)
    except Exception:
        return str(value or "-")
    return f"R$ {num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _first_numeric_key(row: dict[str, Any]) -> str | None:
    for key, value in row.items():
        if isinstance(value, (int, float)):
            return str(key)
    return None


def _build_summary(plan: SemanticPlan, execution: ExecutionResult, rows: list[dict[str, Any]]) -> str:
    filters = plan.request.entity_filters or {}
    seller_name = filters.get("seller_name")
    period_label = _build_period_label(plan)

    if execution.pending_action:
        tool = str((execution.pending_action or {}).get("tool") or "ação")
        return (
            f"Identifiquei a ação `{tool}` e preparei a execução com governança por risco. "
            "Preciso da sua confirmação para continuar."
        )

    if not execution.success:
        return "Não foi possível concluir a execução semântica."

    if not rows:
        return f"Execução concluída para {period_label}, mas não encontrei dados suficientes para montar o relatório."

    first = rows[0]
    if "valor_comissao" in first:
        cliente = first.get("cliente") or "cliente não informado"
        vendedor = seller_name or first.get("vendedor") or "vendedor"
        return (
            f"Preparei um relatório detalhado das vendas de {vendedor} em {period_label}. "
            f"O primeiro registro disponível é de {cliente}, com comissão estimada de {_format_number(first.get('valor_comissao'))}."
        )

    if "total_comprado" in first:
        cliente = first.get("nome") or first.get("cliente_nome") or first.get("cliente")
        return (
            f"Montei o ranking de clientes em {period_label}. "
            f"O maior volume atual é de {cliente}, com {_format_number(first.get('total_comprado'))}."
        )

    if "total_movimentado" in first and "categoria" in first:
        return (
            f"Consolidei o desempenho financeiro por categoria em {period_label}. "
            f"A categoria de maior peso no recorte é {first.get('categoria')}."
        )

    if "total_vendas" in first and "vendedor" in first:
        return (
            f"Preparei o desempenho comercial por vendedor em {period_label}. "
            f"O maior resultado atual é de {first.get('vendedor')} com {_format_number(first.get('total_vendas'))}."
        )

    numeric_key = _first_numeric_key(first)
    if numeric_key:
        return (
            f"Relatório semântico concluído para {period_label}. "
            f"Foram retornadas {len(rows)} linhas com destaque inicial em {numeric_key}."
        )

    return f"Relatório semântico concluído para {period_label} com {len(rows)} linhas retornadas."


def _build_chart_payload(plan: SemanticPlan, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if "chart" not in plan.request.output_formats or not rows:
        return None
    first = rows[0]
    keys = list(first.keys())
    if len(keys) < 2:
        return None

    label_key = str(keys[0])
    numeric_keys = [key for key in keys[1:] if isinstance(first.get(key), (int, float))]
    if not numeric_keys:
        return None
    chart_type = "line" if "date" in label_key.lower() or "dia" in label_key.lower() or "mes" in label_key.lower() else "bar"
    return {
        "type": chart_type,
        "labels": [str(row.get(label_key, "")) for row in rows[:24]],
        "datasets": [
            {
                "label": str(key),
                "data": [row.get(key, 0) for row in rows[:24]],
            }
            for key in numeric_keys[:2]
        ],
    }


def _build_printable_payload(
    plan: SemanticPlan,
    execution: ExecutionResult,
    rows: list[dict[str, Any]],
    summary: str,
    insights: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if "printable" not in plan.request.output_formats:
        return None
    title = _human_capability_title(plan)
    period_label = _build_period_label(plan)
    metadata = execution.metrics or {}
    return {
        "title": title,
        "subtitle": "Relatório estruturado pelo assistente com governança semântica",
        "summary": summary,
        "period_days": plan.request.period_days,
        "period_label": period_label,
        "filters": plan.request.entity_filters,
        "rows": rows[:500],
        "generated_at": metadata.get("generated_at"),
        "theme": _build_theme(plan),
        "brand": {"name": "Assistente COTTE"},
        "sections": [
            {"id": "summary", "label": "Resumo executivo"},
            {"id": "insights", "label": "Insights"},
            {"id": "table", "label": "Detalhamento"},
        ],
        "metadata": {
            "capability": plan.capability,
            "metrics": plan.request.metrics,
            "dimensions": plan.request.dimensions,
            "confidence_hint": 0.86 if execution.success else 0.45,
        },
        "insights": insights,
        "export_formats": ["csv", "txt", "html", "pdf"],
        "force_printable": True,
    }


def compose_response_contract(plan: SemanticPlan, execution: ExecutionResult, override_args: dict[str, Any] | None = None) -> ResponseContract:
    rows = _extract_rows(execution)
    truncated = len(rows) > 100
        
    prefs = (override_args or {}).get("preferencias") or {}
    instrucoes_empresa = str(prefs.get("instrucoes_empresa") or "")
    formato_preferido = str((prefs.get("preferencia_visualizacao_usuario") or {}).get("formato_preferido") or "")
    
    summary = _build_summary(plan, execution, rows)
    
    if formato_preferido == "tabela" and "table" not in plan.request.output_formats:
        plan.request.output_formats.append("table")
    elif formato_preferido == "resumo" and "table" in plan.request.output_formats:
        # Prioriza resumo
        pass

    data_sources = [
        item.get("name")
        for item in (execution.outputs.get("tools") or [])
        if isinstance(item, dict) and item.get("name")
    ]
    chart_payload = _build_chart_payload(plan, rows)
    insights = build_structured_insights(rows=rows[:100], capability=plan.capability)
    printable_payload = _build_printable_payload(
        plan=plan,
        execution=execution,
        rows=rows,
        summary=summary,
        insights=insights,
    )
    metadata = {
        "capability": plan.capability,
        "domain": plan.request.domain,
        "period_days": plan.request.period_days,
        "period_label": _build_period_label(plan),
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
        "report_title": _human_capability_title(plan),
        "instrucoes_empresa": instrucoes_empresa,
        "pending_confirmation": bool(execution.pending_action),
        "policy": execution.policy_snapshot,
    }
    suggested_actions = suggest_actions(
        capability=plan.capability,
        metadata=metadata,
        printable_payload=printable_payload,
    )

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
                        "policy": execution.policy_snapshot,
                    },
                },
                "trace": [item.__dict__ for item in execution.trace],
                "metrics": execution.metrics,
            },
        }

    payload = {
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
    if execution.pending_action:
        payload["pending_action"] = execution.pending_action
    return payload
