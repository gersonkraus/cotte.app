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
    numeric_keys = [key for key in keys if isinstance(first.get(key), (int, float))]

    if len(keys) >= 2:
        insights.append(
            {
                "type": "highlight",
                "title": "Primeiro resultado",
                "detail": f"{keys[0]}={first.get(keys[0])}; {keys[1]}={first.get(keys[1])}",
            }
        )

    if numeric_keys:
        key = numeric_keys[0]
        total = sum(float(row.get(key) or 0) for row in rows if isinstance(row.get(key), (int, float)))
        insights.append(
            {
                "type": "summary",
                "title": "Soma do principal indicador",
                "detail": f"{key} acumulado no recorte: {round(total, 2)}",
            }
        )

    if "valor_comissao" in first:
        insights.append(
            {
                "type": "highlight",
                "title": "Comissão visível por venda",
                "detail": "O relatório já traz o valor de comissão por venda, facilitando conferência individual antes de exportar.",
            }
        )
    elif "total_comprado" in first:
        insights.append(
            {
                "type": "highlight",
                "title": "Cliente líder do período",
                "detail": "Use o topo do ranking para direcionar retenção, upsell ou follow-up comercial prioritário.",
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
