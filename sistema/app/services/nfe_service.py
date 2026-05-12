from app.core.config import settings
from app.core.crypto import decrypt_secret

def _get_api_key(empresa) -> str:
    return decrypt_secret(empresa.notaas_api_key, crypto_secret=settings.NOTAAS_CRYPTO_SECRET) or empresa.notaas_api_key or ""

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
from app.core.database import SessionLocal
from app.services.fiscal_ai_service import sugerir_dados_fiscais

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


_MAPA_PAGAMENTO = {
    "pix": "17",
    "cartao_credito": "03",
    "cartao_debito": "04",
    "boleto": "15",
    "dinheiro": "01",
    "cheque": "02",
}


async def _montar_payload_nfe(
    empresa: Empresa,
    orcamento: Orcamento,
    tipo: str,
    natureza_operacao: str,
    serie: str,
    itens_override=None,
) -> dict:
    """Monta o payload JSON para API Notaas baseado nos dados do orçamento.

    Notaas NF-e usa JSON próprio (não tags XML SEFAZ):
    - naturezaOperacao na raiz (não ide.natOp)
    - dest.cpf / dest.cnpj em minúsculas
    - dest.endereco (não enderDest)
    - items (não det)
    """
    cliente: Cliente = orcamento.cliente

    # Usa documento por presença real, não por tipo_pessoa
    limpo_cnpj = _limpar_doc(cliente.cnpj or "")
    limpo_cpf = _limpar_doc(cliente.cpf or "")
    if limpo_cnpj:
        dest_doc = {"cnpj": limpo_cnpj}
        dest_nome = cliente.razao_social or cliente.nome
    elif limpo_cpf:
        dest_doc = {"cpf": limpo_cpf}
        dest_nome = cliente.nome
    else:
        dest_doc = {}
        dest_nome = cliente.razao_social or cliente.nome

    # Notaas NF-e: campos em lowercase, sem nomes XML SEFAZ
    endereco_dest: dict = {
        "logradouro": cliente.logradouro or "",
        "numero": cliente.numero or "SN",
        "bairro": cliente.bairro or "",
        "cidade": cliente.cidade or "",
        "uf": cliente.estado or "",
        "cep": _limpar_cep(cliente.cep or ""),
    }
    if cliente.complemento:
        endereco_dest["complemento"] = cliente.complemento
    cod_mun = getattr(cliente, "codigo_municipio_ibge", None)
    if cod_mun:
        endereco_dest["codigoMunicipio"] = int(cod_mun)

    destinatario = {
        **dest_doc,
        "nome": dest_nome,
        "ie": cliente.inscricao_estadual or "",
        "email": cliente.email or "",
        "endereco": endereco_dest,
    }

    itens = itens_override or orcamento.itens
    items = []
    for item in itens:
        # Dados fiscais do catálogo (servico)
        servico = getattr(item, "servico", None)
        ncm = (getattr(servico, "ncm", None) or None) if servico else None
        cfop = (getattr(servico, "cfop", None) or "5102") if servico else "5102"
        csosn = (getattr(servico, "csosn", None) or "400") if servico else "400"
        unidade = (getattr(servico, "unidade_fiscal", None) or getattr(servico, "unidade", None) or "UN") if servico else "UN"

        # IA fallback: se não tem NCM no catálogo, pede para IA sugerir
        if not ncm:
            try:
                categoria = getattr(getattr(servico, "categoria", None), "nome", None) if servico else None
                sugestao = await sugerir_dados_fiscais(item.descricao, categoria)
                ncm = sugestao.get("ncm") or "00000000"
                if not getattr(servico, "cfop", None):
                    cfop = sugestao.get("cfop", "5102")
            except Exception:
                ncm = "00000000"

        # Notaas NF-e: estrutura flat (não aninhada em prod/imposto como SEFAZ XML)
        items.append({
            "descricao": item.descricao,
            "ncm": ncm,
            "cfop": cfop,
            "valorTotal": round(float(item.total), 2),
            "quantidade": float(item.quantidade),
            "valorUnitario": round(float(item.valor_unit), 2),
            "unidade": unidade,
            "csosn": csosn,
        })

    forma_pag = getattr(orcamento, "forma_pagamento", None) or ""
    tpag = _MAPA_PAGAMENTO.get(forma_pag.lower() if forma_pag else "", "99")

    return {
        "naturezaOperacao": natureza_operacao,
        "modelo": 55 if tipo == "nfe" else 65,
        "dest": destinatario,
        "items": items,
        # Notaas NF-e: "pagamentos" com tipoPagamento/valor (não pag.detPag.tPag)
        "pagamentos": [{"tipoPagamento": tpag, "valor": round(float(orcamento.total), 2)}],
    }


def _normalizar_codigo_servico(codigo: str) -> str:
    """Normaliza código LC116 para 6 dígitos sem pontos (formato Notaas).

    "1.07"  → "010700"   "17.06" → "170600"   "010302" → "010302"
    """
    if not codigo:
        return "170600"
    s = codigo.strip()
    if "." in s:
        partes = s.split(".")
        padded = [p.zfill(2) for p in partes[:3]]
        while len(padded) < 3:
            padded.append("00")
        return "".join(padded)
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return "170600"
    if len(digits) == 6:
        return digits
    if len(digits) == 5:
        return digits + "0"     # "01070" → "010700" (pad direito, não esquerdo)
    if len(digits) == 4:
        return digits + "00"    # "1706" → "170600"
    if len(digits) < 4:
        return digits.zfill(6)  # códigos muito curtos: zfill esquerdo
    return digits[:6]           # trunca se > 6


