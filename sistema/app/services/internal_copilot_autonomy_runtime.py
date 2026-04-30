from __future__ import annotations

import inspect
from typing import Any

from sqlalchemy import text

from app.services.audit_service import registrar_auditoria
from app.services.internal_copilot_autonomy_models import CopilotIntent, CopilotSafetyDecision, CopilotStructuredPlan
from app.services.internal_copilot_sql_guard import validate_sql_query


_ALLOWED_TABLES = {
    "orcamentos": {"empresa_column": "empresa_id"},
}


async def run_internal_copilot_autonomy(*, db, current_user, mensagem: str, sessao_id: str | None, request_id: str | None):
    intent = await _interpret_message(
        mensagem=mensagem,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    plan = await _build_plan(
        intent=intent,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    sql_candidate = (plan or {}).get("sql_candidate") or ""
    safety = validate_sql_query(
        sql=sql_candidate,
        empresa_id=getattr(current_user, "empresa_id", 0),
        allowed_tables=_ALLOWED_TABLES,
    )
    structured_plan = _build_structured_plan(intent=intent, sql_candidate=sql_candidate)

    if not safety.allowed:
        _record_audit(
            db=db,
            current_user=current_user,
            intent=intent,
            structured_plan=structured_plan,
            safety=safety,
            sessao_id=sessao_id,
            request_id=request_id,
        )
        return _blocked_response(intent=intent, safety=safety)

    query_result = await _execute_validated_query(db=db, sql=safety.rewritten_sql or "")

    _record_audit(
        db=db,
        current_user=current_user,
        intent=intent,
        structured_plan=structured_plan,
        safety=safety,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    return _success_response(intent=intent, safety=safety, query_result=query_result)


async def _interpret_message(*, mensagem: str, current_user, sessao_id: str | None, request_id: str | None) -> dict[str, Any]:
    raw_message = str(mensagem or "").strip()
    lowered = raw_message.lower()

    intent = CopilotIntent(raw_message=raw_message)
    if "orcamento" in lowered and any(keyword in lowered for keyword in ("listar", "liste", "mostrar", "mostre")):
        intent.intent = "listar_orcamentos"
        intent.preferred_output = "table"

    return intent.model_dump()


async def _build_plan(*, intent: dict[str, Any], current_user, sessao_id: str | None, request_id: str | None) -> dict[str, Any]:
    if (intent or {}).get("intent") == "listar_orcamentos":
        return {"sql_candidate": "SELECT id, cliente_nome FROM orcamentos"}
    return {"sql_candidate": "SELECT 1"}


async def _execute_validated_query(*, db, sql: str) -> dict[str, Any]:
    result = db.execute(text(sql))
    if inspect.isawaitable(result):
        result = await result
    rows = result.fetchall()
    columns = list(result.keys())
    return {
        "columns": columns,
        "rows": [list(row) for row in rows],
        "row_count": len(rows),
    }


def _build_structured_plan(*, intent: dict[str, Any], sql_candidate: str) -> CopilotStructuredPlan | None:
    intent_name = (intent or {}).get("intent")
    if not intent_name:
        return None
    tables = ["orcamentos"] if "orcamento" in str(intent_name) else []
    columns = ["id", "cliente_nome"] if "listar" in str(intent_name) else []
    return CopilotStructuredPlan(
        intent=intent_name,
        tables=tables,
        columns=columns,
    )


def _record_audit(*, db, current_user, intent: dict[str, Any], structured_plan: CopilotStructuredPlan | None, safety, sessao_id: str | None, request_id: str | None):
    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="copiloto_interno_autonomo",
        recurso="copiloto_interno",
        recurso_id=str(getattr(current_user, "id", "")),
        detalhes={
            "intent": intent,
            "structured_plan": structured_plan.model_dump() if structured_plan else None,
            "sql_final": getattr(safety, "rewritten_sql", None),
            "safety_mode": getattr(safety, "mode", None),
            "needs_confirmation": bool(getattr(safety, "needs_confirmation", False)),
            "sessao_id": sessao_id,
            "request_id": request_id,
        },
    )


def _success_response(*, intent: dict[str, Any], safety: CopilotSafetyDecision | Any, query_result: dict[str, Any]) -> dict[str, Any]:
    columns = list(query_result.get("columns") or [])
    rows = list(query_result.get("rows") or [])
    table = [dict(zip(columns, row)) for row in rows]
    row_count = int(query_result.get("row_count") or len(table))

    payload = {
        "answer": f"Encontrei {row_count} resultado(s).",
        "summary": "Consulta executada com leitura validada.",
        "table": table,
        "safety": _serialize_safety(safety),
        "needs_confirmation": bool(getattr(safety, "needs_confirmation", False)),
        "suggested_followups": [],
    }
    return _build_response_payload(success=True, data=payload)


def _blocked_response(*, intent: dict[str, Any], safety: CopilotSafetyDecision | Any) -> dict[str, Any]:
    reason = getattr(safety, "reason", None)
    needs_confirmation = bool(getattr(safety, "needs_confirmation", False))
    answer = "A consulta foi bloqueada por seguranca."
    if needs_confirmation:
        answer = "A consulta exige confirmacao antes de qualquer escrita."

    payload = {
        "answer": answer,
        "summary": answer,
        "table": [],
        "safety": _serialize_safety(safety),
        "needs_confirmation": needs_confirmation,
        "suggested_followups": [],
    }
    return _build_response_payload(success=False, data=payload, error=reason or "query_blocked", code="scope_not_proven")


def _serialize_safety(safety: CopilotSafetyDecision | Any) -> dict[str, Any]:
    return {
        "mode": getattr(safety, "mode", None),
        "needs_confirmation": bool(getattr(safety, "needs_confirmation", False)),
        "reason": getattr(safety, "reason", None),
    }


def _build_response_payload(*, success: bool, data: dict[str, Any], error: str | None = None, code: str | None = None) -> dict[str, Any]:
    semantic_contract = {
        "answer": data.get("answer"),
        "summary": data.get("summary"),
        "table": data.get("table") or [],
        "safety": data.get("safety") or {},
        "needs_confirmation": bool(data.get("needs_confirmation")),
        "suggested_followups": data.get("suggested_followups") or [],
        "metadata": {
            "runtime": "internal_copilot_autonomy",
            "version": "task3_minimal",
        },
    }
    payload = {
        "success": success,
        "data": data,
        "sucesso": success,
        "dados": {
            "semantic_contract": semantic_contract,
        },
    }
    if error is not None:
        payload["error"] = error
    if code is not None:
        payload["code"] = code
    return payload
