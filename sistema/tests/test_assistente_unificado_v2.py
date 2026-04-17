"""Testes do loop assistente_unificado_v2 (Tool Use)."""
from __future__ import annotations

import asyncio
import json
import sys
import types
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

if "litellm" not in sys.modules:
    litellm_stub = types.ModuleType("litellm")

    async def _acompletion(*args, **kwargs):
        raise RuntimeError("litellm stub: acompletion não deve ser chamado diretamente neste teste")

    def _completion(*args, **kwargs):
        raise RuntimeError("litellm stub: completion não deve ser chamado diretamente neste teste")

    litellm_stub.acompletion = _acompletion
    litellm_stub.completion = _completion
    sys.modules["litellm"] = litellm_stub

from app.services import cotte_ai_hub, ia_service as ia_service_module
from app.services import assistant_engine_registry
from app.services.ai_tools import REGISTRY
from app.services.ai_tools._base import ToolSpec
from app.services.cotte_context_builder import SessionStore
from app.models.models import (
    AIChatMensagem,
    AIChatSessao,
    ContaFinanceira,
    MovimentacaoCaixa,
    OrigemRegistro,
    StatusConta,
    StatusOrcamento,
    TipoConta,
)
from pydantic import BaseModel, Field
from tests.conftest import make_empresa, make_usuario
from tests.conftest import make_cliente, make_orcamento


# ── Mock tool de leitura ──────────────────────────────────────────────────
class _EchoInput(BaseModel):
    txt: str = Field(min_length=1)


async def _echo_handler(inp: _EchoInput, *, db, current_user):
    return {"echo": inp.txt}


_ECHO = ToolSpec(
    name="mock_echo",
    description="echo",
    input_model=_EchoInput,
    handler=_echo_handler,
    destrutiva=False,
    permissao_recurso="ia",
    permissao_acao="leitura",
)


@pytest.fixture(autouse=True)
def _register_echo():
    REGISTRY["mock_echo"] = _ECHO
    yield
    REGISTRY.pop("mock_echo", None)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _run_stream(coro):
    async def _collect():
        items = []
        async for item in coro:
            items.append(item)
        return items
    return asyncio.get_event_loop().run_until_complete(_collect())


def _allow_mock_tools(monkeypatch, *tool_names: str):
    policy = assistant_engine_registry.ENGINE_POLICIES[assistant_engine_registry.ENGINE_OPERATIONAL]
    updated = replace(
        policy,
        allowed_tools=tuple(dict.fromkeys(policy.allowed_tools + tuple(tool_names))),
    )
    monkeypatch.setitem(
        assistant_engine_registry.ENGINE_POLICIES,
        assistant_engine_registry.ENGINE_OPERATIONAL,
        updated,
    )


