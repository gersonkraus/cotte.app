from types import SimpleNamespace

from app.schemas.schemas import EmpresaOut
from app.services import email_service


def _fake_send_capture(store: dict):
    def _fake_send(destinatario, assunto, html, attachment_filename=None, attachment_base64=None, attachments=None, **kwargs):
        store["destinatario"] = destinatario
        store["assunto"] = assunto
        store["attachment_filename"] = attachment_filename
        store["attachment_base64"] = attachment_base64
        store["attachments"] = attachments
        return True, ""

    return _fake_send


def test_empresa_out_default_anexar_pdf_email_false():
    empresa = SimpleNamespace(
        id=1, nome="Empresa Teste",
        telefone=None, telefone_operador=None, email=None,
        logo_url=None, cor_primaria="#00e5a0",
    )
    out = EmpresaOut.model_validate(empresa, from_attributes=True)
    assert out.anexar_pdf_email is False


def test_envio_email_sem_anexo_por_padrao(monkeypatch):
    captured = {}
    monkeypatch.setattr(email_service, "email_habilitado", lambda: True)
    monkeypatch.setattr(email_service, "brevo_api_habilitado", lambda: True)
    monkeypatch.setattr(email_service, "_enviar_via_brevo_api", _fake_send_capture(captured))

    ok = email_service.enviar_orcamento_por_email(
        destinatario="cliente@teste.com",
        cliente_nome="Cliente",
        numero_orcamento="ORC-1-26",
        empresa_nome="Empresa",
        link_publico="token-publico",
        pdf_bytes=b"%PDF-1.4 fake",
        app_url="https://cotte.app",
    )

    assert ok is True
    assert not captured.get("attachments")


def test_envio_email_com_anexo_quando_config_ativa(monkeypatch):
    captured = {}
    monkeypatch.setattr(email_service, "email_habilitado", lambda: True)
    monkeypatch.setattr(email_service, "brevo_api_habilitado", lambda: True)
    monkeypatch.setattr(email_service, "_enviar_via_brevo_api", _fake_send_capture(captured))

    ok = email_service.enviar_orcamento_por_email(
        destinatario="cliente@teste.com",
        cliente_nome="Cliente",
        numero_orcamento="ORC-2-26",
        empresa_nome="Empresa",
        link_publico="token-publico",
        pdf_bytes=b"%PDF-1.4 fake",
        anexar_pdf=True,
        app_url="https://cotte.app",
    )

    assert ok is True
    attachments = captured.get("attachments") or []
    assert len(attachments) == 1
    assert attachments[0]["name"] == "orcamento-ORC-2-26.pdf"
    assert isinstance(attachments[0]["content"], str)
    assert len(attachments[0]["content"]) > 0


def test_envio_email_config_ativa_sem_pdf_envia_sem_anexo(monkeypatch):
    captured = {}
    monkeypatch.setattr(email_service, "email_habilitado", lambda: True)
    monkeypatch.setattr(email_service, "brevo_api_habilitado", lambda: True)
    monkeypatch.setattr(email_service, "_enviar_via_brevo_api", _fake_send_capture(captured))

    ok = email_service.enviar_orcamento_por_email(
        destinatario="cliente@teste.com",
        cliente_nome="Cliente",
        numero_orcamento="ORC-3-26",
        empresa_nome="Empresa",
        link_publico="token-publico",
        pdf_bytes=None,
        anexar_pdf=True,
        app_url="https://cotte.app",
    )

    assert ok is True
    assert not captured.get("attachments")
