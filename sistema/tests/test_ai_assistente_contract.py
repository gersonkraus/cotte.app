from __future__ import annotations

import asyncio
import base64
import json

import pytest

from app.core.config import settings
from app.core.auth import criar_token
from app.models.models import (
    AIChatMensagem,
    AIChatSessao,
    CommercialLead,
    DocumentoEmpresa,
)
from app.routers import ai_hub as ai_hub_router
from app.services import cotte_ai_hub
from app.services.cotte_ai_hub import AIResponse, SimpleCache, ai_hub
from app.services.cotte_context_builder import ContextBuilder, SessionStore
from app.services.rag import TenantRAGService
from tests.conftest import make_empresa, make_usuario


def _headers_for(user_id: int, token_version: int = 0) -> dict[str, str]:
    token = criar_token({"sub": str(user_id), "v": token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_assistente_sync_contract(client, admin_token, monkeypatch):
    captured: dict = {}

    async def fake_v2(**kwargs):
        captured.update(kwargs)
        return AIResponse(
            sucesso=True,
            resposta="ok",
            tipo_resposta="orcamento_preview",
            confianca=0.95,
            modulo_origem="assistente_v2",
            dados={"input_tokens": 1, "output_tokens": 1},
            pending_action={"tool": "recusar_orcamento", "confirmation_token": "tok"},
            tool_trace=[{"tool": "recusar_orcamento", "status": "pending"}],
        )

    monkeypatch.setattr(cotte_ai_hub, "assistente_unificado_v2", fake_v2)
    resp = await client.post(
        "/api/v1/ai/assistente",
        json={"mensagem": "recusar orçamento 1", "sessao_id": "sess-contract-1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sucesso"] is True
    assert "pending_action" in data and data["pending_action"]["confirmation_token"]
    assert isinstance(data.get("tool_trace"), list)
    assert captured.get("engine") == "operational"


@pytest.mark.asyncio
async def test_assistente_stream_contract(client, admin_token, monkeypatch):
    async def fake_stream(**kwargs):
        yield 'data: {"phase":"thinking"}\n\n'
        yield (
            'data: {"is_final":true,"final_text":"Feito","metadata":{"tipo":"geral",'
            '"dados":{"ok":true},"pending_action":{"tool":"x","confirmation_token":"abc"},'
            '"tool_trace":[{"tool":"x","status":"pending"}]}}\n\n'
        )

    monkeypatch.setattr(cotte_ai_hub, "assistente_unificado_stream", fake_stream)
    resp = await client.post(
        "/api/v1/ai/assistente/stream",
        json={"mensagem": "oi", "sessao_id": "sess-contract-stream"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert '"phase":"thinking"' in body
    assert '"is_final":true' in body
    assert '"confirmation_token":"abc"' in body


@pytest.mark.asyncio
async def test_assistente_capabilities_contract(client, admin_token):
    resp = await client.get(
        "/api/v1/ai/assistente/capabilities",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert "flags" in (payload.get("data") or {})
    assert "engines" in (payload.get("data") or {})
    assert "available_engines" in (payload.get("data") or {})
    data = payload.get("data") or {}
    assert isinstance(data.get("flags"), dict)
    assert isinstance(data.get("engines"), dict)
    assert isinstance(data.get("components"), dict)
    assert isinstance(data.get("available_engines"), dict)
    for key in ("operational", "analytics", "documental", "internal_copilot"):
        assert key in data["available_engines"]
        assert isinstance(data["available_engines"][key], bool)


@pytest.mark.asyncio
async def test_ai_status_expoe_runtime_litellm(client, admin_token):
    resp = await client.get(
        "/api/v1/ai/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    versoes = payload.get("versoes_modelos") or {}
    assert versoes.get("gateway") == "litellm"
    assert versoes.get("provider") == settings.AI_PROVIDER
    assert versoes.get("conversa_configurada") == settings.AI_MODEL


@pytest.mark.asyncio
async def test_assistente_rejeita_engine_internal_no_endpoint_operacional(
    client, admin_token
):
    resp = await client.post(
        "/api/v1/ai/assistente",
        json={
            "mensagem": "teste",
            "sessao_id": "sess-internal-reject",
            "engine": "internal_copilot",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    detail = str(payload.get("detail", "")).lower()
    wrapped_message = str(
        ((payload.get("error") or {}).get("message")) or ""
    ).lower()
    assert "copiloto técnico" in (detail + " " + wrapped_message)


@pytest.mark.asyncio
async def test_assistente_stream_rejeita_engine_internal_no_endpoint_operacional(
    client, admin_token
):
    resp = await client.post(
        "/api/v1/ai/assistente/stream",
        json={
            "mensagem": "teste",
            "sessao_id": "sess-internal-reject-stream",
            "engine": "internal_copilot",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    detail = str(payload.get("detail", "")).lower()
    wrapped_message = str(
        ((payload.get("error") or {}).get("message")) or ""
    ).lower()
    assert "copiloto técnico" in (detail + " " + wrapped_message)


@pytest.mark.asyncio
async def test_copiloto_interno_consulta_tecnica_requires_code_rag_flag(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_INTERNAL_COPILOT", "true")
    monkeypatch.setenv("V2_CODE_RAG", "false")
    resp = await client.post(
        "/api/v1/ai/copiloto-interno/consulta-tecnica",
        json={"mensagem": "investigar erro", "sessao_id": "sess-tech-flag", "include_code_context": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_copiloto_interno_consulta_tecnica_contract(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_INTERNAL_COPILOT", "true")
    monkeypatch.setenv("V2_CODE_RAG", "true")
    monkeypatch.setenv("V2_SQL_AGENT", "true")

    async def fake_flow(**kwargs):
        return {
            "success": True,
            "flow_id": "flow-tech-1",
            "data": {"registro": {"flow_id": "flow-tech-1"}},
            "trace": [{"step": "code_rag_context", "status": "ok"}],
            "metrics": {"total_steps": 2},
        }

    monkeypatch.setattr(ai_hub_router, "run_internal_technical_flow", fake_flow)
    resp = await client.post(
        "/api/v1/ai/copiloto-interno/consulta-tecnica",
        json={
            "mensagem": "investigar erro no serviço",
            "sessao_id": "sess-tech-ok",
            "include_code_context": True,
            "sql_query": "SELECT id FROM orcamentos",
            "sql_limit": 10,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload.get("flow_id") == "flow-tech-1"


@pytest.mark.asyncio
async def test_operacional_catalogo_contract(client, admin_token):
    resp = await client.get(
        "/api/v1/ai/operacional/catalogo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert "orcamentos" in data
    assert isinstance(data["orcamentos"], list)
    all_tools = [item.get("name") for items in data.values() for item in (items or [])]
    assert "analisar_tool_logs" not in all_tools


@pytest.mark.asyncio
async def test_operacional_fluxo_valida_entrada(client, admin_token):
    resp = await client.post(
        "/api/v1/ai/operacional/fluxo-orcamento",
        json={"sessao_id": "sess-op-valida"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_operacional_fluxo_pending_confirmation_contract(client, admin_token, monkeypatch):
    async def fake_flow(**kwargs):
        return {
            "success": False,
            "code": "pending_confirmation",
            "error": "Confirmação necessária",
            "pending_action": {"tool": "enviar_orcamento_email", "confirmation_token": "tok-flow"},
            "trace": [{"step": "enviar_canal", "status": "pending"}],
        }

    monkeypatch.setattr(ai_hub_router, "run_orcamento_operational_flow", fake_flow)
    resp = await client.post(
        "/api/v1/ai/operacional/fluxo-orcamento",
        json={
            "sessao_id": "sess-op-pending",
            "orcamento_id": 1,
            "canal_envio": "email",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    payload = resp.json()
    assert payload.get("code") == "pending_confirmation"
    assert (payload.get("pending_action") or {}).get("confirmation_token") == "tok-flow"


@pytest.mark.asyncio
async def test_operacional_fluxo_financeiro_valida_entrada(client, admin_token):
    resp = await client.post(
        "/api/v1/ai/operacional/fluxo-financeiro",
        json={"sessao_id": "sess-op-fin-422", "tipo": "entrada", "valor": 0, "descricao": "x"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_operacional_fluxo_financeiro_pending_confirmation_contract(client, admin_token, monkeypatch):
    async def fake_flow(**kwargs):
        return {
            "success": False,
            "code": "pending_confirmation",
            "error": "Confirmação necessária",
            "flow_id": "flow-fin-1",
            "metrics": {"total_steps": 2, "steps_pending": 1},
            "pending_action": {"tool": "criar_movimentacao_financeira", "confirmation_token": "tok-fin"},
            "trace": [{"step": "executar_acao_financeira", "status": "pending"}],
        }

    monkeypatch.setattr(ai_hub_router, "run_financeiro_operational_flow", fake_flow)
    resp = await client.post(
        "/api/v1/ai/operacional/fluxo-financeiro",
        json={
            "sessao_id": "sess-op-fin-pending",
            "tipo": "entrada",
            "valor": 120.0,
            "descricao": "Recebimento teste",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    payload = resp.json()
    assert payload.get("flow_id") == "flow-fin-1"
    assert payload.get("code") == "pending_confirmation"
    assert (payload.get("pending_action") or {}).get("confirmation_token") == "tok-fin"


@pytest.mark.asyncio
async def test_operacional_fluxo_agendamento_valida_entrada(client, admin_token):
    resp = await client.post(
        "/api/v1/ai/operacional/fluxo-agendamento",
        json={"sessao_id": "sess-op-ag-422", "acao": "criar"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_operacional_fluxo_agendamento_pending_confirmation_contract(client, admin_token, monkeypatch):
    async def fake_flow(**kwargs):
        return {
            "success": False,
            "code": "pending_confirmation",
            "error": "Confirmação necessária",
            "flow_id": "flow-ag-1",
            "metrics": {"total_steps": 2, "steps_pending": 1},
            "pending_action": {"tool": "remarcar_agendamento", "confirmation_token": "tok-ag"},
            "trace": [{"step": "executar_acao_agenda", "status": "pending"}],
        }

    monkeypatch.setattr(ai_hub_router, "run_agendamento_operational_flow", fake_flow)
    resp = await client.post(
        "/api/v1/ai/operacional/fluxo-agendamento",
        json={
            "sessao_id": "sess-op-ag-pending",
            "acao": "remarcar",
            "agendamento_id": 123,
            "nova_data": "2026-04-25T15:00:00",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    payload = resp.json()
    assert payload.get("flow_id") == "flow-ag-1"
    assert payload.get("code") == "pending_confirmation"
    assert (payload.get("pending_action") or {}).get("confirmation_token") == "tok-ag"


@pytest.mark.asyncio
async def test_documental_catalogo_contract(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_DOCUMENT_ENGINE", "true")
    resp = await client.get(
        "/api/v1/ai/documental/catalogo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert data.get("engine") == "documental"
    assert "domains" in data


@pytest.mark.asyncio
async def test_documental_fluxo_pending_confirmation_contract(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_DOCUMENT_ENGINE", "true")

    async def fake_flow(**kwargs):
        return {
            "success": False,
            "code": "pending_confirmation",
            "error": "Confirmação necessária",
            "flow_id": "flow-doc-1",
            "metrics": {"total_steps": 3, "steps_pending": 1},
            "pending_action": {"tool": "anexar_documento_orcamento", "confirmation_token": "tok-doc"},
            "trace": [{"step": "anexar_documento_orcamento", "status": "pending"}],
        }

    monkeypatch.setattr(ai_hub_router, "run_documental_orcamento_flow", fake_flow)
    resp = await client.post(
        "/api/v1/ai/documental/fluxo-orcamento",
        json={"sessao_id": "sess-doc-pending", "orcamento_id": 10, "documento_id": 4},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    payload = resp.json()
    assert payload.get("flow_id") == "flow-doc-1"
    assert payload.get("code") == "pending_confirmation"
    assert (payload.get("pending_action") or {}).get("confirmation_token") == "tok-doc"


@pytest.mark.asyncio
async def test_analytics_catalogo_contract(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_ANALYTICS_ENGINE", "true")
    resp = await client.get(
        "/api/v1/ai/analytics/catalogo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert data.get("engine") == "analytics"
    assert "domains" in data


@pytest.mark.asyncio
async def test_analytics_fluxo_contract(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_ANALYTICS_ENGINE", "true")

    async def fake_flow(**kwargs):
        return {
            "success": True,
            "flow_id": "flow-an-1",
            "data": {"scope": "financeiro_resumo"},
            "trace": [{"step": "consultar_superficie_analitica", "status": "ok"}],
            "metrics": {"total_steps": 2},
        }

    monkeypatch.setattr(ai_hub_router, "run_analytics_flow", fake_flow)
    resp = await client.post(
        "/api/v1/ai/analytics/fluxo",
        json={"sessao_id": "sess-an-flow", "scope": "financeiro_resumo", "dias": 30, "limit": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload.get("flow_id") == "flow-an-1"


@pytest.mark.asyncio
async def test_analytics_sql_agent_requires_flag(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_ANALYTICS_ENGINE", "true")
    monkeypatch.setenv("V2_SQL_AGENT", "false")
    resp = await client.post(
        "/api/v1/ai/analytics/sql-agent",
        json={"sessao_id": "sess-sql-off", "sql": "SELECT id FROM orcamentos", "limit": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analytics_sql_agent_contract(client, admin_token, monkeypatch):
    monkeypatch.setenv("V2_ANALYTICS_ENGINE", "true")
    monkeypatch.setenv("V2_SQL_AGENT", "true")

    async def fake_flow(**kwargs):
        return {
            "success": True,
            "flow_id": "flow-sql-1",
            "data": {"resultado_sql": {"row_count": 1}},
            "trace": [{"step": "executar_sql_analitico", "status": "ok"}],
            "metrics": {"total_steps": 1},
        }

    monkeypatch.setattr(ai_hub_router, "run_analytics_sql_query_flow", fake_flow)
    resp = await client.post(
        "/api/v1/ai/analytics/sql-agent",
        json={"sessao_id": "sess-sql-on", "sql": "SELECT id FROM orcamentos", "limit": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert payload.get("flow_id") == "flow-sql-1"


@pytest.mark.asyncio
async def test_feedback_and_preferences_contract(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    pref_get = await client.get("/api/v1/ai/assistente/preferencias", headers=headers)
    assert pref_get.status_code == 200
    pref_data = pref_get.json()
    assert "instrucoes_empresa" in pref_data
    assert "preferencia_visualizacao" in pref_data
    assert "playbook_setor" in pref_data

    pref_patch = await client.patch(
        "/api/v1/ai/assistente/preferencias",
        json={"formato_preferido": "resumo", "dominio": "geral"},
        headers=headers,
    )
    assert pref_patch.status_code == 200
    assert "preferencia_visualizacao" in pref_patch.json()

    feedback = await client.post(
        "/api/v1/ai/feedback",
        json={
            "sessao_id": "sess-fb",
            "pergunta": "Como está o caixa?",
            "resposta": "Tudo certo",
            "avaliacao": "positivo",
        },
        headers=headers,
    )
    assert feedback.status_code == 201
    assert feedback.json()["ok"] is True


@pytest.mark.asyncio
async def test_assistente_prompt_library_crud_contract(client, db):
    emp = make_empresa(db, nome="Prompt CRUD")
    gestor = make_usuario(db, emp, email="prompt-crud@teste.com", is_gestor=True)
    db.commit()
    headers = _headers_for(gestor.id, token_version=getattr(gestor, "token_versao", 0) or 0)

    create_resp = await client.post(
        "/api/v1/ai/assistente/prompts",
        json={
            "titulo": "Ranking mensal de clientes",
            "conteudo_prompt": "Monte ranking de clientes por faturamento no mês atual.",
            "categoria": "ranking",
            "favorito": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    create_payload = create_resp.json()
    assert create_payload.get("success") is True
    created = create_payload.get("data") or {}
    prompt_id = int(created["id"])

    list_resp = await client.get(
        "/api/v1/ai/assistente/prompts?categoria=ranking&limit=10",
        headers=headers,
    )
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload.get("success") is True
    items = (list_payload.get("data") or {}).get("items") or []
    assert isinstance(items, list)

    assert prompt_id > 0


@pytest.mark.asyncio
async def test_assistente_prompt_library_rejects_non_manager_changes(client, db):
    emp = make_empresa(db, nome="Prompt Tenant")
    operador = make_usuario(db, emp, email="operador@teste.com", is_gestor=False)
    db.commit()
    headers = _headers_for(operador.id, token_version=getattr(operador, "token_versao", 0) or 0)

    resp = await client.post(
        "/api/v1/ai/assistente/prompts",
        json={
            "titulo": "Tentativa sem permissão",
            "conteudo_prompt": "Teste de permissão",
            "categoria": "ranking",
        },
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_assistente_prompt_library_scoped_by_empresa(client, db):
    emp1 = make_empresa(db, nome="Prompt A")
    emp2 = make_empresa(db, nome="Prompt B")
    gestor_a = make_usuario(db, emp1, email="gestor-a@teste.com", is_gestor=True)
    gestor_b = make_usuario(db, emp2, email="gestor-b@teste.com", is_gestor=True)
    db.commit()

    h1 = _headers_for(gestor_a.id, token_version=getattr(gestor_a, "token_versao", 0) or 0)
    h2 = _headers_for(gestor_b.id, token_version=getattr(gestor_b, "token_versao", 0) or 0)

    create_resp = await client.post(
        "/api/v1/ai/assistente/prompts",
        json={
            "titulo": "Prompt Privado A",
            "conteudo_prompt": "Somente tenant A",
            "categoria": "inadimplencia",
        },
        headers=h1,
    )
    assert create_resp.status_code == 200
    prompt_id = int((create_resp.json().get("data") or {}).get("id"))

    list_b = await client.get("/api/v1/ai/assistente/prompts?categoria=inadimplencia", headers=h2)
    assert list_b.status_code == 200
    list_b_items = (list_b.json().get("data") or {}).get("items") or []
    assert not any(int(item.get("id")) == prompt_id for item in list_b_items)

    get_other = await client.post(f"/api/v1/ai/assistente/prompts/{prompt_id}/usar", headers=h2)
    assert get_other.status_code == 404


def test_simple_cache_scoped_by_empresa():
    cache = SimpleCache(ttl_seconds=60)
    resp = AIResponse(sucesso=True, confianca=0.9, modulo_origem="financeiro")
    cache.set("financeiro", "saldo", resp, empresa_id=1)
    assert cache.get("financeiro", "saldo", empresa_id=1) is not None
    assert cache.get("financeiro", "saldo", empresa_id=2) is None


def test_sessionstore_scoped_by_empresa(db):
    emp1 = make_empresa(db, nome="E1")
    emp2 = make_empresa(db, nome="E2")
    user1 = make_usuario(db, emp1, email="u1@teste.com")
    user2 = make_usuario(db, emp2, email="u2@teste.com")

    sessao = AIChatSessao(id="sess-shared", empresa_id=emp1.id, usuario_id=user1.id)
    db.add(sessao)
    db.flush()
    db.add(AIChatMensagem(sessao_id=sessao.id, role="user", content="segredo e1"))
    db.commit()

    hist_emp1 = SessionStore.get_or_create(
        "sess-shared",
        db=db,
        empresa_id=emp1.id,
        usuario_id=user1.id,
    )
    assert any("segredo e1" in m["content"] for m in hist_emp1)

    hist_emp2 = SessionStore.get_or_create(
        "sess-shared",
        db=db,
        empresa_id=emp2.id,
        usuario_id=user2.id,
    )
    assert not any("segredo e1" in m["content"] for m in hist_emp2)


def test_ctx_leads_filtra_por_empresa(db):
    emp1 = make_empresa(db, nome="Empresa A")
    emp2 = make_empresa(db, nome="Empresa B")
    db.add_all(
        [
            CommercialLead(
                nome_responsavel="Resp A",
                nome_empresa="Lead A",
                empresa_id=emp1.id,
                status_pipeline="novo",
                ativo=True,
            ),
            CommercialLead(
                nome_responsavel="Resp B",
                nome_empresa="Lead B",
                empresa_id=emp2.id,
                status_pipeline="novo",
                ativo=True,
            ),
        ]
    )
    db.commit()

    out = asyncio.get_event_loop().run_until_complete(ContextBuilder._ctx_leads(db, emp1.id))
    assert out["total_leads_ativos"] == 1
    assert out["funil"].get("novo") == 1


def test_rag_context_scoped_by_tenant(db):
    emp1 = make_empresa(db, nome="Tenant RAG A")
    emp2 = make_empresa(db, nome="Tenant RAG B")

    db.add(
        DocumentoEmpresa(
            empresa_id=emp1.id,
            nome="Documento A",
            descricao="Processo interno de orçamento alpha",
            conteudo_html="Regras de orçamento alpha e aprovação",
        )
    )
    db.add(
        DocumentoEmpresa(
            empresa_id=emp2.id,
            nome="Documento B",
            descricao="Processo confidencial beta",
            conteudo_html="Segredo beta somente tenant B",
        )
    )
    db.commit()

    ctx_a = TenantRAGService.build_prompt_context(
        db=db, empresa_id=emp1.id, query="orçamento alpha", top_k=3
    )
    ctx_b = TenantRAGService.build_prompt_context(
        db=db, empresa_id=emp2.id, query="segredo beta", top_k=3
    )
    assert "alpha" in (ctx_a.get("context") or "").lower()
    assert "beta" not in (ctx_a.get("context") or "").lower()
    assert "beta" in (ctx_b.get("context") or "").lower()


@pytest.mark.asyncio
async def test_langgraph_wrapper_fallback_to_legacy(monkeypatch, db):
    emp = make_empresa(db, nome="LG")
    user = make_usuario(db, emp, email="lg@teste.com")

    async def fake_legacy(**kwargs):
        return AIResponse(
            sucesso=True,
            resposta="legacy",
            confianca=0.9,
            modulo_origem="assistente_v2",
        )

    monkeypatch.setenv("USE_LANGGRAPH_ASSISTANT", "true")
    monkeypatch.setattr(cotte_ai_hub, "_assistente_unificado_v2_legacy", fake_legacy)
    out = await cotte_ai_hub.assistente_unificado_v2(
        mensagem="oi",
        sessao_id="sess-lg",
        db=db,
        current_user=user,
    )
    assert out.sucesso is True
    assert out.resposta == "legacy"


@pytest.mark.asyncio
async def test_assistente_report_export_contract(client, admin_token):
    resp = await client.post(
        "/api/v1/ai/assistente/report/export",
        json={
            "format": "csv",
            "printable_payload": {
                "title": "Relatorio Teste",
                "summary": "Resumo teste",
                "rows": [{"cliente": "A", "total": 10}, {"cliente": "B", "total": 20}],
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert str(data.get("file_name", "")).endswith(".csv")
    assert "cliente,total" in str(data.get("content") or "")


@pytest.mark.asyncio
async def test_assistente_report_export_html_contract(client, admin_token):
    resp = await client.post(
        "/api/v1/ai/assistente/report/export",
        json={
            "format": "html",
            "printable_payload": {
                "title": "Relatorio HTML",
                "summary": "Resumo html",
                "rows": [{"cliente": "A", "total": 10}],
                "theme": {"accent_color": "#1d4ed8"},
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    data = payload.get("data") or {}
    assert str(data.get("file_name", "")).endswith(".html")
    assert "<html" in str(data.get("content") or "").lower()


@pytest.mark.asyncio
async def test_assistente_report_export_pdf_contract(client, admin_token, monkeypatch):
    monkeypatch.setattr(
        ai_hub_router,
        "render_semantic_report_pdf",
        lambda payload: b"%PDF-1.4 fake semantic report",
    )
    resp = await client.post(
        "/api/v1/ai/assistente/report/export",
        json={
            "format": "pdf",
            "printable_payload": {
                "title": "Relatorio PDF",
                "summary": "Resumo pdf",
                "rows": [{"cliente": "A", "total": 10}],
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    data = payload.get("data") or {}
    assert str(data.get("file_name", "")).endswith(".pdf")
    assert data.get("content_encoding") == "base64"
    assert base64.b64decode(data.get("content_base64") or b"").startswith(b"%PDF")
