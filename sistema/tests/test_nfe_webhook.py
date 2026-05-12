import hashlib
import hmac
import json

import pytest
from tests.conftest import make_empresa, make_usuario, make_cliente, make_orcamento


@pytest.fixture
def empresa_nfe(db):
    emp = make_empresa(db, nome="Empresa NFe")
    emp.cnpj = "12345678000100"
    emp.notaas_api_key = "ntaas_test_key"
    emp.notaas_webhook_secret = "webhook_secret_123"
    db.flush()
    return emp


@pytest.fixture
def nota_nfe(db, empresa_nfe):
    from app.models.models import NotaFiscal
    nota = NotaFiscal(
        empresa_id=empresa_nfe.id,
        tipo="nfse",
        status="processando",
        notaas_invoice_id="inv_test_001",
    )
    db.add(nota)
    db.commit()
    return nota


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_nfse_issued(http_client, db, empresa_nfe, nota_nfe):
    body = json.dumps({
        "event": "nfse.issued",
        "deliveryId": "delv_001",
        "invoiceId": "inv_test_001",
        "numeroNfe": "123",
        "chNFSe": "chave123",
        "xmlUrl": "https://xml.example.com/123",
        "pdfUrl": "https://pdf.example.com/123",
    }).encode()
    sig = _sign(body, empresa_nfe.notaas_webhook_secret)

    resp = http_client.post(
        "/api/v1/notas-fiscais/webhook/notaas",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Notaas-Event": "nfse.issued",
            "X-Notaas-Delivery": "delv_001",
            "X-Notaas-Signature": sig,
        },
    )
    assert resp.status_code == 200

    from app.models.models import NotaFiscal
    nota = db.query(NotaFiscal).get(nota_nfe.id)
    assert nota.status == "emitida"
    assert nota.numero == "123"
    assert nota.chave_acesso == "chave123"
    assert nota.xml_url == "https://xml.example.com/123"


def test_webhook_nfse_error(http_client, db, empresa_nfe, nota_nfe):
    body = json.dumps({
        "event": "nfse.error",
        "deliveryId": "delv_002",
        "invoiceId": "inv_test_001",
        "errorCode": "E001",
        "errorMessage": "Erro de validacao",
    }).encode()
    sig = _sign(body, empresa_nfe.notaas_webhook_secret)

    resp = http_client.post(
        "/api/v1/notas-fiscais/webhook/notaas",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Notaas-Event": "nfse.error",
            "X-Notaas-Delivery": "delv_002",
            "X-Notaas-Signature": sig,
        },
    )
    assert resp.status_code == 200

    from app.models.models import NotaFiscal
    nota = db.query(NotaFiscal).get(nota_nfe.id)
    assert nota.status == "erro"
    assert nota.erro_codigo == "E001"


def test_webhook_documents_ready(http_client, db, empresa_nfe, nota_nfe):
    nota_nfe.status = "emitida"
    db.commit()

    body = json.dumps({
        "event": "nfse.documents_ready",
        "deliveryId": "delv_doc_001",
        "invoiceId": "inv_test_001",
        "data": {
            "xmlUrl": "https://xml-new.example.com/123",
            "pdfUrl": "https://pdf-new.example.com/123",
        },
    }).encode()
    sig = _sign(body, empresa_nfe.notaas_webhook_secret)

    resp = http_client.post(
        "/api/v1/notas-fiscais/webhook/notaas",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Notaas-Event": "nfse.documents_ready",
            "X-Notaas-Delivery": "delv_doc_001",
            "X-Notaas-Signature": sig,
        },
    )
    assert resp.status_code == 200

    from app.models.models import NotaFiscal
    nota = db.query(NotaFiscal).get(nota_nfe.id)
    assert nota.xml_url == "https://xml-new.example.com/123"
    assert nota.danfe_url == "https://pdf-new.example.com/123"


def test_webhook_rejects_without_signature_when_secret_set(http_client, db, empresa_nfe, nota_nfe):
    body = json.dumps({
        "event": "nfse.issued",
        "deliveryId": "delv_no_sig",
        "invoiceId": "inv_test_001",
    }).encode()

    resp = http_client.post(
        "/api/v1/notas-fiscais/webhook/notaas",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Notaas-Event": "nfse.issued",
            "X-Notaas-Delivery": "delv_no_sig",
        },
    )
    assert resp.status_code == 401


def test_webhook_rejects_invalid_signature(http_client, db, empresa_nfe, nota_nfe):
    body = json.dumps({
        "event": "nfse.issued",
        "deliveryId": "delv_bad_sig",
        "invoiceId": "inv_test_001",
    }).encode()

    resp = http_client.post(
        "/api/v1/notas-fiscais/webhook/notaas",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Notaas-Event": "nfse.issued",
            "X-Notaas-Delivery": "delv_bad_sig",
            "X-Notaas-Signature": "invalid_hash_value",
        },
    )
    assert resp.status_code == 401


def test_webhook_idempotency(http_client, db, empresa_nfe, nota_nfe):
    body = json.dumps({
        "event": "nfse.issued",
        "deliveryId": "delv_dup",
        "invoiceId": "inv_test_001",
        "numeroNfe": "999",
    }).encode()
    sig = _sign(body, empresa_nfe.notaas_webhook_secret)
    headers = {
        "Content-Type": "application/json",
        "X-Notaas-Event": "nfse.issued",
        "X-Notaas-Delivery": "delv_dup",
        "X-Notaas-Signature": sig,
    }

    resp1 = http_client.post("/api/v1/notas-fiscais/webhook/notaas", content=body, headers=headers)
    assert resp1.status_code == 200

    nota_nfe.status = "processando"
    nota_nfe.numero = None
    db.commit()

    resp2 = http_client.post("/api/v1/notas-fiscais/webhook/notaas", content=body, headers=headers)
    assert resp2.status_code == 200

    from app.models.models import NotaFiscal
    nota = db.query(NotaFiscal).get(nota_nfe.id)
    assert nota.numero is None


def test_webhook_registers_historico(http_client, db, empresa_nfe):
    from app.models.models import NotaFiscal
    usuario = make_usuario(db, empresa_nfe)
    cliente = make_cliente(db, empresa_nfe)
    orc = make_orcamento(db, empresa_nfe, cliente, usuario)
    nota = NotaFiscal(
        empresa_id=empresa_nfe.id,
        orcamento_id=orc.id,
        tipo="nfse",
        status="processando",
        notaas_invoice_id="inv_hist_001",
    )
    db.add(nota)
    db.commit()

    body = json.dumps({
        "event": "nfse.issued",
        "deliveryId": "delv_hist_001",
        "invoiceId": "inv_hist_001",
        "numeroNfe": "456",
    }).encode()
    sig = _sign(body, empresa_nfe.notaas_webhook_secret)

    resp = http_client.post(
        "/api/v1/notas-fiscais/webhook/notaas",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Notaas-Event": "nfse.issued",
            "X-Notaas-Delivery": "delv_hist_001",
            "X-Notaas-Signature": sig,
        },
    )
    assert resp.status_code == 200

    from app.models.models import HistoricoEdicao
    hist = db.query(HistoricoEdicao).filter(HistoricoEdicao.orcamento_id == orc.id).first()
    assert hist is not None
    assert "nota_fiscal" in hist.tipo
    assert "456" in hist.descricao
