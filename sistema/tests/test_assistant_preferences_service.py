from __future__ import annotations

from app.models.models import FeedbackAssistente, ToolCallLog
from app.services.assistant_preferences_service import AssistantPreferencesService
from tests.conftest import make_empresa, make_usuario


def test_service_upsert_preferencia_visualizacao(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)

    out = AssistantPreferencesService.upsert_preferencia_visualizacao(
        db,
        empresa_id=emp.id,
        usuario_id=user.id,
        formato_preferido="tabela",
        dominio="financeiro",
    )
    assert out["formato_preferido"] == "tabela"
    assert out["dominio"] == "financeiro"

    pref = AssistantPreferencesService.obter_preferencia_visualizacao(
        db,
        empresa_id=emp.id,
        usuario_id=user.id,
        dominio="financeiro",
    )
    assert pref["formato_preferido"] == "tabela"
    assert pref["confianca"] >= 0.5


def test_service_contexto_prompt_inclui_playbook_instrucao(db):
    emp = make_empresa(db)
    user = make_usuario(db, emp)
    emp.assistente_instrucoes = "Sempre comece com resumo executivo e destaque margem."
    db.add(emp)
    db.flush()

    db.add(
        FeedbackAssistente(
            empresa_id=emp.id,
            sessao_id="sess-a",
            pergunta="Resumo financeiro",
            resposta="...",
            avaliacao="positivo",
            comentario="bom",
            modulo_origem="assistente_v2",
        )
    )
    db.add(
        ToolCallLog(
            empresa_id=emp.id,
            usuario_id=user.id,
            sessao_id="sess-a",
            tool="listar_movimentacoes_financeiras",
            args_json={"dias": 30},
            resultado_json={"ok": True},
            status="ok",
            latencia_ms=45,
        )
    )
    db.commit()

    ctx = AssistantPreferencesService.get_context_for_prompt(
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
        mensagem="quero um resumo do fluxo de caixa",
    )
    assert ctx["dominio_contextual"] == "financeiro"
    assert "resumo executivo" in (ctx["instrucoes_empresa"] or "").lower()
    assert "playbook_setor" in ctx
    assert "janelas" in ctx["playbook_setor"]
    assert "90d" in ctx["playbook_setor"]["janelas"]
