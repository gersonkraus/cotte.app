import hashlib
import hmac
from decimal import Decimal
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services import nfe_service
from app.services.nfe_service import (
    _limpar_doc,
    _limpar_cep,
    verificar_assinatura_webhook,
    _normalizar_cfop_para_string,
    _cfop_formato_notaas_valido,
    _cfop_padrao_por_uf_empresa_cliente,
    _quantidade_valores_item_nfe,
    sugerir_acao_campo_erro_notaas,
)


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


def test_normalizar_cfop_para_string():
    assert _normalizar_cfop_para_string(5102, "5102") == "5102"
    assert _normalizar_cfop_para_string("61.02", "5102") == "6102"
    assert _normalizar_cfop_para_string(None, "6102") == "6102"
    assert _normalizar_cfop_para_string("12", "5102") == "0012"


def test_cfop_formato_notaas_valido():
    assert _cfop_formato_notaas_valido("5102") is True
    assert _cfop_formato_notaas_valido("510") is False
    assert _cfop_formato_notaas_valido("abcd") is False


def test_cfop_padrao_interestadual():
    emp = SimpleNamespace(endereco_uf="PR")
    cli = SimpleNamespace(estado="PR")
    assert _cfop_padrao_por_uf_empresa_cliente(emp, cli) == "5102"
    cli2 = SimpleNamespace(estado="SP")
    assert _cfop_padrao_por_uf_empresa_cliente(emp, cli2) == "6102"


def test_quantidade_valores_item_nfe_recalcula_total():
    item = SimpleNamespace(quantidade=2, valor_unit=Decimal("10"), total=Decimal("0"))
    q, vu, vt = _quantidade_valores_item_nfe(item)
    assert q == 2.0 and vu == 10.0 and vt == 20.0


def test_quantidade_valores_item_nfe_qtd_zero_vai_para_um():
    item = SimpleNamespace(quantidade=0, valor_unit=Decimal("5"), total=Decimal("5"))
    q, vu, vt = _quantidade_valores_item_nfe(item)
    assert q == 1.0 and vt == 5.0


def test_sugerir_acao_campo_erro_notaas_substrings():
    assert "IBGE" in (sugerir_acao_campo_erro_notaas("dest.endereco.codigoMunicipio deve ser 7") or "")
    assert sugerir_acao_campo_erro_notaas("items[0].cfop inválido") and "CFOP" in sugerir_acao_campo_erro_notaas(
        "items[0].cfop inválido"
    )
    assert "valor" in (sugerir_acao_campo_erro_notaas("items[0].valorTotal deve ser > 0") or "").lower()


@pytest.mark.asyncio
async def test_montar_payload_nfe_codigo_municipio_cliente():
    cliente = SimpleNamespace(
        cnpj="12345678000195",
        cpf=None,
        razao_social="ACME",
        nome="ACME",
        logradouro="Rua A",
        numero="1",
        bairro="Centro",
        cidade="Curitiba",
        estado="PR",
        cep="80010000",
        complemento=None,
        email="a@b.com",
        inscricao_estadual="",
        codigo_municipio_ibge="4106902",
    )
    serv = SimpleNamespace(
        nome="Produto X",
        ncm="61091000",
        cfop="5102",
        csosn="102",
        unidade="UN",
        unidade_fiscal=None,
        categoria=None,
    )
    item = SimpleNamespace(
        descricao="Camiseta",
        quantidade=Decimal("1"),
        valor_unit=Decimal("50"),
        total=Decimal("50"),
        servico=serv,
    )
    emp = SimpleNamespace(endereco_uf="PR")
    orc = SimpleNamespace(cliente=cliente, itens=[item], total=Decimal("50"), forma_pagamento="pix")

    payload = await nfe_service._montar_payload_nfe(emp, orc, "nfe", "Venda", "1", db=None)
    assert payload["dest"]["endereco"]["codigoMunicipio"] == 4106902
    assert payload["items"][0]["cfop"] == "5102"
    assert payload["items"][0]["descricao"] == "Camiseta"


