from __future__ import annotations

from app.services.cotte_context_builder import SessionStore
from app.services.internal_copilot_artifacts import ArtifactManager
from app.services.internal_copilot_memory import InternalCopilotMemoryStore
from app.services.internal_copilot_orchestrator import SupervisorOrchestrator
from tests.conftest import make_empresa, make_usuario


def test_orchestrator_classifies_executive_report_as_analytics_and_updates_memory(db):
    emp = make_empresa(db, nome="Orquestrador Analytics")
    user = make_usuario(db, emp, email="orchestrator-analytics@teste.com")
    sessao_id = "sess-orch-analytics"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="Gere um relatorio executivo com metricas, tabela e grafico de vendas por vendedor.",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "analytics"
    assert decision.subagente_primario == "analytics_specialist"
    assert decision.subagentes_secundarios == ["artifact_manager"]
    assert decision.tipo_resposta_esperada == "relatorio_executivo"
    assert decision.memoria_atualizada.tipo_fluxo_ativo == "analytics"
    assert decision.memoria_atualizada.subagente_primario == "analytics_specialist"
    assert decision.memoria_atualizada.tipo_resposta_esperada == "relatorio_executivo"


def test_orchestrator_classifies_technical_investigation_as_technical(db):
    emp = make_empresa(db, nome="Orquestrador Technical")
    user = make_usuario(db, emp, email="orchestrator-technical@teste.com")
    sessao_id = "sess-orch-technical"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="Investigue este bug no arquivo service.py com stacktrace de erro e funcao quebrando.",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "technical"
    assert decision.subagente_primario == "technical_investigator"
    assert decision.subagentes_secundarios == ["code_rag"]
    assert decision.tipo_resposta_esperada == "resposta_tecnica"


def test_orchestrator_classifies_mixed_request_as_hybrid_with_coherent_subagents(db):
    emp = make_empresa(db, nome="Orquestrador Hybrid")
    user = make_usuario(db, emp, email="orchestrator-hybrid@teste.com")
    sessao_id = "sess-orch-hybrid"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="Analise o bug no repositorio e gere uma tabela com metricas do impacto financeiro.",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "hybrid"
    assert decision.subagente_primario == "technical_investigator"
    assert decision.subagentes_secundarios == ["analytics_specialist", "artifact_manager"]
    assert decision.tipo_resposta_esperada == "relatorio_executivo"


def test_orchestrator_reuses_active_flow_on_short_follow_up(db):
    emp = make_empresa(db, nome="Orquestrador Follow-up")
    user = make_usuario(db, emp, email="orchestrator-follow-up@teste.com")
    sessao_id = "sess-orch-follow-up"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Investigar regressao de totalizacao",
            "tipo_fluxo_ativo": "technical",
            "subagente_primario": "technical_investigator",
            "subagentes_secundarios": ["code_rag"],
            "tipo_resposta_esperada": "resposta_tecnica",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="continue",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "technical"
    assert decision.tipo_resposta_esperada == "resposta_tecnica"
    assert decision.memoria_atualizada.objetivo_ativo == "Investigar regressao de totalizacao"


def test_orchestrator_reuses_explicit_follow_up_with_only_active_flow_type(db):
    emp = make_empresa(db, nome="Orquestrador Flow Type")
    user = make_usuario(db, emp, email="orchestrator-flow-type@teste.com")
    sessao_id = "sess-orch-flow-type"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "tipo_fluxo_ativo": "technical",
            "subagente_primario": "technical_investigator",
            "subagentes_secundarios": ["code_rag"],
            "tipo_resposta_esperada": "resposta_tecnica",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="continue.",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "technical"
    assert decision.continuidade_aplicada is True
    assert decision.tipo_resposta_esperada == "resposta_tecnica"


def test_orchestrator_short_message_with_clear_new_subject_does_not_reuse_previous_technical_flow(db):
    emp = make_empresa(db, nome="Orquestrador Novo Assunto")
    user = make_usuario(db, emp, email="orchestrator-new-topic@teste.com")
    sessao_id = "sess-orch-new-topic"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Investigar stacktrace do backend",
            "tipo_fluxo_ativo": "technical",
            "subagente_primario": "technical_investigator",
            "subagentes_secundarios": ["code_rag"],
            "tipo_resposta_esperada": "resposta_tecnica",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="mostre faturamento mensal",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "analytics"
    assert decision.subagente_primario == "analytics_specialist"
    assert decision.tipo_resposta_esperada == "relatorio_executivo"