def _fake_response(*, content=None, tool_calls=None, finish="stop"):
    return {
        "choices": [
            {
                "finish_reason": finish,
                "message": {"content": content or "", "tool_calls": tool_calls},
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _fake_tool_call(call_id, name, args):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def test_loop_resposta_direta(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(messages, tools=None, **kw):
        return _fake_response(content="Olá!", finish="stop")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="oi", sessao_id="sess-1", db=db, current_user=user
        )
    )
    assert out.sucesso is True
    assert "Olá" in (out.resposta or "")
    # histórico foi gravado
    hist = SessionStore.get_or_create("sess-1")
    assert any(m["role"] == "assistant" for m in hist)


def test_loop_com_tool_call_e_resposta_final(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    calls = {"n": 0}

    async def fake_chat(messages, tools=None, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _fake_response(
                tool_calls=[_fake_tool_call("c1", "mock_echo", {"txt": "ping"})],
                finish="tool_calls",
            )
        return _fake_response(content="resultado: ping", finish="stop")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
    _allow_mock_tools(monkeypatch, "mock_echo")

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="ecoa ping", sessao_id="sess-2", db=db, current_user=user
        )
    )
    assert out.sucesso is True
    assert calls["n"] == 2
    assert out.tool_trace and out.tool_trace[0]["tool"] == "mock_echo"
    assert out.tool_trace[0]["status"] == "ok"


def test_session_store_append_db_cria_sessao_ausente(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    sessao_id = "sess-append-db-cria"

    assert (
        db.query(AIChatSessao)
        .filter(AIChatSessao.id == sessao_id, AIChatSessao.empresa_id == emp.id)
        .first()
        is None
    )

    SessionStore.append_db(
        sessao_id=sessao_id,
        role="user",
        content="mensagem de teste",
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    sessao = (
        db.query(AIChatSessao)
        .filter(AIChatSessao.id == sessao_id, AIChatSessao.empresa_id == emp.id)
        .first()
    )
    assert sessao is not None
    msg = (
        db.query(AIChatMensagem)
        .filter(AIChatMensagem.sessao_id == sessao_id)
        .first()
    )
    assert msg is not None
    assert msg.role == "user"


def test_loop_pending_action_interrompe(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    # Mock destrutivo
    class _WInput(BaseModel):
        x: str

    async def _wh(inp, *, db, current_user):
        return {"ok": True}

    REGISTRY["mock_destr"] = ToolSpec(
        name="mock_destr",
        description="destrutivo",
        input_model=_WInput,
        handler=_wh,
        destrutiva=True,
        permissao_recurso="ia",
        permissao_acao="leitura",
    )

    try:
        async def fake_chat(messages, tools=None, **kw):
            return _fake_response(
                tool_calls=[_fake_tool_call("c1", "mock_destr", {"x": "a"})],
                finish="tool_calls",
            )

        monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
        _allow_mock_tools(monkeypatch, "mock_destr")

        out = _run(
            cotte_ai_hub.assistente_unificado_v2(
                mensagem="faz aí", sessao_id="sess-3", db=db, current_user=user
            )
        )
        assert out.pending_action is not None
        assert out.pending_action.get("tool") == "mock_destr"
        assert out.pending_action.get("confirmation_token")
        assert out.dados is not None
        assert out.dados.get("x") == "a"
        assert "input_tokens" in out.dados and "output_tokens" in out.dados
    finally:
        REGISTRY.pop("mock_destr", None)


def test_loop_limite_iteracoes(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    calls = {"n": 0}

    async def fake_chat(messages, tools=None, **kw):
        calls["n"] += 1
        # Sempre devolve uma nova tool_call → loop deve estourar em 5
        return _fake_response(
            tool_calls=[_fake_tool_call(f"c{calls['n']}", "mock_echo", {"txt": "x"})],
            finish="tool_calls",
        )

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="loop", sessao_id="sess-4", db=db, current_user=user
        )
    )
    assert calls["n"] == 5
    assert "Limite" in (out.resposta or "")


def test_stream_evento_final_exige_final_text(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(messages, tools=None, **kw):
        return _fake_response(content="Resumo final do orçamento.", finish="stop")

    async def fake_chat_stream(messages, **kw):
        yield "Resumo "
        yield "final."

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
    monkeypatch.setattr(ia_service_module.ia_service, "chat_stream", fake_chat_stream)

    events_raw = _run_stream(
        cotte_ai_hub.assistente_v2_stream_core(
            mensagem="teste de resposta",
            sessao_id="sess-stream-final-text",
            db=db,
            current_user=user,
        )
    )

    decoded = []
    for evt in events_raw:
        if not evt.startswith("data: "):
            continue
        payload = evt[len("data: "):].strip()
        if payload:
            decoded.append(json.loads(payload))

    final_events = [e for e in decoded if e.get("is_final") is True]
    assert final_events, "Deve existir ao menos um evento final no SSE"
    for evt in final_events:
        assert isinstance(evt.get("final_text"), str)
        assert evt["final_text"].strip() != ""
        metadata = evt.get("metadata") or {}
        assert metadata.get("final_text") == evt["final_text"]
        dados = metadata.get("dados") or {}
        semantic = dados.get("semantic_contract") or {}
        assert semantic.get("summary") == evt["final_text"]
        assert "table" in semantic


def test_v2_excel_chart_capability_fallback_sem_llm(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM não deve ser chamado no fallback de capability Excel")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="Crie uma planilha Excel com gráfico do meu financeiro",
            sessao_id="sess-capability-excel",
            db=db,
            current_user=user,
        )
    )
    assert out.sucesso is True
    assert "não gero arquivo Excel" in (out.resposta or "")
    assert (out.dados or {}).get("capability") == "excel_nao_suportado"


def test_v2_onboarding_bootstrap_fastpath_sem_llm(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM não deve ser chamado no fast-path de onboarding")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="começar",
            sessao_id="sess-onboarding-fastpath",
            db=db,
            current_user=user,
        )
    )
    assert out.sucesso is True
    assert out.tipo_resposta == "onboarding"
    assert out.modulo_origem == "onboarding"
    assert isinstance((out.dados or {}).get("checklist"), list)
    assert (out.dados or {}).get("concluido") is False


def test_v2_saldo_rapido_fastpath_sem_llm(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM do V2 não deve ser chamado no fast-path de saldo")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="qual o saldo do caixa?",
            sessao_id="sess-saldo-fastpath",
            db=db,
            current_user=user,
        )
    )
    assert out.sucesso is True
    assert out.tipo_resposta == "saldo_caixa"
    assert out.modulo_origem == "financeiro_saldo"
    assert (out.dados or {}).get("saldo_atual") is not None


def test_v2_orcamento_fastpath_sem_prompt_completo(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM do V2 não deve ser chamado no fast-path de orçamento")

    async def fake_criar_orcamento_ia(*args, **kwargs):
        return cotte_ai_hub.AIResponse(
            sucesso=True,
            resposta="Revise o orçamento abaixo e confirme.",
            tipo_resposta="orcamento_preview",
            dados={"cliente_nome": "Ana Julia", "valor": 32.58, "servico": "um bolinho"},
            confianca=0.95,
            modulo_origem="criar_orcamento",
        )

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
    monkeypatch.setattr(cotte_ai_hub, "criar_orcamento_ia", fake_criar_orcamento_ia)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="orçamento para ana julia de um bolinho por 32,58",
            sessao_id="sess-orc-fastpath",
            db=db,
            current_user=user,
        )
    )
    assert out.sucesso is True
    assert out.tipo_resposta == "orcamento_preview"
    assert (out.dados or {}).get("cliente_nome") == "Ana Julia"


def test_v2_ranking_clientes_capability_fallback_sem_llm(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM não deve ser chamado no fallback de ranking de clientes")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem=(
                "Monte um ranking dos 10 clientes com maior faturamento no mês atual, "
                "com ticket médio e variação vs mês anterior."
            ),
            sessao_id="sess-capability-ranking-clientes",
            db=db,
            current_user=user,
        )
    )
    assert out.sucesso is True
    assert "Atualmente, não há uma ferramenta disponível" in (out.resposta or "")
    assert "ticket médio e a variação em relação ao mês anterior manualmente" in (out.resposta or "")
    assert (out.dados or {}).get("capability") == "ranking_clientes_indisponivel"


