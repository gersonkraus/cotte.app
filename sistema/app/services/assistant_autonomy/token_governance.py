"""Governança de tokens/custos para autonomia semântica."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenBudgetDecision:
    allowed: bool
    reason: str | None = None
    degraded: bool = False


def _budget_limit() -> int:
    raw = os.getenv("SEMANTIC_TOKEN_BUDGET_PER_CALL", "12000")
    try:
        return max(2000, int(raw))
    except Exception:
        return 12000


def estimate_prompt_tokens(mensagem: str) -> int:
    # Estimativa simples conservadora (aprox. 4 chars por token).
    return max(1, int(len(mensagem or "") / 4))


def evaluate_token_budget(mensagem: str, *, override_args: dict[str, Any] | None = None) -> TokenBudgetDecision:
    est = estimate_prompt_tokens(mensagem)
    limit = _budget_limit()
    if est > limit:
        return TokenBudgetDecision(
            allowed=False,
            reason=f"Prompt excede orçamento estimado de tokens ({est}>{limit}).",
            degraded=True,
        )
    if est > int(limit * 0.75):
        return TokenBudgetDecision(
            allowed=True,
            reason=f"Prompt alto ({est} tokens estimados). Aplicando modo degradado.",
            degraded=True,
        )
    return TokenBudgetDecision(allowed=True, reason=None, degraded=False)
