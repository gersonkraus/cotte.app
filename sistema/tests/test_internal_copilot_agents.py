from __future__ import annotations

from app.services.internal_copilot_agents import LogicalAgentRunner
from app.services.internal_copilot_orchestrator import ArtifactSnapshot, SupervisorDecision, WorkingMemorySnapshot


def _build_decision(
    *,
    rota_primaria: str,
    subagente_primario: str,
    subagentes_secundarios: list[str],
    tipo_resposta_esperada: str,
    objetivo_ativo: str | None = None,
    continuidade_aplicada: bool = False,
    memoria_anterior: WorkingMemorySnapshot | None = None,
    memoria_atualizada: WorkingMemorySnapshot | None = None,
    artefato_ativo: ArtifactSnapshot | None = None,
) -> SupervisorDecision:
    return SupervisorDecision(
        rota_primaria=rota_primaria,
        subagente_primario=subagente_primario,
        subagentes_secundarios=subagentes_secundarios,
        tipo_resposta_esperada=tipo_resposta_esperada,
        objetivo_ativo=objetivo_ativo,
        tipo_fluxo_ativo=rota_primaria,
        continuidade_aplicada=continuidade_aplicada,
        rationale="teste",
        memoria_anterior=memoria_anterior or WorkingMemorySnapshot(),
        memoria_atualizada=memoria_atualizada or WorkingMemorySnapshot(),
        artefato_ativo=artefato_ativo or ArtifactSnapshot(),
    )


def test_logical_agent_runner_builds_analytics_internal_plan_with_artifact_reuse():
    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Gerar relatorio executivo semanal",
        continuidade_aplicada=True,
        memoria_anterior=WorkingMemorySnapshot(
            objetivo_ativo="Gerar relatorio executivo semanal",
            proximos_passos_sugeridos=["Consolidar principais KPIs"],
        ),
        memoria_atualizada=WorkingMemorySnapshot(
            objetivo_ativo="Gerar relatorio executivo semanal",
            tipo_fluxo_ativo="analytics",
            subagente_primario="analytics_specialist",
            subagentes_secundarios=["artifact_manager"],
            tipo_resposta_esperada="relatorio_executivo",
            proximos_passos_sugeridos=["Consolidar principais KPIs"],
        ),
        artefato_ativo=ArtifactSnapshot(
            artifact_id="rel-1",
            artifact_type="report",
            title="Relatorio semanal",
            status="in_progress",
            suggested_actions=["Atualizar tabela consolidada"],
        ),
    )

    result = LogicalAgentRunner.run(
        mensagem="  Gere  uma   tabela com indicadores e resumo executivo. ",
        decision=decision,
    )

    assert result.executed_agents == [
        "understanding",
        "business_data",
        "response_structuring",
        "conversation_continuity",
    ]
    assert result.understanding.normalized_message == "Gere uma tabela com indicadores e resumo executivo."
    assert result.business_data is not None
    assert result.business_data.needs_business_data is True
    assert result.business_data.artifact_action == "update_report"
    assert result.business_data.target_artifact_type == "report"
    assert result.technical is None
    assert result.response_structuring.section_order == ["resumo_executivo", "tabela", "insights", "proximos_passos"]
    assert result.continuity is not None
    assert result.continuity.should_reuse_artifact is True
    assert "Atualizar tabela consolidada" in result.continuity.suggested_next_steps


def test_logical_agent_runner_builds_technical_plan_with_code_context_only():
    decision = _build_decision(
        rota_primaria="technical",
        subagente_primario="technical_investigator",
        subagentes_secundarios=["code_rag"],
        tipo_resposta_esperada="resposta_tecnica",
        objetivo_ativo="Investigar erro de totalizacao",
        memoria_atualizada=WorkingMemorySnapshot(
            objetivo_ativo="Investigar erro de totalizacao",
            tipo_fluxo_ativo="technical",
            subagente_primario="technical_investigator",
            subagentes_secundarios=["code_rag"],
            tipo_resposta_esperada="resposta_tecnica",
        ),
    )

    result = LogicalAgentRunner.run(
        mensagem="Investigue este bug no arquivo service.py com stacktrace de erro.",
        decision=decision,
    )

    assert result.executed_agents == [
        "understanding",
        "technical",
        "response_structuring",
        "conversation_continuity",
    ]
    assert result.technical is not None
    assert result.technical.include_code_context is True
    assert result.technical.include_sql_context is False
    assert result.technical.sql_query is None
    assert result.technical.investigation_targets == ["service.py"]
    assert result.business_data is None
    assert result.response_structuring.section_order == ["diagnostico", "evidencias", "acoes_recomendadas"]