def _montar_payload_nfse(
    empresa: Empresa,
    orcamento: Orcamento,
    codigo_servico: str,
    aliquota_iss: Decimal,
) -> dict:
    """Monta payload NFS-e no formato real da API Notaas.

    Emitente NÃO vai no payload — fica configurado na conta Notaas vinculada à API key.
    Estrutura: tomador + servico + valores + competencia + referencia.
    """
    from datetime import date

    cliente: Cliente = orcamento.cliente
    nome_cliente = cliente.razao_social or cliente.nome

    # tomador: usa presença real do documento, não tipo_pessoa (pode ser inconsistente)
    limpo_cnpj = _limpar_doc(cliente.cnpj or "")
    limpo_cpf = _limpar_doc(cliente.cpf or "")
    if limpo_cnpj:
        doc_tomador = {"cnpj": limpo_cnpj}
    elif limpo_cpf:
        doc_tomador = {"cpf": limpo_cpf}
    else:
        doc_tomador = {}

    tomador: dict = {"nome": nome_cliente, **doc_tomador}
    if cliente.email:
        tomador["email"] = cliente.email
    if cliente.logradouro:
        tomador["endereco"] = {
            "logradouro": cliente.logradouro,
            "numero": cliente.numero or "S/N",
            "bairro": cliente.bairro or "",
            "cidade": cliente.cidade or "",
            "uf": cliente.estado or "",
            "cep": _limpar_cep(cliente.cep or ""),
        }
        if cliente.complemento:
            tomador["endereco"]["complemento"] = cliente.complemento

    # descricao agrega os itens do orçamento
    descricao = "; ".join(i.descricao for i in orcamento.itens) or "Prestação de serviços"

    return {
        "tomador": tomador,
        "servico": {
            "descricao": descricao,
            "codigo": _normalizar_codigo_servico(codigo_servico),
        },
        "valores": {
            "total": round(float(orcamento.total), 2),       # BUG5: evita float impreciso
            "aliquotaIss": round(float(aliquota_iss), 4),
            "issRetido": False,
        },
        "competencia": date.today().strftime("%Y-%m"),
        "referencia": orcamento.numero or str(orcamento.id),
    }


async def emitir_nota_background(nota_id: int, empresa_id: int, payload: dict) -> None:
    """Wrapper para rodar emitir_nota em BackgroundTask com session própria.

    BUG1-FIX: a session do request é fechada antes da background task executar.
    Esta função cria uma session nova, garantindo que o polling (~60s) funcione.
    """
    db = SessionLocal()
    try:
        nota = db.query(NotaFiscal).filter(NotaFiscal.id == nota_id).first()
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if nota and empresa:
            await emitir_nota(db, nota, empresa, payload)
    except Exception as e:
        logger.error("Erro no background task emitir_nota nota_id=%s: %s", nota_id, e)
        try:
            nota = db.query(NotaFiscal).filter(NotaFiscal.id == nota_id).first()
            if nota and nota.status not in ("emitida", "cancelada"):
                nota.status = "erro"
                nota.erro_codigo = "BACKGROUND_ERROR"
                nota.erro_mensagem = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def emitir_nota(
    db: Session,
    nota_fiscal: NotaFiscal,
    empresa: Empresa,
    payload: dict,
) -> NotaFiscal:
    """Envia payload para API Notaas e aguarda resultado por polling."""
    nota_fiscal.status = "processando"
    nota_fiscal.payload_enviado = payload
    db.commit()  # commit imediato para visibilidade do status

    endpoint = "/emitir" if nota_fiscal.tipo == "nfse" else "/nfe/emitir"

    async with _get_client(_get_api_key(empresa)) as client:
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
        db.commit()  # BUG4-FIX: commit para persistir invoice_id antes do polling longo

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
                nota_fiscal.numero = str(status_data.get("numeroNfe") or status_data.get("nfNumber") or "")
                # BUG3-FIX: NF-e usa chaveAcesso; NFS-e usa chNFSe
                nota_fiscal.chave_acesso = (
                    status_data.get("chaveAcesso")      # NF-e/NFC-e
                    or status_data.get("chNFSe")        # NFS-e
                    or status_data.get("accessKey")     # fallback legado
                )
                nota_fiscal.protocolo = status_data.get("nProt") or status_data.get("protocol")
                nota_fiscal.xml_url = status_data.get("xmlUrl")
                nota_fiscal.danfe_url = status_data.get("pdfUrl")
                nota_fiscal.emitida_em = datetime.utcnow()
                db.commit()
                return nota_fiscal

            if current_status == "error":
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = status_data.get("errorCode", "UNKNOWN")
                nota_fiscal.erro_mensagem = status_data.get("errorMessage", "Erro desconhecido")
                db.commit()
                return nota_fiscal

            if current_status == "cancelled":
                nota_fiscal.status = "cancelada"
                nota_fiscal.cancelada_em = datetime.utcnow()
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

    # Notaas usa /cancelar para NFS-e; NF-e usa /nfe/cancelar (confirmar quando docs disponíveis)
    endpoint = "/cancelar" if nota_fiscal.tipo == "nfse" else "/nfe/cancelar"
    payload = {"invoiceId": invoice_id, "motivo": motivo}

    async with _get_client(_get_api_key(empresa)) as client:
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
    """Valida HMAC-SHA256 do webhook Notaas.

    A Notaas envia o hex do HMAC diretamente no X-Notaas-Signature (sem prefixo sha256=).
    """
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    # Aceita com ou sem prefixo "sha256=" para compatibilidade
    sig = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, sig)


def _limpar_doc(doc: str) -> str:
    return "".join(filter(str.isdigit, doc or ""))


def _limpar_cep(cep: str) -> str:
    return "".join(filter(str.isdigit, cep or ""))