@pytest.mark.asyncio
async def test_montar_payload_nfe_ibge_via_viacep_persiste_no_cliente(db):
    from tests.conftest import make_empresa, make_usuario
    from app.models.models import Cliente, Orcamento, ItemOrcamento, Servico

    emp = make_empresa(db, nome="Emp NFe ViaCEP")
    u = make_usuario(db, emp)
    cli = Cliente(
        empresa_id=emp.id,
        criado_por_id=u.id,
        nome="Cliente ViaCEP",
        cnpj="12345678000195",
        logradouro="Rua Teste",
        numero="10",
        bairro="Centro",
        cidade="São Paulo",
        estado="SP",
        cep="01310100",
        codigo_municipio_ibge=None,
    )
    db.add(cli)
    db.flush()
    srv = Servico(empresa_id=emp.id, nome="Serviço A", ncm="61091000", cfop="5102", csosn="400")
    db.add(srv)
    db.flush()
    orc = Orcamento(
        empresa_id=emp.id,
        cliente_id=cli.id,
        criado_por_id=u.id,
        numero="ORC-NFE-1",
        total=Decimal("100"),
    )
    db.add(orc)
    db.flush()
    db.add(
        ItemOrcamento(
            orcamento_id=orc.id,
            servico_id=srv.id,
            descricao="Item",
            quantidade=Decimal("1"),
            valor_unit=Decimal("100"),
            total=Decimal("100"),
        )
    )
    db.commit()

    async def fake_via_cep(_cep: str):
        return 3550308

    with patch("app.services.nfe_service._buscar_ibge_via_cep", new=fake_via_cep):
        db.refresh(orc)
        orc = (
            db.query(Orcamento)
            .filter(Orcamento.id == orc.id)
            .first()
        )
        payload = await nfe_service._montar_payload_nfe(emp, orc, "nfe", "Venda", "1", db=db)

    assert payload["dest"]["endereco"]["codigoMunicipio"] == 3550308
    db.flush()
    db.refresh(cli)
    assert cli.codigo_municipio_ibge == "3550308"


@pytest.mark.asyncio
async def test_coletar_bloqueios_preparacao_nfe_sem_ibge_nem_cep():
    cliente = SimpleNamespace(
        cnpj="12345678000195",
        cpf=None,
        razao_social="X",
        nome="X",
        cep="",
        cidade="",
        estado="",
        codigo_municipio_ibge=None,
    )
    item = SimpleNamespace(
        id=1,
        descricao="A",
        quantidade=Decimal("1"),
        valor_unit=Decimal("10"),
        total=Decimal("10"),
        servico=None,
    )
    emp = SimpleNamespace(endereco_uf="PR")
    orc = SimpleNamespace(cliente=cliente, itens=[item])

    with patch("app.services.nfe_service._buscar_ibge_via_cep", new_callable=AsyncMock, return_value=None):
        with patch("app.services.nfe_service._buscar_ibge_por_cidade_uf", new_callable=AsyncMock, return_value=None):
            bloqueios, _avisos = await nfe_service.coletar_bloqueios_avisos_preparacao_nfe(emp, orc)

    assert any("IBGE" in b for b in bloqueios)


@pytest.mark.asyncio
async def test_coletar_bloqueios_valor_item_zero():
    cliente = SimpleNamespace(
        cnpj="12345678000195",
        cpf=None,
        razao_social="X",
        nome="X",
        cep="",
        cidade="Curitiba",
        estado="PR",
        codigo_municipio_ibge="4106902",
    )
    item = SimpleNamespace(
        id=1,
        descricao="Z",
        quantidade=Decimal("1"),
        valor_unit=Decimal("0"),
        total=Decimal("0"),
        servico=None,
    )
    emp = SimpleNamespace(endereco_uf="PR")
    orc = SimpleNamespace(cliente=cliente, itens=[item])

    bloqueios, _ = await nfe_service.coletar_bloqueios_avisos_preparacao_nfe(emp, orc)
    assert any("zero" in b.lower() for b in bloqueios)