def test_logical_agent_runner_builds_hybrid_plan_with_data_and_technical_intents():
    decision = _build_decision(
        rota_primaria="hybrid",
        subagente_primario="technical_investigator",
        subagentes_secundarios=["analytics_specialist", "artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Cruzar bug com impacto financeiro",
        memoria_atualizada=WorkingMemorySnapshot(
            objetivo_ativo="Cruzar bug com impacto financeiro",
            tipo_fluxo_ativo="hybrid",
            subagente_primario="technical_investigator",
            subagentes_secundarios=["analytics_specialist", "artifact_manager"],
            tipo_resposta_esperada="relatorio_executivo",
        ),
    )

    result = LogicalAgentRunner.run(
        mensagem="Analise o bug no repositorio e gere uma tabela com impacto financeiro por cliente.",
        decision=decision,
    )

    assert result.executed_agents == [
        "understanding",
        "business_data",
        "technical",
        "response_structuring",
        "conversation_continuity",
    ]
    assert result.business_data is not None
    assert result.business_data.needs_business_data is True
    assert result.business_data.preferred_output == "table"
    assert result.technical is not None
    assert result.technical.include_code_context is True
    assert result.technical.include_sql_context is True
    assert result.technical.sql_query is None
    assert result.response_structuring.section_order == ["resumo_executivo", "diagnostico_tecnico", "tabela", "proximos_passos"]


def test_logical_agent_runner_preserves_contextual_follow_up_suggestions_without_artifact():
    decision = _build_decision(
        rota_primaria="conversational",
        subagente_primario="conversation_manager",
        subagentes_secundarios=[],
        tipo_resposta_esperada="resposta_contextual",
        objetivo_ativo="Orientar proxima etapa",
        continuidade_aplicada=True,
        memoria_anterior=WorkingMemorySnapshot(
            objetivo_ativo="Orientar proxima etapa",
            proximos_passos_sugeridos=["Detalhar impacto antes de agir"],
            ultimo_resultado_relevante={"resumo": "Erro isolado no fechamento"},
        ),
        memoria_atualizada=WorkingMemorySnapshot(
            objetivo_ativo="Orientar proxima etapa",
            tipo_fluxo_ativo="conversational",
            subagente_primario="conversation_manager",
            tipo_resposta_esperada="resposta_contextual",
            proximos_passos_sugeridos=["Detalhar impacto antes de agir"],
            ultimo_resultado_relevante={"resumo": "Erro isolado no fechamento"},
        ),
    )

    result = LogicalAgentRunner.run(mensagem="continue", decision=decision)

    assert result.executed_agents == [
        "understanding",
        "response_structuring",
        "conversation_continuity",
    ]
    assert result.business_data is None
    assert result.technical is None
    assert result.continuity is not None
    assert result.continuity.should_reuse_artifact is False
    assert result.continuity.last_relevant_result == {"resumo": "Erro isolado no fechamento"}
    assert result.continuity.suggested_next_steps == ["Detalhar impacto antes de agir"]


def test_logical_agent_runner_prepares_new_analytics_report_when_continuity_is_disabled():
    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Novo ranking de faturamento",
        continuidade_aplicada=False,
        artefato_ativo=ArtifactSnapshot(
            artifact_id="rel-antigo",
            artifact_type="report",
            title="Relatorio anterior",
            status="in_progress",
            suggested_actions=["Continuar consolidacao antiga"],
        ),
    )

    result = LogicalAgentRunner.run(
        mensagem="Monte um novo relatorio analitico com tabela por vendedor.",
        decision=decision,
    )

    assert result.business_data is not None
    assert result.business_data.artifact_action == "prepare_report"


def test_logical_agent_runner_does_not_reuse_active_artifact_when_continuity_is_disabled():
    decision = _build_decision(
        rota_primaria="conversational",
        subagente_primario="conversation_manager",
        subagentes_secundarios=[],
        tipo_resposta_esperada="resposta_contextual",
        continuidade_aplicada=False,
        memoria_atualizada=WorkingMemorySnapshot(
            tipo_fluxo_ativo="conversational",
            subagente_primario="conversation_manager",
            tipo_resposta_esperada="resposta_contextual",
            proximos_passos_sugeridos=["Reformular pedido atual"],
        ),
        artefato_ativo=ArtifactSnapshot(
            artifact_id="rel-stale",
            artifact_type="report",
            status="in_progress",
            suggested_actions=["Nao deveria reaproveitar"],
        ),
    )

    result = LogicalAgentRunner.run(mensagem="mude de assunto", decision=decision)

    assert result.continuity is not None
    assert result.continuity.continuity_active is False
    assert result.continuity.should_reuse_artifact is False
    assert result.continuity.suggested_next_steps == ["Reformular pedido atual"]


def test_logical_agent_runner_preserves_chart_visualization_intent_for_analytics_prompt():
    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Visualizar tendencia mensal",
    )

    result = LogicalAgentRunner.run(
        mensagem="Gere um dashboard com grafico de faturamento mensal por vendedor.",
        decision=decision,
    )

    assert result.business_data is not None
    assert result.business_data.preferred_output == "chart"


