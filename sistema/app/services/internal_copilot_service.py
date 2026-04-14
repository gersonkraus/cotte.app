"""Fluxos dedicados do copiloto técnico interno (Sprint 7)."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.models import Usuario
from app.services.assistant_engine_registry import (
    ENGINE_INTERNAL_COPILOT,
    is_code_rag_enabled,
    is_sql_agent_enabled,
)
from app.services.audit_service import registrar_auditoria
from app.services.code_rag_service import build_code_context
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


def can_use_internal_copilot(*, is_superadmin: bool, is_gestor: bool) -> bool:
    return bool(is_superadmin or is_gestor)


async def run_internal_technical_flow(
    *,
    db: Session,
    current_user: Usuario,
    request_id: Optional[str],
    sessao_id: Optional[str],
    mensagem: str,
    include_code_context: bool,
    sql_query: Optional[str],
    sql_limit: int,
) -> dict[str, Any]:
    """Fluxo técnico interno: Code RAG opcional + SQL técnico opcional + auditoria."""
    flow_id = str(uuid.uuid4())
    flow_started_perf = time.perf_counter()
    trace: list[dict[str, Any]] = []

    code_ctx: dict[str, Any] = {}
    if include_code_context:
        step_started = time.perf_counter()
        if not is_code_rag_enabled():
            trace.append(
                _build_step_trace(
                    step="code_rag_context",
                    status="erro",
                    started_perf=step_started,
                    data={"error": "Code RAG técnico desabilitado", "code": "code_rag_disabled"},
                )
            )
            return {
                "success": False,
                "error": "Code RAG técnico desabilitado.",
                "code": "code_rag_disabled",
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }
        code_ctx = build_code_context(query=mensagem, top_k=4)
        trace.append(
            _build_step_trace(
                step="code_rag_context",
                status="ok",
                started_perf=step_started,
                data={
                    "sources": code_ctx.get("sources") or [],
                    "matches": code_ctx.get("matches") or 0,
                },
            )
        )

    sql_result_data: dict[str, Any] | None = None
    sql_query_clean = (sql_query or "").strip()
    if sql_query_clean:
        step_started = time.perf_counter()
        if not is_sql_agent_enabled():
            trace.append(
                _build_step_trace(
                    step="sql_agent_tecnico",
                    status="erro",
                    started_perf=step_started,
                    data={"error": "SQL Agent técnico desabilitado", "code": "sql_agent_disabled"},
                )
            )
            return {
                "success": False,
                "error": "SQL Agent técnico desabilitado.",
                "code": "sql_agent_disabled",
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }
        sql_tc = {
            "id": "flow_internal_sql_agent",
            "type": "function",
            "function": {
                "name": "executar_sql_analitico",
                "arguments": json.dumps({"sql": sql_query_clean, "limit": sql_limit}, ensure_ascii=False),
            },
        }
        sql_result = await execute_tool(
            sql_tc,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            engine=ENGINE_INTERNAL_COPILOT,
        )
        trace.append(
            _build_step_trace(
                step="sql_agent_tecnico",
                status=sql_result.status,
                started_perf=step_started,
                data=sql_result.data,
            )
        )
        if sql_result.status != "ok":
            return {
                "success": False,
                "error": sql_result.error or "Falha ao executar SQL técnico.",
                "code": sql_result.code,
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }
        sql_result_data = sql_result.data or {}

    registro_started = time.perf_counter()
    registro = {
        "flow_id": flow_id,
        "request_id": request_id,
        "sessao_id": sessao_id,
        "usuario_id": getattr(current_user, "id", None),
        "empresa_id": getattr(current_user, "empresa_id", None),
        "incluiu_code_rag": bool(include_code_context),
        "incluiu_sql_agent": bool(sql_query_clean),
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="fluxo_copiloto_tecnico",
        recurso="copiloto_interno",
        recurso_id=str(getattr(current_user, "id", "")),
        detalhes=registro,
    )
    trace.append(
        _build_step_trace(
            step="registrar_resultado_tecnico",
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
            "code_context": code_ctx if include_code_context else None,
            "sql_result": sql_result_data,
            "registro": registro,
            "metrics": metrics,
        },
        "trace": trace,
        "metrics": metrics,
    }
