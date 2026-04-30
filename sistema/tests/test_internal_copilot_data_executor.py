from __future__ import annotations

from types import SimpleNamespace

import pytest

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


@pytest.mark.asyncio
async def test_data_executor_skips_when_run_has_no_business_data(monkeypatch):
    from app.services.internal_copilot_data_executor import InternalCopilotDataExecutor

    called = False

    async def _fake_runtime(**kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(
        "app.services.internal_copilot_data_executor.try_handle_semantic_autonomy",
        _fake_runtime,
    )

    decision = _build_decision(
        rota_primaria="technical",
        subagente_primario="technical_investigator",
        subagentes_secundarios=["code_rag"],
        tipo_resposta_esperada="resposta_tecnica",
        objetivo_ativo="Investigar regressao no backend",
    )
    run_result = LogicalAgentRunner.run(
        mensagem="Investigue este bug em service.py",
        decision=decision,
    )

    result = await InternalCopilotDataExecutor.execute(
        agent_run=run_result,
        db=None,
        current_user=SimpleNamespace(id=1, empresa_id=10, is_superadmin=True, is_gestor=True),
        sessao_id="sess-skip",
        request_id="req-skip",
    )

    assert result.executed is False
    assert result.skip_reason == "no_business_data_plan"
    assert called is False


@pytest.mark.asyncio
async def test_data_executor_calls_semantic_runtime_with_analytics_engine_and_table_hint(monkeypatch):
    from app.services.internal_copilot_data_executor import InternalCopilotDataExecutor

    captured: dict[str, object] = {}

    async def _fake_runtime(**kwargs):
        captured.update(kwargs)
        return {
            "sucesso": True,
            "resposta": "Relatorio pronto.",
            "dados": {
                "semantic_contract": {
                    "summary": "Resumo de vendas por vendedor.",
                    "table": [{"vendedor": "Ana", "total_vendas": 1200.0}],
                    "chart": None,
                    "insights": ["Ana lidera no periodo."],
                    "suggested_actions": ["Comparar com o mes anterior"],
                    "metadata": {"report_title": "Vendas por vendedor"},
                }
            },
        }

    monkeypatch.setattr(
        "app.services.internal_copilot_data_executor.try_handle_semantic_autonomy",
        _fake_runtime,
    )

    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Gerar relatorio comercial por vendedor",
    )
    run_result = LogicalAgentRunner.run(
        mensagem="Gere indicadores de vendas por vendedor",
        decision=decision,
    )

    result = await InternalCopilotDataExecutor.execute(
        agent_run=run_result,
        db=None,
        current_user=SimpleNamespace(id=2, empresa_id=20, is_superadmin=True, is_gestor=True),
        sessao_id="sess-table",
        request_id="req-table",
    )

    assert result.executed is True
    assert captured["engine"] == "analytics"
    assert "formato de tabela" in str(captured["mensagem"]).lower()
    assert result.artifact_patch is not None
    assert result.artifact_patch["artifact_type"] == "report"
    assert result.artifact_patch["metadata"]["preferred_output"] == "table"
    assert result.artifact_patch["title"] == "Vendas por vendedor"


@pytest.mark.asyncio
async def test_data_executor_uses_active_objective_for_short_analytics_follow_up(monkeypatch):
    from app.services.internal_copilot_data_executor import InternalCopilotDataExecutor

    captured: dict[str, object] = {}

    async def _fake_runtime(**kwargs):
        captured.update(kwargs)
        return {
            "sucesso": True,
            "resposta": "Grafico atualizado.",
            "dados": {
                "semantic_contract": {
                    "summary": "Tendencia mensal atualizada.",
                    "table": [],
                    "chart": {"type": "line", "labels": ["Jan"], "datasets": [{"label": "total", "data": [10]}]},
                    "insights": [],
                    "suggested_actions": [],
                    "metadata": {},
                }
            },
        }

    monkeypatch.setattr(
        "app.services.internal_copilot_data_executor.try_handle_semantic_autonomy",
        _fake_runtime,
    )

    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Gerar tendencia mensal de faturamento por grafico",
        continuidade_aplicada=True,
        artefato_ativo=ArtifactSnapshot(
            artifact_id="rel-chart",
            artifact_type="report",
            status="in_progress",
            chart={"type": "line"},
            metadata={"preferred_output": "chart"},
        ),
    )
    run_result = LogicalAgentRunner.run(mensagem="continue", decision=decision)

    result = await InternalCopilotDataExecutor.execute(
        agent_run=run_result,
        db=None,
        current_user=SimpleNamespace(id=3, empresa_id=30, is_superadmin=True, is_gestor=True),
        sessao_id="sess-chart",
        request_id="req-chart",
    )

    assert result.executed is True
    assert "tendencia mensal de faturamento" in str(captured["mensagem"]).lower()
    assert "gráfico" in str(captured["mensagem"]).lower() or "grafico" in str(captured["mensagem"]).lower()
    assert str(captured["mensagem"]).lower() != "continue"


