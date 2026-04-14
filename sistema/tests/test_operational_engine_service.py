from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import operational_engine_service as svc


@pytest.mark.asyncio
async def test_fluxo_orcamento_success_expoe_flow_id_trace_metrics(monkeypatch):
    calls: list[str] = []
    audit_payload: dict = {}

    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        calls.append(name)
        if name == "obter_orcamento":
            return SimpleNamespace(status="ok", data={"id": 10}, error=None, pending_action=None)
        if name == "enviar_orcamento_email":
            return SimpleNamespace(status="ok", data={"canal": "email"}, error=None, pending_action=None)
        raise AssertionError(f"tool inesperada: {name}")

    def fake_pdf(*args, **kwargs):
        return {"ok": True, "pdf_bytes_len": 123, "orcamento_id": 10, "numero": "ORC-10"}

    def fake_audit(*args, **kwargs):
        audit_payload.update(kwargs.get("detalhes") or {})

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(svc, "_gerar_pdf_orcamento_runtime", fake_pdf)
    monkeypatch.setattr(svc, "registrar_auditoria", fake_audit)

    user = SimpleNamespace(id=99, empresa_id=7)
    out = await svc.run_orcamento_operational_flow(
        db=None,
        current_user=user,
        request_id="req-1",
        sessao_id="sess-1",
        cliente_id=None,
        cliente_nome=None,
        itens=[],
        observacoes=None,
        cadastrar_materiais_novos=False,
        orcamento_id=10,
        canal_envio="email",
        confirmation_token=None,
    )

    assert out["success"] is True
    assert out.get("flow_id")
    assert out["data"]["registro"]["flow_id"] == out["flow_id"]
    assert audit_payload.get("flow_id") == out["flow_id"]
    assert out["metrics"]["total_steps"] == 4
    assert calls == ["obter_orcamento", "enviar_orcamento_email"]
    for step in out["trace"]:
        assert "duration_ms" in step
        assert "executado_em_utc" in step


@pytest.mark.asyncio
async def test_fluxo_orcamento_pending_montagem_expoe_step_e_metrics(monkeypatch):
    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        if name != "criar_orcamento":
            raise AssertionError(f"tool inesperada: {name}")
        return SimpleNamespace(
            status="pending",
            data=None,
            error=None,
            pending_action={"tool": "criar_orcamento", "confirmation_token": "tok-1"},
        )

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)

    user = SimpleNamespace(id=100, empresa_id=8)
    out = await svc.run_orcamento_operational_flow(
        db=None,
        current_user=user,
        request_id="req-2",
        sessao_id="sess-2",
        cliente_id=1,
        cliente_nome="Cliente Teste",
        itens=[{"descricao": "Servico", "quantidade": 1}],
        observacoes=None,
        cadastrar_materiais_novos=False,
        orcamento_id=None,
        canal_envio=None,
        confirmation_token=None,
    )

    assert out["success"] is False
    assert out["code"] == "pending_confirmation"
    assert out.get("flow_id")
    assert out["pending_action"]["flow_step"] == "montar_orcamento"
    assert out["pending_action"]["confirmation_required"] is True
    assert out["metrics"]["steps_pending"] == 1
    assert out["metrics"]["total_steps"] == 1


@pytest.mark.asyncio
async def test_fluxo_financeiro_success_expoe_flow_e_metrics(monkeypatch):
    calls: list[str] = []
    audit_payload: dict = {}

    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        calls.append(name)
        if name == "obter_saldo_caixa":
            return SimpleNamespace(status="ok", data={"saldo_atual": 1500.0}, error=None, pending_action=None)
        if name == "criar_movimentacao_financeira":
            return SimpleNamespace(status="ok", data={"id": 88, "criado": True}, error=None, pending_action=None)
        raise AssertionError(f"tool inesperada: {name}")

    def fake_audit(*args, **kwargs):
        audit_payload.update(kwargs.get("detalhes") or {})

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(svc, "registrar_auditoria", fake_audit)

    user = SimpleNamespace(id=111, empresa_id=9)
    out = await svc.run_financeiro_operational_flow(
        db=None,
        current_user=user,
        request_id="req-fin-1",
        sessao_id="sess-fin-1",
        tipo="entrada",
        valor=250.0,
        descricao="Recebimento avulso",
        categoria="servicos",
        data=None,
        confirmation_token=None,
    )

    assert out["success"] is True
    assert out.get("flow_id")
    assert out["data"]["registro"]["flow_id"] == out["flow_id"]
    assert audit_payload.get("flow_id") == out["flow_id"]
    assert calls == ["obter_saldo_caixa", "criar_movimentacao_financeira"]
    assert out["metrics"]["total_steps"] == 3
    assert out["metrics"]["steps_with_error"] == 0


