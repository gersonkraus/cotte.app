import hashlib
import hmac
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services import nfe_service
from app.services.nfe_service import _limpar_doc, _limpar_cep, verificar_assinatura_webhook


def test_limpar_doc():
    assert _limpar_doc("123.456.789-00") == "12345678900"
    assert _limpar_doc("12.345.678/0001-90") == "12345678000190"
    assert _limpar_doc("") == ""
    assert _limpar_doc(None) == ""


def test_limpar_cep():
    assert _limpar_cep("12345-678") == "12345678"
    assert _limpar_cep("") == ""
    assert _limpar_cep(None) == ""


def test_verificar_assinatura_webhook_valid():
    body = b'{"event":"test"}'
    secret = "my_secret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verificar_assinatura_webhook(body, sig, secret) is True


def test_verificar_assinatura_webhook_invalid():
    assert verificar_assinatura_webhook(b'{"event":"test"}', "bad_sig", "my_secret") is False


def test_verificar_assinatura_webhook_with_prefix():
    body = b'{"event":"test"}'
    secret = "my_secret"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verificar_assinatura_webhook(body, sig, secret) is True


@pytest.mark.asyncio
async def test_emitir_nota_timeout_keeps_processing(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp NF Test")
    emp.notaas_api_key = "ntaas_test_key"
    emp.cnpj = "11222333000144"
    db.flush()

    nota = NotaFiscal(
        empresa_id=emp.id,
        tipo="nfse",
        status="processando",
        notaas_invoice_id="inv_timeout_001",
    )
    db.add(nota)
    db.commit()

    with patch("app.services.nfe_service._get_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "processing"}
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        
        async def mock_get(*args, **kwargs):
            return mock_resp
            
        async def mock_post(*args, **kwargs):
            return mock_resp
            
        mock_ctx = MagicMock()
        mock_ctx.get = mock_get
        mock_ctx.post = mock_post
        
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        
        mock_client.return_value = mock_client_instance

        with patch("app.services.nfe_service.POLLING_MAX_ATTEMPTS", 2):
            with patch("app.services.nfe_service.POLLING_INTERVAL", 0):
                await nfe_service.emitir_nota(db, nota, emp, {"test": True})

    db.refresh(nota)
    assert nota.status in ("processando", "erro")
