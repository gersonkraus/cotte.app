import base64
import json

import pytest
from unittest.mock import patch

from tests.conftest import make_empresa, make_usuario, make_cliente, make_orcamento


def _basic_auth(token: str) -> str:
    encoded = base64.b64encode(f"{token}:".encode()).decode()
    return f"Basic {encoded}"


FOCUS_TOKEN_TEST = "focus_test_token"


@pytest.fixture
def empresa_nfe(db):
    emp = make_empresa(db, nome="Empresa NFe Focus")
    emp.cnpj = "12345678000100"
    emp.nfe_ambiente = "homologacao"
    db.flush()
    return emp


@pytest.fixture
def nota_nfe(db, empresa_nfe):
    from app.models.models import NotaFiscal

    nota = NotaFiscal(
        empresa_id=empresa_nfe.id,
        tipo="nfse",
        status="processando",
        focus_ref="12345678000100-42",
    )
    db.add(nota)
    db.commit()
    return nota


def test_webhook_focus_autorizado(http_client, db, empresa_nfe, nota_nfe):
    payload = {
        "ref": "12345678000100-42",
        "status": "autorizado",
        "chave_nfe": "35240512345678000100550010000000421000000421",
        "numero": "42",
        "protocolo": "135240000000042",
        "caminho_xml_nota_fiscal": "/arquivos/nfe/xml/nota42.xml",
        "caminho_danfe": "/arquivos/nfe/danfe/nota42.pdf",
    }

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": _basic_auth(FOCUS_TOKEN_TEST)},
        )

    assert resp.status_code == 200

    from app.models.models import NotaFiscal

    nota = db.query(NotaFiscal).get(nota_nfe.id)
    assert nota.status == "emitida"
    assert nota.chave_acesso == "35240512345678000100550010000000421000000421"
    assert nota.numero == "42"
    assert nota.protocolo == "135240000000042"
    assert nota.xml_url == "/arquivos/nfe/xml/nota42.xml"
    assert nota.danfe_url == "/arquivos/nfe/danfe/nota42.pdf"


def test_webhook_focus_erro_autorizacao(http_client, db, empresa_nfe, nota_nfe):
    payload = {
        "ref": "12345678000100-42",
        "status": "erro_autorizacao",
        "erros": [{"codigo": "539", "mensagem": "CNPJ do emitente invalido"}],
    }

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": _basic_auth(FOCUS_TOKEN_TEST)},
        )

    assert resp.status_code == 200

    from app.models.models import NotaFiscal

    nota = db.query(NotaFiscal).get(nota_nfe.id)
    assert nota.status == "erro"
    assert nota.denegada is False


def test_webhook_focus_denegado(http_client, db, empresa_nfe, nota_nfe):
    payload = {
        "ref": "12345678000100-42",
        "status": "denegado",
        "erros": [{"codigo": "301", "mensagem": "CNPJ emitente irregular na Receita"}],
    }

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": _basic_auth(FOCUS_TOKEN_TEST)},
        )

    assert resp.status_code == 200

    from app.models.models import NotaFiscal

    nota = db.query(NotaFiscal).get(nota_nfe.id)
    assert nota.status == "erro"
    assert nota.denegada is True


def test_webhook_focus_rejeita_sem_auth(http_client, db, empresa_nfe, nota_nfe):
    payload = {"ref": "12345678000100-42", "status": "autorizado"}

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
        )

    assert resp.status_code == 401


def test_webhook_focus_aceita_authorization_somente_token_sem_basic(http_client, db, empresa_nfe, nota_nfe):
    """Gatilho Focus com «Chave» = token puro (sem prefixo Basic) também autentica."""
    payload = {"ref": "12345678000100-42", "status": "autorizado", "numero": "42"}

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": FOCUS_TOKEN_TEST},
        )

    assert resp.status_code == 200


def test_webhook_focus_rejeita_token_errado(http_client, db, empresa_nfe, nota_nfe):
    payload = {"ref": "12345678000100-42", "status": "autorizado"}

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": _basic_auth("token_errado")},
        )

    assert resp.status_code == 401


def test_webhook_focus_aceita_token_homologacao(http_client, db, empresa_nfe, nota_nfe):
    """Webhooks de notas emitidas em homologação podem autenticar com FOCUS_TOKEN_HOMOLOGACAO."""
    payload = {
        "ref": "12345678000100-42",
        "status": "autorizado",
        "chave_nfe": "35240512345678000100550010000000421000000421",
        "numero": "42",
    }
    homolog = "focus_homolog_secret"

    with patch("app.core.config.settings.FOCUS_TOKEN", ""), patch(
        "app.core.config.settings.FOCUS_TOKEN_HOMOLOGACAO", homolog
    ):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": _basic_auth(homolog)},
        )

    assert resp.status_code == 200


def test_webhook_focus_ref_desconhecida_ignora(http_client, db, empresa_nfe):
    """Payload com ref que não existe no banco deve retornar 200 sem erro."""
    payload = {"ref": "00000000000000-999", "status": "autorizado"}

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": _basic_auth(FOCUS_TOKEN_TEST)},
        )

    assert resp.status_code == 200


def test_webhook_focus_registra_historico(http_client, db, empresa_nfe):
    from app.models.models import NotaFiscal

    usuario = make_usuario(db, empresa_nfe)
    cliente = make_cliente(db, empresa_nfe)
    orc = make_orcamento(db, empresa_nfe, cliente, usuario)

    nota = NotaFiscal(
        empresa_id=empresa_nfe.id,
        orcamento_id=orc.id,
        tipo="nfe",
        status="processando",
        focus_ref="12345678000100-77",
    )
    db.add(nota)
    db.commit()

    payload = {
        "ref": "12345678000100-77",
        "status": "autorizado",
        "numero": "77",
        "chave_nfe": "35240512345678000100550010000000771000000771",
    }

    with patch("app.core.config.settings.FOCUS_TOKEN", FOCUS_TOKEN_TEST):
        resp = http_client.post(
            "/api/v1/notas-fiscais/webhook/focus",
            json=payload,
            headers={"Authorization": _basic_auth(FOCUS_TOKEN_TEST)},
        )

    assert resp.status_code == 200

    from app.models.models import HistoricoEdicao

    hist = db.query(HistoricoEdicao).filter(HistoricoEdicao.orcamento_id == orc.id).first()
    assert hist is not None
    assert "nota_fiscal" in hist.tipo
    assert "77" in hist.descricao
