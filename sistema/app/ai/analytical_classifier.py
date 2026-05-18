"""Classifier de intenção analítica — zero latência, sem chamada LLM.

Detecta se uma mensagem requer análise SQL/multi-tool antes de entrar
nos fast-paths do hub. Retorna AnalyticalIntent com is_analytical, confidence e triggers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


_ANALYTICAL_KEYWORDS: frozenset[str] = frozenset({
    # Rankings e comparações
    "ranking", "top", "mais vendido", "mais comprou", "mais compraram",
    "melhores clientes", "piores clientes", "maiores clientes",
    "melhor cliente", "pior cliente", "maior cliente",
    "top clientes", "quem mais",
    # Agrupamentos temporais
    "por mês", "por semana", "por período", "por dia", "por cliente",
    "por vendedor", "por serviço", "por status", "por categoria",
    "mês passado", "ano passado", "mês anterior", "ano anterior",
    "últimos 30", "últimos 60", "últimos 90",
    "ultimos 30", "ultimos 60", "ultimos 90",
    "entre janeiro", "entre fevereiro", "de janeiro a",
    "nos últimos", "nos ultimos",
    # Métricas e análise
    "crescimento", "média", "ticket médio", "ticket medio",
    "inadimplente", "inadimplência", "inadimplencia",
    "histórico", "historico",
    "análise", "analise", "cruzar", "cruzamento", "combinar",
    # Perguntas analíticas
    "quais clientes", "quais orçamentos", "quais orcamentos",
    "quanto faturou", "quanto gastou", "quanto gerou",
    "total por", "soma por", "agrupado", "agrupa", "agrupar",
    "relatório detalhado", "relatorio detalhado",
    "faturamento por", "receita por", "despesa por",
})

_RANKING_PATTERN = re.compile(
    r"\b("
    r"top\s*\d+"
    r"|os?\s+\d+\s+(melhores?|piores?|maiores?|menores?|primeiros?)"
    r"|\d+\s+primeiros?"
    r"|primeiros?\s+\d+"
    r")\b",
    re.IGNORECASE,
)

_MULTI_FINANCIAL_PATTERN = re.compile(
    r"(?=.*\b(saldo|caixa|financeiro|receita|faturamento|despesa)\b)"
    r"(?=.*\b(cliente|orçamento|orcamento|serviço|servico|período|periodo|mês|mes)\b)",
    re.IGNORECASE,
)


@dataclass
class AnalyticalIntent:
    is_analytical: bool
    confidence: float
    triggers: List[str] = field(default_factory=list)


def classify_analytical_intent(mensagem: str) -> AnalyticalIntent:
    """Classifica se a mensagem requer análise SQL/multi-tool. Sem chamada LLM."""
    if not mensagem or not mensagem.strip():
        return AnalyticalIntent(is_analytical=False, confidence=0.0)

    normalized = mensagem.lower().strip()
    triggers: list[str] = []

    for keyword in _ANALYTICAL_KEYWORDS:
        if keyword in normalized:
            triggers.append(keyword)

    if _RANKING_PATTERN.search(normalized):
        triggers.append("ranking_pattern")

    if _MULTI_FINANCIAL_PATTERN.search(normalized):
        triggers.append("multi_financial_topic")

    if not triggers:
        return AnalyticalIntent(is_analytical=False, confidence=0.0)

    confidence = min(0.5 + len(triggers) * 0.15, 1.0)
    return AnalyticalIntent(is_analytical=True, confidence=confidence, triggers=triggers)
