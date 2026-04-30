from __future__ import annotations

from datetime import datetime, timedelta
import inspect
import logging
import time
import unicodedata
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.services.audit_service import registrar_auditoria
from app.services.assistant_autonomy.llm_sql_planner import try_generate_sql_from_llm, llm_sql_planner_enabled
from app.services.assistant_autonomy.schema_context import get_allowed_tables_for_guard
from app.services.internal_copilot_autonomy_models import CopilotIntent, CopilotSafetyDecision, CopilotStructuredPlan
from app.services.internal_copilot_sql_guard import validate_sql_query

logger = logging.getLogger(__name__)

_BUSINESS_TZ = ZoneInfo("America/Sao_Paulo")
_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


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
    history_text = _load_session_history(
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
    )

    try:
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
            history_text=history_text,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
        )
        sql_candidate = (plan or {}).get("sql_candidate") or ""
        llm_rationale = (plan or {}).get("llm_rationale") or ""
        total_in += int((plan or {}).get("input_tokens", 0) or 0)
        total_out += int((plan or {}).get("output_tokens", 0) or 0)
        trace_steps.append(
            {
                "step": "plan",
                "duration_ms": int((time.monotonic() - t_start) * 1000),
                "status": "ok",
                "llm_used": bool(llm_rationale),
                **_build_history_preview(history_text),
            }
        )

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

    except Exception as exc:
        logger.error("[Copiloto] Erro inesperado no runtime: %s", exc, exc_info=True)
        return _textual_response(
            answer=f"Erro interno ao processar sua mensagem. Detalhes: {exc}",
            trace=trace_steps,
            metrics={"total_duration_ms": int((time.monotonic() - t0) * 1000), "steps_with_error": 1},
            input_tokens=total_in,
            output_tokens=total_out,
        )


async def _interpret_message(*, mensagem: str, current_user, sessao_id: str | None, request_id: str | None) -> dict[str, Any]:
    lowered = _normalize_text(mensagem)

    intent = CopilotIntent(raw_message=mensagem)

    refers_to_sales = any(k in lowered for k in ("venda", "vendas", "proposta", "propostas", "orcamento", "orcamentos"))
    asks_for_non_approved = any(
        k in lowered
        for k in (
            "nao aprovada",
            "nao aprovadas",
            "nao aprovado",
            "nao aprovados",
            "pendente de aprovacao",
            "pendentes de aprovacao",
            "aguardando aprovacao",
            "aguardando aprovacoes",
        )
    )
    asks_for_list = any(
        k in lowered
        for k in (
            "listar",
            "liste",
            "mostrar",
            "mostre",
            "buscar",
            "relatorio",
            "gerencial",
            "detalhado",
            "detalhe",
            "crie",
        )
    )
    asks_for_aggregate = any(
        k in lowered for k in ("quantidade", "contar", "total", "qtd", "quantos", "quantas", "valor total", "soma")
    )
    asks_for_approved = any(k in lowered for k in ("aprovado", "aprovada", "aprovados", "aprovadas"))
    asks_for_rejected = any(k in lowered for k in ("recusado", "recusada", "recusados", "recusadas"))
    asks_for_draft = any(k in lowered for k in ("rascunho", "rascunhos"))
    has_civil_period = _extract_civil_period(mensagem) is not None

    if refers_to_sales and asks_for_aggregate:
        if asks_for_approved:
            intent.intent = "contar_orcamentos_aprovados"
        else:
            intent.intent = "contar_orcamentos"
        intent.preferred_output = "summary"
    elif refers_to_sales and asks_for_non_approved:
        intent.intent = "listar_orcamentos_nao_aprovados"
        intent.preferred_output = "table"
    elif refers_to_sales and asks_for_approved and (asks_for_list or has_civil_period):
        intent.intent = "listar_orcamentos_aprovados"
        intent.preferred_output = "table"
    elif refers_to_sales and asks_for_rejected and (asks_for_list or has_civil_period):
        intent.intent = "listar_orcamentos_recusados"
        intent.preferred_output = "table"
    elif refers_to_sales and asks_for_draft and (asks_for_list or has_civil_period):
        intent.intent = "listar_orcamentos_rascunho"
        intent.preferred_output = "table"
    elif "orcamento" in lowered and asks_for_list:
        intent.intent = "listar_orcamentos"
        intent.preferred_output = "table"
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


