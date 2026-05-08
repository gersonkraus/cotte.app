"""
nfe_service.py — Integração com API Notaas para emissão de NF-e/NFC-e/NFS-e.
URL base: https://platform.notaas.com.br/api/v1
Auth: header x-api-key por empresa (multi-tenant)
"""

import asyncio
import hashlib
import hmac
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.models.models import Empresa, NotaFiscal, Orcamento, Cliente

logger = logging.getLogger(__name__)

NOTAAS_BASE_URL = "https://platform.notaas.com.br/api/v1"
POLLING_INTERVAL = 3
POLLING_MAX_ATTEMPTS = 20


def _get_client(api_key: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=NOTAAS_BASE_URL,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        timeout=30.0,
    )


def _montar_payload_nfe(
    empresa: Empresa,
    orcamento: Orcamento,
    tipo: str,
    natureza_operacao: str,
    serie: str,
    itens_override=None,
) -> dict:
    """Monta o payload JSON para API Notaas baseado nos dados do orçamento."""
    cliente: Cliente = orcamento.cliente

    emitente = {
        "cnpj": _limpar_doc(empresa.cnpj),
        "xNome": empresa.nome,
        "xFant": empresa.nome,
        "IE": empresa.inscricao_estadual or "",
        "IM": empresa.inscricao_municipal or "",
        "CRT": empresa.crt or 1,
        "enderEmit": {
            "xLgr": empresa.endereco_logradouro or "",
            "nro": empresa.endereco_numero or "S/N",
            "xCpl": empresa.endereco_complemento or "",
            "xBairro": empresa.endereco_bairro or "",
            "xMun": empresa.endereco_cidade or "",
            "UF": empresa.endereco_uf or "",
            "CEP": _limpar_cep(empresa.endereco_cep or ""),
            "cMun": empresa.endereco_codigo_municipio_ibge or "",
        },
    }

    if cliente.tipo_pessoa == "PJ":
        dest_doc = {"CNPJ": _limpar_doc(cliente.cnpj or "")}
        dest_nome = cliente.razao_social or cliente.nome
    else:
        dest_doc = {"CPF": _limpar_doc(cliente.cpf or "")} if cliente.cpf else {}
        dest_nome = cliente.nome

    destinatario = {
        **dest_doc,
        "xNome": dest_nome,
        "IE": cliente.inscricao_estadual or "",
        "email": cliente.email or "",
        "enderDest": {
            "xLgr": cliente.logradouro or "",
            "nro": cliente.numero or "S/N",
            "xCpl": cliente.complemento or "",
            "xBairro": cliente.bairro or "",
            "xMun": cliente.cidade or "",
            "UF": cliente.estado or "",
            "CEP": _limpar_cep(cliente.cep or ""),
        },
    }

    itens = itens_override or orcamento.itens
    det = []
    for idx, item in enumerate(itens, start=1):
        det.append({
            "nItem": idx,
            "prod": {
                "cProd": str(item.servico_id or idx),
                "xProd": item.descricao,
                "NCM": getattr(item, "ncm", "00000000") or "00000000",
                "CFOP": getattr(item, "cfop", "5933") or "5933",
                "uCom": "UN",
                "qCom": str(item.quantidade),
                "vUnCom": str(item.valor_unit),
                "vProd": str(item.total),
                "indTot": 1,
            },
            "imposto": {
                "ICMS": {"ICMSSN400": {"orig": 0, "CSOSN": "400"}},
                "PIS": {"PISAliq": {"CST": "07", "vBC": "0.00", "pPIS": "0.00", "vPIS": "0.00"}},
                "COFINS": {"COFINSAliq": {"CST": "07", "vBC": "0.00", "pCOFINS": "0.00", "vCOFINS": "0.00"}},
            },
        })

    total = str(orcamento.total)

    return {
        "ide": {
            "tpAmb": 1 if empresa.notaas_ambiente == "producao" else 2,
            "mod": 55 if tipo == "nfe" else 65,
            "serie": int(serie),
            "natOp": natureza_operacao,
        },
        "emit": emitente,
        "dest": destinatario,
        "det": det,
        "total": {"ICMSTot": {"vNF": total, "vProd": total}},
        "transp": {"modFrete": 9},
        "pag": {"detPag": [{"indPag": 0, "tPag": "01", "vPag": total}]},
    }


def _montar_payload_nfse(
    empresa: Empresa,
    orcamento: Orcamento,
    codigo_servico: str,
    aliquota_iss: Decimal,
) -> dict:
    """Monta payload para NFS-e (serviço)."""
    cliente: Cliente = orcamento.cliente
    total = str(orcamento.total)

    return {
        "prestador": {
            "cnpj": _limpar_doc(empresa.cnpj),
            "im": empresa.inscricao_municipal or "",
        },
        "tomador": {
            "cpfCnpj": _limpar_doc(cliente.cnpj or cliente.cpf or ""),
            "nome": cliente.razao_social or cliente.nome,
            "email": cliente.email or "",
            "endereco": {
                "logradouro": cliente.logradouro or "",
                "numero": cliente.numero or "S/N",
                "complemento": cliente.complemento or "",
                "bairro": cliente.bairro or "",
                "codigoMunicipio": empresa.endereco_codigo_municipio_ibge or "",
                "uf": cliente.estado or "",
                "cep": _limpar_cep(cliente.cep or ""),
            },
        },
        "servico": {
            "valorServicos": total,
            "issRetido": False,
            "aliquota": float(aliquota_iss),
            "itemListaServico": codigo_servico,
            "discriminacao": "; ".join(i.descricao for i in orcamento.itens),
            "codigoMunicipio": empresa.endereco_codigo_municipio_ibge or "",
        },
    }


