"""Sugestões de ações seguras baseadas no contrato semântico."""

from __future__ import annotations

from typing import Any


def suggest_actions(
    *,
    capability: str,
    metadata: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    meta = metadata or {}
    out: list[dict[str, Any]] = []

    if capability == "GenerateAnalyticsReport":
        out.extend(
            [
                {
                    "id": "reexecutar_periodo_30d",
                    "label": "Reexecutar para 30 dias",
                    "type": "non_destructive",
                    "params": {"period_days": 30},
                },
                {
                    "id": "comparar_mes_anterior",
                    "label": "Comparar com mês anterior",
                    "type": "non_destructive",
                    "params": {"comparison_mode": "month_over_month"},
                },
            ]
        )

    if meta.get("domain") == "analytics":
        out.append(
            {
                "id": "exportar_csv",
                "label": "Exportar relatório em CSV",
                "type": "non_destructive",
                "params": {"export_format": "csv"},
            }
        )
    return out[:6]