async def _build_plan(*, intent: dict[str, Any], raw_message: str, history_text: str, current_user, sessao_id: str | None, request_id: str | None) -> dict[str, Any]:
    intent_name = (intent or {}).get("intent")

    if llm_sql_planner_enabled():
        llm_plan = await try_generate_sql_from_llm(
            message=raw_message,
            period_days=30,
            historico=history_text,
        )
        if llm_plan.used and llm_plan.sql:
            return {"sql_candidate": llm_plan.sql, "llm_rationale": llm_plan.rationale, "input_tokens": llm_plan.input_tokens, "output_tokens": llm_plan.output_tokens}

    if intent_name == "listar_orcamentos":
        return {"sql_candidate": "SELECT id, cliente_nome FROM orcamentos"}
    if intent_name == "listar_orcamentos_aprovados":
        return {"sql_candidate": _build_orcamentos_status_query(status_sql="= 'APROVADO'", date_column="aprovado_em", raw_message=raw_message)}
    if intent_name == "listar_orcamentos_recusados":
        return {"sql_candidate": _build_orcamentos_status_query(status_sql="= 'RECUSADO'", date_column="criado_em", raw_message=raw_message)}
    if intent_name == "listar_orcamentos_rascunho":
        return {"sql_candidate": _build_orcamentos_status_query(status_sql="= 'RASCUNHO'", date_column="criado_em", raw_message=raw_message)}
    if intent_name == "listar_orcamentos_nao_aprovados":
        return {"sql_candidate": _build_orcamentos_status_query(status_sql="<> 'APROVADO'", date_column="criado_em", raw_message=raw_message)}
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


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _build_history_preview(history_text: str, *, max_lines: int = 2, max_chars: int = 220) -> dict[str, Any]:
    lines = [line.strip() for line in str(history_text or "").splitlines() if line.strip()]
    preview = "\n".join(lines[:max_lines])
    truncated = len(lines) > max_lines
    if len(preview) > max_chars:
        preview = preview[: max_chars - 3].rstrip() + "..."
        truncated = True
    return {
        "history_preview": preview,
        "history_messages": len(lines),
        "history_truncated": truncated,
    }


def _business_now() -> datetime:
    return datetime.now(_BUSINESS_TZ)


def _format_sql_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _extract_civil_period(value: str) -> tuple[str, str, str] | None:
    normalized = _normalize_text(value)
    now = _business_now()

    if "hoje" in normalized:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return (_format_sql_datetime(start), _format_sql_datetime(end), "exclusive")

    if "ontem" in normalized:
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
        return (_format_sql_datetime(start), _format_sql_datetime(end), "exclusive")

    if "este mes" in normalized:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (_format_sql_datetime(start), _format_sql_datetime(now), "inclusive")

    for month_name, month_number in _MONTHS.items():
        if month_name not in normalized:
            continue
        year = now.year
        start = datetime(year, month_number, 1, tzinfo=_BUSINESS_TZ)
        if month_number == 12:
            end = datetime(year + 1, 1, 1, tzinfo=_BUSINESS_TZ)
        else:
            end = datetime(year, month_number + 1, 1, tzinfo=_BUSINESS_TZ)
        return (_format_sql_datetime(start), _format_sql_datetime(end), "exclusive")

    return None


def _build_orcamentos_status_query(*, status_sql: str, date_column: str, raw_message: str) -> str:
    columns = f"id, numero, total, status, {date_column}"
    filters = [f"status {status_sql}"]
    civil_period = _extract_civil_period(raw_message)
    if civil_period:
        start, end, boundary = civil_period
        filters.append(f"{date_column} >= '{start}'")
        operator = "<=" if boundary == "inclusive" else "<"
        filters.append(f"{date_column} {operator} '{end}'")
    return f"SELECT {columns} FROM orcamentos WHERE " + " AND ".join(filters)


def _load_session_history(*, db, current_user, sessao_id: str | None) -> str:
    if not sessao_id:
        return ""
    try:
        from app.services.cotte_context_builder import SessionStore

        history = SessionStore.get_or_create(
            sessao_id,
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0) or 0,
            usuario_id=getattr(current_user, "id", 0) or 0,
        )
    except Exception as exc:
        logger.warning("[Copiloto] Falha ao carregar historico da sessao %s: %s", sessao_id, exc)
        return ""

    lines = []
    for item in history[-6:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "user").strip().lower()
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        prefix = "assistente" if role == "assistant" else "usuario"
        lines.append(f"{prefix}: {content}")
    return "\n".join(lines)


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