async def emitir_nota(
    db: Session,
    nota_fiscal: NotaFiscal,
    empresa: Empresa,
    payload: dict,
) -> NotaFiscal:
    """Envia payload para API Notaas e aguarda resultado por polling."""
    nota_fiscal.status = "processando"
    nota_fiscal.payload_enviado = payload
    db.flush()

    endpoint = "/nfse/emitir" if nota_fiscal.tipo == "nfse" else "/nfe/emitir"

    async with _get_client(empresa.notaas_api_key) as client:
        try:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = str(e.response.status_code)
            nota_fiscal.erro_mensagem = e.response.text[:500]
            db.commit()
            return nota_fiscal
        except httpx.RequestError as e:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = "REQUEST_ERROR"
            nota_fiscal.erro_mensagem = str(e)[:500]
            db.commit()
            return nota_fiscal

        invoice_id = data.get("invoiceId")
        if not invoice_id:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_mensagem = "invoiceId ausente na resposta"
            db.commit()
            return nota_fiscal

        nota_fiscal.notaas_invoice_id = invoice_id
        db.flush()

        for _ in range(POLLING_MAX_ATTEMPTS):
            await asyncio.sleep(POLLING_INTERVAL)
            try:
                status_resp = await client.get(f"/invoices/{invoice_id}/status")
            except httpx.RequestError:
                continue

            if status_resp.status_code == 404:
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = "INVOICE_NOT_FOUND"
                nota_fiscal.erro_mensagem = "Invoice não encontrado na Notaas"
                db.commit()
                return nota_fiscal
            if status_resp.status_code >= 400:
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = str(status_resp.status_code)
                nota_fiscal.erro_mensagem = status_resp.text[:200]
                db.commit()
                return nota_fiscal
            if status_resp.status_code != 200:
                continue

            status_data = status_resp.json()
            current_status = status_data.get("status")

            if current_status == "issued":
                nota_fiscal.status = "emitida"
                nota_fiscal.numero = str(status_data.get("nfNumber", ""))
                nota_fiscal.serie = str(status_data.get("nfSerie", nota_fiscal.serie or ""))
                nota_fiscal.chave_acesso = status_data.get("accessKey")
                nota_fiscal.protocolo = status_data.get("protocol")
                nota_fiscal.xml_url = status_data.get("xmlUrl")
                nota_fiscal.danfe_url = status_data.get("pdfUrl")
                nota_fiscal.emitida_em = datetime.utcnow()
                db.commit()
                return nota_fiscal

            if current_status == "error":
                erro = status_data.get("error", {})
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = erro.get("code", "UNKNOWN")
                nota_fiscal.erro_mensagem = erro.get("message", "Erro desconhecido")
                db.commit()
                return nota_fiscal

    nota_fiscal.status = "erro"
    nota_fiscal.erro_mensagem = "Timeout aguardando processamento da SEFAZ"
    db.commit()
    return nota_fiscal


async def cancelar_nota(
    db: Session,
    nota_fiscal: NotaFiscal,
    empresa: Empresa,
    motivo: str,
) -> NotaFiscal:
    """Cancela uma NF emitida."""
    invoice_id = nota_fiscal.notaas_invoice_id
    if not invoice_id:
        raise ValueError("Nota sem invoiceId para cancelar")

    endpoint = "/nfse/cancelar" if nota_fiscal.tipo == "nfse" else "/nfe/cancelar"
    payload = {"invoiceId": invoice_id, "justificativa": motivo}

    async with _get_client(empresa.notaas_api_key) as client:
        try:
            resp = await client.post(endpoint, json=payload)
            if resp.status_code not in (200, 202):
                raise httpx.HTTPStatusError(
                    f"Cancelamento falhou: {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
        except httpx.RequestError as e:
            raise ValueError(f"Erro de conexão ao cancelar nota: {e}") from e

    nota_fiscal.status = "cancelada"
    nota_fiscal.cancelada_em = datetime.utcnow()
    nota_fiscal.cancelamento_motivo = motivo
    db.commit()
    return nota_fiscal


def verificar_assinatura_webhook(body: bytes, signature: str, secret: str) -> bool:
    """Valida HMAC-SHA256 do webhook Notaas."""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def _limpar_doc(doc: str) -> str:
    return "".join(filter(str.isdigit, doc or ""))


def _limpar_cep(cep: str) -> str:
    return "".join(filter(str.isdigit, cep or ""))
