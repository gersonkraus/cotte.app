"""
notas_fiscais.py — Endpoints para emissão e gestão de NF-e/NFC-e/NFS-e.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_usuario_atual, exigir_permissao
from app.core.tenant_context import set_tenant_context

from app.models.models import Empresa, NotaFiscal, Orcamento
from app.schemas.schemas import (
    ConfiguracaoFiscalEmpresa,
    NotaFiscalCancelarRequest,
    NotaFiscalEmitirRequest,
    NotaFiscalOut,
)
from app.services import nfe_service

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
    set_tenant_context(usuario.empresa_id)
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
    set_tenant_context(usuario.empresa_id)
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
    set_tenant_context(usuario.empresa_id)
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
    background_tasks.add_task(nfe_service.emitir_nota, db, nota, empresa, payload)
    return nota


@router.get("/orcamento/{orcamento_id}", response_model=List[NotaFiscalOut])
def listar_notas_por_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    set_tenant_context(usuario.empresa_id)
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
    set_tenant_context(usuario.empresa_id)
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
    set_tenant_context(usuario.empresa_id)
    empresa = _get_empresa_com_nfe(db, usuario)

    nota = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    if nota.status != "emitida":
        raise HTTPException(400, f"Nota em status '{nota.status}' não pode ser cancelada")

    return await nfe_service.cancelar_nota(db, nota, empresa, dados.motivo)


@router.post("/webhook/notaas")
async def receber_webhook_notaas(
    request: Request,
    db: Session = Depends(get_db),
    x_notaas_event: str = Header(None),
    x_notaas_delivery: str = Header(None),
    x_notaas_signature: str = Header(None),
):
    body = await request.body()
    payload = await request.json()

    invoice_id = payload.get("invoiceId") or payload.get("id")
    if not invoice_id:
        return {"ok": True}

    nota = db.query(NotaFiscal).filter(NotaFiscal.notaas_invoice_id == invoice_id).first()
    if not nota:
        return {"ok": True}

    empresa = db.query(Empresa).filter(Empresa.id == nota.empresa_id).first()
    if empresa and empresa.notaas_webhook_secret and x_notaas_signature:
        if not nfe_service.verificar_assinatura_webhook(body, x_notaas_signature, empresa.notaas_webhook_secret):
            raise HTTPException(401, "Assinatura de webhook inválida")

    if x_notaas_delivery and nota.notaas_delivery_id == x_notaas_delivery:
        return {"ok": True}
    nota.notaas_delivery_id = x_notaas_delivery

    event = x_notaas_event or ""

    if "issued" in event or payload.get("status") == "issued":
        nota.status = "emitida"
        nota.numero = str(payload.get("nfNumber", nota.numero or ""))
        nota.serie = str(payload.get("nfSerie", nota.serie or ""))
        nota.chave_acesso = payload.get("accessKey")
        nota.protocolo = payload.get("protocol")
        nota.xml_url = payload.get("xmlUrl")
        nota.danfe_url = payload.get("pdfUrl")
        nota.emitida_em = nota.emitida_em or datetime.utcnow()
    elif "error" in event or payload.get("status") == "error":
        erro = payload.get("error", {})
        nota.status = "erro"
        nota.erro_codigo = erro.get("code", "WEBHOOK_ERROR")
        nota.erro_mensagem = erro.get("message", "Erro via webhook")
    elif "cancelled" in event:
        nota.status = "cancelada"
        nota.cancelada_em = datetime.utcnow()

    db.commit()
    return {"ok": True}
