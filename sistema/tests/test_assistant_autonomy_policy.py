from types import SimpleNamespace

from app.services.assistant_autonomy.policy_engine import evaluate_policy
from app.services.assistant_autonomy.semantic_planner import build_semantic_plan


def test_policy_denies_without_tenant(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_engine_available_for_user",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_sql_agent_enabled",
        lambda: True,
    )
    user = SimpleNamespace(empresa_id=None, is_superadmin=False, is_gestor=False)
    plan = build_semantic_plan("quero relatório de vendas")
    out = evaluate_policy(plan=plan, current_user=user, engine="analytics")
    assert out.allowed is False
    assert any("escopo de empresa" in reason.lower() for reason in out.reasons)


def test_policy_allows_analytics_with_flags(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_engine_available_for_user",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_sql_agent_enabled",
        lambda: True,
    )
    user = SimpleNamespace(empresa_id=1, is_superadmin=False, is_gestor=True)
    plan = build_semantic_plan("quero relatório financeiro")
    out = evaluate_policy(plan=plan, current_user=user, engine="analytics")
    assert out.allowed is True
    assert out.governance_mode == "read_only"
    assert "pdf" in out.allowed_export_formats


def test_policy_denies_printable_document_in_operational_engine(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_engine_available_for_user",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_sql_agent_enabled",
        lambda: True,
    )
    user = SimpleNamespace(empresa_id=1, is_superadmin=False, is_gestor=True)
    plan = build_semantic_plan("quero relatório para imprimir com vendas do mês")
    out = evaluate_policy(plan=plan, current_user=user, engine="operational")
    assert out.allowed is False
    assert any("analytics" in reason.lower() for reason in out.reasons)


def test_policy_marks_transacional_capability_with_confirmation(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_engine_available_for_user",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "app.services.assistant_autonomy.policy_engine.is_sql_agent_enabled",
        lambda: True,
    )
    user = SimpleNamespace(empresa_id=1, is_superadmin=False, is_gestor=True)
    plan = build_semantic_plan("Crie um orçamento para cliente Maria e envie por WhatsApp")
    out = evaluate_policy(plan=plan, current_user=user, engine="operational")
    assert out.allowed is True
    assert out.requires_confirmation is True
    assert out.risk_level == "high"