@pytest.mark.asyncio
async def test_data_executor_does_not_prefix_hybrid_request(monkeypatch):
    from app.services.internal_copilot_data_executor import InternalCopilotDataExecutor

    captured: dict[str, object] = {}

    async def _fake_runtime(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(
        "app.services.internal_copilot_data_executor.try_handle_semantic_autonomy",
        _fake_runtime,
    )

    decision = _build_decision(
        rota_primaria="hybrid",
        subagente_primario="technical_investigator",
        subagentes_secundarios=["analytics_specialist", "artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Cruzar bug tecnico com impacto financeiro",
    )
    run_result = LogicalAgentRunner.run(
        mensagem="Analise o bug e gere um dashboard do impacto financeiro por cliente",
        decision=decision,
    )

    result = await InternalCopilotDataExecutor.execute(
        agent_run=run_result,
        db=None,
        current_user=SimpleNamespace(id=4, empresa_id=40, is_superadmin=True, is_gestor=True),
        sessao_id="sess-hybrid",
        request_id="req-hybrid",
    )

    assert captured["engine"] == "analytics"
    assert "Considere apenas a parte analítica desta solicitação" not in str(captured.get("mensagem", ""))
    assert result.executed is False
    assert result.skip_reason == "semantic_runtime_unavailable"

@pytest.mark.asyncio
async def test_data_executor_safely_extracts_malformed_contract_fields(monkeypatch):
    from app.services.internal_copilot_data_executor import InternalCopilotDataExecutor

    captured: dict[str, object] = {}

    async def _fake_runtime(**kwargs):
        captured.update(kwargs)
        return {
            "sucesso": True,
            "resposta": "Relatorio malformado.",
            "dados": {
                "semantic_contract": {
                    "summary": 123,  # wrong type
                    "table": "isso nao e uma lista",
                    "chart": ["isso nao e um dicionario"],
                    "insights": "apenas uma string solta",
                    "suggested_actions": {"chave": "valor"},
                    "metadata": {"report_title": "Titulo"},
                }
            },
        }

    monkeypatch.setattr(
        "app.services.internal_copilot_data_executor.try_handle_semantic_autonomy",
        _fake_runtime,
    )

    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=["artifact_manager"],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Gerar relatorio com payload quebrado",
    )
    run_result = LogicalAgentRunner.run(
        mensagem="Gere indicadores que vao quebrar",
        decision=decision,
    )

    result = await InternalCopilotDataExecutor.execute(
        agent_run=run_result,
        db=None,
        current_user=SimpleNamespace(id=7, empresa_id=70, is_superadmin=True, is_gestor=True),
        sessao_id="sess-malformed",
        request_id="req-malformed",
    )

    assert result.executed is True
    assert result.artifact_patch is not None
    
    assert result.artifact_patch["table"] == []
    assert result.artifact_patch["chart"] == {}
    assert result.artifact_patch["insights"] == []
    assert result.artifact_patch["suggested_actions"] == []


@pytest.mark.asyncio
async def test_data_executor_returns_none_when_runtime_returns_handled_false(monkeypatch):
    from app.services.internal_copilot_data_executor import InternalCopilotDataExecutor

    async def _fake_runtime(**kwargs):
        return {"handled": False, "error": "Not a data intent"}

    monkeypatch.setattr(
        "app.services.internal_copilot_data_executor.try_handle_semantic_autonomy",
        _fake_runtime,
    )

    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=[],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Gerar relatorio",
    )
    run_result = LogicalAgentRunner.run(mensagem="teste", decision=decision)

    result = await InternalCopilotDataExecutor.execute(
        agent_run=run_result,
        db=None,
        current_user=SimpleNamespace(id=5, empresa_id=50, is_superadmin=True, is_gestor=True),
        sessao_id="sess-handled",
        request_id="req-handled",
    )

    assert result.executed is False
    assert result.artifact_patch is None
    assert result.skip_reason == "handled_false"


@pytest.mark.asyncio
async def test_data_executor_returns_none_on_runtime_exception(monkeypatch):
    from app.services.internal_copilot_data_executor import InternalCopilotDataExecutor

    async def _fake_runtime(**kwargs):
        raise ValueError("Timeout no LLM")

    monkeypatch.setattr(
        "app.services.internal_copilot_data_executor.try_handle_semantic_autonomy",
        _fake_runtime,
    )

    decision = _build_decision(
        rota_primaria="analytics",
        subagente_primario="analytics_specialist",
        subagentes_secundarios=[],
        tipo_resposta_esperada="relatorio_executivo",
        objetivo_ativo="Gerar relatorio com erro",
    )
    run_result = LogicalAgentRunner.run(mensagem="teste com erro", decision=decision)

    result = await InternalCopilotDataExecutor.execute(
        agent_run=run_result,
        db=None,
        current_user=SimpleNamespace(id=6, empresa_id=60, is_superadmin=True, is_gestor=True),
        sessao_id="sess-err",
        request_id="req-err",
    )

    assert result.executed is False
    assert result.artifact_patch is None
    assert result.skip_reason == "semantic_runtime_unavailable"

