"""Serviços da Sprint 6: engine analítica e SQL Agent seguro."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.models import Usuario
from app.services.ai_tools import operational_tool_catalog
from app.services.assistant_engine_registry import (
    ENGINE_ANALYTICS,
    get_engine_policy,
    is_sql_agent_enabled,
)
from app.services.audit_service import registrar_auditoria
from app.services.tool_executor import execute as execute_tool


def _build_step_trace(
    *,
    step: str,
    status: str,
    started_perf: float,
    data: Any = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "step": step,
        "status": status,
        "duration_ms": int((time.perf_counter() - started_perf) * 1000),
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    if data is not None:
        payload["data"] = data
    return payload


def _build_flow_metrics(trace: list[dict[str, Any]], flow_started_perf: float) -> dict[str, Any]:
    return {
        "total_steps": len(trace),
        "total_duration_ms": int((time.perf_counter() - flow_started_perf) * 1000),
        "steps_with_error": sum(1 for step in trace if str(step.get("status", "")).lower() in {"erro", "error"}),
        "steps_pending": sum(1 for step in trace if str(step.get("status", "")).lower() == "pending"),
    }


def get_analytics_catalog() -> dict[str, Any]:
    policy = get_engine_policy(ENGINE_ANALYTICS)
    allowed = set(policy.allowed_tools)
    if not is_sql_agent_enabled():
        allowed.discard("executar_sql_analitico")
    return {
        "engine": policy.key,
        "label": policy.label,
        "description": policy.description,
        "sql_agent_enabled": bool(is_sql_agent_enabled()),
        "domains": operational_tool_catalog(allowed_tools=allowed),
    }


def _scope_to_tool_args(scope: str, dias: int, limit: int) -> tuple[str, dict[str, Any]]:
    key = (scope or "").strip().lower()
    if key == "financeiro_resumo":
        return "listar_movimentacoes_financeiras", {"dias": dias, "limit": limit}
    if key == "orcamentos_resumo":
        return "listar_orcamentos", {"dias": dias, "limit": min(limit, 50)}
    if key == "clientes_resumo":
        return "listar_clientes", {"limit": min(limit, 50)}
    if key == "despesas_resumo":
        return "listar_despesas", {"dias": dias, "limit": limit}
    return "listar_movimentacoes_financeiras", {"dias": dias, "limit": limit}


async def run_analytics_flow(
    *,
    db: Session,
    current_user: Usuario,
    request_id: Optional[str],
    sessao_id: Optional[str],
    scope: str,
    dias: int,
    limit: int,
) -> dict[str, Any]:
    """Fluxo analítico MVP: consultar superfície read-only -> registrar resultado."""
    flow_id = str(uuid.uuid4())
    flow_started_perf = time.perf_counter()
    trace: list[dict[str, Any]] = []

    step_started = time.perf_counter()
    tool_name, args = _scope_to_tool_args(scope, dias, limit)
    consultar_tc = {
        "id": "flow_analytics_consulta",
        "type": "function",
        "function": {"name": tool_name, "arguments": json.dumps(args, ensure_ascii=False)},
    }
    consultar_result = await execute_tool(
        consultar_tc,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    trace.append(
        _build_step_trace(
            step="consultar_superficie_analitica",
            status=consultar_result.status,
            started_perf=step_started,
            data=consultar_result.data,
        )
    )
    if consultar_result.status != "ok":
        return {
            "success": False,
            "error": consultar_result.error or "Falha na consulta analítica.",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    registro_started = time.perf_counter()
    registro = {
        "flow_id": flow_id,
        "request_id": request_id,
        "sessao_id": sessao_id,
        "scope": scope,
        "tool": tool_name,
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="fluxo_analytics_operacional",
        recurso="analytics",
        recurso_id=str(current_user.empresa_id),
        detalhes=registro,
    )
    trace.append(
        _build_step_trace(
            step="registrar_resultado_analitico",
            status="ok",
            started_perf=registro_started,
            data=registro,
        )
    )
    metrics = _build_flow_metrics(trace, flow_started_perf)
    return {
        "success": True,
        "flow_id": flow_id,
        "data": {
            "scope": scope,
            "tool": tool_name,
            "resultado": consultar_result.data,
            "registro": registro,
            "metrics": metrics,
        },
        "trace": trace,
        "metrics": metrics,
    }


async def run_analytics_sql_query_flow(
    *,
    db: Session,
    current_user: Usuario,
    request_id: Optional[str],
    sessao_id: Optional[str],
    sql: str,
    limit: int,
) -> dict[str, Any]:
    """Fluxo SQL Agent analítico (read-only, behind flag)."""
    if not is_sql_agent_enabled():
        return {
            "success": False,
            "error": "SQL Agent analítico desabilitado.",
            "code": "sql_agent_disabled",
        }

    flow_id = str(uuid.uuid4())
    flow_started_perf = time.perf_counter()
    trace: list[dict[str, Any]] = []

    step_started = time.perf_counter()
    sql_tc = {
        "id": "flow_analytics_sql_agent",
        "type": "function",
        "function": {
            "name": "executar_sql_analitico",
            "arguments": json.dumps({"sql": sql, "limit": limit}, ensure_ascii=False),
        },
    }
    sql_result = await execute_tool(
        sql_tc,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    trace.append(
        _build_step_trace(
            step="executar_sql_analitico",
            status=sql_result.status,
            started_perf=step_started,
            data=sql_result.data,
        )
    )
    if sql_result.status != "ok":
        return {
            "success": False,
            "error": sql_result.error or "Falha ao executar SQL analítico.",
            "code": sql_result.code,
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    metrics = _build_flow_metrics(trace, flow_started_perf)
    return {
        "success": True,
        "flow_id": flow_id,
        "data": {
            "resultado_sql": sql_result.data,
            "metrics": metrics,
        },
        "trace": trace,
        "metrics": metrics,
    }