@pytest.mark.asyncio
async def test_fluxo_financeiro_pending_expoe_flow_step(monkeypatch):
    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        if name == "obter_saldo_caixa":
            return SimpleNamespace(status="ok", data={"saldo_atual": 100.0}, error=None, pending_action=None)
        if name == "criar_movimentacao_financeira":
            return SimpleNamespace(
                status="pending",
                data=None,
                error=None,
                pending_action={"tool": "criar_movimentacao_financeira", "confirmation_token": "tok-fin"},
            )
        raise AssertionError(f"tool inesperada: {name}")

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)

    user = SimpleNamespace(id=222, empresa_id=10)
    out = await svc.run_financeiro_operational_flow(
        db=None,
        current_user=user,
        request_id="req-fin-2",
        sessao_id="sess-fin-2",
        tipo="saida",
        valor=30.0,
        descricao="Compra de material",
        categoria="insumos",
        data=None,
        confirmation_token=None,
    )

    assert out["success"] is False
    assert out["code"] == "pending_confirmation"
    assert out.get("flow_id")
    assert out["pending_action"]["flow_step"] == "executar_acao_financeira"
    assert out["pending_action"]["confirmation_required"] is True
    assert out["metrics"]["steps_pending"] == 1


@pytest.mark.asyncio
async def test_fluxo_agendamento_success_expoe_flow_e_metrics(monkeypatch):
    calls: list[str] = []
    audit_payload: dict = {}

    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        calls.append(name)
        if name == "listar_agendamentos":
            return SimpleNamespace(status="ok", data={"total": 3}, error=None, pending_action=None)
        if name == "criar_agendamento":
            return SimpleNamespace(status="ok", data={"id": 501, "criado": True}, error=None, pending_action=None)
        raise AssertionError(f"tool inesperada: {name}")

    def fake_audit(*args, **kwargs):
        audit_payload.update(kwargs.get("detalhes") or {})

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(svc, "registrar_auditoria", fake_audit)

    user = SimpleNamespace(id=333, empresa_id=11)
    out = await svc.run_agendamento_operational_flow(
        db=None,
        current_user=user,
        request_id="req-ag-1",
        sessao_id="sess-ag-1",
        acao="criar",
        cliente_id=22,
        data_agendada="2026-04-20T10:00:00",
        duracao_estimada_min=60,
        tipo="servico",
        orcamento_id=None,
        endereco=None,
        observacoes=None,
        agendamento_id=None,
        nova_data=None,
        motivo=None,
        confirmation_token=None,
    )

    assert out["success"] is True
    assert out.get("flow_id")
    assert out["data"]["registro"]["flow_id"] == out["flow_id"]
    assert audit_payload.get("flow_id") == out["flow_id"]
    assert calls == ["listar_agendamentos", "criar_agendamento"]
    assert out["metrics"]["total_steps"] == 3


@pytest.mark.asyncio
async def test_fluxo_agendamento_pending_expoe_flow_step(monkeypatch):
    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        if name == "listar_agendamentos":
            return SimpleNamespace(status="ok", data={"total": 1}, error=None, pending_action=None)
        if name == "remarcar_agendamento":
            return SimpleNamespace(
                status="pending",
                data=None,
                error=None,
                pending_action={"tool": "remarcar_agendamento", "confirmation_token": "tok-ag"},
            )
        raise AssertionError(f"tool inesperada: {name}")

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)

    user = SimpleNamespace(id=444, empresa_id=12)
    out = await svc.run_agendamento_operational_flow(
        db=None,
        current_user=user,
        request_id="req-ag-2",
        sessao_id="sess-ag-2",
        acao="remarcar",
        cliente_id=None,
        data_agendada=None,
        duracao_estimada_min=None,
        tipo=None,
        orcamento_id=None,
        endereco=None,
        observacoes=None,
        agendamento_id=900,
        nova_data="2026-04-21T11:30:00",
        motivo="Ajuste de agenda",
        confirmation_token=None,
    )

    assert out["success"] is False
    assert out["code"] == "pending_confirmation"
    assert out.get("flow_id")
    assert out["pending_action"]["flow_step"] == "executar_acao_agenda"
    assert out["pending_action"]["confirmation_required"] is True
    assert out["metrics"]["steps_pending"] == 1
