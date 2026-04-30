"""Contratos internos tipados do copiloto tecnico."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class InternalTraceStep(BaseModel):
    step: str
    status: str
    duration_ms: int
    executado_em_utc: str
    data: Any | None = None


class InternalFlowMetrics(BaseModel):
    total_steps: int
    total_duration_ms: int
    steps_with_error: int
    steps_pending: int


class InternalFlowAuditRecord(BaseModel):
    flow_id: str
    request_id: str | None = None
    sessao_id: str | None = None
    usuario_id: int | None = None
    empresa_id: int | None = None
    incluiu_code_rag: bool
    incluiu_sql_agent: bool
    executado_em_utc: str


class InternalTechnicalFlowPayload(BaseModel):
    code_context: dict[str, Any] | None = None
    sql_result: dict[str, Any] | None = None
    registro: InternalFlowAuditRecord
    metrics: InternalFlowMetrics


TInternalPayload = TypeVar("TInternalPayload")


class InternalResultEnvelope(BaseModel, Generic[TInternalPayload]):
    success: bool
    flow_id: str
    data: TInternalPayload | None = None
    error: str | None = None
    code: str | None = None
    trace: list[InternalTraceStep] = Field(default_factory=list)
    metrics: InternalFlowMetrics

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value

    def to_response_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": self.success,
            "flow_id": self.flow_id,
            "trace": [step.model_dump(exclude_none=True) for step in self.trace],
            "metrics": self.metrics.model_dump(),
        }
        if self.data is not None:
            payload["data"] = self._serialize_value(self.data)
        if self.error is not None:
            payload["error"] = self.error
        if self.code is not None:
            payload["code"] = self.code
        return payload
