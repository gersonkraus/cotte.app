"""Execution graph semântico com etapas auditáveis."""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable
from datetime import datetime, timezone

from app.services.assistant_autonomy.capability_layer import ToolCallSpec
from app.services.assistant_autonomy.contracts import (
    ExecutionResult,
    ExecutionStepResult,
    SemanticPlan,
)


ToolExecutor = Callable[..., Awaitable[Any]]


async def run_execution_graph(
    *,
    plan: SemanticPlan,
    tool_calls: list[ToolCallSpec],
    tool_execute: ToolExecutor,
    db: Any,
    current_user: Any,
    sessao_id: str | None,
    request_id: str | None,
    engine: str | None,
    confirmation_token: str | None,
) -> ExecutionResult:
    trace: list[ExecutionStepResult] = []
    started = time.perf_counter()
    outputs: dict[str, Any] = {"plan": plan.rationale, "tools": []}
    total_rows = 0

    for step in plan.steps:
        t0 = time.perf_counter()
        trace.append(
            ExecutionStepResult(
                step=step.name,
                stage=step.stage,
                status="ok",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )
        )

    for call in tool_calls:
        t1 = time.perf_counter()
        tool_call = {
            "id": f"semantic_{call.name}",
            "type": "function",
            "function": {"name": call.name, "arguments": json.dumps(call.args, ensure_ascii=False)},
        }
        result = await tool_execute(
            tool_call,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            engine=engine,
            confirmation_token=confirmation_token,
        )
        latency = int((time.perf_counter() - t1) * 1000)
        status = getattr(result, "status", "erro")
        trace.append(
            ExecutionStepResult(
                step=f"tool:{call.name}",
                stage="fetch",
                status=status,
                latency_ms=latency,
                data=getattr(result, "data", None),
                error=getattr(result, "error", None),
                code=getattr(result, "code", None),
            )
        )
        outputs["tools"].append(
            {
                "name": call.name,
                "status": status,
                "data": getattr(result, "data", None),
                "error": getattr(result, "error", None),
                "code": getattr(result, "code", None),
            }
        )
        data_payload = getattr(result, "data", None)
        if isinstance(data_payload, dict):
            rows = data_payload.get("rows")
            if isinstance(rows, list):
                total_rows += len(rows)
        if status != "ok":
            return ExecutionResult(
                success=False,
                capability=plan.capability,
                trace=trace,
                outputs=outputs,
                metrics={
                    "total_steps": len(trace),
                    "total_duration_ms": int((time.perf_counter() - started) * 1000),
                    "tools_total": len(tool_calls),
                    "tools_ok": len([t for t in outputs["tools"] if t.get("status") == "ok"]),
                    "tools_failed": len([t for t in outputs["tools"] if t.get("status") != "ok"]),
                    "rows_total": total_rows,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                error=getattr(result, "error", "Falha de execução semântica."),
                code=getattr(result, "code", "semantic_execution_error"),
            )

    return ExecutionResult(
        success=True,
        capability=plan.capability,
        trace=trace,
        outputs=outputs,
        metrics={
            "total_steps": len(trace),
            "total_duration_ms": int((time.perf_counter() - started) * 1000),
            "tools_total": len(tool_calls),
            "tools_ok": len([t for t in outputs["tools"] if t.get("status") == "ok"]),
            "tools_failed": len([t for t in outputs["tools"] if t.get("status") != "ok"]),
            "rows_total": total_rows,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
