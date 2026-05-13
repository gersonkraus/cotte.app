"""
nfe_service.py — Integração com API Focus NFe para emissão de NF-e/NFC-e/NFS-e.
URLs notas: https://api.focusnfe.com.br (prod) | https://homologacao.focusnfe.com.br (homolog)
URL empresas/certificado: sempre https://api.focusnfe.com.br (API de cadastro só neste host, doc. Focus)
Auth: HTTP Basic Auth — token como username, senha vazia (token único COTTE no .env)
Multitenancy: ref = "{cnpj_emitente}-{nota_id}" por nota
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Empresa, NotaFiscal, Orcamento, Cliente
from app.core.database import SessionLocal
from app.services.fiscal_ai_service import sugerir_dados_fiscais

logger = logging.getLogger(__name__)

POLLING_INTERVAL = 3
POLLING_MAX_ATTEMPTS = 20


def _focus_base_url() -> str:
    if settings.FOCUS_AMBIENTE == "producao":
        return "https://api.focusnfe.com.br"
    return "https://homologacao.focusnfe.com.br"


def _focus_base_url_empresas() -> str:
    """Host da API de cadastro de empresas/certificado na Focus.

    A documentação oficial indica que a API de Empresas opera somente no host
    de produção (`api.focusnfe.com.br`), mesmo quando as notas são emitidas em
    homologação; o token do painel continua sendo o de autenticação Basic.
    """
    return "https://api.focusnfe.com.br"


def _get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_focus_base_url(),
        auth=(settings.FOCUS_TOKEN, ""),
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )


def _get_client_empresas() -> httpx.AsyncClient:
    """Cliente HTTP só para rotas /v2/empresas (sempre host de produção da Focus)."""
    return httpx.AsyncClient(
        base_url=_focus_base_url_empresas(),
        auth=(settings.FOCUS_TOKEN, ""),
        headers={"Content-Type": "application/json"},
        timeout=60.0,
    )


def _gerar_ref(empresa: Empresa, nota_id: int) -> str:
    cnpj = re.sub(r"\D", "", empresa.cnpj or "")
    if not cnpj:
        raise ValueError("Empresa sem CNPJ — impossível gerar ref Focus")
    return f"{cnpj}-{nota_id}"


def _path_focus(tipo: str, ref: str) -> str:
    """Caminho relativo para consulta/cancelamento na Focus por tipo de nota."""
    t = (tipo or "").lower()
    if t == "nfce":
        return f"/v2/nfce/{ref}"
    if t == "nfse":
        return f"/v2/nfse/{ref}"
    return f"/v2/nfe/{ref}"


def _endpoint_emissao_focus(tipo: str) -> str:
    t = (tipo or "").lower()
    if t == "nfce":
        return "/v2/nfce"
    if t == "nfse":
        return "/v2/nfse"
    return "/v2/nfe"



_MAPA_PAGAMENTO = {
    "pix": "17",
    "cartao_credito": "03",
    "cartao_debito": "04",
    "boleto": "15",
    "dinheiro": "01",
    "cheque": "02",
}


def _regime_tributario_para_focus(regime: Optional[str]) -> int:
    """Converte regime tributário do COTTE para código numérico da Focus NFe.

    Focus NFe aceita:
      1 = Simples Nacional
      2 = Simples Nacional — excesso de receita
      3 = Regime Normal
    """
    if not regime:
        return 1
    r = regime.lower()
    if "simples" in r or "mei" in r:
        return 1
    return 3


def _sanitizar_texto_fiscal(texto: Optional[str]) -> Optional[str]:
    """Remove placeholders que a API da Focus rejeita (ex.: '-' como município)."""
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
        return None
    tl = t.lower()
    if t in ("-", "—", "–", ".", "..", "...", "null", "none"):
        return None
    if tl in ("n/a", "na", "s/n", "sn", "inválido", "invalido", "cidade", "município", "municipio", "digite", "a definir"):
        return None
    return t


def _montar_payload_cadastro_empresa_focus_com_certificado(
    empresa: Empresa,
    cert_b64: str,
    senha_certificado: str,
) -> Dict[str, Any]:
    """Monta JSON para POST/PUT ``/v2/empresas`` com endereço exigido pela Focus.

    A validação da Focus falha com \"Município inválido: -\" quando o cadastro
    COTTE usa '-' ou vazio em cidade/UF/CEP.
    """
    cnpj = re.sub(r"\D", "", empresa.cnpj or "")
    if not cnpj:
        raise ValueError("Empresa sem CNPJ — impossível registrar na Focus NFe")

    email = _sanitizar_texto_fiscal(empresa.email)
    if not email or "@" not in email:
        raise ValueError(
            "E-mail da empresa é obrigatório e deve ser válido (Configurações) "
            "para cadastro na Focus NFe."
        )

    mun = _sanitizar_texto_fiscal(getattr(empresa, "endereco_cidade", None))
    if not mun:
        raise ValueError(
            "Município (cidade) do endereço fiscal é obrigatório nas configurações da empresa. "
            "Informe o nome completo do município (a Focus rejeita '-' ou campo vazio)."
        )

    uf_raw = _sanitizar_texto_fiscal(getattr(empresa, "endereco_uf", None))
    uf = (uf_raw or "").upper()[:2]
    if len(uf) != 2:
        raise ValueError(
            "UF do endereço fiscal deve ter 2 letras (ex.: SP) nas configurações da empresa."
        )

    logradouro = _sanitizar_texto_fiscal(getattr(empresa, "endereco_logradouro", None)) or "Não informado"
    bairro = _sanitizar_texto_fiscal(getattr(empresa, "endereco_bairro", None)) or "Centro"

    cep_digits = re.sub(r"\D", "", getattr(empresa, "endereco_cep", None) or "")
    if len(cep_digits) != 8:
        raise ValueError(
            "CEP fiscal com 8 dígitos é obrigatório nas configurações da empresa para cadastro na Focus NFe."
        )

    num_raw = _sanitizar_texto_fiscal(getattr(empresa, "endereco_numero", None))
    numero_int = 0
    if num_raw:
        m = re.match(r"^(\d+)", str(num_raw))
        if m:
            numero_int = int(m.group(1))

    complemento = _sanitizar_texto_fiscal(getattr(empresa, "endereco_complemento", None))

    razao = _sanitizar_texto_fiscal(empresa.nome) or "Razão social"
    payload: Dict[str, Any] = {
        "cnpj": cnpj,
        "nome": razao,
        "nome_fantasia": razao[:150],
        "regime_tributario": _regime_tributario_para_focus(empresa.regime_tributario),
        "logradouro": logradouro,
        "numero": numero_int,
        "bairro": bairro,
        "municipio": mun,
        "uf": uf,
        "cep": int(cep_digits),
        "email": email,
        "habilita_nfe": True,
        "arquivo_certificado_base64": cert_b64,
        "senha_certificado": senha_certificado,
    }
    if complemento:
        payload["complemento"] = complemento

    ie = _sanitizar_texto_fiscal(getattr(empresa, "inscricao_estadual", None))
    if ie and re.fullmatch(r"\d+", ie):
        payload["inscricao_estadual"] = int(ie)

    im = _sanitizar_texto_fiscal(getattr(empresa, "inscricao_municipal", None))
    if im and re.fullmatch(r"\d+", im):
        payload["inscricao_municipal"] = int(im)

    cm = re.sub(r"\D", "", getattr(empresa, "endereco_codigo_municipio_ibge", None) or "")
    if len(cm) in (7, 8):
        payload["codigo_municipio"] = cm

    tel = re.sub(r"\D", "", getattr(empresa, "telefone", None) or "")
    if tel:
        payload["telefone"] = tel

    return payload


def _normalizar_texto_ibge(s: str) -> str:
    if not s:
        return ""
    nfd = unicodedata.normalize("NFD", s.strip().lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _codigo_ibge_7_valido(val: Optional[str]) -> Optional[int]:
    if not val:
        return None
    d = "".join(c for c in str(val) if c.isdigit())
    if len(d) == 7:
        return int(d)
    return None


async def _buscar_ibge_via_cep(cep_limpo: str) -> Optional[int]:
    """Consulta ViaCEP e retorna código IBGE do município (7 dígitos) ou None."""
    if len(cep_limpo) != 8:
        return None
    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            if data.get("erro"):
                return None
            ibge = data.get("ibge")
            if not ibge:
                return None
            return _codigo_ibge_7_valido(str(ibge))
    except Exception as e:
        logger.warning("ViaCEP indisponível ou erro ao consultar CEP %s: %s", cep_limpo, e)
        return None


async def _buscar_ibge_por_cidade_uf(cidade: str, uf: str) -> Optional[int]:
    """API pública IBGE: match por nome do município (normalizado)."""
    uf = (uf or "").strip().upper()
    if len(uf) != 2 or not cidade or not cidade.strip():
        return None
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
    alvo = _normalizar_texto_ibge(cidade)
    if not alvo:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            lista = r.json()
            if not isinstance(lista, list):
                return None
            for mun in lista:
                nome = mun.get("nome") or ""
                if _normalizar_texto_ibge(nome) == alvo:
                    mid = mun.get("id")
                    if mid is not None:
                        return _codigo_ibge_7_valido(str(mid))
            return None
    except Exception as e:
        logger.warning("IBGE municípios indisponível UF=%s: %s", uf, e)
        return None


async def resolver_codigo_municipio_ibge(
    cliente: Cliente,
    db: Optional[Session] = None,
    persistir_se_viacep: bool = True,
) -> Tuple[Optional[int], str]:
    """Resolve código IBGE (7 dígitos) para dest.endereco.codigoMunicipio (Focus).

    Ordem: campo do cliente → ViaCEP (CEP) → API IBGE (cidade+UF).
    Persiste em `cliente.codigo_municipio_ibge` apenas quando a fonte for ViaCEP.
    """
    cod = _codigo_ibge_7_valido(getattr(cliente, "codigo_municipio_ibge", None))
    if cod is not None:
        return cod, "cliente"

    cep = _limpar_cep(cliente.cep or "")
    cod = await _buscar_ibge_via_cep(cep)
    if cod is not None:
        if persistir_se_viacep and db is not None and hasattr(cliente, "codigo_municipio_ibge"):
            cliente.codigo_municipio_ibge = f"{cod:07d}"
            try:
                db.add(cliente)
            except Exception:
                pass
        return cod, "viacep"

    cod = await _buscar_ibge_por_cidade_uf(cliente.cidade or "", cliente.estado or "")
    if cod is not None:
        return cod, "ibge_api"

    return None, "nao_resolvido"


def _cfop_padrao_por_uf_empresa_cliente(empresa: Empresa, cliente: Cliente) -> str:
    """Heurística Simples: mesma UF → 5102; UF diferente (quando ambas conhecidas) → 6102."""
    uf_e = (getattr(empresa, "endereco_uf", None) or "").strip().upper()
    uf_c = (getattr(cliente, "estado", None) or "").strip().upper()
    if len(uf_e) == 2 and len(uf_c) == 2 and uf_e != uf_c:
        return "6102"
    return "5102"


def _normalizar_cfop_para_string(cfop: object, padrao: str) -> str:
    """A Focus exige CFOP como string de 4 dígitos."""
    if cfop is None:
        return padrao
    digitos = "".join(c for c in str(cfop) if c.isdigit())
    if len(digitos) >= 4:
        return digitos[:4]
    if len(digitos) > 0:
        return digitos.zfill(4)
    return padrao


def _cfop_formato_focus_valido(cfop_str: str) -> bool:
    """CFOP deve ser exatamente 4 dígitos (string), conforme Focus."""
    return bool(cfop_str) and len(cfop_str) == 4 and cfop_str.isdigit()


def _quantidade_valores_item_nfe(item) -> tuple[float, float, float]:
    """Quantidade, valor unitário e total coerentes para linha da NF-e."""
    qtd = float(item.quantidade or 0)
    if qtd <= 0:
        qtd = 1.0
    v_unit = float(item.valor_unit or 0)
    v_total = float(item.total or 0)
    if v_total <= 0 and qtd > 0 and v_unit > 0:
        v_total = round(qtd * v_unit, 2)
    if v_unit <= 0 and qtd > 0 and v_total > 0:
        v_unit = round(v_total / qtd, 2)
    return qtd, v_unit, v_total


def _normalizar_ncm_para_string(ncm: object) -> str:
    """NCM com 8 dígitos numéricos (string)."""
    if ncm is None:
        return "00000000"
    digitos = "".join(c for c in str(ncm) if c.isdigit())
    if len(digitos) >= 8:
        return digitos[:8]
    if len(digitos) >= 4:
        return digitos.ljust(8, "0")[:8]
    return "00000000"


def _tz_brasilia() -> ZoneInfo:
    return ZoneInfo("America/Sao_Paulo")


def _data_emissao_focus_iso() -> str:
    """Data/hora de emissão no formato ISO com offset de Brasília (exigência Focus)."""
    return datetime.now(_tz_brasilia()).isoformat(timespec="seconds")


def _empresa_optante_simples(empresa: Empresa) -> bool:
    try:
        c = int(empresa.crt) if empresa.crt is not None else None
    except (TypeError, ValueError):
        c = None
    if c is not None:
        return c in (1, 2)
    r = (empresa.regime_tributario or "").lower()
    return "simples" in r or "mei" in r


def _icms_situacao_tributaria_item(empresa: Empresa, servico) -> int:
    """CST/CSOSN numérico conforme documentação Focus (ItemNotaFiscal)."""
    if _empresa_optante_simples(empresa):
        raw = (getattr(servico, "csosn", None) or "102") if servico else "102"
        digits = "".join(c for c in str(raw) if c.isdigit())
        if len(digits) >= 3:
            return int(digits[:3])
        if digits:
            return int(digits)
        return 102
    # Regime normal: serviços comuns sem ICMS destacado → 41 (não tributada)
    return 41


def _icms_origem_item(servico) -> int:
    if not servico:
        return 0
    try:
        return int(getattr(servico, "origem", None) or 0)
    except (TypeError, ValueError):
        return 0


def _local_destino_focus(empresa: Empresa, cliente: Cliente) -> int:
    uf_e = (getattr(empresa, "endereco_uf", None) or "").strip().upper()
    uf_c = (getattr(cliente, "estado", None) or "").strip().upper()
    if len(uf_e) == 2 and len(uf_c) == 2 and uf_e != uf_c:
        return 2
    return 1


def _consumidor_final_focus(cliente: Cliente) -> int:
    limpo_cnpj = _limpar_doc(cliente.cnpj or "")
    if limpo_cnpj and len(limpo_cnpj) == 14:
        return 0
    return 1


def _indicador_ie_destinatario_focus(cliente: Cliente) -> int:
    ie = (cliente.inscricao_estadual or "").strip()
    if ie and ie.upper() not in ("ISENTO", "NAO", "N/A"):
        return 1
    return 9


def _cfop_int(cfop_str: str) -> int:
    d = "".join(c for c in str(cfop_str) if c.isdigit())
    if len(d) >= 4:
        return int(d[:4])
    return int(d) if d else 5102


def focus_media_absolute_url(caminho: Optional[str]) -> Optional[str]:
    """Converte caminho relativo retornado pela Focus (/arquivos/...) em URL absoluta."""
    if not caminho:
        return None
    s = str(caminho).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/"):
        return f"{_focus_base_url().rstrip('/')}{s}"
    return s


async def montar_payload_focus_nfe(
    empresa: Empresa,
    orcamento: Orcamento,
    tipo: str,
    natureza_operacao: str,
    serie: str,
    itens_override=None,
    db: Optional[Session] = None,
) -> dict:
    """Monta o corpo JSON para POST /v2/nfe ou /v2/nfce (API Focus NFe v2).

    A referência `ref` vai na query string (?ref=), conforme manual Focus.
    """
    cliente: Cliente = orcamento.cliente
    if not cliente:
        raise ValueError("Orçamento sem cliente — impossível emitir NF-e")

    limpo_cnpj = _limpar_doc(cliente.cnpj or "")
    limpo_cpf = _limpar_doc(cliente.cpf or "")
    if limpo_cnpj:
        dest_nome = (cliente.razao_social or cliente.nome or "").strip() or "Destinatário"
    else:
        dest_nome = (cliente.nome or cliente.razao_social or "").strip() or "Destinatário"

    cod_ibge, _fonte_ibge = await resolver_codigo_municipio_ibge(
        cliente, db=db, persistir_se_viacep=True
    )

    cnpj_emit = _limpar_doc(empresa.cnpj or "")
    if not cnpj_emit:
        raise ValueError("Empresa sem CNPJ emitente")

    data_emissao = _data_emissao_focus_iso()
    cfop_padrao_uf = _cfop_padrao_por_uf_empresa_cliente(empresa, cliente)

    lista_itens = list(itens_override) if itens_override is not None else list(orcamento.itens)
    items_focus: List[Dict[str, Any]] = []
    soma_produtos = 0.0

    for idx, row in enumerate(lista_itens, start=1):
        servico = None
        if isinstance(row, dict):
            ncm_raw = row.get("ncm")
            cfop_catalogo = row.get("cfop")
            unidade = str(row.get("unidade") or "UN")
            qtd = float(row.get("quantidade") or 1)
            v_unit = float(row.get("valor_unit") or 0)
            v_total = float(row.get("total") or 0)
            if v_total <= 0 and qtd > 0 and v_unit > 0:
                v_total = round(qtd * v_unit, 2)
            if v_unit <= 0 and qtd > 0 and v_total > 0:
                v_unit = round(v_total / qtd, 2)
            cod_prod = str(row.get("codigo_produto") or idx)
            descricao_item = str(row.get("descricao") or "").strip()
        elif hasattr(row, "orcamento_id"):
            servico = getattr(row, "servico", None)
            ncm_raw = (getattr(servico, "ncm", None) or None) if servico else None
            cfop_catalogo = (getattr(servico, "cfop", None) or None) if servico else None
            unidade = (
                (getattr(servico, "unidade_fiscal", None) or getattr(servico, "unidade", None) or "UN")
                if servico
                else "UN"
            )
            qtd, v_unit, v_total = _quantidade_valores_item_nfe(row)
            cod_prod = str(getattr(servico, "id", None) or getattr(row, "id", None) or idx)
            descricao_item = (getattr(row, "descricao", None) or "").strip()
        else:
            ncm_raw = getattr(row, "ncm", None)
            cfop_catalogo = getattr(row, "cfop", None)
            unidade = str(getattr(row, "unidade", None) or "UN")
            qtd = float(getattr(row, "quantidade", None) or 1)
            v_unit = float(getattr(row, "valor_unit", None) or 0)
            v_total = float(getattr(row, "total", None) or 0)
            if v_total <= 0 and qtd > 0 and v_unit > 0:
                v_total = round(qtd * v_unit, 2)
            if v_unit <= 0 and qtd > 0 and v_total > 0:
                v_unit = round(v_total / qtd, 2)
            cod_prod = str(idx)
            descricao_item = (getattr(row, "descricao", None) or "").strip()

        if not descricao_item and servico and getattr(servico, "nome", None):
            descricao_item = (servico.nome or "").strip()
        if not descricao_item:
            descricao_item = "Item conforme orçamento"

        ncm = _normalizar_ncm_para_string(ncm_raw) if ncm_raw else None
        cfop = _normalizar_cfop_para_string(
            cfop_catalogo if cfop_catalogo is not None else cfop_padrao_uf, cfop_padrao_uf
        )

        precisa_ia_ncm_cfop = not ncm_raw or ncm == "00000000" or not _cfop_formato_focus_valido(cfop)
        if precisa_ia_ncm_cfop:
            try:
                categoria = getattr(getattr(servico, "categoria", None), "nome", None) if servico else None
                sugestao = await sugerir_dados_fiscais(descricao_item, categoria)
                if not ncm_raw or ncm == "00000000":
                    ncm = (
                        _normalizar_ncm_para_string(sugestao.get("ncm"))
                        if sugestao.get("ncm")
                        else "00000000"
                    )
                if not cfop_catalogo or not _cfop_formato_focus_valido(cfop):
                    sug_cfop = sugestao.get("cfop")
                    cfop = _normalizar_cfop_para_string(
                        sug_cfop if sug_cfop else cfop_padrao_uf, cfop_padrao_uf
                    )
            except Exception:
                ncm = ncm or "00000000"
                cfop = _normalizar_cfop_para_string(cfop_padrao_uf, cfop_padrao_uf)

        if not _cfop_formato_focus_valido(cfop):
            cfop = _normalizar_cfop_para_string(cfop_padrao_uf, "5102")
        ncm = _normalizar_ncm_para_string(ncm)
        cfop_i = _cfop_int(cfop)
        icms_st = _icms_situacao_tributaria_item(empresa, servico)
        icms_or = _icms_origem_item(servico)
        valor_bruto = round(float(v_total), 2)
        soma_produtos += valor_bruto

        unidade_c = (unidade or "UN")[:6]
        item_payload: Dict[str, Any] = {
            "numero_item": idx,
            "codigo_produto": cod_prod,
            "descricao": descricao_item[:120],
            "cfop": cfop_i,
            "unidade_comercial": unidade_c.lower() if unidade_c else "un",
            "quantidade_comercial": float(qtd),
            "valor_unitario_comercial": round(float(v_unit), 10),
            "valor_unitario_tributavel": round(float(v_unit), 10),
            "unidade_tributavel": unidade_c.lower() if unidade_c else "un",
            "codigo_ncm": int(ncm)
            if ncm.isdigit()
            else int("".join(c for c in ncm if c.isdigit()).ljust(8, "0")[:8] or "61000000"),
            "quantidade_tributavel": float(qtd),
            "valor_bruto": valor_bruto,
            "icms_situacao_tributaria": icms_st,
            "icms_origem": icms_or,
            "pis_situacao_tributaria": "07",
            "cofins_situacao_tributaria": "07",
        }
        items_focus.append(item_payload)

    valor_total = round(float(orcamento.total), 2)
    if abs(valor_total - round(soma_produtos, 2)) > 0.05:
        valor_total = round(soma_produtos, 2)

    forma_pag = getattr(orcamento, "forma_pagamento", None) or ""
    tpag = _MAPA_PAGAMENTO.get(forma_pag.lower() if forma_pag else "", "99")
    formas_pagamento = [{"forma_pagamento": str(tpag), "valor_pagamento": f"{valor_total:.2f}"}]

    cep_emit = _limpar_cep(empresa.endereco_cep or "") or "00000000"
    cep_dest = _limpar_cep(cliente.cep or "") or ""

    payload: Dict[str, Any] = {
        "natureza_operacao": (natureza_operacao or "Venda de mercadorias").strip()[:120],
        "data_emissao": data_emissao,
        "data_entrada_saida": data_emissao,
        "tipo_documento": 1,
        "local_destino": _local_destino_focus(empresa, cliente),
        "finalidade_emissao": 1,
        "consumidor_final": _consumidor_final_focus(cliente),
        "presenca_comprador": 2 if (tipo or "").lower() == "nfe" else 1,
        "cnpj_emitente": cnpj_emit,
        "nome_emitente": (empresa.nome or "").strip()[:120],
        "logradouro_emitente": (empresa.endereco_logradouro or "").strip()[:60],
        "numero_emitente": str(empresa.endereco_numero or "S/N")[:10],
        "bairro_emitente": (empresa.endereco_bairro or "").strip()[:60],
        "municipio_emitente": (empresa.endereco_cidade or "").strip()[:60],
        "uf_emitente": (empresa.endereco_uf or "SP").strip().upper()[:2],
        "cep_emitente": cep_emit,
        "inscricao_estadual_emitente": (empresa.inscricao_estadual or "").strip()[:20],
        "regime_tributario_emitente": _regime_tributario_para_focus(empresa.regime_tributario),
        "nome_destinatario": dest_nome[:120],
        "logradouro_destinatario": (cliente.logradouro or "").strip()[:60],
        "numero_destinatario": str(cliente.numero or "S/N")[:10],
        "bairro_destinatario": (cliente.bairro or "").strip()[:60],
        "municipio_destinatario": (cliente.cidade or "").strip()[:60],
        "uf_destinatario": (cliente.estado or "").strip().upper()[:2],
        "cep_destinatario": cep_dest if cep_dest else "00000000",
        "pais_destinatario": "Brasil",
        "indicador_inscricao_estadual_destinatario": _indicador_ie_destinatario_focus(cliente),
        "valor_frete": 0.0,
        "valor_seguro": 0.0,
        "valor_desconto": 0.0,
        "valor_outras_despesas": 0.0,
        "valor_total": valor_total,
        "valor_produtos": round(soma_produtos, 2),
        "modalidade_frete": 9,
        "items": items_focus,
        "formas_pagamento": formas_pagamento,
        "serie": str(serie or "1").strip()[:3] or "1",
    }

    if limpo_cnpj:
        payload["cnpj_destinatario"] = limpo_cnpj
        if (cliente.inscricao_estadual or "").strip():
            payload["inscricao_estadual_destinatario"] = (cliente.inscricao_estadual or "").strip()[:20]
    elif limpo_cpf:
        payload["cpf_destinatario"] = limpo_cpf

    tel_cli = _limpar_doc(getattr(cliente, "telefone", None) or "")
    if tel_cli:
        if len(tel_cli) <= 11 and tel_cli.isdigit():
            payload["telefone_destinatario"] = int(tel_cli)
        else:
            payload["telefone_destinatario"] = tel_cli[:15]

    if cliente.email:
        payload["email_destinatario"] = (cliente.email or "").strip()[:60]

    if cod_ibge is not None:
        payload["codigo_municipio_destinatario"] = f"{cod_ibge:07d}"

    return payload


async def _montar_payload_nfe(
    empresa: Empresa,
    orcamento: Orcamento,
    tipo: str,
    natureza_operacao: str,
    serie: str,
    itens_override=None,
    db: Optional[Session] = None,
) -> dict:
    """Alias: monta JSON Focus v2 para NF-e / NFC-e (compatível com rotas existentes)."""
    return await montar_payload_focus_nfe(
        empresa, orcamento, tipo, natureza_operacao, serie, itens_override, db=db
    )


async def coletar_bloqueios_avisos_preparacao_nfe(
    empresa: Empresa,
    orcamento: Orcamento,
) -> tuple[list[str], list[str]]:
    """Regras alinhadas à montagem NF-e: IBGE resolvível, itens com valor > 0.

    Não persiste IBGE (usa db=None no resolver).
    """
    bloqueios: list[str] = []
    avisos: list[str] = []
    cliente = orcamento.cliente
    if not cliente:
        return bloqueios, avisos

    cod_ibge, fonte_ibge = await resolver_codigo_municipio_ibge(
        cliente, db=None, persistir_se_viacep=False
    )
    if cod_ibge is None:
        bloqueios.append(
            "Código IBGE do município do cliente ausente ou não resolvido. "
            "Informe o código IBGE (7 dígitos) no cadastro do cliente, ou CEP válido com cidade e UF corretos."
        )
    elif fonte_ibge == "ibge_api":
        avisos.append(
            "Código IBGE foi inferido pela cidade e UF (API IBGE). Confira o município; "
            "prefira cadastrar o código IBGE ou um CEP válido para maior precisão."
        )

    for item in orcamento.itens:
        _q, _vu, v_total = _quantidade_valores_item_nfe(item)
        if v_total <= 0:
            rotulo = ((item.descricao or "").strip() or f"item #{item.id}")[:120]
            bloqueios.append(
                f'O item "{rotulo}" tem valor total zero ou inválido; corrija quantidade e valores no orçamento.'
            )

    return bloqueios, avisos


def sugerir_acao_campo_erro_focus(campo_msg: str) -> Optional[str]:
    """Mapeia texto do array `campos` retornado pela Focus/SEFAZ para orientação ao operador."""
    if not campo_msg:
        return None
    m = campo_msg.lower()
    if "codigomunicipio" in m or "codigo ibge" in m or "código ibge" in m:
        return (
            "O município do destinatário precisa do código IBGE de 7 dígitos. "
            "Cadastre o código no cliente, ou informe CEP válido com cidade e UF corretos "
            "(o sistema tenta resolver automaticamente)."
        )
    if "cfop" in m:
        return (
            "CFOP inválido ou em formato incorreto (deve ser 4 dígitos, ex.: 5102). "
            "Revise o CFOP no catálogo do produto/serviço ou deixe em branco para sugestão automática."
        )
    if "valortotal" in m or "vprod" in m:
        return (
            "Valor total do item deve ser maior que zero. "
            "Ajuste quantidade e preço unitário no orçamento ou corrija o item no catálogo."
        )
    if "descricao" in m or "xprod" in m:
        return (
            "Descrição do produto na linha da nota é obrigatória. "
            "Preencha a descrição do item no orçamento ou o nome do serviço no catálogo."
        )
    if "quantidade" in m or "qcom" in m:
        return (
            "Quantidade do item deve ser maior que zero. "
            "Corrija a quantidade no orçamento."
        )
    return None


def sugerir_acao_mensagem_erro_focus(erro_texto: str) -> Optional[str]:
    """Interpreta mensagens de erro completas (Focus/SEFAZ) para o operador."""
    if not erro_texto:
        return None
    t = erro_texto.lower()
    # NF-e: IE do emitente inválida (cadastro da empresa)
    if re.search(r"cstat\s*=\s*209", erro_texto, re.I) or (
        "209" in erro_texto and "ie" in t and "emit" in t
    ):
        return (
            "A SEFAZ rejeitou a emissão (cStat 209): a Inscrição Estadual (IE) do emitente está incorreta, "
            "incompatível com o CNPJ ou com a UF da empresa. Ajuste em Configurações → Fiscal o campo "
            "Inscrição estadual (use apenas o que consta no cadastro estadual; em alguns casos de não "
            "contribuinte ou MEI o valor pode ser ‘ISENTO’, conforme regra da sua UF — confirme com o contador). "
            "Depois de corrigir, use Reemitir ou emita uma nova nota."
        )
    # NF-e: grupo infRespTec obrigatório na UF (responsável técnico do sistema emissor)
    if re.search(r"cstat\s*=\s*972", erro_texto, re.I) or (
        "972" in erro_texto and "respons" in t and "tecnic" in t
    ):
        return (
            "A SEFAZ rejeitou a emissão (cStat 972): é obrigatório informar o responsável técnico (dados de quem "
            "mantém o sistema emissor da NF-e — CNPJ, contato, e-mail e telefone, conforme layout SEFAZ). "
            "Em geral isso é configurado no painel da Focus no projeto vinculado à sua API key "
            "(projeto → configurações de NF-e / dados fiscais ou equivalente — cadastre o RT homologado na sua UF). "
            "Se já estiver preenchido na Focus e o erro continuar, abra um chamado no suporte Focus com o invoiceId. "
            "Depois de ajustar, use Reemitir ou emita novamente."
        )
    return None


# Compatibilidade retroativa com imports antigos
_cfop_formato_notaas_valido = _cfop_formato_focus_valido
sugerir_acao_campo_erro_notaas = sugerir_acao_campo_erro_focus
sugerir_acao_mensagem_erro_notaas = sugerir_acao_mensagem_erro_focus


def _crt_descricao(crt: Optional[int]) -> str:
    if crt is None:
        return ""
    try:
        c = int(crt)
    except (TypeError, ValueError):
        return ""
    m = {1: "Simples Nacional", 2: "Simples Nacional (excesso de sublimite)", 3: "Regime Normal"}
    return m.get(c, f"CRT {c}")


def emitente_preview_para_previa(empresa: Empresa, orcamento: Orcamento) -> dict:
    """Emitente + referência do orçamento para prévia visual local (sem chamar a Focus)."""
    ref = str(orcamento.id)
    if getattr(orcamento, "numero", None):
        num = str(orcamento.numero).strip()
        if num:
            ref = num
    end = {
        "logradouro": empresa.endereco_logradouro or "",
        "numero": empresa.endereco_numero or "",
        "complemento": empresa.endereco_complemento or "",
        "bairro": empresa.endereco_bairro or "",
        "cidade": empresa.endereco_cidade or "",
        "uf": empresa.endereco_uf or "",
        "cep": empresa.endereco_cep or "",
        "codigoMunicipio": empresa.endereco_codigo_municipio_ibge or "",
    }
    return {
        "razao_social": empresa.nome or "",
        "cnpj": empresa.cnpj or "",
        "inscricao_estadual": (empresa.inscricao_estadual or "").strip(),
        "inscricao_municipal": (empresa.inscricao_municipal or "").strip(),
        "regime_tributario": empresa.regime_tributario or "",
        "crt": empresa.crt,
        "crt_descricao": _crt_descricao(getattr(empresa, "crt", None)),
        "endereco": end,
        "telefone": empresa.telefone or "",
        "email": empresa.email or "",
        "referencia_orcamento": ref,
    }


def _normalizar_codigo_servico(codigo: str) -> str:
    """Normaliza código LC116 para 6 dígitos sem pontos (formato Focus).

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
    """Monta payload NFS-e no formato real da API Focus NFe.

    Emitente NÃO vai no payload — fica configurado na conta Focus vinculada à API key.
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



def _atualizar_nota_com_status_focus(nota_fiscal: NotaFiscal, status_data: dict) -> None:
    """Aplica campos da resposta Focus no objeto NotaFiscal conforme status."""
    status = status_data.get("status", "")

    if status == "autorizado":
        nota_fiscal.status = "emitida"
        nota_fiscal.chave_acesso = (
            status_data.get("chave_nfe")
            or status_data.get("chave_nfse")
            or status_data.get("chave_cte")
        )
        nota_fiscal.numero = str(status_data.get("numero") or "")
        nota_fiscal.protocolo = str(status_data.get("protocolo") or "")
        nota_fiscal.xml_url = status_data.get("caminho_xml_nota_fiscal")
        nota_fiscal.danfe_url = status_data.get("caminho_danfe")
        nota_fiscal.emitida_em = nota_fiscal.emitida_em or datetime.utcnow()

    elif status == "denegado":
        nota_fiscal.status = "erro"
        nota_fiscal.denegada = True
        erros = status_data.get("erros") or []
        primeiro = erros[0] if erros else {}
        nota_fiscal.erro_codigo = str(primeiro.get("codigo") or "DENEGADO")
        nota_fiscal.erro_mensagem = primeiro.get("mensagem") or "Nota denegada pela SEFAZ"

    elif status in ("erro_autorizacao", "erro"):
        nota_fiscal.status = "erro"
        nota_fiscal.denegada = False
        erros = status_data.get("erros") or []
        primeiro = erros[0] if erros else {}
        nota_fiscal.erro_codigo = str(primeiro.get("codigo") or "ERRO_AUTORIZACAO")
        nota_fiscal.erro_mensagem = primeiro.get("mensagem") or "Erro na autorização SEFAZ"

    elif status == "cancelado":
        nota_fiscal.status = "cancelada"
        nota_fiscal.cancelada_em = datetime.utcnow()

    else:
        nota_fiscal.status = "erro"
        nota_fiscal.erro_codigo = "STATUS_DESCONHECIDO"
        nota_fiscal.erro_mensagem = f"Status não reconhecido pela Focus: {status}"


async def emitir_nota(
    db: Session,
    nota_fiscal: NotaFiscal,
    empresa: Empresa,
    payload: dict,
) -> NotaFiscal:
    """Envia payload para API Focus NFe e aguarda resultado via polling."""
    ref = nota_fiscal.focus_ref or _gerar_ref(empresa, nota_fiscal.id)
    endpoint = _endpoint_emissao_focus(nota_fiscal.tipo)

    nota_fiscal.status = "processando"
    nota_fiscal.focus_ref = ref
    nota_fiscal.payload_enviado = payload
    db.commit()

    async with _get_client() as client:
        try:
            resp = await client.post(f"{endpoint}?ref={ref}", json=payload)
        except httpx.RequestError as e:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = "REQUEST_ERROR"
            nota_fiscal.erro_mensagem = str(e)[:500]
            db.commit()
            return nota_fiscal

        if resp.status_code == 401:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = "AUTH_ERROR"
            nota_fiscal.erro_mensagem = "Token Focus inválido — verifique FOCUS_TOKEN no ambiente"
            logger.critical("FOCUS_TOKEN inválido — revisar configuração (empresa_id=%s)", empresa.id)
            db.commit()
            return nota_fiscal

        if resp.status_code >= 400:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = str(resp.status_code)
            try:
                err_body = resp.json()
                nota_fiscal.erro_mensagem = str(err_body.get("mensagem") or err_body)[:800]
            except Exception:
                nota_fiscal.erro_mensagem = resp.text[:500]
            db.commit()
            return nota_fiscal

        # 201 = emissão síncrona (resultado na mesma resposta)
        if resp.status_code == 201:
            try:
                status_data = resp.json()
            except Exception as e:
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = "JSON_ERROR"
                nota_fiscal.erro_mensagem = f"Resposta Focus inválida: {e}"[:500]
                db.commit()
                return nota_fiscal
            _atualizar_nota_com_status_focus(nota_fiscal, status_data)
            db.commit()
            return nota_fiscal

        # 202 = processamento assíncrono (polling ou webhook)
        if resp.status_code != 202:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = str(resp.status_code)
            nota_fiscal.erro_mensagem = f"Resposta HTTP inesperada da Focus: {resp.status_code}"
            db.commit()
            return nota_fiscal

        path = _path_focus(nota_fiscal.tipo, ref)
        for _ in range(POLLING_MAX_ATTEMPTS):
            await asyncio.sleep(POLLING_INTERVAL)
            try:
                status_resp = await client.get(path)
            except httpx.RequestError:
                continue

            if status_resp.status_code == 404:
                continue
            if status_resp.status_code >= 400:
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = str(status_resp.status_code)
                nota_fiscal.erro_mensagem = status_resp.text[:200]
                db.commit()
                return nota_fiscal

            status_data = status_resp.json()
            current = status_data.get("status", "")

            if current == "processando_autorizacao":
                continue

            _atualizar_nota_com_status_focus(nota_fiscal, status_data)
            db.commit()
            return nota_fiscal

    nota_fiscal.status = "erro"
    nota_fiscal.erro_mensagem = "Timeout aguardando processamento da SEFAZ"
    db.commit()
    return nota_fiscal


async def _focus_resolver_id_empresa_por_cnpj(client: httpx.AsyncClient, cnpj: str) -> Optional[int]:
    """GET /v2/empresas?cnpj= — id numérico usado em PUT (não é o CNPJ)."""
    resp = await client.get("/v2/empresas", params={"cnpj": cnpj})
    if resp.status_code != 200:
        logger.warning(
            "Focus GET /v2/empresas?cnpj=… retornou %s: %s",
            resp.status_code,
            (resp.text or "")[:240],
        )
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    if isinstance(data, list) and data:
        raw_id = data[0].get("id")
    elif isinstance(data, dict) and data.get("id") is not None:
        raw_id = data.get("id")
    else:
        return None
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        return None


async def registrar_empresa_focus(
    empresa: Empresa,
    cert_bytes: bytes,
    senha_certificado: str,
) -> dict:
    """Cadastra ou atualiza empresa (emissor) na Focus NFe com certificado A1.

    A API de empresas da Focus responde sempre em ``https://api.focusnfe.com.br``
    (independente de ``FOCUS_AMBIENTE`` para emissão de notas).

    POST /v2/empresas — primeiro cadastro (ou recuperação se não existir id na Focus).
    PUT /v2/empresas/{id} — atualização; envia **cadastro completo** + certificado
    (a Focus valida endereço; PUT só com certificado pode manter/rejeitar '-').
    """
    cnpj = re.sub(r"\D", "", empresa.cnpj or "")
    if not cnpj:
        raise ValueError("Empresa sem CNPJ — impossível registrar na Focus NFe")

    cert_b64 = base64.b64encode(cert_bytes).decode()
    payload_completo = _montar_payload_cadastro_empresa_focus_com_certificado(
        empresa, cert_b64, senha_certificado
    )

    ja_cadastrada = bool(getattr(empresa, "focus_certificado_configurado", None))

    async with _get_client_empresas() as client:
        try:
            if ja_cadastrada:
                id_focus = await _focus_resolver_id_empresa_por_cnpj(client, cnpj)
                if id_focus is not None:
                    resp = await client.put(
                        f"/v2/empresas/{id_focus}",
                        json=payload_completo,
                    )
                else:
                    logger.info(
                        "Certificado já marcado no COTTE, mas empresa não listada na Focus "
                        "para CNPJ %s — tentando POST /v2/empresas.",
                        cnpj,
                    )
                    resp = await client.post("/v2/empresas", json=payload_completo)
            else:
                resp = await client.post("/v2/empresas", json=payload_completo)

            if resp.status_code not in (200, 201):
                detalhe = (resp.text or "")[:800]
                try:
                    body = resp.json()
                    if isinstance(body.get("erros"), list):
                        msgs = [
                            e.get("mensagem")
                            for e in body["erros"]
                            if isinstance(e, dict) and e.get("mensagem")
                        ]
                        if msgs:
                            detalhe = "; ".join(msgs) + " | " + detalhe[:400]
                except Exception:
                    pass
                return {"success": False, "erro": f"Focus retornou {resp.status_code}: {detalhe}"}

            data = resp.json()
        except httpx.RequestError as e:
            return {"success": False, "erro": f"Erro de conexão com a Focus NFe: {e}"}

    empresa.focus_certificado_configurado = True

    validade_raw = data.get("data_expiracao_certificado") or data.get("certificate_expires_at")
    if validade_raw:
        try:
            empresa.focus_certificado_validade = datetime.fromisoformat(
                str(validade_raw).replace("Z", "+00:00")
            )
        except Exception:
            pass

    return {"success": True, "data": data}


async def consultar_nota_focus_e_persistir(
    db: Session,
    nota_fiscal: NotaFiscal,
) -> NotaFiscal:
    """GET /v2/{nfe|nfce|nfse}/{ref}?completa=1 — atualiza status local."""
    ref = nota_fiscal.focus_ref
    if not ref:
        raise ValueError("Nota sem focus_ref — impossível consultar na Focus")
    path = _path_focus(nota_fiscal.tipo, ref)
    async with _get_client() as client:
        resp = await client.get(path, params={"completa": 1})
        if resp.status_code == 404:
            raise ValueError("Referência não encontrada na Focus NFe")
        if resp.status_code >= 400:
            raise ValueError(resp.text[:500])
        status_data = resp.json()
    _atualizar_nota_com_status_focus(nota_fiscal, status_data)
    db.commit()
    return nota_fiscal


async def emitir_carta_correcao_focus(
    db: Session,
    nota_fiscal: NotaFiscal,
    correcao: str,
) -> dict:
    """POST /v2/nfe/{ref}/carta_correcao — apenas NF-e modelo 55."""
    if (nota_fiscal.tipo or "").lower() != "nfe":
        raise ValueError("Carta de correção é suportada apenas para NF-e.")
    ref = nota_fiscal.focus_ref
    if not ref:
        raise ValueError("Nota sem focus_ref")
    txt = (correcao or "").strip()
    if len(txt) < 15 or len(txt) > 1000:
        raise ValueError("Texto da carta de correção deve ter entre 15 e 1000 caracteres.")
    path = f"/v2/nfe/{ref}/carta_correcao"
    async with _get_client() as client:
        resp = await client.post(path, json={"correcao": txt})
        try:
            data = resp.json()
        except Exception:
            data = {"detalhe": resp.text[:500]}
        if resp.status_code >= 400:
            raise ValueError(str(data.get("mensagem") or data)[:900])
    hist = nota_fiscal.focus_extras if isinstance(getattr(nota_fiscal, "focus_extras", None), dict) else {}
    cartas = list(hist.get("cartas_correcao") or [])
    cartas.append({"em": datetime.now(timezone.utc).isoformat(), "resposta": data})
    hist = dict(hist)
    hist["cartas_correcao"] = cartas
    nota_fiscal.focus_extras = hist
    db.commit()
    return data


async def previsualizar_danfe_pdf(payload: dict) -> bytes:
    """POST /v2/nfe/danfe — retorna PDF (pré-visualização Focus)."""
    async with httpx.AsyncClient(
        base_url=_focus_base_url(),
        auth=(settings.FOCUS_TOKEN, ""),
        headers={"Content-Type": "application/json", "Accept": "application/pdf"},
        timeout=90.0,
    ) as client:
        resp = await client.post("/v2/nfe/danfe", json=payload)
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text[:500]
            raise ValueError(str(err)[:900])
        return resp.content


async def reenviar_webhook_focus(nota_fiscal: NotaFiscal) -> dict:
    """POST /v2/{tipo}/{ref}/hook — reenvia notificação (gatilho) Focus."""
    ref = nota_fiscal.focus_ref
    if not ref:
        raise ValueError("Nota sem focus_ref")
    base = _path_focus(nota_fiscal.tipo, ref).rstrip("/")
    path = f"{base}/hook"
    async with _get_client() as client:
        resp = await client.post(path)
        try:
            return resp.json()
        except Exception:
            return {"status_code": resp.status_code, "texto": resp.text[:500]}


async def cancelar_nota(
    db: Session,
    nota_fiscal: NotaFiscal,
    empresa: Empresa,
    motivo: str,
) -> NotaFiscal:
    """Cancela NF emitida via Focus: DELETE /v2/{tipo}/{ref}."""
    ref = nota_fiscal.focus_ref
    if not ref:
        raise ValueError("Nota sem focus_ref para cancelar")
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 15 or len(motivo_limpo) > 255:
        raise ValueError("Justificativa de cancelamento deve ter entre 15 e 255 caracteres.")

    path = _path_focus(nota_fiscal.tipo, ref)

    async with _get_client() as client:
        try:
            resp = await client.delete(path, json={"justificativa": motivo_limpo})
            if resp.status_code not in (200, 201, 204):
                raise httpx.HTTPStatusError(
                    f"Cancelamento falhou: {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
        except httpx.RequestError as e:
            raise ValueError(f"Erro de conexão ao cancelar nota: {e}") from e

    nota_fiscal.status = "cancelada"
    nota_fiscal.cancelada_em = datetime.utcnow()
    nota_fiscal.cancelamento_motivo = motivo_limpo
    db.commit()
    return nota_fiscal


def verificar_token_webhook_focus(authorization_header: str, expected_token: str) -> bool:
    """Valida header Authorization: Basic {base64(token:)} enviado pela Focus."""
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(authorization_header[6:]).decode()
        token = decoded.split(":")[0]
        return hmac.compare_digest(token, expected_token)
    except Exception:
        return False


def _limpar_doc(doc: str) -> str:
    return "".join(filter(str.isdigit, doc or ""))


def _limpar_cep(cep: str) -> str:
    return "".join(filter(str.isdigit, cep or ""))
