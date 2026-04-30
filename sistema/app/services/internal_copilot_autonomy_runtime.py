from __future__ import annotations

import inspect
import logging
import time
from typing import Any

from sqlalchemy import text

from app.services.audit_service import registrar_auditoria
from app.services.assistant_autonomy.llm_sql_planner import try_generate_sql_from_llm, llm_sql_planner_enabled
from app.services.assistant_autonomy.schema_context import get_allowed_tables_for_guard
from app.services.internal_copilot_autonomy_models import CopilotIntent, CopilotSafetyDecision, CopilotStructuredPlan
from app.services.internal_copilot_sql_guard import validate_sql_query

logger = logging.getLogger(__name__)


def _get_allowed_tables() -> dict[str, dict[str, str]]:
    return get_allowed_tables_for_guard()


async def _ask_llm_textual_fallback(*, mensagem: str, llm_rationale: str) -> dict[str, Any]:
    """Quando o LLM SQL Planner falha, pede ao LLM uma resposta textual direta."""
    from app.services.ia_service import ia_service
    fallback_prompt = (
        "Você é um assistente técnico interno de um sistema de gestão empresarial.\n"
        f"O operador perguntou: {mensagem!r}\n\n"
        "Tentei gerar uma consulta automatica mas nao foi possivel.\n"
        "Responda de forma objetiva e util ao operador.\n"
        "Se puder, sugira uma forma mais clara de pedir a informacao desejada."
    )
    try:
        resp = await ia_service.chat(
            messages=[
                {"role": "system", "content": "Voce e um assistente tecnico interno."},
                {"role": "user", "content": fallback_prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        choices = (resp or {}).get("choices") or []
        content = (((choices[0] or {}).get("message") or {}).get("content") or "") if choices else ""
        usage = (resp or {}).get("usage") or {}
        input_t = int(usage.get("prompt_tokens", 0) or 0)
        output_t = int(usage.get("completion_tokens", 0) or 0)
        if content:
            logger.info("[Copiloto Fallback] Resposta textual gerada com sucesso.")
            return {"answer": content, "input_tokens": input_t, "output_tokens": output_t}
    except Exception as exc:
        logger.warning("[Copiloto Fallback] Falha no fallback textual: %s", exc)
    return {"answer": "Nao foi possivel gerar uma consulta para esse pedido. Tente reformular com termos mais especificos, como 'quantos orcamentos' ou 'listar clientes'.", "input_tokens": 0, "output_tokens": 0}


async def run_internal_copilot_autonomy(*, db, current_user, mensagem: str, sessao_id: str | None, request_id: str | None):
    t0 = time.monotonic()
    trace_steps = []
    total_in = 0
    total_out = 0

    raw_message = str(mensagem or "").strip()

    t_start = time.monotonic()
    intent = await _interpret_message(
        mensagem=raw_message,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    trace_steps.append({"step": "interpret", "duration_ms": int((time.monotonic() - t_start) * 1000), "status": "ok"})

    t_start = time.monotonic()
    plan = await _build_plan(
        intent=intent,
        raw_message=raw_message,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    sql_candidate = (plan or {}).get("sql_candidate") or ""
    llm_rationale = (plan or {}).get("llm_rationale") or ""
    total_in += int((plan or {}).get("input_tokens", 0) or 0)
    total_out += int((plan or {}).get("output_tokens", 0) or 0)
    trace_steps.append({"step": "plan", "duration_ms": int((time.monotonic() - t_start) * 1000), "status": "ok", "llm_used": bool(llm_rationale)})

    if not sql_candidate:
        logger.info("[Copiloto] Nenhum SQL gerado, usando fallback textual para: %r", raw_message[:100])
        fallback = await _ask_llm_textual_fallback(mensagem=raw_message, llm_rationale=llm_rationale)
        total_in += int(fallback.get("input_tokens", 0) or 0)
        total_out += int(fallback.get("output_tokens", 0) or 0)
        trace_steps.append({"step": "fallback_textual", "duration_ms": int((time.monotonic() - t_start) * 1000), "status": "ok"})
        return _textual_response(
            answer=fallback["answer"],
            trace=trace_steps,
            metrics={"total_duration_ms": int((time.monotonic() - t0) * 1000), "steps_with_error": 0},
            input_tokens=total_in,
            output_tokens=total_out,
        )

    t_start = time.monotonic()
    allowed_tables = _get_allowed_tables()
    safety = validate_sql_query(
        sql=sql_candidate,
        empresa_id=getattr(current_user, "empresa_id", 0),
        allowed_tables=allowed_tables,
    )
    trace_steps.append({"step": "sql_guard", "duration_ms": int((time.monotonic() - t_start) * 1000), "status": "ok" if safety.allowed else "blocked"})

    structured_plan = _build_structured_plan(intent=intent, sql_candidate=sql_candidate)

    if not safety.allowed:
        logger.warning(
            "[Copiloto] SQL bloqueado pelo guard. SQL: %r | Reason: %s",
            sql_candidate[:200], getattr(safety, "reason", None),
        )
        _record_audit(
            db=db,
            current_user=current_user,
            intent=intent,
            structured_plan=structured_plan,
            safety=safety,
            sessao_id=sessao_id,
            request_id=request_id,
            llm_rationale=llm_rationale,
        )
        fallback = await _ask_llm_textual_fallback(mensagem=raw_message, llm_rationale=llm_rationale)
        total_in += int(fallback.get("input_tokens", 0) or 0)
        total_out += int(fallback.get("output_tokens", 0) or 0)
        return _textual_response(
            answer=fallback["answer"],
            trace=trace_steps,
            metrics={"total_duration_ms": int((time.monotonic() - t0) * 1000), "steps_with_error": 0},
            input_tokens=total_in,
            output_tokens=total_out,
        )

    t_start = time.monotonic()
    query_result = await _execute_validated_query(db=db, sql=safety.rewritten_sql or "")
    trace_steps.append({"step": "execute", "duration_ms": int((time.monotonic() - t_start) * 1000), "status": "ok"})

    _record_audit(
        db=db,
        current_user=current_user,
        intent=intent,
        structured_plan=structured_plan,
        safety=safety,
        sessao_id=sessao_id,
        request_id=request_id,
        llm_rationale=llm_rationale,
    )
    return _success_response(
        intent=intent,
        safety=safety,
        query_result=query_result,
        llm_rationale=llm_rationale,
        trace=trace_steps,
        metrics={"total_duration_ms": int((time.monotonic() - t0) * 1000), "steps_with_error": 0},
        input_tokens=total_in,
        output_tokens=total_out,
    )


async def _interpret_message(*, mensagem: str, current_user, sessao_id: str | None, request_id: str | None) -> dict[str, Any]:
    lowered = mensagem.lower()

    intent = CopilotIntent(raw_message=mensagem)

    if "orcamento" in lowered and any(k in lowered for k in ("listar", "liste", "mostrar", "mostre", "buscar")):
        intent.intent = "listar_orcamentos"
        intent.preferred_output = "table"
    elif "orcamento" in lowered and any(k in lowered for k in ("quantidade", "contar", "total", "qtd", "quantos", "quantas")):
        if "aprovado" in lowered:
            intent.intent = "contar_orcamentos_aprovados"
        else:
            intent.intent = "contar_orcamentos"
        intent.preferred_output = "summary"
    elif any(k in lowered for k in ("catalogo", "catálogo", "serviço", "servico", "produto", "material")):
        if any(k in lowered for k in ("quantidade", "contar", "total", "qtd", "quantos", "quantas")):
            intent.intent = "contar_catalogo"
        else:
            intent.intent = "listar_catalogo"
        intent.preferred_output = "table"
    elif "cliente" in lowered and any(k in lowered for k in ("listar", "liste", "mostrar", "mostre", "buscar", "quantos", "quantas", "quantidade")):
        intent.intent = "listar_clientes"
        intent.preferred_output = "table"
    elif any(k in lowered for k in ("despesa", "despesas", "receita", "receitas", "caixa", "movimentação", "movimentacao")):
        intent.intent = "financeiro"
        intent.preferred_output = "table"
    else:
        intent.intent = "llm_query"
        intent.preferred_output = "table"

    return intent.model_dump()


async def _build_plan(*, intent: dict[str, Any], raw_message: str, current_user, sessao_id: str | None, request_id: str | None) -> dict[str, Any]:
    intent_name = (intent or {}).get("intent")

    if llm_sql_planner_enabled():
        llm_plan = await try_generate_sql_from_llm(
            message=raw_message,
            period_days=30,
        )
        if llm_plan.used and llm_plan.sql:
            return {"sql_candidate": llm_plan.sql, "llm_rationale": llm_plan.rationale, "input_tokens": llm_plan.input_tokens, "output_tokens": llm_plan.output_tokens}

    if intent_name == "listar_orcamentos":
        return {"sql_candidate": "SELECT id, cliente_nome FROM orcamentos"}
    if intent_name == "contar_orcamentos_aprovados":
        return {"sql_candidate": "SELECT COUNT(*) as total FROM orcamentos WHERE status = 'APROVADO'"}
    if intent_name == "contar_orcamentos":
        return {"sql_candidate": "SELECT COUNT(*) as total FROM orcamentos"}
    if intent_name == "contar_catalogo":
        return {"sql_candidate": "SELECT COUNT(*) as total_itens FROM servicos WHERE ativo = true"}
    if intent_name == "listar_catalogo":
        return {"sql_candidate": "SELECT nome, preco_padrao, unidade FROM servicos WHERE ativo = true LIMIT 50"}
    if intent_name == "listar_clientes":
        return {"sql_candidate": "SELECT nome, telefone, cidade FROM clientes LIMIT 50"}
    if intent_name == "financeiro":
        return {"sql_candidate": "SELECT tipo, descricao, valor, data FROM movimentacoes_caixa LIMIT 50"}

    return {"sql_candidate": ""}


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
    lowered = intent_name.lower()
    tables = []
    columns = []
    if "orcamento" in lowered:
        tables = ["orcamentos"]
        columns = ["id", "cliente_nome"] if "listar" in lowered else ["total"]
    elif "catalogo" in lowered:
        tables = ["servicos"]
        columns = ["total_itens"] if "contar" in lowered else ["nome", "preco_padrao"]
    elif "cliente" in lowered:
        tables = ["clientes"]
        columns = ["nome", "telefone"]
    elif "financeiro" in lowered:
        tables = ["movimentacoes_caixa"]
        columns = ["tipo", "valor", "data"]
    elif "llm_query" in lowered:
        return None
    return CopilotStructuredPlan(
        intent=intent_name,
        tables=tables,
        columns=columns,
    )


def _record_audit(*, db, current_user, intent: dict[str, Any], structured_plan: CopilotStructuredPlan | None, safety, sessao_id: str | None, request_id: str | None, llm_rationale: str = ""):
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
            "llm_rationale": llm_rationale or None,
            "sessao_id": sessao_id,
            "request_id": request_id,
        },
    )


def _success_response(*, intent: dict[str, Any], safety: CopilotSafetyDecision | Any, query_result: dict[str, Any], llm_rationale: str = "", trace: list | None = None, metrics: dict | None = None, input_tokens: int = 0, output_tokens: int = 0) -> dict[str, Any]:
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
        "llm_rationale": llm_rationale or None,
    }
    return _build_response_payload(success=True, data=payload, trace=trace, metrics=metrics, input_tokens=input_tokens, output_tokens=output_tokens)


def _textual_response(*, answer: str, trace: list | None = None, metrics: dict | None = None, input_tokens: int = 0, output_tokens: int = 0) -> dict[str, Any]:
    payload = {
        "answer": answer,
        "summary": answer,
        "table": [],
        "safety": {"mode": None, "needs_confirmation": False, "reason": None},
        "needs_confirmation": False,
        "suggested_followups": [],
        "llm_rationale": None,
    }
    return _build_response_payload(success=True, data=payload, trace=trace, metrics=metrics, input_tokens=input_tokens, output_tokens=output_tokens)


def _serialize_safety(safety: CopilotSafetyDecision | Any) -> dict[str, Any]:
    return {
        "mode": getattr(safety, "mode", None),
        "needs_confirmation": bool(getattr(safety, "needs_confirmation", False)),
        "reason": getattr(safety, "reason", None),
    }


def _build_response_payload(*, success: bool, data: dict[str, Any], error: str | None = None, code: str | None = None, trace: list | None = None, metrics: dict | None = None, input_tokens: int = 0, output_tokens: int = 0) -> dict[str, Any]:
    semantic_contract = {
        "answer": data.get("answer"),
        "summary": data.get("summary"),
        "table": data.get("table") or [],
        "safety": data.get("safety") or {},
        "needs_confirmation": bool(data.get("needs_confirmation")),
        "suggested_followups": data.get("suggested_followups") or [],
        "llm_rationale": data.get("llm_rationale") or None,
        "metadata": {
            "runtime": "internal_copilot_autonomy",
            "version": "llm_planner_v1",
        },
    }
    payload = {
        "success": success,
        "data": data,
        "sucesso": success,
        "dados": {
            "semantic_contract": semantic_contract,
        },
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "trace": trace or [],
        "metrics": metrics or {},
        "contexto_operacional": {
            "rota_primaria": "copiloto_autonomia",
            "subagente_primario": "internal_copilot_autonomy_runtime",
            "tipo_resposta_esperada": "autonomous_sql",
            "continuidade_aplicada": False,
        },
    }
    if error is not None:
        payload["error"] = error
    if code is not None:
        payload["code"] = code
    return payload
