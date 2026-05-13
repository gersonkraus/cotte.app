import hashlib
import hmac
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services import nfe_service
from app.services.nfe_service import (
    _limpar_doc,
    _limpar_cep,
    verificar_token_webhook_focus,
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


def test_verificar_token_webhook_focus_valido():
    import base64
    token = "meu_token_focus"
    encoded = base64.b64encode(f"{token}:".encode()).decode()
    assert verificar_token_webhook_focus(f"Basic {encoded}", token) is True


def test_verificar_token_webhook_focus_invalido():
    import base64
    encoded = base64.b64encode(b"token_errado:").decode()
    assert verificar_token_webhook_focus(f"Basic {encoded}", "token_correto") is False


def test_verificar_token_webhook_focus_header_ausente():
    assert verificar_token_webhook_focus("", "qualquer") is False
    assert verificar_token_webhook_focus(None, "qualquer") is False



def test_sugerir_acao_mensagem_erro_cstat_209_ie_emitente():
    msg = "[NFE_SEFAZ_REJECTION] cStat=209 — Rejeicao: IE do emitente invalida"
    acao = nfe_service.sugerir_acao_mensagem_erro_notaas(msg)
    assert acao is not None
    assert "209" in acao
    assert "Configurações" in acao or "Fiscal" in acao


def test_sugerir_acao_mensagem_erro_cstat_972_responsavel_tecnico():
    msg = "[NFE_SEFAZ_REJECTION] cStat=972 — Rejeicao: Obrigatoria as informacoes do responsavel tecnico"
    acao = nfe_service.sugerir_acao_mensagem_erro_notaas(msg)
    assert acao is not None
    assert "972" in acao
    assert "Focus" in acao


@pytest.mark.asyncio
async def test_emitir_nota_timeout_keeps_processing(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp NF Test")
    emp.cnpj = "11222333000144"
    db.flush()

    nota = NotaFiscal(
        empresa_id=emp.id,
        tipo="nfse",
        status="processando",
        focus_ref="NFe_timeout_001",
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
    emp = SimpleNamespace(
        cnpj="98765432000188",
        nome="Emitente Teste",
        endereco_uf="PR",
        endereco_logradouro="Rua Emit",
        endereco_numero="1",
        endereco_bairro="Centro",
        endereco_cidade="Curitiba",
        endereco_cep="80010000",
        inscricao_estadual="123",
        regime_tributario="simples_nacional",
        crt=1,
    )
    orc = SimpleNamespace(cliente=cliente, itens=[item], total=Decimal("50"), forma_pagamento="pix")

    payload = await nfe_service._montar_payload_nfe(emp, orc, "nfe", "Venda", "1", db=None)
    assert payload["codigo_municipio_destinatario"] == "4106902"
    assert payload["items"][0]["cfop"] == 5102
    assert payload["items"][0]["descricao"] == "Camiseta"


@pytest.mark.asyncio
async def test_montar_payload_nfe_ibge_via_viacep_persiste_no_cliente(db):
    from tests.conftest import make_empresa, make_usuario
    from app.models.models import Cliente, Orcamento, ItemOrcamento, Servico

    emp = make_empresa(db, nome="Emp NFe ViaCEP", cnpj="11222333000181")
    emp.endereco_logradouro = "Rua Emp"
    emp.endereco_numero = "1"
    emp.endereco_bairro = "Centro"
    emp.endereco_cidade = "Curitiba"
    emp.endereco_uf = "PR"
    emp.endereco_cep = "80010000"
    emp.inscricao_estadual = "1234567890"
    emp.regime_tributario = "simples_nacional"
    emp.crt = 1
    db.flush()
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

    assert payload["codigo_municipio_destinatario"] == "3550308"
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


# ---------------------------------------------------------------------------
# Task 1 — Focus NFe: _gerar_ref
# ---------------------------------------------------------------------------

from app.services.nfe_service import _gerar_ref


def test_gerar_ref_formata_cnpj_sem_mascara():
    emp = SimpleNamespace(cnpj="12.345.678/0001-90")
    assert _gerar_ref(emp, 42) == "12345678000190-42"


def test_gerar_ref_cnpj_sem_mascara():
    emp = SimpleNamespace(cnpj="12345678000190")
    assert _gerar_ref(emp, 1) == "12345678000190-1"


def test_gerar_ref_cnpj_vazio_levanta_value_error():
    emp = SimpleNamespace(cnpj="")
    with pytest.raises(ValueError, match="CNPJ"):
        _gerar_ref(emp, 1)


def test_gerar_ref_cnpj_none_levanta_value_error():
    emp = SimpleNamespace(cnpj=None)
    with pytest.raises(ValueError, match="CNPJ"):
        _gerar_ref(emp, 1)


@pytest.mark.asyncio
async def test_montar_payload_focus_nfe_estrutura(db):
    from tests.conftest import make_empresa, make_usuario, make_cliente, make_orcamento

    emp = make_empresa(db, cnpj="12.345.678/0001-90")
    emp.endereco_logradouro = "Av Paulista"
    emp.endereco_numero = "1000"
    emp.endereco_bairro = "Bela Vista"
    emp.endereco_cidade = "São Paulo"
    emp.endereco_uf = "SP"
    emp.endereco_cep = "01310100"
    emp.inscricao_estadual = "123456789012"
    emp.regime_tributario = "simples_nacional"
    emp.crt = 1
    db.flush()
    u = make_usuario(db, emp)
    cli = make_cliente(db, emp, nome="Cliente Consumidor")
    cli.cpf = "12345678909"
    cli.logradouro = "Rua das Flores"
    cli.numero = "10"
    cli.bairro = "Centro"
    cli.cidade = "São Paulo"
    cli.estado = "SP"
    cli.cep = "01310100"
    cli.codigo_municipio_ibge = "3550308"
    db.commit()
    orc = make_orcamento(db, emp, cli, u, total=150.0)
    with patch("app.services.nfe_service.sugerir_dados_fiscais", new_callable=AsyncMock) as mock_ia:
        mock_ia.return_value = {"ncm": "85171231", "cfop": "5102"}
        payload = await nfe_service.montar_payload_focus_nfe(
            emp, orc, "nfe", "Venda de teste", "1", None, db=db
        )
    assert payload["cnpj_emitente"] == "12345678000190"
    assert payload["tipo_documento"] == 1
    assert payload["finalidade_emissao"] == 1
    assert "items" in payload and len(payload["items"]) >= 1
    assert payload["formas_pagamento"]
    assert payload["valor_total"] == 150.0
    assert payload["codigo_municipio_destinatario"] == "3550308"


@pytest.mark.asyncio
async def test_emitir_nota_focus_201_sincrono_sem_polling(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Empresa Sync", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="pendente")
    db.add(nota)
    db.flush()

    _req = httpx.Request("POST", "http://focus-test")
    resp_emissao = httpx.Response(
        201,
        json={
            "status": "autorizado",
            "chave_nfe": "35240512345678000195550010000000011000000011",
            "numero": "9",
            "protocolo": "135240000000099",
            "caminho_xml_nota_fiscal": "/arquivos/nfe/xml/sync.xml",
            "caminho_danfe": "/arquivos/nfe/danfe/sync.pdf",
        },
        request=_req,
    )

    with patch("app.services.nfe_service._get_client") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_emissao)
        mock_client_ctx.return_value = mock_client

        resultado = await nfe_service.emitir_nota(db, nota, emp, {"natureza_operacao": "Venda"})

    assert resultado.status == "emitida"
    mock_client.get.assert_not_called()


# ---------------------------------------------------------------------------
# Task 3 — emitir_nota() Focus NFe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emitir_nota_focus_sucesso(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Empresa Focus", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="pendente")
    db.add(nota)
    db.flush()

    _req = httpx.Request("POST", "http://focus-test")
    resp_emissao = httpx.Response(202, json={}, request=_req)
    resp_status = httpx.Response(200, json={
        "status": "autorizado",
        "chave_nfe": "35240512345678000195550010000000011000000011",
        "numero": "1",
        "protocolo": "135240000000001",
        "caminho_xml_nota_fiscal": "/arquivos/nfe/xml/nota.xml",
        "caminho_danfe": "/arquivos/nfe/danfe/nota.pdf",
    }, request=_req)

    with patch("app.services.nfe_service._get_client") as mock_client_ctx, \
         patch("app.services.nfe_service.asyncio.sleep", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_emissao)
        mock_client.get = AsyncMock(return_value=resp_status)
        mock_client_ctx.return_value = mock_client

        resultado = await nfe_service.emitir_nota(db, nota, emp, {"natureza_operacao": "Venda"})

    assert resultado.status == "emitida"
    assert resultado.focus_ref == f"12345678000195-{nota.id}"
    assert resultado.chave_acesso == "35240512345678000195550010000000011000000011"
    assert resultado.numero == "1"
    assert resultado.protocolo == "135240000000001"
    assert resultado.xml_url == "/arquivos/nfe/xml/nota.xml"
    assert resultado.danfe_url == "/arquivos/nfe/danfe/nota.pdf"


@pytest.mark.asyncio
async def test_emitir_nota_focus_erro_autorizacao(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Empresa Erro", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="pendente")
    db.add(nota)
    db.flush()

    _req = httpx.Request("POST", "http://focus-test")
    resp_emissao = httpx.Response(202, json={}, request=_req)
    resp_status = httpx.Response(200, json={
        "status": "erro_autorizacao",
        "erros": [{"codigo": "539", "mensagem": "Rejeicao: CNPJ do emitente invalido"}],
    }, request=_req)

    with patch("app.services.nfe_service._get_client") as mock_client_ctx, \
         patch("app.services.nfe_service.asyncio.sleep", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_emissao)
        mock_client.get = AsyncMock(return_value=resp_status)
        mock_client_ctx.return_value = mock_client

        resultado = await nfe_service.emitir_nota(db, nota, emp, {})

    assert resultado.status == "erro"
    assert resultado.denegada is False


@pytest.mark.asyncio
async def test_emitir_nota_focus_denegado(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Empresa Denegada", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="pendente")
    db.add(nota)
    db.flush()

    _req = httpx.Request("POST", "http://focus-test")
    resp_emissao = httpx.Response(202, json={}, request=_req)
    resp_status = httpx.Response(200, json={
        "status": "denegado",
        "erros": [{"codigo": "301", "mensagem": "CNPJ emitente irregular na Receita"}],
    }, request=_req)

    with patch("app.services.nfe_service._get_client") as mock_client_ctx, \
         patch("app.services.nfe_service.asyncio.sleep", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_emissao)
        mock_client.get = AsyncMock(return_value=resp_status)
        mock_client_ctx.return_value = mock_client

        resultado = await nfe_service.emitir_nota(db, nota, emp, {})

    assert resultado.status == "erro"
    assert resultado.denegada is True


@pytest.mark.asyncio
async def test_cancelar_nota_focus_sucesso(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp Cancel", cnpj="12345678000195")
    nota = NotaFiscal(
        empresa_id=emp.id, tipo="nfe", status="emitida",
        focus_ref="12345678000195-99",
    )
    db.add(nota)
    db.flush()

    resp_cancel = httpx.Response(
        200,
        json={"status": "cancelado"},
        request=httpx.Request("DELETE", "https://homologacao.focusnfe.com.br/v2/nfe/12345678000195-99"),
    )

    with patch("app.services.nfe_service._get_client") as mock_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.delete = AsyncMock(return_value=resp_cancel)
        mock_ctx.return_value = mock_client

        resultado = await nfe_service.cancelar_nota(db, nota, emp, "Erro no preço informado")

    assert resultado.status == "cancelada"
    assert resultado.cancelamento_motivo == "Erro no preço informado"


@pytest.mark.asyncio
async def test_cancelar_nota_focus_sem_ref_levanta_erro(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp SemRef", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="emitida", focus_ref=None)
    db.add(nota)
    db.flush()

    with pytest.raises(ValueError, match="focus_ref"):
        await nfe_service.cancelar_nota(db, nota, emp, "motivo qualquer")


# ---------------------------------------------------------------------------
# Task 9 — _path_focus tipos de nota
# ---------------------------------------------------------------------------

def test_path_focus_tipos():
    from app.services.nfe_service import _path_focus
    assert _path_focus("nfe", "12345678000195-1") == "/v2/nfe/12345678000195-1"
    assert _path_focus("nfce", "12345678000195-2") == "/v2/nfce/12345678000195-2"
    assert _path_focus("nfse", "12345678000195-3") == "/v2/nfse/12345678000195-3"


@pytest.mark.asyncio
async def test_registrar_empresa_focus_sucesso(db):
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp Cert", cnpj="12345678000195")
    emp.email = "cert@teste.com"
    emp.telefone = "5511999990001"
    emp.endereco_cidade = "São Paulo"
    emp.endereco_uf = "SP"
    emp.endereco_cep = "01310100"
    emp.endereco_logradouro = "Av Paulista"
    emp.endereco_numero = "1000"
    emp.endereco_bairro = "Bela Vista"
    emp.inscricao_estadual = "118888888119"
    db.flush()

    cert_bytes = b"fake-pfx-content"
    senha = "senha123"

    resp_focus = httpx.Response(
        200,
        json={"id": "12345678000195", "status": "ativo"},
        request=httpx.Request("POST", "https://api.focusnfe.com.br/v2/empresas"),
    )

    with patch("app.services.nfe_service._get_client_empresas") as mock_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_focus)
        mock_ctx.return_value = mock_client

        resultado = await nfe_service.registrar_empresa_focus(emp, cert_bytes, senha)

    assert resultado["success"] is True
    assert emp.focus_certificado_configurado is True


@pytest.mark.asyncio
async def test_registrar_empresa_focus_atualiza_se_ja_existe(db):
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp Cert Existe", cnpj="12345678000195")
    emp.email = "cert2@teste.com"
    emp.telefone = "5511888880002"
    emp.endereco_cidade = "São Paulo"
    emp.endereco_uf = "SP"
    emp.endereco_cep = "01310100"
    emp.endereco_logradouro = "Rua X"
    emp.endereco_numero = "10"
    emp.endereco_bairro = "Centro"
    emp.focus_certificado_configurado = True
    db.flush()

    cert_bytes = b"new-pfx-content"
    senha = "nova_senha"

    resp_lista = httpx.Response(
        200,
        json=[{"id": 987, "cnpj": "12345678000195", "nome": "Emp Cert Existe"}],
        request=httpx.Request("GET", "https://api.focusnfe.com.br/v2/empresas"),
    )
    resp_focus = httpx.Response(
        200,
        json={"id": 987, "status": "ativo"},
        request=httpx.Request("PUT", "https://api.focusnfe.com.br/v2/empresas/987"),
    )

    with patch("app.services.nfe_service._get_client_empresas") as mock_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=resp_lista)
        mock_client.put = AsyncMock(return_value=resp_focus)
        mock_ctx.return_value = mock_client

        resultado = await nfe_service.registrar_empresa_focus(emp, cert_bytes, senha)

    assert resultado["success"] is True


@pytest.mark.asyncio
async def test_registrar_empresa_focus_cnpj_vazio_levanta_erro(db):
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp SemCNPJ", cnpj=None)

    with pytest.raises(ValueError, match="CNPJ"):
        await nfe_service.registrar_empresa_focus(emp, b"pfx", "senha")


@pytest.mark.asyncio
async def test_registrar_empresa_focus_exige_endereco_valido(db):
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp Sem Cidade", cnpj="12345678000195")
    emp.email = "x@teste.com"
    emp.endereco_cidade = "-"
    emp.endereco_uf = "SP"
    emp.endereco_cep = "01310100"
    db.flush()

    with pytest.raises(ValueError, match="Município"):
        await nfe_service.registrar_empresa_focus(emp, b"pfx", "senha")