def test_stream_grafico_financeiro_retorna_metadata_grafico(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    db.add(
        MovimentacaoCaixa(
            empresa_id=emp.id,
            tipo="entrada",
            valor=Decimal("150.00"),
            descricao="Recebimento teste",
            categoria="teste",
            data=date.today(),
            confirmado=True,
            criado_por_id=user.id,
        )
    )
    db.add(
        MovimentacaoCaixa(
            empresa_id=emp.id,
            tipo="saida",
            valor=Decimal("60.00"),
            descricao="Despesa teste",
            categoria="teste",
            data=date.today(),
            confirmado=True,
            criado_por_id=user.id,
        )
    )
    db.commit()

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM não deve ser chamado no fast-path de gráfico financeiro")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    events_raw = _run_stream(
        cotte_ai_hub.assistente_v2_stream_core(
            mensagem="Gere um gráfico do meu financeiro dos últimos 7 dias",
            sessao_id="sess-chart-fastpath",
            db=db,
            current_user=user,
        )
    )
    decoded = []
    for evt in events_raw:
        if not evt.startswith("data: "):
            continue
        payload = evt[len("data: "):].strip()
        if payload:
            decoded.append(json.loads(payload))

    final_evt = next((e for e in decoded if e.get("is_final") is True), None)
    assert final_evt is not None
    metadata = final_evt.get("metadata") or {}
    assert metadata.get("tipo") == "financeiro"
    assert metadata.get("grafico") is not None
    assert (metadata.get("grafico") or {}).get("dados")
    semantic = (metadata.get("dados") or {}).get("semantic_contract") or {}
    assert semantic.get("summary")
    assert isinstance(semantic.get("table"), list)
    assert isinstance((semantic.get("chart") or {}).get("datasets", []), list)
    tools = metadata.get("tool_trace") or []
    tool_names = [t.get("tool") for t in tools]
    assert "listar_movimentacoes_financeiras" in tool_names
    assert "obter_saldo_caixa" in tool_names


