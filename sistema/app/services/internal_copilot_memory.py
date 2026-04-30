"""Memoria de trabalho explicita do copiloto tecnico."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.services.cotte_context_builder import SessionStore

INTERNAL_COPILOT_WORKING_MEMORY_KEY = "internal_copilot_working_memory"


class SessionWorkingMemory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    objetivo_ativo: str | None = None
    tipo_fluxo_ativo: str | None = None
    escopo_ativo: dict[str, Any] | None = None
    entidades_ativas: dict[str, Any] = Field(default_factory=dict)
    subagente_primario: str | None = None
    subagentes_secundarios: list[str] = Field(default_factory=list)
    ultimo_resultado_relevante: dict[str, Any] | None = None
    artefato_em_andamento: dict[str, Any] | None = None
    tipo_resposta_esperada: str | None = None
    pendencia_confirmacao: dict[str, Any] | None = None
    proximos_passos_sugeridos: list[str] = Field(default_factory=list)
    confianca_contextual: float | None = None


class InternalCopilotMemoryStore:
    @staticmethod
    def get_memory(
        sessao_id: str,
        db: Session | None = None,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> SessionWorkingMemory:
        context = SessionStore.get_operational_context(
            sessao_id,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        payload = context.get(INTERNAL_COPILOT_WORKING_MEMORY_KEY)
        if not isinstance(payload, dict):
            return SessionWorkingMemory()
        try:
            return SessionWorkingMemory.model_validate(payload)
        except ValidationError:
            return SessionWorkingMemory()

    @staticmethod
    def apply_patch(
        current: SessionWorkingMemory,
        patch: dict[str, Any] | None,
    ) -> SessionWorkingMemory:
        if not isinstance(patch, dict):
            return current

        merged = current.model_dump()
        allowed_fields = set(SessionWorkingMemory.model_fields.keys())
        for key, value in patch.items():
            if key in allowed_fields:
                merged[key] = value
        return SessionWorkingMemory.model_validate(merged)

    @staticmethod
    def patch_memory(
        sessao_id: str,
        patch: dict[str, Any] | None,
        db: Session | None = None,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> SessionWorkingMemory:
        if not isinstance(patch, dict):
            return InternalCopilotMemoryStore.get_memory(
                sessao_id,
                db=db,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
            )
        current = InternalCopilotMemoryStore.get_memory(
            sessao_id,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        updated = InternalCopilotMemoryStore.apply_patch(current, patch)
        SessionStore.set_operational_context(
            sessao_id,
            {INTERNAL_COPILOT_WORKING_MEMORY_KEY: updated.model_dump()},
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        return updated

    @staticmethod
    def clear_memory(
        sessao_id: str,
        db: Session | None = None,
        empresa_id: int = 0,
        usuario_id: int = 0,
    ) -> SessionWorkingMemory:
        SessionStore.set_operational_context(
            sessao_id,
            {INTERNAL_COPILOT_WORKING_MEMORY_KEY: None},
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        return SessionWorkingMemory()
