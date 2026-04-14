"""Geração de insights estruturados para relatórios semânticos."""

from __future__ import annotations

from typing import Any


def build_structured_insights(
    *,
    rows: list[dict[str, Any]],
    capability: str,
) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "type": "warning",
                "title": "Sem dados para insight",
                "detail": "Não houve linhas suficientes para inferências no período informado.",
            }
        ]

    insights: list[dict[str, Any]] = []
    first = rows[0]
    keys = list(first.keys())
    if len(keys) >= 2:
        insights.append(
            {
                "type": "highlight",
                "title": "Primeiro resultado",
                "detail": f"{keys[0]}={first.get(keys[0])}; {keys[1]}={first.get(keys[1])}",
            }
        )
    if capability == "GenerateAnalyticsReport":
        insights.append(
            {
                "type": "opportunity",
                "title": "Ação recomendada",
                "detail": "Valide os 3 maiores resultados e compare com o período anterior para priorização comercial.",
            }
        )
    return insights[:5]