def test_stream_onboarding_bootstrap_fastpath_sem_llm(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM não deve ser chamado no SSE de onboarding")

    async def fake_chat_stream(*args, **kwargs):
        raise AssertionError("chat_stream não deve ser chamado no SSE de onboarding")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
    monkeypatch.setattr(ia_service_module.ia_service, "chat_stream", fake_chat_stream)

    events_raw = _run_stream(
        cotte_ai_hub.assistente_v2_stream_core(
            mensagem="começar",
            sessao_id="sess-stream-onboarding-fastpath",
            db=db,
            current_user=user,
        )
    )
    decoded = []
    for evt in events_raw:
        if not evt.startswith("data: "):
            continue
        payload = evt[len("data: "):].strip()
        if payload:
            decoded.append(json.loads(payload))

    final_evt = next((e for e in decoded if e.get("is_final") is True), None)
    assert final_evt is not None
    metadata = final_evt.get("metadata") or {}
    assert metadata.get("tipo") == "onboarding"
    assert metadata.get("input_tokens") == 0
    assert metadata.get("output_tokens") == 0
    dados = metadata.get("dados") or {}
    assert isinstance(dados.get("checklist"), list)
    assert dados.get("concluido") is False
    assert "semantic_contract" not in dados


def test_stream_saldo_rapido_fastpath_sem_llm(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM do V2 não deve ser chamado no SSE de saldo")

    async def fake_chat_stream(*args, **kwargs):
        raise AssertionError("chat_stream não deve ser chamado no SSE de saldo")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
    monkeypatch.setattr(ia_service_module.ia_service, "chat_stream", fake_chat_stream)

    events_raw = _run_stream(
        cotte_ai_hub.assistente_v2_stream_core(
            mensagem="qual o saldo do caixa?",
            sessao_id="sess-stream-saldo-fastpath",
            db=db,
            current_user=user,
        )
    )
    decoded = []
    for evt in events_raw:
        if not evt.startswith("data: "):
            continue
        payload = evt[len("data: "):].strip()
        if payload:
            decoded.append(json.loads(payload))

    final_evt = next((e for e in decoded if e.get("is_final") is True), None)
    assert final_evt is not None
    metadata = final_evt.get("metadata") or {}
    assert metadata.get("tipo") == "saldo_caixa"
    assert metadata.get("input_tokens") == 0
    assert metadata.get("output_tokens") == 0
    dados = metadata.get("dados") or {}
    assert dados.get("saldo_atual") is not None
    assert "semantic_contract" not in dados


def test_stream_orcamento_fastpath_sem_prompt_completo(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    async def fake_chat(*args, **kwargs):
        raise AssertionError("LLM do V2 não deve ser chamado no SSE de orçamento")

    async def fake_chat_stream(*args, **kwargs):
        raise AssertionError("chat_stream não deve ser chamado no SSE de orçamento")

    async def fake_criar_orcamento_ia(*args, **kwargs):
        return cotte_ai_hub.AIResponse(
            sucesso=True,
            resposta="Revise o orçamento abaixo e confirme.",
            tipo_resposta="orcamento_preview",
            dados={"cliente_nome": "Ana Julia", "valor": 32.58, "servico": "um bolinho"},
            confianca=0.95,
            modulo_origem="criar_orcamento",
        )

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)
    monkeypatch.setattr(ia_service_module.ia_service, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(cotte_ai_hub, "criar_orcamento_ia", fake_criar_orcamento_ia)

    events_raw = _run_stream(
        cotte_ai_hub.assistente_v2_stream_core(
            mensagem="orçamento para ana julia de um bolinho por 32,58",
            sessao_id="sess-stream-orc-fastpath",
            db=db,
            current_user=user,
        )
    )
    decoded = []
    for evt in events_raw:
        if not evt.startswith("data: "):
            continue
        payload = evt[len("data: "):].strip()
        if payload:
            decoded.append(json.loads(payload))

    final_evt = next((e for e in decoded if e.get("is_final") is True), None)
    assert final_evt is not None
    metadata = final_evt.get("metadata") or {}
    assert metadata.get("tipo") == "orcamento_preview"
    assert metadata.get("input_tokens") == 0
    assert metadata.get("output_tokens") == 0
    dados = metadata.get("dados") or {}
    assert dados.get("cliente_nome") == "Ana Julia"
    assert "semantic_contract" not in dados


def test_v2_pending_recusar_orcamento_expoe_impacto_financeiro(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Cliente Recusa")
    orc = make_orcamento(db, emp, cli, user, status=StatusOrcamento.APROVADO, total=500)

    db.add(
        ContaFinanceira(
            empresa_id=emp.id,
            orcamento_id=orc.id,
            tipo=TipoConta.RECEBER,
            descricao=f"Receber {orc.numero}",
            valor=Decimal("500.00"),
            valor_pago=Decimal("0.00"),
            status=StatusConta.PENDENTE,
            origem=OrigemRegistro.SISTEMA,
        )
    )
    db.commit()

    async def fake_chat(messages, tools=None, **kw):
        return _fake_response(
            tool_calls=[
                _fake_tool_call("c1", "recusar_orcamento", {"orcamento_id": orc.id})
            ],
            finish="tool_calls",
        )

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem=f"Recusar orçamento {orc.id}",
            sessao_id="sess-recusa-impacto",
            db=db,
            current_user=user,
        )
    )

    assert out.pending_action is not None
    assert out.pending_action.get("tool") == "recusar_orcamento"
    impacto = (out.dados or {}).get("impacto_financeiro") or {}
    assert impacto.get("contas_pendentes_removidas", 0) >= 1


def test_v2_injeta_memoria_semantica_empresa_no_prompt(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    sessao_hist = AIChatSessao(id="sess-hist-mem", empresa_id=emp.id, usuario_id=user.id)
    db.add(sessao_hist)
    db.flush()
    db.add(
        AIChatMensagem(
            sessao_id=sessao_hist.id,
            role="user",
            content="Qual meu padrão de fluxo de caixa nos últimos meses?",
        )
    )
    db.commit()

    captured = {"messages": None}

    async def fake_chat(messages, tools=None, **kw):
        captured["messages"] = messages
        return _fake_response(content="Resumo com memória", finish="stop")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="Qual meu padrão de fluxo de caixa?",
            sessao_id="sess-memoria-v2",
            db=db,
            current_user=user,
        )
    )
    assert out.sucesso is True
    msgs = captured["messages"] or []
    system_blobs = [m.get("content", "") for m in msgs if m.get("role") == "system"]
    merged = "\n".join(system_blobs)
    assert "Memória semântica da empresa" in merged
    assert "padrão de fluxo de caixa" in merged
    assert "Preferências adaptativas da empresa/usuário" in merged
    assert "perfil_operacional_dinamico" in merged
    assert "\"90d\"" in merged
    assert "prioridade_kpis" in merged


def test_v2_prompt_minimal_nao_inclui_kb_em_conversa_simples(db, monkeypatch):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    captured = {"messages": None, "tools_count": None}

    async def fake_chat(messages, tools=None, **kw):
        captured["messages"] = messages
        captured["tools_count"] = len(tools or [])
        return _fake_response(content="Olá!", finish="stop")

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = _run(
        cotte_ai_hub.assistente_unificado_v2(
            mensagem="oi tudo bem?",
            sessao_id="sess-minimal-prompt",
            db=db,
            current_user=user,
        )
    )

    assert out.sucesso is True
    assert (out.dados or {}).get("prompt_strategy") == "minimal"
    msgs = captured["messages"] or []
    system_blobs = [m.get("content", "") for m in msgs if m.get("role") == "system"]
    merged = "\n".join(system_blobs)
    assert "Manual funcional do sistema" not in merged
    assert captured["tools_count"] == 0


def test_v2_history_window_conversa_curta_minimal():
    size = cotte_ai_hub._v2_history_window_size(
        prompt_strategy="minimal",
        mensagem="oi tudo bem",
    )
    assert size == 1


def test_v2_tool_selection_profile_conversa_curta():
    selected, full, reduced, profile = cotte_ai_hub._v2_select_tools_payload(
        mensagem="oi",
        prompt_strategy="minimal",
        resolved_engine=assistant_engine_registry.ENGINE_OPERATIONAL,
    )
    assert selected == []
    assert len(full) >= 1
    assert reduced is True
    assert profile == "minimal_conversation_no_tools"


@pytest.mark.asyncio
async def test_processar_financeiro_analise_popula_resposta(db, monkeypatch):
    """JSON da IA vem em dados (resumo); resposta textual deve ser preenchida para SSE/UI."""
    payload = {
        "tipo_analise": "inadimplencia",
        "resumo": "Três clientes com valores em atraso.",
        "insights": ["Cliente A em atraso", "Cliente B em atraso"],
        "recomendacoes": ["Cobrar por WhatsApp"],
        "confianca": 0.9,
    }

    async def fake_chat(messages, **kw):
        return {
            "choices": [
                {"message": {"content": json.dumps(payload, ensure_ascii=False)}}
            ]
        }

    monkeypatch.setattr(ia_service_module.ia_service, "chat", fake_chat)

    out = await cotte_ai_hub.ai_hub.processar(
        "financeiro_analise",
        "Quem está devendo?",
        contexto={"empresa_id": 1},
        db=None,
        usar_cache=False,
    )
    assert out.sucesso is True
    assert out.resposta
    assert "Três clientes" in out.resposta


def test_derive_display_text_fallback_dados_financeiro_analise():
    """Fastpath SSE: se resposta top-level vazia, deriva de dados estruturados."""
    from app.services.cotte_ai_hub import AIResponse, _derive_ai_response_display_text

    r = AIResponse(
        sucesso=True,
        resposta=None,
        dados={"resumo": "Lista de inadimplentes atualizada.", "confianca": 0.9},
        confianca=0.9,
        modulo_origem="financeiro_analise",
    )
    text = _derive_ai_response_display_text(r)
    assert text
    assert "inadimplentes" in text


def test_texto_exibicao_inadimplencia_campos_ia():
    """IA retorna cliente/valor_devido/data_vencimento sem resumo (caso real do assistente)."""
    from app.services.cotte_ai_hub import _texto_exibicao_para_modulo

    dados = {
        "cliente": "O-99",
        "valor_devido": 7.5,
        "data_vencimento": "2026-04-05",
        "confianca": 0.5,
    }
    txt = _texto_exibicao_para_modulo("financeiro_analise", dados)
    assert "O-99" in txt
    assert "7,50" in txt or "7.50" in txt
    assert "2026-04-05" in txt
    assert "Análise financeira concluída" not in txt


def test_texto_exibicao_inadimplencia_lista():
    from app.services.cotte_ai_hub import _texto_exibicao_para_modulo

    dados = {
        "clientes": [
            {"cliente": "A", "valor_devido": 10.0, "data_vencimento": "2026-03-01"},
            {"cliente": "B", "valor_devido": 20.0},
        ],
        "confianca": 0.8,
    }
    txt = _texto_exibicao_para_modulo("financeiro_analise", dados)
    assert "A" in txt and "B" in txt
    assert "Análise financeira concluída" not in txt


def test_intencao_orcamentos_pendentes_nao_dispara_inadimplencia():
    """'Pendente' em orçamentos é pipeline; não deve ser INADIMPLENCIA (fastpath clientes_devendo)."""
    from app.services.ai_intention_classifier import detectar_intencao_assistente

    assert detectar_intencao_assistente("Quais orçamentos pendentes?") != "INADIMPLENCIA"
    assert detectar_intencao_assistente("Quem está devendo?") == "INADIMPLENCIA"
