"""Serviços da Sprint 4: engine operacional universal."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session, selectinload

from app.models.models import Orcamento, Usuario
from app.services.ai_tools import operational_tool_catalog
from app.services.assistant_engine_registry import ENGINE_OPERATIONAL, get_engine_policy
from app.services.audit_service import registrar_auditoria
from app.services.tool_executor import execute as execute_tool


def get_operational_catalog() -> dict[str, list[dict[str, Any]]]:
    """Retorna o catálogo explícito da superfície operacional."""
    allowed = set(get_engine_policy(ENGINE_OPERATIONAL).allowed_tools)
    return operational_tool_catalog(allowed_tools=allowed)


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


def _load_orcamento_for_pdf(
    db: Session, *, empresa_id: int, orcamento_id: int
) -> Optional[Orcamento]:
    return (
        db.query(Orcamento)
        .options(selectinload(Orcamento.itens), selectinload(Orcamento.cliente))
        .filter(Orcamento.id == orcamento_id, Orcamento.empresa_id == empresa_id)
        .first()
    )


def _gerar_pdf_orcamento_runtime(db: Session, *, empresa_id: int, orcamento_id: int) -> dict[str, Any]:
    from app.services.pdf_service import gerar_pdf_orcamento
    from app.utils.pdf_utils import get_empresa_dict_for_pdf, get_orcamento_dict_for_pdf

    orc = _load_orcamento_for_pdf(db, empresa_id=empresa_id, orcamento_id=orcamento_id)
    if not orc:
        return {"ok": False, "error": "Orçamento não encontrado para gerar PDF."}
    try:
        orc_dict = get_orcamento_dict_for_pdf(orc, db)
        empresa_dict = get_empresa_dict_for_pdf(orc.empresa)
        pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict) or b""
        return {
            "ok": True,
            "pdf_bytes_len": len(pdf_bytes),
            "orcamento_id": orc.id,
            "numero": orc.numero,
        }
    except Exception as exc:
        return {"ok": False, "error": f"Falha ao gerar PDF: {exc}"}


async def run_orcamento_operational_flow(
    *,
    db: Session,
    current_user: Usuario,
    request_id: Optional[str],
    sessao_id: Optional[str],
    cliente_id: Optional[int],
    cliente_nome: Optional[str],
    itens: list[dict[str, Any]],
    observacoes: Optional[str],
    cadastrar_materiais_novos: bool,
    orcamento_id: Optional[int],
    canal_envio: Optional[str],
    confirmation_token: Optional[str],
) -> dict[str, Any]:
    """Fluxo composto operacional: consultar/montar -> gerar PDF -> enviar -> registrar."""
    flow_id = str(uuid.uuid4())
    flow_started_perf = time.perf_counter()
    trace: list[dict[str, Any]] = []
    target_orcamento_id = orcamento_id

    if target_orcamento_id:
        step_started = time.perf_counter()
        consultar_tc = {
            "id": "flow_obter_orcamento",
            "type": "function",
            "function": {
                "name": "obter_orcamento",
                "arguments": f'{{"id": {int(target_orcamento_id)}}}',
            },
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
                step="consultar",
                status=consultar_result.status,
                started_perf=step_started,
                data=consultar_result.data,
            )
        )
        if consultar_result.status != "ok":
            return {
                "success": False,
                "error": consultar_result.error or "Falha ao consultar orçamento",
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }
    else:
        step_started = time.perf_counter()
        criar_args = {
            "cliente_id": cliente_id,
            "cliente_nome": cliente_nome,
            "itens": itens,
            "observacoes": observacoes,
            "cadastrar_materiais_novos": cadastrar_materiais_novos,
        }
        criar_tc = {
            "id": "flow_criar_orcamento",
            "type": "function",
            "function": {"name": "criar_orcamento", "arguments": json.dumps(criar_args, ensure_ascii=False)},
        }
        criar_result = await execute_tool(
            criar_tc,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            confirmation_token=confirmation_token,
        )
        # cria_orcamento é destrutiva e normalmente gera pending; o fluxo composto deve
        # exigir confirmação explícita fora deste endpoint para preservar segurança.
        if criar_result.status == "pending":
            trace.append(
                _build_step_trace(
                    step="montar_orcamento",
                    status="pending",
                    started_perf=step_started,
                    extra={"pending_action": criar_result.pending_action},
                )
            )
            return _pending_confirmation_payload(
                step="montar_orcamento",
                error="Confirmação necessária para criar orçamento no fluxo composto.",
                flow_id=flow_id,
                trace=trace,
                metrics=_build_flow_metrics(trace, flow_started_perf),
                pending_action=criar_result.pending_action,
            )
        trace.append(
            _build_step_trace(
                step="montar_orcamento",
                status=criar_result.status,
                started_perf=step_started,
                data=criar_result.data,
            )
        )
        if criar_result.status != "ok":
            return {
                "success": False,
                "error": criar_result.error or "Falha ao criar orçamento",
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }
        target_orcamento_id = int((criar_result.data or {}).get("id") or 0)
        if not target_orcamento_id:
            return {
                "success": False,
                "error": "ID de orçamento ausente após criação.",
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }

    pdf_started = time.perf_counter()
    pdf_result = _gerar_pdf_orcamento_runtime(
        db,
        empresa_id=current_user.empresa_id,
        orcamento_id=int(target_orcamento_id),
    )
    trace.append(
        _build_step_trace(
            step="gerar_pdf",
            status="ok" if pdf_result.get("ok") else "erro",
            started_perf=pdf_started,
            data=pdf_result,
        )
    )
    if not pdf_result.get("ok"):
        return {
            "success": False,
            "error": pdf_result.get("error") or "Falha ao gerar PDF",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    envio_data: dict[str, Any] | None = None
    if canal_envio in {"whatsapp", "email"}:
        envio_started = time.perf_counter()
        tool_name = "enviar_orcamento_whatsapp" if canal_envio == "whatsapp" else "enviar_orcamento_email"
        enviar_tc = {
            "id": "flow_enviar_orcamento",
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": f'{{"orcamento_id": {int(target_orcamento_id)}}}',
            },
        }
        enviar_result = await execute_tool(
            enviar_tc,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            confirmation_token=confirmation_token,
        )
        trace.append(
            _build_step_trace(
                step="enviar_canal",
                status=enviar_result.status,
                started_perf=envio_started,
                data=enviar_result.data,
            )
        )
        if enviar_result.status == "pending":
            return _pending_confirmation_payload(
                step="enviar_canal",
                error="Confirmação necessária para envio no fluxo composto.",
                flow_id=flow_id,
                trace=trace,
                metrics=_build_flow_metrics(trace, flow_started_perf),
                pending_action=enviar_result.pending_action,
            )
        if enviar_result.status != "ok":
            return {
                "success": False,
                "error": enviar_result.error or "Falha no envio",
                "flow_id": flow_id,
                "trace": trace,
                "metrics": _build_flow_metrics(trace, flow_started_perf),
            }
        envio_data = enviar_result.data or {}

    registro_started = time.perf_counter()
    registro = {
        "flow_id": flow_id,
        "request_id": request_id,
        "sessao_id": sessao_id,
        "orcamento_id": int(target_orcamento_id),
        "canal_envio": canal_envio,
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="fluxo_orcamento_operacional",
        recurso="orcamentos",
        recurso_id=str(target_orcamento_id),
        detalhes=registro,
    )
    trace.append(
        _build_step_trace(
            step="registrar_resultado",
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
            "orcamento_id": int(target_orcamento_id),
            "pdf_bytes_len": int(pdf_result.get("pdf_bytes_len") or 0),
            "envio": envio_data,
            "registro": registro,
            "metrics": metrics,
        },
        "trace": trace,
        "metrics": metrics,
    }


async def run_financeiro_operational_flow(
    *,
    db: Session,
    current_user: Usuario,
    request_id: Optional[str],
    sessao_id: Optional[str],
    tipo: str,
    valor: float,
    descricao: str,
    categoria: Optional[str],
    data: Optional[str],
    confirmation_token: Optional[str],
) -> dict[str, Any]:
    """Fluxo composto financeiro: consultar contexto -> executar ação -> registrar."""
    flow_id = str(uuid.uuid4())
    flow_started_perf = time.perf_counter()
    trace: list[dict[str, Any]] = []

    consultar_started = time.perf_counter()
    saldo_tc = {
        "id": "flow_obter_saldo_caixa",
        "type": "function",
        "function": {"name": "obter_saldo_caixa", "arguments": "{}"},
    }
    saldo_result = await execute_tool(
        saldo_tc,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    trace.append(
        _build_step_trace(
            step="consultar_contexto_financeiro",
            status=saldo_result.status,
            started_perf=consultar_started,
            data=saldo_result.data,
        )
    )
    if saldo_result.status != "ok":
        return {
            "success": False,
            "error": saldo_result.error or "Falha ao consultar saldo atual.",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    executar_started = time.perf_counter()
    criar_args = {
        "tipo": tipo,
        "valor": valor,
        "descricao": descricao,
        "categoria": categoria or "geral",
        "data": data,
    }
    criar_tc = {
        "id": "flow_criar_movimentacao_financeira",
        "type": "function",
        "function": {"name": "criar_movimentacao_financeira", "arguments": json.dumps(criar_args, ensure_ascii=False)},
    }
    criar_result = await execute_tool(
        criar_tc,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
        confirmation_token=confirmation_token,
    )
    trace.append(
        _build_step_trace(
            step="executar_acao_financeira",
            status=criar_result.status,
            started_perf=executar_started,
            data=criar_result.data,
            extra={"pending_action": criar_result.pending_action} if criar_result.status == "pending" else None,
        )
    )
    if criar_result.status == "pending":
        return _pending_confirmation_payload(
            step="executar_acao_financeira",
            error="Confirmação necessária para criar movimentação financeira.",
            flow_id=flow_id,
            trace=trace,
            metrics=_build_flow_metrics(trace, flow_started_perf),
            pending_action=criar_result.pending_action,
        )
    if criar_result.status != "ok":
        return {
            "success": False,
            "error": criar_result.error or "Falha ao criar movimentação financeira.",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    registro_started = time.perf_counter()
    registro = {
        "flow_id": flow_id,
        "request_id": request_id,
        "sessao_id": sessao_id,
        "tipo": tipo,
        "valor": valor,
        "descricao": descricao,
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="fluxo_financeiro_operacional",
        recurso="financeiro",
        recurso_id=str((criar_result.data or {}).get("id") or ""),
        detalhes=registro,
    )
    trace.append(
        _build_step_trace(
            step="registrar_resultado_financeiro",
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
            "saldo_antes": saldo_result.data,
            "movimentacao": criar_result.data,
            "registro": registro,
            "metrics": metrics,
        },
        "trace": trace,
        "metrics": metrics,
    }


async def run_agendamento_operational_flow(
    *,
    db: Session,
    current_user: Usuario,
    request_id: Optional[str],
    sessao_id: Optional[str],
    acao: str,
    cliente_id: Optional[int],
    data_agendada: Optional[str],
    duracao_estimada_min: Optional[int],
    tipo: Optional[str],
    orcamento_id: Optional[int],
    endereco: Optional[str],
    observacoes: Optional[str],
    agendamento_id: Optional[int],
    nova_data: Optional[str],
    motivo: Optional[str],
    confirmation_token: Optional[str],
) -> dict[str, Any]:
    """Fluxo composto de agenda: consultar contexto -> criar/remarcar -> registrar."""
    flow_id = str(uuid.uuid4())
    flow_started_perf = time.perf_counter()
    trace: list[dict[str, Any]] = []

    consultar_started = time.perf_counter()
    agenda_tc = {
        "id": "flow_listar_agendamentos",
        "type": "function",
        "function": {
            "name": "listar_agendamentos",
            "arguments": json.dumps({"dias": 30, "limit": 10}),
        },
    }
    agenda_result = await execute_tool(
        agenda_tc,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    trace.append(
        _build_step_trace(
            step="consultar_contexto_agenda",
            status=agenda_result.status,
            started_perf=consultar_started,
            data=agenda_result.data,
        )
    )
    if agenda_result.status != "ok":
        return {
            "success": False,
            "error": agenda_result.error or "Falha ao consultar contexto de agenda.",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    executar_started = time.perf_counter()
    acao_norm = (acao or "").strip().lower()
    if acao_norm == "criar":
        criar_args = {
            "cliente_id": cliente_id,
            "data_agendada": data_agendada,
            "duracao_estimada_min": duracao_estimada_min or 60,
            "tipo": tipo or "servico",
            "orcamento_id": orcamento_id,
            "endereco": endereco,
            "observacoes": observacoes,
        }
        exec_tc = {
            "id": "flow_criar_agendamento",
            "type": "function",
            "function": {"name": "criar_agendamento", "arguments": json.dumps(criar_args, ensure_ascii=False)},
        }
    elif acao_norm == "remarcar":
        remarcar_args = {
            "agendamento_id": agendamento_id,
            "nova_data": nova_data,
            "motivo": motivo,
        }
        exec_tc = {
            "id": "flow_remarcar_agendamento",
            "type": "function",
            "function": {
                "name": "remarcar_agendamento",
                "arguments": json.dumps(remarcar_args, ensure_ascii=False),
            },
        }
    else:
        return {
            "success": False,
            "error": "Ação inválida para fluxo de agenda.",
            "code": "invalid_action",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    exec_result = await execute_tool(
        exec_tc,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
        confirmation_token=confirmation_token,
    )
    trace.append(
        _build_step_trace(
            step="executar_acao_agenda",
            status=exec_result.status,
            started_perf=executar_started,
            data=exec_result.data,
            extra={"pending_action": exec_result.pending_action} if exec_result.status == "pending" else None,
        )
    )
    if exec_result.status == "pending":
        return _pending_confirmation_payload(
            step="executar_acao_agenda",
            error="Confirmação necessária para ação de agenda.",
            flow_id=flow_id,
            trace=trace,
            metrics=_build_flow_metrics(trace, flow_started_perf),
            pending_action=exec_result.pending_action,
        )
    if exec_result.status != "ok":
        return {
            "success": False,
            "error": exec_result.error or "Falha na ação de agenda.",
            "flow_id": flow_id,
            "trace": trace,
            "metrics": _build_flow_metrics(trace, flow_started_perf),
        }

    registro_started = time.perf_counter()
    registro = {
        "flow_id": flow_id,
        "request_id": request_id,
        "sessao_id": sessao_id,
        "acao": acao_norm,
        "agendamento_id": agendamento_id,
        "cliente_id": cliente_id,
        "data_agendada": data_agendada,
        "nova_data": nova_data,
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    registrar_auditoria(
        db=db,
        usuario=current_user,
        acao="fluxo_agendamento_operacional",
        recurso="agendamentos",
        recurso_id=str((exec_result.data or {}).get("id") or ""),
        detalhes=registro,
    )
    trace.append(
        _build_step_trace(
            step="registrar_resultado_agenda",
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
            "contexto_agenda": agenda_result.data,
            "resultado_acao": exec_result.data,
            "registro": registro,
            "metrics": metrics,
        },
        "trace": trace,
        "metrics": metrics,
    }
