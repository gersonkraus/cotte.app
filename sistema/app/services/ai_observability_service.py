"""Serviço de observabilidade da IA V2 (Sprint 9)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.models import AuditLog, ToolCallLog


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_engine_from_log(log: ToolCallLog) -> str:
    args = log.args_json if isinstance(log.args_json, dict) else {}
    meta = args.get("_meta") if isinstance(args, dict) else {}
    engine = str((meta or {}).get("engine") or "").strip().lower()
    return engine or "unknown"


def _percent(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    arr = sorted(v for v in values if isinstance(v, int))
    if not arr:
        return 0
    idx = min(len(arr) - 1, max(0, int((len(arr) * 0.95) - 1)))
    return arr[idx]


def _engine_health(total: int, erros: int, p95_ms: int) -> str:
    if total == 0:
        return "no_data"
    err_rate = _percent(erros, total)
    if err_rate >= 15.0 or p95_ms >= 6000:
        return "critical"
    if err_rate >= 5.0 or p95_ms >= 3000:
        return "degraded"
    return "healthy"


def build_ai_health_summary(
    *,
    db: Session,
    empresa_id: Optional[int],
    hours: int,
    engine_filter: Optional[str] = None,
) -> dict[str, Any]:
    window_hours = max(1, min(168, _safe_int(hours, default=24)))
    dt_from = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    logs_query = db.query(ToolCallLog).filter(ToolCallLog.criado_em >= dt_from)
    if empresa_id is not None:
        logs_query = logs_query.filter(ToolCallLog.empresa_id == empresa_id)
    logs = logs_query.order_by(ToolCallLog.criado_em.desc()).all()

    by_engine: dict[str, dict[str, Any]] = {}
    for row in logs:
        engine = _extract_engine_from_log(row)
        if engine_filter and engine != engine_filter:
            continue
        bucket = by_engine.setdefault(
            engine,
            {
                "total": 0,
                "errors": 0,
                "pending": 0,
                "rate_limited": 0,
                "latencies": [],
                "top_tools": {},
            },
        )
        bucket["total"] += 1
        status = str(row.status or "").lower()
        if status in {"erro", "error", "forbidden", "unknown_tool", "invalid_input"}:
            bucket["errors"] += 1
        if status == "pending":
            bucket["pending"] += 1
        if status == "rate_limited":
            bucket["rate_limited"] += 1
        if isinstance(row.latencia_ms, int):
            bucket["latencies"].append(row.latencia_ms)
        tool = str(row.tool or "unknown")
        bucket["top_tools"][tool] = bucket["top_tools"].get(tool, 0) + 1

    engines_out: dict[str, Any] = {}
    total_calls = 0
    total_errors = 0
    max_p95 = 0
    for engine_key, stats in by_engine.items():
        total = int(stats["total"])
        errors = int(stats["errors"])
        latencies = list(stats["latencies"])
        p95_ms = _p95(latencies)
        max_p95 = max(max_p95, p95_ms)
        total_calls += total
        total_errors += errors
        top_tools_sorted = sorted(
            stats["top_tools"].items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        engines_out[engine_key] = {
            "total": total,
            "errors": errors,
            "error_rate_pct": _percent(errors, total),
            "pending": int(stats["pending"]),
            "rate_limited": int(stats["rate_limited"]),
            "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
            "p95_latency_ms": p95_ms,
            "health": _engine_health(total, errors, p95_ms),
            "top_tools": [
                {"tool": tool_name, "total": tool_total}
                for tool_name, tool_total in top_tools_sorted
            ],
        }

    audit_query = db.query(AuditLog).filter(
        AuditLog.criado_em >= dt_from,
        AuditLog.acao.in_(
            (
                "fluxo_orcamento_operacional",
                "fluxo_financeiro_operacional",
                "fluxo_agendamento_operacional",
                "fluxo_documental_orcamento",
                "fluxo_analytics_operacional",
                "fluxo_copiloto_tecnico",
                "ai_rollout_plan_update",
            )
        ),
    )
    if empresa_id is not None:
        audit_query = audit_query.filter(AuditLog.empresa_id == empresa_id)
    audit_events = audit_query.count()

    overview = {
        "window_hours": window_hours,
        "total_tool_calls": total_calls,
        "total_errors": total_errors,
        "error_rate_pct": _percent(total_errors, total_calls),
        "p95_latency_ms_max": max_p95,
        "audit_events": int(audit_events),
        "health": _engine_health(total_calls, total_errors, max_p95),
    }

    return {
        "overview": overview,
        "engines": engines_out,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# Custo estimado por token (Claude Sonnet pricing blended)
_COST_INPUT_PER_M = 3.0    # USD por 1M input tokens
_COST_OUTPUT_PER_M = 15.0  # USD por 1M output tokens


def build_token_chart_data(
    *,
    db: Session,
    hours: int,
    empresa_id: Optional[int] = None,
) -> dict[str, Any]:
    """Agrega consumo de tokens do ToolCallLog por dia e por engine."""
    window_hours = max(1, min(168, _safe_int(hours, default=24)))
    dt_from = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    query = db.query(ToolCallLog).filter(
        ToolCallLog.criado_em >= dt_from,
    )
    if empresa_id is not None:
        query = query.filter(ToolCallLog.empresa_id == empresa_id)
    logs = query.all()

    total_in = 0
    total_out = 0
    by_engine: dict[str, dict] = {}
    # keyed by "YYYY-MM-DD" → {engine: tokens}
    daily: dict[str, dict[str, int]] = {}

    for row in logs:
        t_in = _safe_int(row.input_tokens)
        t_out = _safe_int(row.output_tokens)
        # Considerar registros mesmo quando tokens não estão preenchidos
        # para manter a integridade dos dados agregados
        tokens = t_in + t_out
        if tokens == 0:
            continue
        total_in += t_in
        total_out += t_out

        engine = _extract_engine_from_log(row)
        bucket = by_engine.setdefault(engine, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        bucket["input_tokens"] += t_in
        bucket["output_tokens"] += t_out
        bucket["total_tokens"] += tokens

        day_key = row.criado_em.strftime("%Y-%m-%d") if row.criado_em else "unknown"
        day_bucket = daily.setdefault(day_key, {})
        day_bucket[engine] = day_bucket.get(engine, 0) + tokens

    # Custo estimado
    cost_usd = (total_in * _COST_INPUT_PER_M + total_out * _COST_OUTPUT_PER_M) / 1_000_000

    # Série diária ordenada
    daily_series = [
        {"date": day, **engines_tokens}
        for day, engines_tokens in sorted(daily.items())
    ]

    return {
        "total_tokens": total_in + total_out,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "cost_usd": round(cost_usd, 6),
        "by_engine": by_engine,
        "daily": daily_series,
        "window_hours": window_hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