def test_logical_agent_runner_preserves_visual_intent_on_short_analytics_follow_up():
    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Dashboard mensal",
        continuidade_aplicada=True,
        artefato_ativo=ArtifactSnapshot(
            artifact_id="rel-chart",
            artifact_type="report",
            status="in_progress",
            chart={"type": "bar", "series": [1, 2, 3]},
            metadata={"preferred_output": "chart"},
        ),
    )

    result = LogicalAgentRunner.run(mensagem="continue", decision=decision)

    assert result.business_data is not None
    assert result.business_data.artifact_action == "update_report"
    assert result.business_data.preferred_output == "chart"


def test_logical_agent_runner_preserves_tabular_intent_on_short_analytics_follow_up_without_metadata():
    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Tabela mensal",
        continuidade_aplicada=True,
        artefato_ativo=ArtifactSnapshot(
            artifact_id="rel-table",
            artifact_type="report",
            status="in_progress",
            table=[{"mes": "jan", "valor": 1000}],
        ),
    )

    result = LogicalAgentRunner.run(mensagem="continue", decision=decision)

    assert result.business_data is not None
    assert result.business_data.artifact_action == "update_report"
    assert result.business_data.preferred_output == "table"
    assert result.response_structuring.section_order == ["resumo_executivo", "tabela", "insights", "proximos_passos"]
    assert result.response_structuring.should_render_artifact is True


def test_logical_agent_runner_does_not_reuse_report_artifact_in_incompatible_follow_up_route():
    decision = _build_decision(
        rota_primaria="technical",
        subagente_primario="technical_investigator",
        subagentes_secundarios=["code_rag"],
        tipo_resposta_esperada="resposta_tecnica",
        continuidade_aplicada=True,
        memoria_atualizada=WorkingMemorySnapshot(
            tipo_fluxo_ativo="technical",
            subagente_primario="technical_investigator",
            tipo_resposta_esperada="resposta_tecnica",
        ),
        artefato_ativo=ArtifactSnapshot(
            artifact_id="rel-residual",
            artifact_type="report",
            status="in_progress",
            suggested_actions=["Atualizar dashboard residual"],
        ),
    )

    result = LogicalAgentRunner.run(mensagem="continue", decision=decision)

    assert result.continuity is not None
    assert result.continuity.continuity_active is True
    assert result.continuity.should_reuse_artifact is False
    assert result.continuity.suggested_next_steps == []


def test_logical_agent_runner_uses_chart_section_for_visual_analytics_prompt():
    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Painel de faturamento",
    )

    result = LogicalAgentRunner.run(
        mensagem="Gere um dashboard com grafico de faturamento mensal.",
        decision=decision,
    )

    assert result.business_data is not None
    assert result.business_data.preferred_output == "chart"
    assert result.response_structuring.section_order == ["resumo_executivo", "grafico", "insights", "proximos_passos"]


def test_logical_agent_runner_uses_summary_only_structure_for_pure_analytics_summary_prompt():
    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Resumo mensal",
    )

    result = LogicalAgentRunner.run(
        mensagem="Gere um resumo executivo do faturamento mensal.",
        decision=decision,
    )

    assert result.business_data is not None
    assert result.business_data.preferred_output == "summary"
    assert result.response_structuring.section_order == ["resumo_executivo", "insights", "proximos_passos"]
    assert result.response_structuring.should_render_artifact is False


def test_logical_agent_runner_uses_summary_only_structure_for_pure_hybrid_summary_prompt():
    decision = _build_decision(
        rota_primaria="hybrid",
        subagente_primario="technical_investigator",
        subagentes_secundarios=["analytics_specialist", "artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Cruzar bug com resumo de impacto",
    )

    result = LogicalAgentRunner.run(
        mensagem="Analise o bug no repositorio e gere um resumo executivo do impacto.",
        decision=decision,
    )

    assert result.business_data is not None
    assert result.business_data.preferred_output == "summary"
    assert result.response_structuring.section_order == ["resumo_executivo", "diagnostico_tecnico", "insights", "proximos_passos"]
    assert result.response_structuring.should_render_artifact is False


def test_logical_agent_runner_uses_operational_sections_for_operational_route():
    decision = _build_decision(
        rota_primaria="operational",
        subagente_primario="operational_generalist",
        subagentes_secundarios=[],
        tipo_resposta_esperada="resposta_contextual",
        objetivo_ativo="Aprovar pendencia operacional",
        memoria_atualizada=WorkingMemorySnapshot(
            objetivo_ativo="Aprovar pendencia operacional",
            tipo_fluxo_ativo="operational",
            subagente_primario="operational_generalist",
            tipo_resposta_esperada="resposta_contextual",
        ),
    )

    result = LogicalAgentRunner.run(mensagem="Aprove e finalize o envio.", decision=decision)

    assert result.executed_agents == [
        "understanding",
        "response_structuring",
        "conversation_continuity",
    ]
    assert result.response_structuring.section_order == ["acao", "status", "proximos_passos"]
    assert result.response_structuring.should_render_artifact is False
