from __future__ import annotations

from app.services.internal_copilot_contracts import (
    InternalFlowAuditRecord,
    InternalFlowMetrics,
    InternalResultEnvelope,
    InternalTechnicalFlowPayload,
    InternalTraceStep,
)


def test_internal_contracts_serialize_expected_shape():
    trace = [
        InternalTraceStep(
            step="code_rag_context",
            status="ok",
            duration_ms=12,
            executado_em_utc="2026-01-01T00:00:00+00:00",
            data={"matches": 1},
        )
    ]
    metrics = InternalFlowMetrics(
        total_steps=1,
        total_duration_ms=12,
        steps_with_error=0,
        steps_pending=0,
    )
    registro = InternalFlowAuditRecord(
        flow_id="flow-1",
        request_id="req-1",
        sessao_id="sess-1",
        usuario_id=7,
        empresa_id=3,
        incluiu_code_rag=True,
        incluiu_sql_agent=False,
        executado_em_utc="2026-01-01T00:00:00+00:00",
    )
    payload = InternalTechnicalFlowPayload(
        code_context={"sources": ["a.py"]},
        sql_result=None,
        registro=registro,
        metrics=metrics,
    )

    result = InternalResultEnvelope[InternalTechnicalFlowPayload](
        success=True,
        flow_id="flow-1",
        data=payload,
        trace=trace,
        metrics=metrics,
    )

    assert result.to_response_dict() == {
        "success": True,
        "flow_id": "flow-1",
        "data": {
            "code_context": {"sources": ["a.py"]},
            "sql_result": None,
            "registro": {
                "flow_id": "flow-1",
                "request_id": "req-1",
                "sessao_id": "sess-1",
                "usuario_id": 7,
                "empresa_id": 3,
                "incluiu_code_rag": True,
                "incluiu_sql_agent": False,
                "executado_em_utc": "2026-01-01T00:00:00+00:00",
            },
            "metrics": {
                "total_steps": 1,
                "total_duration_ms": 12,
                "steps_with_error": 0,
                "steps_pending": 0,
            },
        },
        "trace": [
            {
                "step": "code_rag_context",
                "status": "ok",
                "duration_ms": 12,
                "executado_em_utc": "2026-01-01T00:00:00+00:00",
                "data": {"matches": 1},
            }
        ],
        "metrics": {
            "total_steps": 1,
            "total_duration_ms": 12,
            "steps_with_error": 0,
            "steps_pending": 0,
        },
    }


def test_internal_trace_step_omits_null_data_in_response_shape():
    result = InternalResultEnvelope[dict](
        success=True,
        flow_id="flow-1",
        data={"ok": True},
        trace=[
            InternalTraceStep(
                step="registrar_resultado_tecnico",
                status="ok",
                duration_ms=1,
                executado_em_utc="2026-01-01T00:00:00+00:00",
            )
        ],
        metrics=InternalFlowMetrics(
            total_steps=1,
            total_duration_ms=1,
            steps_with_error=0,
            steps_pending=0,
        ),
    )

    assert result.to_response_dict()["trace"] == [
        {
            "step": "registrar_resultado_tecnico",
            "status": "ok",
            "duration_ms": 1,
            "executado_em_utc": "2026-01-01T00:00:00+00:00",
        }
    ]


def test_internal_result_envelope_accepts_plain_dict_data_in_response():
    result = InternalResultEnvelope[dict](
        success=False,
        flow_id="flow-1",
        data={"error_type": "unexpected"},
        error="Falha interna.",
        code="internal_error",
        trace=[],
        metrics=InternalFlowMetrics(
            total_steps=0,
            total_duration_ms=0,
            steps_with_error=0,
            steps_pending=0,
        ),
    )

    assert result.to_response_dict()["data"] == {"error_type": "unexpected"}