def test_orchestrator_short_follow_up_with_only_active_goal_preserves_continuity(db):
    emp = make_empresa(db, nome="Orquestrador Objetivo")
    user = make_usuario(db, emp, email="orchestrator-goal@teste.com")
    sessao_id = "sess-orch-goal"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Investigar regressao de totalizacao",
            "subagente_primario": "technical_investigator",
            "subagentes_secundarios": ["code_rag"],
            "tipo_resposta_esperada": "resposta_tecnica",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="continue",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "technical"
    assert decision.continuidade_aplicada is True
    assert decision.memoria_atualizada.objetivo_ativo == "Investigar regressao de totalizacao"


def test_orchestrator_infers_operational_continuity_from_partial_memory(db):
    emp = make_empresa(db, nome="Orquestrador Operational")
    user = make_usuario(db, emp, email="orchestrator-operational@teste.com")
    sessao_id = "sess-orch-operational"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Concluir atualizacao operacional pendente",
            "subagente_primario": "operational_generalist",
            "tipo_resposta_esperada": "resposta_contextual",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="continue por favor",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "operational"
    assert decision.continuidade_aplicada is True
    assert decision.subagente_primario == "operational_generalist"
    assert decision.tipo_resposta_esperada == "resposta_contextual"


def test_orchestrator_does_not_infer_operational_from_contextual_response_only(db):
    emp = make_empresa(db, nome="Orquestrador Contextual")
    user = make_usuario(db, emp, email="orchestrator-contextual@teste.com")
    sessao_id = "sess-orch-contextual"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Responder conversa pendente",
            "tipo_resposta_esperada": "resposta_contextual",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="continue",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "conversational"
    assert decision.continuidade_aplicada is False
    assert decision.tipo_resposta_esperada == "resposta_contextual"


def test_orchestrator_follow_up_with_active_artifact_preserves_continuity(db):
    emp = make_empresa(db, nome="Orquestrador Artifact")
    user = make_usuario(db, emp, email="orchestrator-artifact@teste.com")
    sessao_id = "sess-orch-artifact"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    ArtifactManager.upsert_artifact(
        sessao_id,
        {
            "artifact_id": "rel-ativo",
            "artifact_type": "report",
            "status": "in_progress",
            "summary": "Parcial",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="gere a tabela",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "analytics"
    assert decision.continuidade_aplicada is True
    assert decision.tipo_resposta_esperada == "relatorio_executivo"
    assert decision.artefato_ativo.status == "in_progress"


def test_orchestrator_gere_a_tabela_after_technical_context_switches_to_analytics(db):
    emp = make_empresa(db, nome="Orquestrador Tabela Analytics")
    user = make_usuario(db, emp, email="orchestrator-table-analytics@teste.com")
    sessao_id = "sess-orch-table-analytics"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Investigar erro de totalizacao",
            "tipo_fluxo_ativo": "technical",
            "subagente_primario": "technical_investigator",
            "subagentes_secundarios": ["code_rag"],
            "tipo_resposta_esperada": "resposta_tecnica",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="gere a tabela",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.rota_primaria == "analytics"
    assert decision.continuidade_aplicada is False
    assert decision.subagente_primario == "analytics_specialist"
    assert decision.tipo_resposta_esperada == "relatorio_executivo"


def test_orchestrator_patch_does_not_remove_unrelated_working_memory_fields(db):
    emp = make_empresa(db, nome="Orquestrador Patch")
    user = make_usuario(db, emp, email="orchestrator-patch@teste.com")
    sessao_id = "sess-orch-patch"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "entidades_ativas": {"arquivo": "service.py"},
            "ultimo_resultado_relevante": {"trace_id": "abc"},
            "pendencia_confirmacao": {"tipo": "nenhuma"},
            "proximos_passos_sugeridos": ["Reproduzir erro"],
            "confianca_contextual": 0.91,
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="Investigue o erro no repositorio.",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert decision.memoria_atualizada.entidades_ativas == {"arquivo": "service.py"}
    assert decision.memoria_atualizada.ultimo_resultado_relevante == {"trace_id": "abc"}
    assert decision.memoria_atualizada.pendencia_confirmacao == {"tipo": "nenhuma"}
    assert decision.memoria_atualizada.proximos_passos_sugeridos == ["Reproduzir erro"]
    assert decision.memoria_atualizada.confianca_contextual == 0.91


def test_orchestrator_returns_local_snapshots_in_decision(db):
    emp = make_empresa(db, nome="Orquestrador Snapshot")
    user = make_usuario(db, emp, email="orchestrator-snapshot@teste.com")
    sessao_id = "sess-orch-snapshot"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    decision = SupervisorOrchestrator.decide_and_sync(
        mensagem="Gere um relatorio com tabela de faturamento.",
        sessao_id=sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert type(decision.memoria_atualizada).__name__ == "WorkingMemorySnapshot"
    assert type(decision.memoria_anterior).__name__ == "WorkingMemorySnapshot"
    assert type(decision.artefato_ativo).__name__ == "ArtifactSnapshot"
