"""Runtime da arquitetura semântica de autonomia do assistente."""

from __future__ import annotations

import os
from typing import Any, Optional
from datetime import datetime, timedelta, timezone
import json

from app.services.assistant_autonomy.capability_layer import build_tool_calls_for_plan
from app.services.assistant_autonomy.execution_graph import run_execution_graph
from app.services.assistant_autonomy.llm_sql_planner import try_generate_sql_from_llm
from app.services.assistant_autonomy.policy_engine import evaluate_policy
from app.services.assistant_autonomy.response_composer import (
    compose_response_contract,
    to_ai_response_payload,
)
from app.services.assistant_autonomy.semantic_planner import build_semantic_plan
from app.services.assistant_autonomy.telemetry import record_semantic_audit
from app.services.assistant_autonomy.token_governance import evaluate_token_budget
from app.services.tool_executor import execute as tool_execute


def semantic_autonomy_enabled() -> bool:
    return str(os.getenv("V2_SEMANTIC_AUTONOMY", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


_SEMANTIC_CACHE: dict[str, tuple[dict[str, Any], datetime]] = {}


def _cache_ttl_seconds() -> int:
    try:
        return max(15, int(os.getenv("V2_SEMANTIC_CACHE_TTL_SECONDS", "120")))
    except Exception:
        return 120


def _cache_key(*, current_user: Any, engine: str, mensagem: str, override_args: Optional[dict]) -> str:
    payload = {
        "empresa_id": getattr(current_user, "empresa_id", None),
        "engine": engine,
        "mensagem": (mensagem or "").strip().lower(),
        "override_args": override_args or {},
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _cache_get(key: str) -> Optional[dict[str, Any]]:
    rec = _SEMANTIC_CACHE.get(key)
    if not rec:
        return None
    payload, exp = rec
    if exp < datetime.now(timezone.utc):
        _SEMANTIC_CACHE.pop(key, None)
        return None
    return dict(payload)


def _cache_put(key: str, payload: dict[str, Any]) -> None:
    _SEMANTIC_CACHE[key] = (
        dict(payload),
        datetime.now(timezone.utc) + timedelta(seconds=_cache_ttl_seconds()),
    )


def _build_policy_degradation_payload(*, reasons: list[str], capability: str) -> dict[str, Any]:
    reason_text = "; ".join([str(r) for r in reasons if r]) or "Política não satisfeita."
    return {
        "sucesso": True,
        "resposta": (
            "Consigo preparar este relatório, mas o fluxo semântico foi degradado por política no momento. "
            f"Motivo: {reason_text}"
        ),
        "confianca": 0.63,
        "modulo_origem": "assistente_autonomia",
        "dados": {
            "capability": capability,
            "policy_degraded": True,
            "policy_reasons": reasons,
            "semantic_contract": {
                "summary": (
                    "Fluxo semântico degradado por política. "
                    "Ajuste engine/flags para execução analítica completa."
                ),
                "table": [],
                "chart": None,
                "printable": None,
                "metadata": {
                    "capability": capability,
                    "policy_degraded": True,
                    "policy_reasons": reasons,
                },
            },
        },
    }


async def try_handle_semantic_autonomy(
    *,
    mensagem: str,
    sessao_id: str,
    db: Any,
    current_user: Any,
    engine: str,
    request_id: Optional[str],
    confirmation_token: Optional[str],
    override_args: Optional[dict],
) -> Optional[dict[str, Any]]:
    if not semantic_autonomy_enabled():
        return None

    budget = evaluate_token_budget(mensagem, override_args=override_args)
    if not budget.allowed:
        return {
            "sucesso": True,
            "resposta": (
                "Sua solicitação ficou extensa para o orçamento de tokens da autonomia semântica. "
                "Refine o período/filtros e tente novamente."
            ),
            "confianca": 0.6,
            "modulo_origem": "assistente_autonomia",
            "dados": {
                "token_budget": {
                    "allowed": budget.allowed,
                    "degraded": budget.degraded,
                    "reason": budget.reason,
                }
            },
        }

    cache_key = _cache_key(
        current_user=current_user,
        engine=engine,
        mensagem=mensagem,
        override_args=override_args,
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        cached_dados = dict(cached.get("dados") or {})
        cached_dados["cache_hit"] = True
        cached["dados"] = cached_dados
        return cached

    plan = build_semantic_plan(mensagem)
    decision = evaluate_policy(plan=plan, current_user=current_user, engine=engine)
    if not decision.allowed:
        if plan.capability == "UnknownCapability":
            return None
        return _build_policy_degradation_payload(
            reasons=decision.reasons,
            capability=plan.capability,
        )

    merged_overrides = dict(override_args or {})
    if plan.capability in {"GenerateAnalyticsReport", "GeneratePrintableDocument"}:
        llm_sql = await try_generate_sql_from_llm(
            plan.request.raw_message,
            period_days=int(plan.request.period_days or 30),
        )
        if llm_sql.used and llm_sql.sql:
            merged_overrides["sql_candidate"] = llm_sql.sql
            merged_overrides["llm_sql_rationale"] = llm_sql.rationale

    tool_calls = build_tool_calls_for_plan(plan, override_args=merged_overrides)
    if not tool_calls and plan.capability in {
        "PrepareQuotePackage",
        "DeliverQuoteMultiChannel",
        "ExecuteCompositeWorkflow",
    }:
        return {
            "sucesso": False,
            "resposta": (
                "Capability semântica identificada, mas faltam parâmetros estruturados. "
                "Use override_args para execução transacional segura."
            ),
            "confianca": 0.62,
            "modulo_origem": "assistente_autonomia",
            "dados": {
                "capability": plan.capability,
                "policy": {"allowed": True},
            },
        }

    execution = await run_execution_graph(
        plan=plan,
        tool_calls=tool_calls,
        tool_execute=tool_execute,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
        engine=engine,
        confirmation_token=confirmation_token,
    )
    contract = compose_response_contract(plan, execution)
    record_semantic_audit(
        db=db,
        current_user=current_user,
        request_id=request_id,
        sessao_id=sessao_id,
        plan=plan,
        execution=execution,
    )
    payload = to_ai_response_payload(contract=contract, execution=execution)
    dados = dict(payload.get("dados") or {})
    dados["token_budget"] = {
        "allowed": budget.allowed,
        "degraded": budget.degraded,
        "reason": budget.reason,
    }
    if merged_overrides.get("llm_sql_rationale"):
        dados["llm_sql_rationale"] = merged_overrides.get("llm_sql_rationale")
    payload["dados"] = dados
    if payload.get("sucesso"):
        _cache_put(cache_key, payload)
    return payload
