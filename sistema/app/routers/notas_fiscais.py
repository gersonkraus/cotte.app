"""
notas_fiscais.py — Endpoints para emissão e gestão de NF-e/NFC-e/NFS-e.
"""

import logging
import httpx
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi import Form
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.auth import get_usuario_atual, exigir_permissao
from app.core.tenant_context import set_tenant_context

from app.models.models import Empresa, NotaFiscal, Orcamento, Usuario, HistoricoEdicao
from app.schemas.schemas import (
    ConfiguracaoFiscalEmpresa,
    NotaFiscalCancelarRequest,
    NotaFiscalEmitirRequest,
    NotaFiscalOut,
    NotaFiscalListOut,
)
from app.services import nfe_service
from app.services import nfe_org_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notas-fiscais", tags=["Notas Fiscais"])


def _get_empresa_com_nfe(db: Session, usuario) -> Empresa:
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")
    if not empresa.notaas_api_key:
        raise HTTPException(422, "Configure a API key da Notaas em Configurações → Fiscal antes de emitir notas")
    if not empresa.cnpj:
        raise HTTPException(422, "Preencha o CNPJ da empresa em Configurações → Fiscal antes de emitir notas")
    return empresa


@router.get("/configuracao", response_model=ConfiguracaoFiscalEmpresa)
def get_configuracao_fiscal(
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")
    return ConfiguracaoFiscalEmpresa(
        cnpj=empresa.cnpj,
        inscricao_estadual=empresa.inscricao_estadual,
        inscricao_municipal=empresa.inscricao_municipal,
        regime_tributario=empresa.regime_tributario,
        crt=empresa.crt,
        endereco_logradouro=empresa.endereco_logradouro,
        endereco_numero=empresa.endereco_numero,
        endereco_complemento=empresa.endereco_complemento,
        endereco_bairro=empresa.endereco_bairro,
        endereco_cidade=empresa.endereco_cidade,
        endereco_uf=empresa.endereco_uf,
        endereco_cep=empresa.endereco_cep,
        endereco_codigo_municipio_ibge=empresa.endereco_codigo_municipio_ibge,
        notaas_project_id=empresa.notaas_project_id,
        notaas_api_key="***" if empresa.notaas_api_key else None,
        notaas_ambiente=empresa.notaas_ambiente,
    )


@router.put("/configuracao")
def salvar_configuracao_fiscal(
    dados: ConfiguracaoFiscalEmpresa,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
    _=Depends(exigir_permissao("configuracoes", "escrita")),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    empresa.cnpj = dados.cnpj
    empresa.inscricao_estadual = dados.inscricao_estadual
    empresa.inscricao_municipal = dados.inscricao_municipal
    empresa.regime_tributario = dados.regime_tributario
    empresa.crt = dados.crt
    empresa.endereco_logradouro = dados.endereco_logradouro
    empresa.endereco_numero = dados.endereco_numero
    empresa.endereco_complemento = dados.endereco_complemento
    empresa.endereco_bairro = dados.endereco_bairro
    empresa.endereco_cidade = dados.endereco_cidade
    empresa.endereco_uf = dados.endereco_uf
    empresa.endereco_cep = dados.endereco_cep
    empresa.endereco_codigo_municipio_ibge = dados.endereco_codigo_municipio_ibge
    empresa.notaas_ambiente = dados.notaas_ambiente or "homologacao"

    if dados.notaas_api_key and dados.notaas_api_key != "***":
        empresa.notaas_api_key = dados.notaas_api_key
    if dados.notaas_webhook_secret:
        empresa.notaas_webhook_secret = dados.notaas_webhook_secret

    db.commit()
    return {"success": True, "message": "Configuração fiscal salva"}


@router.post("/emitir", response_model=NotaFiscalOut)
async def emitir_nota_fiscal(
    dados: NotaFiscalEmitirRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = _get_empresa_com_nfe(db, usuario)

    orcamento = (
        db.query(Orcamento)
        .filter(Orcamento.id == dados.orcamento_id, Orcamento.empresa_id == usuario.empresa_id)
        .first()
    )
    if not orcamento:
        raise HTTPException(404, "Orçamento não encontrado")

    nota = NotaFiscal(
        empresa_id=usuario.empresa_id,
        orcamento_id=dados.orcamento_id,
        tipo=dados.tipo,
        modelo=55 if dados.tipo == "nfe" else (65 if dados.tipo == "nfce" else None),
        serie=dados.serie,
        natureza_operacao=dados.natureza_operacao,
        status="pendente",
        criado_por_id=usuario.id,
    )
    db.add(nota)
    db.flush()

    if dados.tipo == "nfse":
        payload = nfe_service._montar_payload_nfse(
            empresa, orcamento,
            dados.codigo_servico_lc116 or "17.06",
            dados.aliquota_iss or 0,
        )
    else:
        payload = nfe_service._montar_payload_nfe(
            empresa, orcamento, dados.tipo,
            dados.natureza_operacao, dados.serie,
            dados.itens_override,
        )

    db.commit()
    # BUG1-FIX: passa IDs em vez de objetos ORM — a session será fechada antes
    # da background task executar; emitir_nota_background cria session própria.
    background_tasks.add_task(nfe_service.emitir_nota_background, nota.id, empresa.id, payload)
    return nota


# ── Onboarding Notaas (Org API) — rotas estáticas ANTES de /{nota_id} ────────

@router.post("/configurar-notaas")
async def configurar_notaas(
    certificado: UploadFile = File(..., description="Certificado A1 (.pfx ou .p12)"),
    senha_certificado: str = Form(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
    _=Depends(exigir_permissao("configuracoes", "escrita")),
):
    """Onboarding automático Notaas: cria projeto + upload certificado + gera API key."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")
    if not empresa.cnpj:
        raise HTTPException(422, "CNPJ da empresa é obrigatório. Preencha os dados fiscais primeiro.")

    cert_bytes = await certificado.read()
    if len(cert_bytes) > 51200:  # 50KB
        raise HTTPException(413, "Certificado deve ter no máximo 50KB")

    try:
        resultado = await nfe_org_service.onboarding_completo(
            db, empresa, cert_bytes, senha_certificado
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except httpx.HTTPStatusError as e:
        logger.error("Erro HTTP Notaas empresa_id=%s: %s - %s", usuario.empresa_id, e, e.response.text)
        raise HTTPException(400, f"Erro na API da Notaas: {e.response.text}")
    except Exception as e:
        logger.error("Erro no onboarding Notaas empresa_id=%s: %s", usuario.empresa_id, e)
        raise HTTPException(400, f"Erro interno na integração: {e}")

    return {
        "success": True,
        "message": "Empresa configurada com sucesso na Notaas",
        **resultado,
    }


@router.get("/status-notaas")
async def status_notaas(
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Retorna o status de configuração Notaas da empresa (projeto, certificado, API key)."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    if not empresa.notaas_project_id:
        return {
            "configurado": False,
            "tem_projeto": False,
            "tem_certificado": False,
            "tem_api_key": bool(empresa.notaas_api_key),
        }

    try:
        status = await nfe_org_service.verificar_status_projeto(empresa.notaas_project_id)
    except Exception as e:
        logger.warning("Erro ao verificar status Notaas: %s", e)
        return {
            "configurado": bool(empresa.notaas_api_key),
            "tem_projeto": True,
            "project_id": empresa.notaas_project_id,
            "erro": "Não foi possível verificar status em tempo real",
        }

    return {
        "configurado": status.get("hasCertificate") and bool(empresa.notaas_api_key),
        "tem_projeto": status.get("found", False),
        "tem_certificado": status.get("hasCertificate", False),
        "tem_api_key": status.get("hasApiKey", False),
        "project_id": empresa.notaas_project_id,
        "ambiente": empresa.notaas_ambiente,
    }


@router.post("/webhook/notaas")
async def receber_webhook_notaas(
    request: Request,
    db: Session = Depends(get_db),
    x_notaas_event: str = Header(None),
    x_notaas_delivery: str = Header(None),
    x_notaas_signature: str = Header(None),
):
    """Recebe eventos NF-e, NFC-e e NFS-e da Notaas.

    NF-e/NFC-e: campos dentro de payload["data"] (chaveAcesso, nProt, cStat, xMotivo).
    NFS-e: campos no root (invoiceId, numeroNfe, chNFSe, errorCode, errorMessage).
    """
    body = await request.body()
    payload = await request.json()

    # Evento: vem no body E no header X-Notaas-Event
    event = payload.get("event") or x_notaas_event or ""

    # deliveryId: vem no body E no header (idempotência)
    delivery_id = payload.get("deliveryId") or x_notaas_delivery

    # NF-e/NFC-e: invoiceId fica dentro de data{}; NFS-e: fica no root
    data = payload.get("data") or {}
    invoice_id = data.get("invoiceId") or payload.get("invoiceId") or payload.get("id")
    if not invoice_id:
        return {"ok": True}

    nota = db.query(NotaFiscal).filter(NotaFiscal.notaas_invoice_id == invoice_id).first()
    if not nota:
        return {"ok": True}

    # Valida assinatura HMAC-SHA256 se o secret estiver configurado
    empresa = db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
    if empresa and empresa.notaas_webhook_secret:
        if not x_notaas_signature:
            raise HTTPException(401, "Assinatura de webhook ausente")
        if not nfe_service.verificar_assinatura_webhook(body, x_notaas_signature, empresa.notaas_webhook_secret):
            raise HTTPException(401, "Assinatura de webhook inválida")
    else:
        import logging
        logging.getLogger(__name__).warning(
            "Webhook Notaas recebido sem secret configurado (empresa_id=%s)",
            nota.empresa_id,
        )

    # Idempotência: ignora reentregas já processadas
    if delivery_id and nota.notaas_delivery_id == delivery_id:
        return {"ok": True}
    nota.notaas_delivery_id = delivery_id

    if "issued" in event:
        nota.status = "emitida"
        nota.chave_acesso = (
            data.get("chaveAcesso")
            or payload.get("chNFSe")
            or payload.get("accessKey")
        )
        nota.protocolo = data.get("nProt") or payload.get("protocol")
        numero = data.get("nfNumber") or payload.get("numeroNfe") or payload.get("nfNumber")
        if numero:
            nota.numero = str(numero)
        nota.xml_url = data.get("xmlUrl") or payload.get("xmlUrl")
        nota.danfe_url = data.get("pdfUrl") or payload.get("pdfUrl")
        nota.qr_code = data.get("qrCode") or payload.get("qrCode")
        nota.emitida_em = nota.emitida_em or datetime.utcnow()

    elif "documents_ready" in event:
        if data.get("xmlUrl") and not nota.xml_url:
            nota.xml_url = data["xmlUrl"]
        if data.get("pdfUrl") and not nota.danfe_url:
            nota.danfe_url = data["pdfUrl"]
        if data.get("cancelXmlUrl"):
            nota.xml_url = data["cancelXmlUrl"]

    elif "error" in event:
        nota.status = "erro"
        nota.erro_codigo = (
            str(data.get("cStat") or "")
            or payload.get("errorCode", "WEBHOOK_ERROR")
        )
        nota.erro_mensagem = (
            data.get("xMotivo")
            or payload.get("errorMessage", "Erro via webhook")
        )

    elif "cancelled" in event:
        nota.status = "cancelada"
        nota.cancelada_em = datetime.utcnow()

    elif event == "batch.completed":
        import logging
        logging.getLogger(__name__).info("batch.completed recebido para empresa_id=%s — processamento em lote concluído", nota.empresa_id)
        db.commit()
        return {"ok": True}
        
    if nota.orcamento_id and nota.status in ("emitida", "cancelada", "erro"):
        descricao = {
            "emitida": f"Nota Fiscal {nota.tipo.upper()} {nota.numero or ''} emitida (via webhook)",
            "cancelada": f"Nota Fiscal {nota.tipo.upper()} {nota.numero or ''} cancelada",
            "erro": f"Erro na emissão da Nota Fiscal: {nota.erro_mensagem or 'desconhecido'}",
        }.get(nota.status, "")
        if descricao:
            historico = HistoricoEdicao(
                orcamento_id=nota.orcamento_id,
                editado_por_id=None,
                descricao=descricao,
                tipo="nota_fiscal",
            )
            db.add(historico)

    db.commit()
    return {"ok": True}


# ── Listagem e consulta por ID — APÓS rotas estáticas ─────────────────────────


@router.get("", response_model=NotaFiscalListOut)
async def listar_notas_fiscais(
    pagina: int = 1,
    por_pagina: int = 20,
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    busca: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    query = db.query(NotaFiscal).filter(NotaFiscal.empresa_id == usuario.empresa_id)
    if status:
        query = query.filter(NotaFiscal.status == status)
    if tipo:
        query = query.filter(NotaFiscal.tipo == tipo)
    if busca:
        query = query.filter(
            or_(
                NotaFiscal.numero.ilike(f"%{busca}%"),
                NotaFiscal.chave_acesso.ilike(f"%{busca}%"),
                NotaFiscal.natureza_operacao.ilike(f"%{busca}%"),
            )
        )
    total = query.count()
    notas = (
        query.order_by(NotaFiscal.criado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    return NotaFiscalListOut(notas=notas, total=total, pagina=pagina, por_pagina=por_pagina)


@router.get("/orcamento/{orcamento_id}", response_model=List[NotaFiscalOut])

def listar_notas_por_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    return (
        db.query(NotaFiscal)
        .filter(NotaFiscal.empresa_id == usuario.empresa_id, NotaFiscal.orcamento_id == orcamento_id)
        .order_by(NotaFiscal.criado_em.desc())
        .all()
    )


@router.get("/{nota_id}", response_model=NotaFiscalOut)
def get_nota_fiscal(
    nota_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    nota = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    return nota


@router.post("/{nota_id}/cancelar", response_model=NotaFiscalOut)
async def cancelar_nota_fiscal(
    nota_id: int,
    dados: NotaFiscalCancelarRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = _get_empresa_com_nfe(db, usuario)

    nota = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    if nota.status != "emitida":
        raise HTTPException(400, f"Nota em status '{nota.status}' não pode ser cancelada")

    return await nfe_service.cancelar_nota(db, nota, empresa, dados.motivo)
