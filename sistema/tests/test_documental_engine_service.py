from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.models import DocumentoEmpresa
from app.services import documental_engine_service as svc


@pytest.mark.asyncio
async def test_documental_flow_success_sem_anexo(db, monkeypatch):
    audit_payload: dict = {}

    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        if name == "obter_orcamento":
            return SimpleNamespace(
                status="ok",
                data={
                    "id": 45,
                    "numero": "O-45",
                    "status": "ENVIADO",
                    "total": 999.0,
                    "cliente": {"id": 8, "nome": "Cliente XPTO"},
                    "itens": [{"descricao": "Servico A"}],
                },
                error=None,
                pending_action=None,
            )
        raise AssertionError(f"tool inesperada: {name}")

    def fake_audit(*args, **kwargs):
        audit_payload.update(kwargs.get("detalhes") or {})

    db.add(
        DocumentoEmpresa(
            empresa_id=1,
            nome="Contrato padrão",
            descricao="Contrato principal",
            conteudo_html="<p>Contrato</p>",
            atualizado_em=datetime.now(timezone.utc),
        )
    )
    db.commit()

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(svc, "registrar_auditoria", fake_audit)

    user = SimpleNamespace(id=12, empresa_id=1)
    out = await svc.run_documental_orcamento_flow(
        db=db,
        current_user=user,
        request_id="req-doc-1",
        sessao_id="sess-doc-1",
        orcamento_id=45,
        documento_id=None,
        exibir_no_portal=True,
        enviar_por_email=True,
        enviar_por_whatsapp=False,
        obrigatorio=False,
        confirmation_token=None,
    )

    assert out["success"] is True
    assert out.get("flow_id")
    assert out["data"]["registro"]["flow_id"] == out["flow_id"]
    assert audit_payload.get("flow_id") == out["flow_id"]
    assert out["data"]["dossie"]["orcamento"]["numero"] == "O-45"
    assert out["metrics"]["total_steps"] == 3


@pytest.mark.asyncio
async def test_documental_flow_pending_anexo(monkeypatch):
    async def fake_execute_tool(tool_call, **kwargs):
        name = (tool_call.get("function") or {}).get("name")
        if name == "obter_orcamento":
            return SimpleNamespace(
                status="ok",
                data={"id": 90, "numero": "O-90", "cliente": {"nome": "Cliente A"}, "itens": []},
                error=None,
                pending_action=None,
            )
        if name == "anexar_documento_orcamento":
            return SimpleNamespace(
                status="pending",
                data=None,
                error=None,
                pending_action={"tool": "anexar_documento_orcamento", "confirmation_token": "tok-doc"},
            )
        raise AssertionError(f"tool inesperada: {name}")

    monkeypatch.setattr(svc, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(svc, "_listar_documentos_empresa", lambda *args, **kwargs: [])

    user = SimpleNamespace(id=21, empresa_id=1)
    out = await svc.run_documental_orcamento_flow(
        db=None,
        current_user=user,
        request_id="req-doc-2",
        sessao_id="sess-doc-2",
        orcamento_id=90,
        documento_id=7,
        exibir_no_portal=True,
        enviar_por_email=True,
        enviar_por_whatsapp=False,
        obrigatorio=False,
        confirmation_token=None,
    )

    assert out["success"] is False
    assert out["code"] == "pending_confirmation"
    assert out.get("flow_id")
    assert out["pending_action"]["flow_step"] == "anexar_documento_orcamento"
    assert out["pending_action"]["confirmation_required"] is True
