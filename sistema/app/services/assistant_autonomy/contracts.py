"""Contratos semânticos para autonomia do assistente."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


IntentDomain = Literal[
    "analytics",
    "quote_ops",
    "commercial",
    "communication",
    "document_ops",
    "composite_ops",
    "unknown",
]

CapabilityName = Literal[
    "GenerateAnalyticsReport",
    "GeneratePrintableDocument",
    "PrepareQuotePackage",
    "DeliverQuoteMultiChannel",
    "CreateCommercialProposal",
    "ExecuteCompositeWorkflow",
    "UnknownCapability",
]

OutputFormat = Literal["text", "table", "chart", "printable"]


@dataclass
class SemanticRequest:
    raw_message: str
    domain: IntentDomain
    capability: CapabilityName
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    period_days: int = 30
    comparison_mode: Literal["none", "month_over_month", "quarter_over_quarter"] = "none"
    output_formats: list[OutputFormat] = field(default_factory=lambda: ["text"])
    entity_filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    name: str
    stage: Literal["resolve", "fetch", "aggregate", "compose", "deliver"]
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    required: bool = True


@dataclass
class SemanticPlan:
    capability: CapabilityName
    request: SemanticRequest
    steps: list[PlanStep] = field(default_factory=list)
    rationale: str = ""


@dataclass
class PolicyDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    limits: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionStepResult:
    step: str
    stage: str
    status: str
    latency_ms: int
    data: dict[str, Any] | None = None
    error: str | None = None
    code: str | None = None


@dataclass
class ExecutionResult:
    success: bool
    capability: CapabilityName
    trace: list[ExecutionStepResult]
    outputs: dict[str, Any]
    metrics: dict[str, Any]
    error: str | None = None
    code: str | None = None


@dataclass
class ResponseContract:
    summary: str
    data_table: list[dict[str, Any]] = field(default_factory=list)
    chart_payload: dict[str, Any] | None = None
    printable_payload: dict[str, Any] | None = None
    insights: list[dict[str, Any]] = field(default_factory=list)
    suggested_actions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
