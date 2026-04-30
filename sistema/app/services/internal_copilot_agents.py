"""Subagentes lógicos mínimos do copiloto interno."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.services.internal_copilot_orchestrator import ArtifactSnapshot, SupervisorDecision, WorkingMemorySnapshot


def _normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", (message or "").strip())


def _extract_file_targets(message: str) -> list[str]:
    return re.findall(r"\b[\w./-]+\.[A-Za-z0-9_]+\b", message or "")


def _contains_any(message: str, terms: tuple[str, ...]) -> bool:
    lowered = (message or "").lower()
    return any(term in lowered for term in terms)


def _artifact_matches_route(artifact: ArtifactSnapshot, route: str) -> bool:
    if artifact.status == "idle":
        return False
    if artifact.artifact_type == "report":
        return route in {"analytics", "hybrid"}
    return True


class AgentExecutionContext(BaseModel):
    mensagem_original: str
    mensagem_normalizada: str
    decision: SupervisorDecision
    memoria_atualizada: WorkingMemorySnapshot
    artefato_ativo: ArtifactSnapshot


class UnderstandingAgentOutput(BaseModel):
    normalized_message: str
    active_objective: str | None = None
    route: str
    expected_response_type: str
    continuity_applied: bool


class BusinessDataAgentOutput(BaseModel):
    needs_business_data: bool
    preferred_output: str
    artifact_action: str
    target_artifact_type: str | None = None
    sql_query: str | None = None


class TechnicalAgentOutput(BaseModel):
    include_code_context: bool
    include_sql_context: bool
    sql_query: str | None = None
    investigation_targets: list[str] = Field(default_factory=list)


class ResponseStructuringAgentOutput(BaseModel):
    response_type: str
    section_order: list[str] = Field(default_factory=list)
    should_render_artifact: bool = False


class ConversationContinuityAgentOutput(BaseModel):
    continuity_active: bool
    should_reuse_artifact: bool
    suggested_next_steps: list[str] = Field(default_factory=list)
    last_relevant_result: dict | None = None


class LogicalAgentRunResult(BaseModel):
    context: AgentExecutionContext
    executed_agents: list[str] = Field(default_factory=list)
    understanding: UnderstandingAgentOutput
    business_data: BusinessDataAgentOutput | None = None
    technical: TechnicalAgentOutput | None = None
    response_structuring: ResponseStructuringAgentOutput
    continuity: ConversationContinuityAgentOutput | None = None


class UnderstandingAgent:
    @staticmethod
    def run(context: AgentExecutionContext) -> UnderstandingAgentOutput:
        return UnderstandingAgentOutput(
            normalized_message=context.mensagem_normalizada,
            active_objective=context.decision.objetivo_ativo,
            route=context.decision.rota_primaria,
            expected_response_type=context.decision.tipo_resposta_esperada,
            continuity_applied=context.decision.continuidade_aplicada,
        )


class BusinessDataAgent:
    @staticmethod
    def run(context: AgentExecutionContext) -> BusinessDataAgentOutput:
        has_active_report = (
            context.decision.continuidade_aplicada
            and context.artefato_ativo.status != "idle"
            and context.artefato_ativo.artifact_type == "report"
        )
        if _contains_any(context.mensagem_normalizada, ("tabela", "indicadores", "metricas", "métricas")):
            preferred_output = "table"
        elif _contains_any(context.mensagem_normalizada, ("grafico", "gráfico", "dashboard", "painel")):
            preferred_output = "chart"
        else:
            preferred_output = "summary"
        if (
            preferred_output == "summary"
            and has_active_report
            and _artifact_matches_route(context.artefato_ativo, context.decision.rota_primaria)
        ):
            artifact_preferred_output = context.artefato_ativo.metadata.get("preferred_output")
            if artifact_preferred_output in {"table", "chart", "summary"}:
                preferred_output = artifact_preferred_output
            elif context.artefato_ativo.chart:
                preferred_output = "chart"
            elif context.artefato_ativo.table:
                preferred_output = "table"
        return BusinessDataAgentOutput(
            needs_business_data=True,
            preferred_output=preferred_output,
            artifact_action="update_report" if has_active_report else "prepare_report",
            target_artifact_type="report",
            sql_query=None,
        )


class TechnicalAgent:
    @staticmethod
    def run(context: AgentExecutionContext) -> TechnicalAgentOutput:
        route = context.decision.rota_primaria
        return TechnicalAgentOutput(
            include_code_context=route in {"technical", "hybrid"},
            include_sql_context=route == "hybrid",
            sql_query=None,
            investigation_targets=_extract_file_targets(context.mensagem_normalizada),
        )


class ResponseStructuringAgent:
    @staticmethod
    def run(context: AgentExecutionContext) -> ResponseStructuringAgentOutput:
        route = context.decision.rota_primaria
        preferred_output = None
        if route in {"analytics", "hybrid"}:
            preferred_output = BusinessDataAgent.run(context).preferred_output
        if route == "technical":
            return ResponseStructuringAgentOutput(
                response_type=context.decision.tipo_resposta_esperada,
                section_order=["diagnostico", "evidencias", "acoes_recomendadas"],
                should_render_artifact=False,
            )
        if route == "hybrid":
            if preferred_output == "summary":
                return ResponseStructuringAgentOutput(
                    response_type=context.decision.tipo_resposta_esperada,
                    section_order=["resumo_executivo", "diagnostico_tecnico", "insights", "proximos_passos"],
                    should_render_artifact=False,
                )
            return ResponseStructuringAgentOutput(
                response_type=context.decision.tipo_resposta_esperada,
                section_order=[
                    "resumo_executivo",
                    "diagnostico_tecnico",
                    "grafico" if preferred_output == "chart" else "tabela",
                    "proximos_passos",
                ],
                should_render_artifact=True,
            )
        if route == "analytics":
            if preferred_output == "summary":
                return ResponseStructuringAgentOutput(
                    response_type=context.decision.tipo_resposta_esperada,
                    section_order=["resumo_executivo", "insights", "proximos_passos"],
                    should_render_artifact=False,
                )
            return ResponseStructuringAgentOutput(
                response_type=context.decision.tipo_resposta_esperada,
                section_order=[
                    "resumo_executivo",
                    "grafico" if preferred_output == "chart" else "tabela",
                    "insights",
                    "proximos_passos",
                ],
                should_render_artifact=True,
            )
        if route == "operational":
            return ResponseStructuringAgentOutput(
                response_type=context.decision.tipo_resposta_esperada,
                section_order=["acao", "status", "proximos_passos"],
                should_render_artifact=False,
            )
        return ResponseStructuringAgentOutput(
            response_type=context.decision.tipo_resposta_esperada,
            section_order=["contexto", "resposta", "proximos_passos"],
            should_render_artifact=False,
        )


class ConversationContinuityAgent:
    @staticmethod
    def run(context: AgentExecutionContext) -> ConversationContinuityAgentOutput:
        memory_steps = list(context.memoria_atualizada.proximos_passos_sugeridos or [])
        artifact_steps = (
            list(context.artefato_ativo.suggested_actions or [])
            if context.decision.continuidade_aplicada
            and _artifact_matches_route(context.artefato_ativo, context.decision.rota_primaria)
            else []
        )
        suggested_next_steps = memory_steps + [step for step in artifact_steps if step not in memory_steps]
        return ConversationContinuityAgentOutput(
            continuity_active=context.decision.continuidade_aplicada,
            should_reuse_artifact=(
                context.decision.continuidade_aplicada
                and _artifact_matches_route(context.artefato_ativo, context.decision.rota_primaria)
            ),
            suggested_next_steps=suggested_next_steps,
            last_relevant_result=context.memoria_atualizada.ultimo_resultado_relevante,
        )


class LogicalAgentRunner:
    @staticmethod
    def _build_context(mensagem: str, decision: SupervisorDecision) -> AgentExecutionContext:
        return AgentExecutionContext(
            mensagem_original=mensagem,
            mensagem_normalizada=_normalize_message(mensagem),
            decision=decision,
            memoria_atualizada=decision.memoria_atualizada,
            artefato_ativo=decision.artefato_ativo,
        )

    @staticmethod
    def run(*, mensagem: str, decision: SupervisorDecision) -> LogicalAgentRunResult:
        context = LogicalAgentRunner._build_context(mensagem, decision)
        executed_agents = ["understanding"]
        understanding = UnderstandingAgent.run(context)

        business_data = None
        if decision.rota_primaria in {"analytics", "hybrid"}:
            business_data = BusinessDataAgent.run(context)
            executed_agents.append("business_data")

        technical = None
        if decision.rota_primaria in {"technical", "hybrid"}:
            technical = TechnicalAgent.run(context)
            executed_agents.append("technical")

        response_structuring = ResponseStructuringAgent.run(context)
        executed_agents.append("response_structuring")

        continuity = ConversationContinuityAgent.run(context)
        executed_agents.append("conversation_continuity")

        return LogicalAgentRunResult(
            context=context,
            executed_agents=executed_agents,
            understanding=understanding,
            business_data=business_data,
            technical=technical,
            response_structuring=response_structuring,
            continuity=continuity,
        )
