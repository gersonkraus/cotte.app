"""Artefatos incrementais do copiloto tecnico."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.services.internal_copilot_memory import InternalCopilotMemoryStore


class LiveArtifact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    artifact_id: str | None = None
    artifact_type: str | None = None
    title: str | None = None
    summary: str | None = None
    table: list[dict[str, Any]] = Field(default_factory=list)
    chart: dict[str, Any] | None = None
    insights: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "idle"
    updated_at: str | None = None


class ArtifactManager:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _coerce_artifact(payload: dict[str, Any] | None) -> LiveArtifact:
        if not isinstance(payload, dict):
            return LiveArtifact()
        try:
            return LiveArtifact.model_validate(payload)
        except ValidationError:
            return LiveArtifact()

    @staticmethod
    def _apply_patch(current: LiveArtifact, patch: dict[str, Any] | None) -> LiveArtifact:
        if not isinstance(patch, dict):
            return current

        merged = current.model_dump()
        allowed_fields = set(LiveArtifact.model_fields.keys())
        for key, value in patch.items():
            if key in allowed_fields:
                merged[key] = value
        merged["updated_at"] = ArtifactManager._now_iso()
        try:
            return LiveArtifact.model_validate(merged)
        except ValidationError:
            return current

    @staticmethod
    def get_active_artifact(
        sessao_id: str,
        db: Session | None = None,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> LiveArtifact:
        memory = InternalCopilotMemoryStore.get_memory(
            sessao_id,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        return ArtifactManager._coerce_artifact(memory.artefato_em_andamento)

    @staticmethod
    def upsert_artifact(
        sessao_id: str,
        patch: dict[str, Any] | None,
        db: Session | None = None,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> LiveArtifact:
        if not isinstance(patch, dict):
            return ArtifactManager.get_active_artifact(
                sessao_id,
                db=db,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
            )
        current = ArtifactManager.get_active_artifact(
            sessao_id,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        updated = ArtifactManager._apply_patch(current, patch)
        InternalCopilotMemoryStore.patch_memory(
            sessao_id,
            {"artefato_em_andamento": updated.model_dump(exclude_none=True)},
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        return updated

    @staticmethod
    def clear_artifact(
        sessao_id: str,
        db: Session | None = None,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> LiveArtifact:
        InternalCopilotMemoryStore.patch_memory(
            sessao_id,
            {"artefato_em_andamento": None},
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        return LiveArtifact()
