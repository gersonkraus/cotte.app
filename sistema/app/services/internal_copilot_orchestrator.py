"""Orquestrador mínimo do copiloto técnico interno."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.internal_copilot_artifacts import ArtifactManager, LiveArtifact
from app.services.internal_copilot_memory import InternalCopilotMemoryStore, SessionWorkingMemory

PrimaryRoute = Literal["technical", "analytics", "operational", "hybrid", "conversational"]
ResponseType = Literal["relatorio_executivo", "resposta_tecnica", "resposta_contextual"]

_ANALYTICS_HINTS = (
    "relatorio",
    "relatório",
    "resumo",
    "metricas",
    "métricas",
    "tabela",
    "grafico",
    "gráfico",
    "dashboard",
    "indicadores",
    "faturamento",
    "mensal",
)
_TECHNICAL_HINTS = (
    "erro",
    "bug",
    "codigo",
    "código",
    "arquivo",
    "stacktrace",
    "reposit",
    "função",
    "funcao",
    "traceback",
    "exception",
)
_OPERATIONAL_HINTS = (
    "aprovar",
    "recusar",
    "enviar",
    "cadastre",
    "cadastrar",
    "criar",
    "atualizar",
    "editar",
)
_FOLLOW_UP_EXACT = {
    "continue",
    "continuar",
    "aprofunde",
    "aprofunda",
    "gere a tabela",
    "e os proximos passos?",
    "e os próximos passos?",
    "proximos passos",
    "próximos passos",
}
_FOLLOW_UP_PATTERNS = (
    re.compile(r"^continue[.!?]?$", flags=re.IGNORECASE),
    re.compile(r"^continue\s+por favor[.!?]?$", flags=re.IGNORECASE),
    re.compile(r"^continuar[.!?]?$", flags=re.IGNORECASE),
)


class SupervisorDecision(BaseModel):
    rota_primaria: PrimaryRoute
    subagente_primario: str
    subagentes_secundarios: list[str] = Field(default_factory=list)
    tipo_resposta_esperada: ResponseType
    objetivo_ativo: str | None = None
    tipo_fluxo_ativo: str
    continuidade_aplicada: bool = False
    rationale: str
    memoria_anterior: "WorkingMemorySnapshot"
    memoria_atualizada: "WorkingMemorySnapshot"
    artefato_ativo: "ArtifactSnapshot"


class WorkingMemorySnapshot(BaseModel):
    objetivo_ativo: str | None = None
    tipo_fluxo_ativo: str | None = None
    escopo_ativo: dict | None = None
    entidades_ativas: dict = Field(default_factory=dict)
    subagente_primario: str | None = None
    subagentes_secundarios: list[str] = Field(default_factory=list)
    ultimo_resultado_relevante: dict | None = None
    artefato_em_andamento: dict | None = None
    tipo_resposta_esperada: str | None = None
    pendencia_confirmacao: dict | None = None
    proximos_passos_sugeridos: list[str] = Field(default_factory=list)
    confianca_contextual: float | None = None

    @staticmethod
    def from_memory(memory: SessionWorkingMemory) -> "WorkingMemorySnapshot":
        return WorkingMemorySnapshot.model_validate(memory.model_dump())


class ArtifactSnapshot(BaseModel):
    artifact_id: str | None = None
    artifact_type: str | None = None
    title: str | None = None
    summary: str | None = None
    table: list[dict] = Field(default_factory=list)
    chart: dict | None = None
    insights: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    status: str = "idle"
    updated_at: str | None = None

    @staticmethod
    def from_artifact(artifact: LiveArtifact) -> "ArtifactSnapshot":
        return ArtifactSnapshot.model_validate(artifact.model_dump())


class SupervisorOrchestrator:
    @staticmethod
    def _normalize_message(message: str) -> str:
        return re.sub(r"\s+", " ", (message or "").strip())

    @staticmethod
    def _is_short_follow_up(message: str) -> bool:
        normalized = SupervisorOrchestrator._normalize_message(message)
        if not normalized:
            return False
        lowered = normalized.lower()
        return lowered in _FOLLOW_UP_EXACT or any(pattern.match(normalized) for pattern in _FOLLOW_UP_PATTERNS)

    @staticmethod
    def _supports_table_follow_up(memory: SessionWorkingMemory, artifact: LiveArtifact) -> bool:
        if memory.tipo_fluxo_ativo == "analytics":
            return True
        if memory.subagente_primario == "analytics_specialist":
            return True
        if memory.tipo_resposta_esperada == "relatorio_executivo":
            return True
        return artifact.status != "idle" and artifact.artifact_type == "report"

    @staticmethod
    def _has_explicit_new_intent(message: str) -> bool:
        if SupervisorOrchestrator._is_short_follow_up(message):
            return False
        route, _ = SupervisorOrchestrator._classify_route(message)
        return route != "conversational"

    @staticmethod
    def _has_active_context(memory: SessionWorkingMemory, artifact: LiveArtifact) -> bool:
        if memory.objetivo_ativo:
            return True
        if memory.tipo_fluxo_ativo in {"technical", "analytics", "operational", "hybrid", "conversational"}:
            return True
        return artifact.status != "idle"

    @staticmethod
    def _classify_route(message: str) -> tuple[PrimaryRoute, str]:
        lowered = SupervisorOrchestrator._normalize_message(message).lower()
        analytics_hits = sum(token in lowered for token in _ANALYTICS_HINTS)
        technical_hits = sum(token in lowered for token in _TECHNICAL_HINTS)
        operational_hits = sum(token in lowered for token in _OPERATIONAL_HINTS)

        if analytics_hits and technical_hits:
            return "hybrid", "Mensagem mistura investigação técnica com pedido analítico."
        if technical_hits:
            return "technical", "Mensagem contém sinais claros de código, erro ou repositório."
        if analytics_hits:
            return "analytics", "Mensagem contém sinais de relatório, métricas ou visualização tabular."
        if operational_hits:
            return "operational", "Mensagem indica execução operacional direta."
        return "conversational", "Mensagem sem sinais fortes de fluxo técnico, analítico ou operacional."

    @staticmethod
    def _resolve_agents(route: PrimaryRoute) -> tuple[str, list[str], ResponseType]:
        if route == "analytics":
            return "analytics_specialist", ["artifact_manager"], "relatorio_executivo"
        if route == "technical":
            return "technical_investigator", ["code_rag"], "resposta_tecnica"
        if route == "hybrid":
            return "technical_investigator", ["analytics_specialist", "artifact_manager"], "relatorio_executivo"
        if route == "operational":
            return "operational_generalist", [], "resposta_contextual"
        return "conversation_manager", [], "resposta_contextual"

    @staticmethod
    def _resolve_continuity_route(memory: SessionWorkingMemory, artifact: LiveArtifact) -> PrimaryRoute | None:
        route = memory.tipo_fluxo_ativo
        if route in {"technical", "analytics", "operational", "hybrid", "conversational"}:
            return route
        if memory.subagente_primario == "technical_investigator":
            return "technical"
        if memory.subagente_primario == "analytics_specialist":
            return "analytics"
        if memory.subagente_primario == "operational_generalist":
            return "operational"
        if memory.tipo_resposta_esperada == "resposta_tecnica":
            return "technical"
        if memory.tipo_resposta_esperada == "relatorio_executivo":
            return "analytics"
        if artifact.status != "idle" and artifact.artifact_type == "report":
            return "analytics"
        return None

    @staticmethod
    def decide_and_sync(
        *,
        mensagem: str,
        sessao_id: str,
        db: Session | None,
        empresa_id: int,
        usuario_id: int,
    ) -> SupervisorDecision:
        memory = InternalCopilotMemoryStore.get_memory(
            sessao_id,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        artifact = ArtifactManager.get_active_artifact(
            sessao_id,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )

        normalized_message = SupervisorOrchestrator._normalize_message(mensagem).lower()
        follow_up = SupervisorOrchestrator._is_short_follow_up(mensagem)
        table_follow_up_supported = False
        if normalized_message == "gere a tabela":
            table_follow_up_supported = SupervisorOrchestrator._supports_table_follow_up(memory, artifact)
            follow_up = table_follow_up_supported
        continuity_route = SupervisorOrchestrator._resolve_continuity_route(memory, artifact)
        has_active_context = SupervisorOrchestrator._has_active_context(memory, artifact)
        has_explicit_new_intent = SupervisorOrchestrator._has_explicit_new_intent(mensagem)
        if normalized_message == "gere a tabela" and not table_follow_up_supported:
            has_explicit_new_intent = True
        should_continue = follow_up and has_active_context and continuity_route and not has_explicit_new_intent

        if should_continue:
            route = continuity_route
            rationale = "Follow-up curto com contexto ativo; continuidade priorizada para evitar deriva."
        else:
            route, rationale = SupervisorOrchestrator._classify_route(mensagem)

        subagente_primario, subagentes_secundarios, tipo_resposta = SupervisorOrchestrator._resolve_agents(route)
        if should_continue and memory.subagente_primario:
            subagente_primario = memory.subagente_primario
        if should_continue and memory.subagentes_secundarios:
            subagentes_secundarios = memory.subagentes_secundarios
        if should_continue and memory.tipo_resposta_esperada in {
            "relatorio_executivo",
            "resposta_tecnica",
            "resposta_contextual",
        }:
            tipo_resposta = memory.tipo_resposta_esperada

        objetivo_ativo = memory.objetivo_ativo if should_continue and memory.objetivo_ativo else SupervisorOrchestrator._normalize_message(mensagem)[:240]
        escopo_atual = memory.escopo_ativo if isinstance(memory.escopo_ativo, dict) else {}
        memory_patch = {
            "objetivo_ativo": objetivo_ativo,
            "tipo_fluxo_ativo": route,
            "subagente_primario": subagente_primario,
            "subagentes_secundarios": subagentes_secundarios,
            "tipo_resposta_esperada": tipo_resposta,
            "escopo_ativo": {
                **escopo_atual,
                "rota_primaria": route,
                "continuidade_aplicada": bool(should_continue),
                "artefato_status": artifact.status,
            },
        }
        updated_memory = InternalCopilotMemoryStore.patch_memory(
            sessao_id,
            memory_patch,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )

        return SupervisorDecision(
            rota_primaria=route,
            subagente_primario=subagente_primario,
            subagentes_secundarios=subagentes_secundarios,
            tipo_resposta_esperada=tipo_resposta,
            objetivo_ativo=objetivo_ativo,
            tipo_fluxo_ativo=route,
            continuidade_aplicada=bool(should_continue),
            rationale=rationale,
            memoria_anterior=WorkingMemorySnapshot.from_memory(memory),
            memoria_atualizada=WorkingMemorySnapshot.from_memory(updated_memory),
            artefato_ativo=ArtifactSnapshot.from_artifact(artifact),
        )
