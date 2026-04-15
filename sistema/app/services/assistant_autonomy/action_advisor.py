"""Sugestões de ações seguras baseadas no contrato semântico."""

from __future__ import annotations

from typing import Any


def suggest_actions(
    *,
    capability: str,
    metadata: dict[str, Any] | None,
    printable_payload: dict[str, Any] | None = None,
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
                {
                    "id": "refinar_periodo_7d",
                    "label": "Refinar para 7 dias",
                    "type": "non_destructive",
                    "params": {"period_days": 7},
                },
            ]
        )

    if meta.get("domain") == "analytics":
        out.extend(
            [
                {
                    "id": "exportar_csv",
                    "label": "Exportar relatório em CSV",
                    "type": "non_destructive",
                    "params": {"export_format": "csv"},
                },
                {
                    "id": "exportar_pdf",
                    "label": "Exportar relatório em PDF",
                    "type": "non_destructive",
                    "params": {"export_format": "pdf"},
                },
            ]
        )
    if printable_payload:
        out.append(
            {
                "id": "visualizar_impressao",
                "label": "Abrir versão imprimível",
                "type": "non_destructive",
                "params": {"print_preview": True},
            }
        )
    return out[:6]
