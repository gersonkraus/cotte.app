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
from app.services.assistant_preferences_service import AssistantPreferencesService
from app.services.cotte_context_builder import SemanticMemoryStore


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


def _serialize_policy(decision: Any) -> dict[str, Any]:
    return {
        "allowed": bool(getattr(decision, "allowed", False)),
        "reasons": list(getattr(decision, "reasons", []) or []),
        "risk_level": getattr(decision, "risk_level", "low"),
        "requires_confirmation": bool(
            getattr(decision, "requires_confirmation", False)
        ),
        "governance_mode": getattr(decision, "governance_mode", "read_only"),
        "recommended_engine": getattr(decision, "recommended_engine", None),
        "allowed_export_formats": list(
            getattr(decision, "allowed_export_formats", []) or []
        ),
        "limits": dict(getattr(decision, "limits", {}) or {}),
    }


def _build_policy_degradation_payload(
    *, reasons: list[str], capability: str, policy: dict[str, Any]
) -> dict[str, Any]:
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
            "policy": policy,
            "semantic_contract": {
                "summary": (
                    "Fluxo semântico degradado por política. "
                    "Ajuste engine/flags para execução analítica completa."
                ),
                "table": [],
                "chart": None,
                "printable": None,
                "insights": [],
                "suggested_actions": [],
                "metadata": {
                    "capability": capability,
                    "policy_degraded": True,
                    "policy_reasons": reasons,
                    "policy": policy,
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
    # Injetar preferencias do usuario no override_args
    if override_args is None:
        override_args = {}
    if "preferencias" not in override_args:
        try:
            prefs = AssistantPreferencesService.get_context_for_prompt(
                db=db,
                empresa_id=getattr(current_user, "empresa_id", 0),
                usuario_id=getattr(current_user, "id", 0),
                mensagem=mensagem
            )
            override_args["preferencias"] = prefs
        except Exception:
            pass

    # Injetar as ultimas mensagens se for uma pergunta curta (follow-up)
    if len(mensagem.split()) <= 8 and "historico" not in override_args:
        try:
            historico = SemanticMemoryStore.build_context(
                db=db,
                empresa_id=getattr(current_user, "empresa_id", 0),
                usuario_id=getattr(current_user, "id", 0),
                mensagem=mensagem
            )
            # Se a query anterior era sql_analytics, anexar ao override
            if historico:
                override_args["historico"] = historico
        except Exception:
            pass

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

        
    # Se for um follow-up com historico
    is_follow_up = "historico" in override_args and len(mensagem.split()) <= 15
    plan = build_semantic_plan(mensagem)
    
    # Se plano falhou mas tem historico analitico
    if is_follow_up and plan.capability == "UnknownCapability":
        historico = override_args.get("historico", "")
        if isinstance(historico, str) and ("sql" in historico.lower() or "relatório" in historico.lower()):
            plan.capability = "GenerateAnalyticsReport"
            plan.request.domain = "analytics"
            plan.request.output_formats.append("table")

    decision = evaluate_policy(plan=plan, current_user=current_user, engine=engine)
    policy_payload = _serialize_policy(decision)
    if not decision.allowed:
        if plan.capability == "UnknownCapability":
            return None
        return _build_policy_degradation_payload(
            reasons=decision.reasons,
            capability=plan.capability,
            policy=policy_payload,
        )

    merged_overrides = dict(override_args or {})
    if plan.capability in {"GenerateAnalyticsReport", "GeneratePrintableDocument"}:
        llm_sql = await try_generate_sql_from_llm(
            plan.request.raw_message,
            period_days=int(plan.request.period_days or 30),
            historico=str(merged_overrides.get("historico", "")),
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
    execution.policy_snapshot = policy_payload
    contract = compose_response_contract(plan, execution, override_args)
    record_semantic_audit(
        db=db,
        current_user=current_user,
        request_id=request_id,
        sessao_id=sessao_id,
        plan=plan,
        execution=execution,
        policy_decision=decision,
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
    dados["policy"] = policy_payload
    payload["dados"] = dados
    if payload.get("sucesso") and not payload.get("pending_action"):
        _cache_put(cache_key, payload)
    return payload
