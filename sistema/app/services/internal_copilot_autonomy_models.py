from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


PreferredOutput = Literal["summary", "table", "chart"]
SafetyMode = Literal["read_only", "blocked", "confirmation_required"]


class CopilotIntent(BaseModel):
    raw_message: str
    intent: str | None = None
    entities: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    preferred_output: PreferredOutput = "summary"


class CopilotStructuredPlan(BaseModel):
    intent: str
    tables: list[str]
    columns: list[str]
    joins: list[dict[str, str]] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    aggregations: list[dict[str, str]] = Field(default_factory=list)
    order_by: list[str] = Field(default_factory=list)
    limit: int = Field(default=100, ge=1)


class CopilotSafetyDecision(BaseModel):
    allowed: bool
    mode: SafetyMode
    needs_confirmation: bool = False
    reason: str | None = None
    rewritten_sql: str | None = None
