from __future__ import annotations

import asyncio
import json

import pytest

from app.core.auth import criar_token
from app.models.models import (
    AIChatMensagem,
    AIChatSessao,
    CommercialLead,
    DocumentoEmpresa,
)
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
    async def fake_v2(**kwargs):
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

