"""Serviços da Sprint 5: engine documental."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.models import DocumentoEmpresa, Usuario
from app.services.ai_tools import operational_tool_catalog
from app.services.assistant_engine_registry import ENGINE_DOCUMENTAL, get_engine_policy
from app.services.audit_service import registrar_auditoria
from app.services.tool_executor import execute as execute_tool


def get_documental_catalog() -> dict[str, Any]:
    """Retorna catálogo explícito da superfície documental."""
    policy = get_engine_policy(ENGINE_DOCUMENTAL)
    allowed = set(policy.allowed_tools)
    tools_grouped = operational_tool_catalog(allowed_tools=allowed)
    return {
        "engine": policy.key,
        "label": policy.label,
        "description": policy.description,
        "domains": tools_grouped,
    }


def _build_step_trace(
    *,
    step: str,
    status: str,
    started_perf: float,
    data: Any = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "step": step,
        "status": status,
        "duration_ms": int((time.perf_counter() - started_perf) * 1000),
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    if data is not None:
        payload["data"] = data
    if extra:
        payload.update(extra)
    return payload


def _build_flow_metrics(trace: list[dict[str, Any]], flow_started_perf: float) -> dict[str, Any]:
    return {
        "total_steps": len(trace),
        "total_duration_ms": int((time.perf_counter() - flow_started_perf) * 1000),
        "steps_with_error": sum(1 for step in trace if str(step.get("status", "")).lower() in {"erro", "error"}),
        "steps_pending": sum(1 for step in trace if str(step.get("status", "")).lower() == "pending"),
    }


def _pending_confirmation_payload(
    *,
    step: str,
    error: str,
    flow_id: str,
    trace: list[dict[str, Any]],
    metrics: dict[str, Any],
    pending_action: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "success": False,
        "error": error,
        "code": "pending_confirmation",
        "flow_id": flow_id,
        "trace": trace,
        "metrics": metrics,
        "pending_action": {
            **(pending_action or {}),
            "flow_step": step,
            "confirmation_required": True,
        },
    }


def _listar_documentos_empresa(
    db: Session,
    *,
    empresa_id: int,
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.empresa_id == empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .order_by(DocumentoEmpresa.atualizado_em.desc(), DocumentoEmpresa.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": d.id,
            "nome": d.nome,
            "tipo": (d.tipo.value if hasattr(d.tipo, "value") else str(d.tipo or "")),
            "atualizado_em": d.atualizado_em.isoformat() if d.atualizado_em else None,
        }
        for d in rows
    ]


async def run_documental_orcamento_flow(
    *,
    db: Session,
    current_user: Usuario,
    request_id: Optional[str],
    sessao_id: Optional[str],
    orcamento_id: int | str,
    documento_id: Optional[int],
    exibir_no_portal: bool,
    enviar_por_email: bool,
    enviar_por_whatsapp: bool,
    obrigatorio: bool,
    confirmation_token: Optional[str],
) -> dict[str, Any]:
    """Fluxo composto documental: consultar orçamento -> montar dossiê -> anexar opcional -> registrar."""
    flow_id = str(uuid.uuid4())
    flow_started_perf = time.perf_counter()
    trace: list[dict[str, Any]] = []

    consultar_started = time.perf_counter()
    obter_tc = {
        "id": "flow_documental_obter_orcamento",
        "type": "function",
        "function": {
            "name": "obter_orcamento",
            "arguments": json.dumps({"id": orcamento_id}, ensure_ascii=False),
        },
    }
    obter_result = await execute_tool(
        obter_tc,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    trace.append(
        _build_step_trace(
            step="consultar_orcamento",
            status=obter_result.status,
            started_perf=consultar_started,
            data=obter_result.data,
        )
    )
    if obter_result.status != "ok":
        return {
            "success": False,
            "error": obter_result.error or "Falha ao consultar orçamento.",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    dossie_started = time.perf_counter()
    docs = _listar_documentos_empresa(db, empresa_id=current_user.empresa_id, limit=8)
    orc_data = obter_result.data or {}
    dossie = {
        "orcamento": {
            "id": orc_data.get("id"),
            "numero": orc_data.get("numero"),
            "status": orc_data.get("status"),
            "total": orc_data.get("total"),
            "cliente": (orc_data.get("cliente") or {}).get("nome"),
            "itens": len(orc_data.get("itens") or []),
        },
        "documentos_empresa": docs,
        "documentos_disponiveis": len(docs),
    }
    trace.append(
        _build_step_trace(
            step="montar_dossie_documental",
            status="ok",
            started_perf=dossie_started,
            data=dossie,
        )
    )

    anexo_result_data: dict[str, Any] | None = None
    if documento_id:
        anexo_started = time.perf_counter()
        anexar_args = {
            "orcamento_id": int(orc_data.get("id") or 0),
            "documento_id": int(documento_id),
            "exibir_no_portal": bool(exibir_no_portal),
            "enviar_por_email": bool(enviar_por_email),
            "enviar_por_whatsapp": bool(enviar_por_whatsapp),
            "obrigatorio": bool(obrigatorio),
        }
        anexar_tc = {
            "id": "flow_documental_anexar_documento",
            "type": "function",
            "function": {
                "name": "anexar_documento_orcamento",
                "arguments": json.dumps(anexar_args, ensure_ascii=False),
            },
        }
        anexar_result = await execute_tool(
            anexar_tc,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            confirmation_token=confirmation_token,
        )
        trace.append(
            _build_step_trace(
                step="anexar_documento_orcamento",
                status=anexar_result.status,
                started_perf=anexo_started,
                data=anexar_result.data,
                extra={"pending_action": anexar_result.pending_action}
                if anexar_result.status == "pending"
                else None,
            )
        )
        if anexar_result.status == "pending":
            return _pending_confirmation_payload(
                step="anexar_documento_orcamento",
                error="Confirmação necessária para anexar documento ao orçamento.",
                flow_id=flow_id,
                trace=trace,
                metrics=_build_flow_metrics(trace, flow_started_perf),
                pending_action=anexar_result.pending_action,
            )
        if anexar_result.status != "ok":
            return {
                "success": False,
                "error": anexar_result.error or "Falha ao anexar documento no orçamento.",
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }
        anexo_result_data = anexar_result.data or {}

    registro_started = time.perf_counter()
    registro = {
        "flow_id": flow_id,
        "request_id": request_id,
        "sessao_id": sessao_id,
        "orcamento_id": orc_data.get("id"),
        "documento_id": documento_id,
        "anexado": bool(anexo_result_data),
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="fluxo_documental_orcamento",
        recurso="orcamentos",
        recurso_id=str(orc_data.get("id") or ""),
        detalhes=registro,
    )
    trace.append(
        _build_step_trace(
            step="registrar_resultado_documental",
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
            "dossie": dossie,
            "anexo": anexo_result_data,
            "registro": registro,
            "metrics": metrics,
        },
        "trace": trace,
        "metrics": metrics,
    }
