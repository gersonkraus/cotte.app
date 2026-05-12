"""
nfe_service.py — Integração com API Focus NFe para emissão de NF-e/NFC-e/NFS-e.
URLs: https://api.focusnfe.com.br (prod) | https://homologacao.focusnfe.com.br (homolog)
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
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

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


def _get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_focus_base_url(),
        auth=(settings.FOCUS_TOKEN, ""),
        headers={"Content-Type": "application/json"},
        timeout=30.0,
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
    """Resolve código IBGE (7 dígitos) para dest.endereco.codigoMunicipio (Notaas).

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
    """Notaas exige CFOP como string de 4 dígitos."""
    if cfop is None:
        return padrao
    digitos = "".join(c for c in str(cfop) if c.isdigit())
    if len(digitos) >= 4:
        return digitos[:4]
    if len(digitos) > 0:
        return digitos.zfill(4)
    return padrao


def _cfop_formato_notaas_valido(cfop_str: str) -> bool:
    """CFOP deve ser exatamente 4 dígitos (string), conforme Notaas."""
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


async def _montar_payload_nfe(
    empresa: Empresa,
    orcamento: Orcamento,
    tipo: str,
    natureza_operacao: str,
    serie: str,
    itens_override=None,
    db: Optional[Session] = None,
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

    cod_ibge, _fonte_ibge = await resolver_codigo_municipio_ibge(cliente, db=db, persistir_se_viacep=True)
    if cod_ibge is not None:
        endereco_dest["codigoMunicipio"] = cod_ibge

    destinatario = {
        **dest_doc,
        "nome": dest_nome,
        "ie": cliente.inscricao_estadual or "",
        "email": cliente.email or "",
        "endereco": endereco_dest,
    }

    itens = itens_override or orcamento.itens
    items = []
    cfop_padrao_uf = _cfop_padrao_por_uf_empresa_cliente(empresa, cliente)

    for item in itens:
        servico = getattr(item, "servico", None)
        ncm_raw = (getattr(servico, "ncm", None) or None) if servico else None
        cfop_catalogo = (getattr(servico, "cfop", None) or None) if servico else None
        csosn = (getattr(servico, "csosn", None) or "400") if servico else "400"
        unidade = (getattr(servico, "unidade_fiscal", None) or getattr(servico, "unidade", None) or "UN") if servico else "UN"

        descricao_item = (item.descricao or "").strip()
        if not descricao_item and servico and getattr(servico, "nome", None):
            descricao_item = (servico.nome or "").strip()
        if not descricao_item:
            descricao_item = "Item conforme orçamento"

        qtd, v_unit, v_total = _quantidade_valores_item_nfe(item)

        ncm = _normalizar_ncm_para_string(ncm_raw) if ncm_raw else None
        cfop = _normalizar_cfop_para_string(cfop_catalogo if cfop_catalogo is not None else cfop_padrao_uf, cfop_padrao_uf)

        precisa_ia_ncm_cfop = not ncm_raw or ncm == "00000000" or not _cfop_formato_notaas_valido(cfop)
        if precisa_ia_ncm_cfop:
            try:
                categoria = getattr(getattr(servico, "categoria", None), "nome", None) if servico else None
                sugestao = await sugerir_dados_fiscais(descricao_item, categoria)
                if not ncm_raw or ncm == "00000000":
                    ncm = _normalizar_ncm_para_string(sugestao.get("ncm")) if sugestao.get("ncm") else "00000000"
                if not cfop_catalogo or not _cfop_formato_notaas_valido(cfop):
                    sug_cfop = sugestao.get("cfop")
                    cfop = _normalizar_cfop_para_string(sug_cfop if sug_cfop else cfop_padrao_uf, cfop_padrao_uf)
            except Exception:
                ncm = ncm or "00000000"
                cfop = _normalizar_cfop_para_string(cfop_padrao_uf, cfop_padrao_uf)

        if not _cfop_formato_notaas_valido(cfop):
            cfop = _normalizar_cfop_para_string(cfop_padrao_uf, "5102")

        ncm = _normalizar_ncm_para_string(ncm)

        items.append({
            "descricao": descricao_item,
            "ncm": ncm,
            "cfop": cfop,
            "valorTotal": round(v_total, 2),
            "quantidade": qtd,
            "valorUnitario": round(v_unit, 2),
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


def sugerir_acao_campo_erro_notaas(campo_msg: str) -> Optional[str]:
    """Mapeia texto do array `campos` da Notaas para orientação ao operador."""
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


def sugerir_acao_mensagem_erro_notaas(erro_texto: str) -> Optional[str]:
    """Interpreta mensagens de erro completas (SEFAZ/Notaas) para o operador."""
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
            "Em geral isso é configurado no painel da Notaas no projeto vinculado à sua API key "
            "(projeto → configurações de NF-e / dados fiscais ou equivalente — cadastre o RT homologado na sua UF). "
            "Se já estiver preenchido na Notaas e o erro continuar, abra um chamado no suporte Notaas com o invoiceId. "
            "Depois de ajustar, use Reemitir ou emita novamente."
        )
    return None


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
    """Emitente + referência do orçamento para prévia visual (DANFE/NFS-e simulada), sem Notaas."""
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
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = "AUTH_ERROR"
                nota_fiscal.erro_mensagem = "Token Focus inválido — verifique FOCUS_TOKEN no ambiente"
                logger.critical("FOCUS_TOKEN inválido — revisar configuração (empresa_id=%s)", empresa.id)
                db.commit()
                return nota_fiscal
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

    async with _get_client() as client:
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
