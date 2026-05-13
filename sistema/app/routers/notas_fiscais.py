"""
notas_fiscais.py — Endpoints para emissão e gestão de NF-e/NFC-e/NFS-e.
"""

import logging
import httpx
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile, Response
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import or_

from app.core.database import get_db
from app.core.auth import get_usuario_atual, exigir_permissao
from app.core.tenant_context import set_tenant_context
from app.core.config import settings

from app.models.models import Empresa, NotaFiscal, Orcamento, Usuario, HistoricoEdicao, ItemOrcamento, Servico, Cliente
from app.schemas.schemas import (
    ConfiguracaoFiscalEmpresa,
    NotaFiscalCancelarRequest,
    NotaFiscalCartaCorrecaoRequest,
    NotaFiscalEmitirRequest,
    NotaFiscalOut,
    NotaFiscalListOut,
    NotaFiscalPrepararRequest,
    NotaFiscalPrepararOut,
)
from app.services import nfe_service
from app.services.email_service import email_habilitado, enviar_nota_fiscal_por_email
from app.services.whatsapp_service import enviar_mensagem_texto, enviar_pdf, whatsapp_envio_disponivel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notas-fiscais", tags=["Notas Fiscais"])


def _absolutizar_midia_focus(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    s = str(val).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/"):
        base = (
            "https://api.focusnfe.com.br"
            if (settings.FOCUS_AMBIENTE or "").lower() == "producao"
            else "https://homologacao.focusnfe.com.br"
        )
        return f"{base.rstrip('/')}{s}"
    return s


def _tipo_nf_label(t: str) -> str:
    u = (t or "").lower().strip()
    return {"nfe": "NF-e", "nfce": "NFC-e", "nfse": "NFS-e"}.get(u, t or "Nota fiscal")


async def _baixar_url_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


def _bloqueios_from_checklist(checklist: list[dict]) -> list[str]:
    return [c.get("titulo") for c in checklist if not c.get("ok")]


def _get_empresa_com_nfe(db: Session, usuario) -> Empresa:
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")
    if not nfe_service.focus_token_emissao_disponivel(empresa):
        raise HTTPException(422, "Token Focus NFe não configurado para emissão neste ambiente. Contate o suporte.")
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
        nfe_ambiente=empresa.nfe_ambiente or "homologacao",
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
    empresa.nfe_ambiente = dados.nfe_ambiente or "homologacao"

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
        .options(
            selectinload(Orcamento.itens).joinedload(ItemOrcamento.servico).joinedload(Servico.categoria),
            joinedload(Orcamento.cliente),
        )
        .filter(Orcamento.id == dados.orcamento_id, Orcamento.empresa_id == usuario.empresa_id)
        .first()
    )
    if not orcamento:
        raise HTTPException(404, "Orçamento não encontrado")

    if dados.itens_override is not None and (dados.tipo or "").strip().lower() in ("nfe", "nfce"):
        if len(dados.itens_override) != len(orcamento.itens):
            raise HTTPException(
                422,
                "itens_override deve incluir uma linha por item do orçamento, na mesma ordem.",
            )

    tipo = (dados.tipo or "").strip().lower()
    natureza = (dados.natureza_operacao or ("Prestação de Serviços" if tipo == "nfse" else "Venda de Mercadorias")).strip()
    serie_val = (dados.serie or "1").strip() or "1"

    duplicidade_equivalente = (
        db.query(NotaFiscal.id)
        .filter(
            NotaFiscal.empresa_id == usuario.empresa_id,
            NotaFiscal.orcamento_id == dados.orcamento_id,
            NotaFiscal.status == "emitida",
            NotaFiscal.tipo == tipo,
            NotaFiscal.serie == serie_val,
        )
        .first()
    )
    checklist_geral = nfe_service.montar_checklist_validacoes_gerais(
        empresa=empresa,
        orcamento=orcamento,
        tipo=tipo,
        natureza_operacao=natureza,
        serie=serie_val,
        duplicidade_equivalente_autorizada=bool(duplicidade_equivalente),
    )
    bloqueios_gerais = _bloqueios_from_checklist(checklist_geral)
    if bloqueios_gerais:
        raise HTTPException(422, {"message": "Validação fiscal impedindo emissão", "bloqueios": bloqueios_gerais})

    nota = NotaFiscal(
        empresa_id=usuario.empresa_id,
        orcamento_id=dados.orcamento_id,
        tipo=tipo,
        modelo=55 if tipo == "nfe" else (65 if tipo == "nfce" else None),
        serie=serie_val,
        natureza_operacao=natureza,
        status="pendente",
        criado_por_id=usuario.id,
        criado_em=datetime.now(timezone.utc),
    )
    db.add(nota)
    db.flush()

    try:
        if tipo == "nfse":
            payload = nfe_service._montar_payload_nfse(
                empresa, orcamento,
                dados.codigo_servico_lc116 or "170600",
                dados.aliquota_iss or 0,
                natureza_operacao=natureza,
            )
            checklist_tipo = nfe_service.montar_checklist_validacoes_nfse(payload, empresa)
        else:
            payload = await nfe_service._montar_payload_nfe(
                empresa, orcamento, tipo,
                natureza, serie_val,
                dados.itens_override,
                db=db,
            )
            checklist_tipo = nfe_service.montar_checklist_validacoes_nfe(payload)
        bloqueios_tipo = _bloqueios_from_checklist(checklist_tipo)
        if bloqueios_tipo:
            raise HTTPException(422, {"message": "Validação fiscal impedindo emissão", "bloqueios": bloqueios_tipo})
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    db.commit()
    # Garante `criado_em` (server_default) e demais colunas persistidas no objeto ORM
    # antes do `response_model=NotaFiscalOut` — evita ResponseValidationError (criado_em=None).
    db.refresh(nota)
    # BUG1-FIX: passa IDs em vez de objetos ORM — a session será fechada antes
    # da background task executar; emitir_nota_background cria session própria.
    background_tasks.add_task(nfe_service.emitir_nota_background, nota.id, empresa.id, payload)
    return nota


@router.post("/preparar", response_model=NotaFiscalPrepararOut)
async def preparar_nota_fiscal(
    dados: NotaFiscalPrepararRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Pré-valida o orçamento para emissão de NF-e. Não cria nota nem envia para a Focus."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)

    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    orcamento = (
        db.query(Orcamento)
        .options(
            selectinload(Orcamento.itens).joinedload(ItemOrcamento.servico).joinedload(Servico.categoria),
            joinedload(Orcamento.cliente),
        )
        .filter(Orcamento.id == dados.orcamento_id, Orcamento.empresa_id == usuario.empresa_id)
        .first()
    )
    if not orcamento:
        raise HTTPException(404, "Orçamento não encontrado")

    tipo = (dados.tipo or "").strip().lower()
    if dados.itens_override is not None and tipo in ("nfe", "nfce"):
        if len(dados.itens_override) != len(orcamento.itens):
            raise HTTPException(
                422,
                "itens_override deve incluir uma linha por item do orçamento, na mesma ordem.",
            )

    natureza = (dados.natureza_operacao or ("Prestação de Serviços" if tipo == "nfse" else "Venda de Mercadorias")).strip()
    serie_val = (dados.serie or "1").strip() or "1"
    bloqueios: list[str] = []
    avisos: list[str] = []

    if tipo in ("nfe", "nfce") and empresa:
        ie_emp = (empresa.inscricao_estadual or "").strip()
        if not ie_emp:
            avisos.append(
                "Inscrição estadual da empresa não preenchida em Configurações → Fiscal. "
                "Sem IE coerente com o CNPJ e a UF, a SEFAZ pode rejeitar a NF-e (ex.: cStat 209 — IE do emitente inválida)."
            )

    cliente = orcamento.cliente
    mutou_autofill_db = False
    # Autocorreção: IBGE do destinatário via CEP antes das validações (desbloqueia emissão sem montar payload antes).
    if dados.auto_fill and cliente and tipo in ("nfe", "nfce"):
        cod_ibge_antes = (getattr(cliente, "codigo_municipio_ibge", None) or "").strip()
        await nfe_service.resolver_codigo_municipio_ibge(cliente, db=db, persistir_se_viacep=True)
        cod_ibge_depois = (getattr(cliente, "codigo_municipio_ibge", None) or "").strip()
        if cod_ibge_depois and cod_ibge_depois != cod_ibge_antes:
            mutou_autofill_db = True
            avisos.append("Código IBGE do cliente preenchido automaticamente a partir do CEP.")

    duplicidade_equivalente = (
        db.query(NotaFiscal.id)
        .filter(
            NotaFiscal.empresa_id == usuario.empresa_id,
            NotaFiscal.orcamento_id == dados.orcamento_id,
            NotaFiscal.status == "emitida",
            NotaFiscal.tipo == tipo,
            NotaFiscal.serie == serie_val,
        )
        .first()
    )
    checklist: list[dict] = nfe_service.montar_checklist_validacoes_gerais(
        empresa=empresa,
        orcamento=orcamento,
        tipo=tipo,
        natureza_operacao=natureza,
        serie=serie_val,
        duplicidade_equivalente_autorizada=bool(duplicidade_equivalente),
    )
    bloqueios.extend(_bloqueios_from_checklist(checklist))

    # Verifica itens e dados fiscais (catálogo); com itens_override o operador define NCM/CFOP só na emissão.
    itens_sem_ncm = []
    if not dados.itens_override:
        for item in orcamento.itens:
            servico = getattr(item, "servico", None)
            ncm = getattr(servico, "ncm", None) if servico else None
            if not ncm:
                itens_sem_ncm.append(item.descricao or f"Item #{item.id}")

    if itens_sem_ncm:
        avisos.append(
            f"NCM de {len(itens_sem_ncm)} item(ns) será sugerido por IA: {', '.join(itens_sem_ncm[:3])}"
            + (" e outros" if len(itens_sem_ncm) > 3 else "")
        )

    if tipo in ("nfe", "nfce") and cliente:
        b_nfe, a_nfe = await nfe_service.coletar_bloqueios_avisos_preparacao_nfe(empresa, orcamento)
        bloqueios.extend(b_nfe)
        avisos.extend(a_nfe)

    checklist_tipo: list[dict] = []
    campos_autopreenchidos: list[str] = []
    auto_fill_aplicado = False
    # Monta payload preview (apenas se não houver bloqueios) — alinhado ao que o emitirá usar
    payload_preview = None
    emitente_preview = None
    if not bloqueios:
        try:
            if tipo == "nfse":
                cod_lc = (dados.codigo_servico_lc116 or "170600").strip() or "170600"
                aliq = dados.aliquota_iss if dados.aliquota_iss is not None else Decimal("0")
                payload_preview = nfe_service._montar_payload_nfse(
                    empresa, orcamento, cod_lc, aliq, natureza_operacao=natureza
                )
                checklist_tipo = nfe_service.montar_checklist_validacoes_nfse(payload_preview, empresa)
            else:
                payload_preview = await nfe_service._montar_payload_nfe(
                    empresa, orcamento, tipo,
                    natureza, serie_val,
                    dados.itens_override,
                    db=db,
                )
                checklist_tipo = nfe_service.montar_checklist_validacoes_nfe(payload_preview)
                if not dados.itens_override:
                    campos_autopreenchidos = nfe_service.listar_campos_autopreenchidos_nfe(orcamento, payload_preview)
                    if dados.auto_fill and campos_autopreenchidos:
                        auto_fill_aplicado = True
                        avisos.append(f"IA autopreencheu: {', '.join(campos_autopreenchidos)}")
                        salvos_cat = nfe_service.persistir_sugestoes_ia_catalogo_nfe(db, orcamento, payload_preview)
                        if salvos_cat:
                            mutou_autofill_db = True
                            avisos.extend(salvos_cat)
                elif dados.auto_fill:
                    avisos.append(
                        "Ajustes fiscais por item neste modal não são gravados no catálogo; só entram na NF desta verificação/emissão."
                    )
            checklist.extend(checklist_tipo)
            bloqueios.extend(_bloqueios_from_checklist(checklist_tipo))
            emitente_preview = nfe_service.emitente_preview_para_previa(empresa, orcamento)
        except Exception as e:
            avisos.append(f"Aviso ao montar payload: {str(e)[:100]}")

    # Resumo legível
    total_itens = len(orcamento.itens)
    itens_com_ia = len(itens_sem_ncm)
    itens_ok = total_itens - itens_com_ia
    if bloqueios:
        resumo = f"{len(bloqueios)} problema(s) impedem a emissão"
    elif itens_com_ia:
        resumo = f"{itens_ok} item(ns) prontos, {itens_com_ia} NCM sugerido(s) por IA"
    else:
        resumo = f"{total_itens} item(ns) prontos para emissão"

    if mutou_autofill_db:
        try:
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            avisos.append(f"Ajustes automáticos não puderam ser gravados no cadastro: {str(exc)[:120]}")

    return NotaFiscalPrepararOut(
        pronto=len(bloqueios) == 0,
        resumo=resumo,
        avisos=list(dict.fromkeys(avisos)),
        bloqueios=list(dict.fromkeys(bloqueios)),
        payload_preview=payload_preview,
        emitente_preview=emitente_preview,
        checklist=checklist,
        campos_autopreenchidos=campos_autopreenchidos,
        auto_fill_aplicado=auto_fill_aplicado,
    )


# ── Configuração Focus NFe — rotas estáticas ANTES de /{nota_id} ─────────────

@router.post("/configurar-focus")
def configurar_focus(
    dados: ConfiguracaoFiscalEmpresa,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
    _=Depends(exigir_permissao("configuracoes", "escrita")),
):
    """Salva o ambiente NF-e preferido da empresa (homologacao/producao)."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    empresa.nfe_ambiente = dados.nfe_ambiente or "homologacao"
    db.commit()

    return {
        "success": True,
        "message": "Configuração fiscal salva",
        "ambiente": empresa.nfe_ambiente,
        "token_configurado": nfe_service.focus_token_emissao_disponivel(empresa),
        "focus_homolog_token_configurado": bool((settings.FOCUS_TOKEN_HOMOLOGACAO or "").strip()),
    }


@router.post("/configurar-certificado")
async def configurar_certificado_focus(
    certificado: UploadFile = File(..., description="Certificado A1 (.pfx ou .p12)"),
    senha_certificado: str = Form(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
    _=Depends(exigir_permissao("configuracoes", "escrita")),
):
    """Faz upload do certificado A1 e registra a empresa na Focus NFe."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    if not empresa.cnpj:
        raise HTTPException(422, "CNPJ da empresa é obrigatório. Preencha os dados fiscais primeiro.")

    if not settings.FOCUS_TOKEN:
        raise HTTPException(
            503,
            "FOCUS_TOKEN (Token Principal de Produção) não configurado — necessário para cadastrar "
            "empresa/certificado na API Focus (api.focusnfe.com.br). Veja documentação Focus: Painel API → Tokens.",
        )

    cert_bytes = await certificado.read()
    if len(cert_bytes) > 102400:  # 100KB
        raise HTTPException(413, "Certificado deve ter no máximo 100KB")

    if not cert_bytes:
        raise HTTPException(422, "Arquivo de certificado vazio")

    try:
        resultado = await nfe_service.registrar_empresa_focus(empresa, cert_bytes, senha_certificado)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error("Erro ao registrar empresa na Focus empresa_id=%s: %s", usuario.empresa_id, e)
        raise HTTPException(400, f"Erro ao registrar empresa na Focus NFe: {e}")

    if not resultado["success"]:
        msg = resultado.get("erro", "Erro desconhecido na Focus NFe")
        if "Focus retornou 422" in msg:
            raise HTTPException(422, msg)
        raise HTTPException(400, msg)

    db.commit()

    return {
        "success": True,
        "message": "Certificado configurado com sucesso na Focus NFe",
        "certificado_configurado": empresa.focus_certificado_configurado,
        "validade": empresa.focus_certificado_validade.isoformat() if empresa.focus_certificado_validade else None,
    }


@router.get("/status-focus")
async def status_focus(
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Verifica conectividade com a API Focus NFe e retorna status de configuração."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    token_ok = nfe_service.focus_token_emissao_disponivel(empresa)
    conectado = False
    focus_probe_http: Optional[int] = None
    focus_token_rejeitado = False

    if token_ok:
        try:
            async with nfe_service._get_client(empresa) as client:
                r = await client.get("/v2/nfe/ref-ping-teste-cotte")
                focus_probe_http = r.status_code
                if r.status_code == 401:
                    focus_token_rejeitado = True
                conectado = r.status_code in (200, 404, 422)
        except Exception:
            conectado = False

    return {
        "configurado": token_ok,
        "conectado": conectado,
        "focus_probe_http": focus_probe_http,
        "focus_token_rejeitado": focus_token_rejeitado,
        "ambiente": settings.FOCUS_AMBIENTE,
        "nfe_ambiente_empresa": empresa.nfe_ambiente or "homologacao",
        "ambiente_emissao_efetivo": nfe_service._ambiente_nf_effective(empresa),
        "host_emissao_efetivo": nfe_service._focus_base_url_for_empresa(empresa),
        "focus_token_tamanho": len(nfe_service._focus_api_token_for_emission(empresa)),
        "focus_homolog_token_configurado": bool((settings.FOCUS_TOKEN_HOMOLOGACAO or "").strip()),
        "focus_token_principal_configurado": bool((settings.FOCUS_TOKEN or "").strip()),
        "certificado_configurado": bool(empresa.focus_certificado_configurado),
        "certificado_validade": empresa.focus_certificado_validade.isoformat()
        if empresa.focus_certificado_validade
        else None,
    }


@router.post("/webhook/focus")
async def receber_webhook_focus(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str = Header(None),
):
    """Recebe notificações de status de NF-e, NFC-e e NFS-e da Focus NFe."""
    if not nfe_service.webhook_focus_autorizado(authorization or ""):
        raise HTTPException(401, "Autenticação do webhook Focus inválida")

    payload = await request.json()
    ref = payload.get("ref", "")
    if not ref:
        return {"ok": True}

    nota = db.query(NotaFiscal).filter(NotaFiscal.focus_ref == ref).first()
    if not nota:
        return {"ok": True}

    nfe_service._atualizar_nota_com_status_focus(nota, payload)

    if nota.orcamento_id and nota.status in ("emitida", "cancelada", "erro"):
        descricao = {
            "emitida": f"Nota Fiscal {nota.tipo.upper()} {nota.numero or ''} emitida (via webhook Focus)",
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


@router.post("/previsualizar-danfe")
async def previsualizar_danfe_focus(
    dados: NotaFiscalPrepararRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Gera PDF de pré-visualização DANFE via POST /v2/nfe/danfe (Focus)."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = _get_empresa_com_nfe(db, usuario)
    orcamento = (
        db.query(Orcamento)
        .options(
            selectinload(Orcamento.itens).joinedload(ItemOrcamento.servico).joinedload(Servico.categoria),
            joinedload(Orcamento.cliente),
        )
        .filter(Orcamento.id == dados.orcamento_id, Orcamento.empresa_id == usuario.empresa_id)
        .first()
    )
    if not orcamento:
        raise HTTPException(404, "Orçamento não encontrado")
    tipo_pv = (dados.tipo or "nfe").strip().lower()
    if dados.itens_override is not None and tipo_pv in ("nfe", "nfce"):
        if len(dados.itens_override) != len(orcamento.itens):
            raise HTTPException(
                422,
                "itens_override deve incluir uma linha por item do orçamento, na mesma ordem.",
            )
    natureza = (dados.natureza_operacao or "Venda de Mercadorias").strip() or "Venda de Mercadorias"
    serie_val = (dados.serie or "1").strip() or "1"
    if dados.tipo == "nfse":
        raise HTTPException(422, "Pré-visualização DANFE via Focus aplica-se a NF-e/NFC-e.")
    payload = await nfe_service.montar_payload_focus_nfe(
        empresa, orcamento, dados.tipo, natureza, serie_val, dados.itens_override, db=db
    )
    try:
        pdf = await nfe_service.previsualizar_danfe_pdf(payload, empresa)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="previa-danfe.pdf"'},
    )


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
        query.options(joinedload(NotaFiscal.orcamento))
        .order_by(NotaFiscal.criado_em.desc())
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
        .options(joinedload(NotaFiscal.orcamento))
        .filter(NotaFiscal.empresa_id == usuario.empresa_id, NotaFiscal.orcamento_id == orcamento_id)
        .order_by(NotaFiscal.criado_em.desc())
        .all()
    )


@router.post("/{nota_id}/sincronizar-focus", response_model=NotaFiscalOut)
async def sincronizar_nota_com_focus(
    nota_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Consulta status na Focus (GET completa=1) e atualiza a nota local."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    _get_empresa_com_nfe(db, usuario)
    nota = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    try:
        await nfe_service.consultar_nota_focus_e_persistir(db, nota)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.refresh(nota)
    return nota


@router.post("/{nota_id}/carta-correcao")
async def carta_correcao_nota_focus(
    nota_id: int,
    dados: NotaFiscalCartaCorrecaoRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Emite carta de correção na Focus (NF-e apenas)."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    _get_empresa_com_nfe(db, usuario)
    nota = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    if nota.status != "emitida":
        raise HTTPException(400, "Somente notas emitidas podem receber carta de correção")
    try:
        resultado = await nfe_service.emitir_carta_correcao_focus(db, nota, dados.correcao)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"success": True, "data": resultado}


@router.post("/{nota_id}/reenviar-hook-focus")
async def reenviar_hook_focus_nota(
    nota_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Reenvia o webhook de notificação da Focus para esta referência."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    _get_empresa_com_nfe(db, usuario)
    nota = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    try:
        out = await nfe_service.reenviar_webhook_focus(nota)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"success": True, "data": out}


@router.post("/{nota_id}/enviar-whatsapp")
async def enviar_nota_whatsapp_cliente(
    nota_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Envia mensagem ao cliente do orçamento com DANFE/PDF da nota (quando disponível)."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    if not whatsapp_envio_disponivel():
        raise HTTPException(
            status_code=503,
            detail="WhatsApp não configurado (Evolution API ou Z-API).",
        )
    nota = (
        db.query(NotaFiscal)
        .options(
            joinedload(NotaFiscal.orcamento).joinedload(Orcamento.cliente),
            joinedload(NotaFiscal.orcamento).joinedload(Orcamento.empresa),
        )
        .filter(NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id)
        .first()
    )
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    if nota.status != "emitida":
        raise HTTPException(400, "Somente notas emitidas podem ser enviadas ao cliente.")
    if not nota.orcamento_id or not nota.orcamento:
        raise HTTPException(400, "Nota sem orçamento vinculado; não é possível obter o telefone do cliente.")
    orc = nota.orcamento
    tel = (orc.cliente.telefone or "").strip() if orc.cliente else ""
    if not tel:
        raise HTTPException(
            status_code=400,
            detail="Cliente sem telefone cadastrado. Atualize o cadastro do cliente para enviar WhatsApp.",
        )
    empresa = orc.empresa or db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    tipo_pt = _tipo_nf_label(nota.tipo)
    num = (nota.numero or "").strip() or "—"
    orc_num = (orc.numero or "").strip()
    danfe_abs = _absolutizar_midia_focus(nota.danfe_url)
    xml_abs = _absolutizar_midia_focus(nota.xml_url)

    pdf_bytes = b""
    if danfe_abs:
        try:
            pdf_bytes = await _baixar_url_bytes(danfe_abs)
        except Exception as e:
            logger.warning("Falha ao baixar DANFE para WhatsApp (nota %s): %s", nota_id, e)
            pdf_bytes = b""

    nome_cli = (orc.cliente.nome or "Cliente").strip()
    nome_emp = (empresa.nome if empresa else "Empresa").strip()
    caption = (
        f"📄 *{tipo_pt}*\n"
        f"Olá, {nome_cli}!\n\n"
        f"Segue o documento da sua nota fiscal *nº {num}*"
    )
    if orc_num:
        caption += f", referente ao orçamento *{orc_num}*"
    caption += f".\n\n_{nome_emp}_"
    if not pdf_bytes and danfe_abs:
        caption += f"\n\n🔗 {danfe_abs}"
    if not pdf_bytes and xml_abs:
        caption += f"\n\n📎 XML: {xml_abs}"

    doc_label = f"NF-{num}".replace("/", "-")[:40]
    ok = False
    if pdf_bytes:
        ok = await enviar_pdf(tel, pdf_bytes, doc_label, caption, empresa=empresa)
    else:
        ok = await enviar_mensagem_texto(tel, caption, empresa=empresa)
    if not ok:
        raise HTTPException(
            status_code=502,
            detail="Falha ao enviar WhatsApp. Verifique a instância Evolution/Z-API e tente novamente.",
        )
    return {"success": True, "data": {"mensagem": "Mensagem enviada ao cliente via WhatsApp."}}


@router.post("/{nota_id}/enviar-email")
def enviar_nota_email_cliente(
    nota_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Envia e-mail ao cliente do orçamento com resumo da nota e anexo DANFE (quando disponível)."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    if not email_habilitado():
        raise HTTPException(
            status_code=503,
            detail="E-mail não configurado (Brevo API ou SMTP).",
        )
    nota = (
        db.query(NotaFiscal)
        .options(joinedload(NotaFiscal.orcamento).joinedload(Orcamento.cliente))
        .filter(NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id)
        .first()
    )
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    if nota.status != "emitida":
        raise HTTPException(400, "Somente notas emitidas podem ser enviadas ao cliente.")
    if not nota.orcamento_id or not nota.orcamento:
        raise HTTPException(400, "Nota sem orçamento vinculado.")
    orc = nota.orcamento
    if not orc.cliente:
        raise HTTPException(400, "Orçamento sem cliente.")
    email_dest = (orc.cliente.email or "").strip()
    if not email_dest:
        raise HTTPException(
            status_code=400,
            detail="Cliente sem e-mail cadastrado. Atualize o cadastro do cliente para enviar e-mail.",
        )
    empresa = orc.empresa or db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    danfe_abs = _absolutizar_midia_focus(nota.danfe_url)

    pdf_bytes: bytes | None = None
    if danfe_abs:
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                r = client.get(danfe_abs)
                r.raise_for_status()
                pdf_bytes = r.content
        except Exception as e:
            logger.warning("Falha ao baixar DANFE para e-mail (nota %s): %s", nota_id, e)
            pdf_bytes = None

    ok = enviar_nota_fiscal_por_email(
        destinatario=email_dest,
        cliente_nome=orc.cliente.nome or "Cliente",
        empresa_nome=empresa.nome if empresa else "Empresa",
        tipo_nf=nota.tipo,
        numero_nf=nota.numero,
        orcamento_numero=orc.numero,
        danfe_url=danfe_abs,
        pdf_bytes=pdf_bytes,
    )
    if not ok:
        raise HTTPException(
            status_code=502,
            detail="Falha ao enviar e-mail. Verifique Brevo/SMTP e tente novamente.",
        )
    return {"success": True, "data": {"mensagem": "E-mail enviado ao cliente."}}


@router.get("/{nota_id}", response_model=NotaFiscalOut)
def get_nota_fiscal(
    nota_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    nota = (
        db.query(NotaFiscal)
        .options(joinedload(NotaFiscal.orcamento))
        .filter(NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id)
        .first()
    )
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    return nota


@router.post("/{nota_id}/analisar-erro")
async def analisar_erro_nota_fiscal(
    nota_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Analisa o erro de uma nota fiscal e retorna sugestões de correção em linguagem simples."""
    import json as _json
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    nota = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota:
        raise HTTPException(404, "Nota fiscal não encontrada")
    if nota.status != "erro":
        raise HTTPException(400, "Somente notas com status 'erro' podem ser analisadas")

    # Extrai campos do erro da Focus/SEFAZ (quando é JSON estruturado)
    campos_erro: list[str] = []
    erro_texto = nota.erro_mensagem or ""
    try:
        erro_obj = _json.loads(erro_texto)
        campos_erro = erro_obj.get("campos", [])
        if not campos_erro and erro_obj.get("error"):
            erro_texto = erro_obj["error"]
    except (_json.JSONDecodeError, TypeError):
        pass

    # Mapeamento de campos técnicos para linguagem do operador
    _MAPA_SUGESTOES = {
        "naturezaOperacao (ou natOp)": (
            "Natureza da operação ausente — campo técnico já corrigido no sistema. "
            "Basta reemitir a nota."
        ),
        "dest.cpf ou dest.cnpj inválido": (
            "O cliente não tem CPF ou CNPJ cadastrado, ou o documento está em formato errado. "
            "Acesse o cadastro do cliente, preencha o CPF (para pessoa física) "
            "ou CNPJ (para pessoa jurídica) e tente novamente."
        ),
        "dest.endereco": (
            "O endereço do cliente está incompleto ou ausente. "
            "Acesse o cadastro do cliente, preencha Logradouro, Número, Bairro, "
            "Cidade e UF, depois reemita a nota."
        ),
        "items: deve conter pelo menos 1 item": (
            "O orçamento não possui itens ou os itens não foram carregados corretamente. "
            "Verifique se o orçamento tem pelo menos um produto/serviço adicionado."
        ),
    }

    sugestoes = []
    for campo in campos_erro:
        acao = nfe_service.sugerir_acao_campo_erro_focus(campo) or _MAPA_SUGESTOES.get(campo)
        if not acao:
            acao = f"Verifique o campo: {campo}"
        sugestoes.append({
            "campo": campo,
            "acao": acao,
        })

    if not sugestoes and erro_texto:
        et_lower = erro_texto.lower()
        if (
            "invoice" in et_lower
            and ("não encontrado" in et_lower or "nao encontrado" in et_lower)
            and nota.tipo in ("nfe", "nfce")
        ):
            acao_geral = (
                "A integração consultava o status no endpoint de NFS-e em vez do de NF-e; "
                "isso foi corrigido. Após atualizar o servidor, use Reemitir nesta nota ou emita novamente. "
                f"(Resposta original: {erro_texto[:200]})"
            )
        else:
            acao_geral = nfe_service.sugerir_acao_mensagem_erro_focus(erro_texto)
            if not acao_geral:
                acao_geral = f"Erro recebido da Focus/SEFAZ: {erro_texto[:300]}"
        sugestoes.append({
            "campo": "erro_geral",
            "acao": acao_geral,
        })

    # Verifica se pode reemitir (orçamento ainda existe)
    pode_reemitir = False
    if nota.orcamento_id:
        orcamento_existe = db.query(Orcamento.id).filter(
            Orcamento.id == nota.orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        ).first()
        pode_reemitir = bool(orcamento_existe)

    return {
        "nota_id": nota_id,
        "erro_original": nota.erro_mensagem,
        "campos_com_erro": campos_erro,
        "sugestoes": sugestoes,
        "pode_reemitir": pode_reemitir,
        "orcamento_id": nota.orcamento_id,
        "tipo": nota.tipo,
        "serie": nota.serie,
        "natureza_operacao": nota.natureza_operacao,
    }


@router.post("/{nota_id}/reemitir", response_model=NotaFiscalOut)
async def reemitir_nota_fiscal(
    nota_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Cria uma nova nota a partir de uma nota com erro, reaproveitando os dados originais."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = _get_empresa_com_nfe(db, usuario)

    nota_original = db.query(NotaFiscal).filter(
        NotaFiscal.id == nota_id, NotaFiscal.empresa_id == usuario.empresa_id
    ).first()
    if not nota_original:
        raise HTTPException(404, "Nota fiscal não encontrada")
    if nota_original.status != "erro":
        raise HTTPException(400, "Somente notas com erro podem ser reemitidas")
    if not nota_original.orcamento_id:
        raise HTTPException(422, "Nota sem orçamento associado — não é possível reemitir")

    orcamento = (
        db.query(Orcamento)
        .options(
            selectinload(Orcamento.itens).joinedload(ItemOrcamento.servico).joinedload(Servico.categoria),
            joinedload(Orcamento.cliente),
        )
        .filter(Orcamento.id == nota_original.orcamento_id, Orcamento.empresa_id == usuario.empresa_id)
        .first()
    )
    if not orcamento:
        raise HTTPException(404, "Orçamento associado não encontrado")

    nova_nota = NotaFiscal(
        empresa_id=usuario.empresa_id,
        orcamento_id=nota_original.orcamento_id,
        tipo=nota_original.tipo,
        modelo=nota_original.modelo,
        serie=nota_original.serie,
        natureza_operacao=nota_original.natureza_operacao,
        status="pendente",
        criado_por_id=usuario.id,
        criado_em=datetime.now(timezone.utc),
    )
    db.add(nova_nota)
    db.flush()

    try:
        if nova_nota.tipo == "nfse":
            payload = nfe_service._montar_payload_nfse(
                empresa, orcamento,
                nota_original.codigo_servico_lc116 if hasattr(nota_original, "codigo_servico_lc116") else "170600",
                0,
            )
        else:
            payload = await nfe_service._montar_payload_nfe(
                empresa, orcamento, nova_nota.tipo,
                nova_nota.natureza_operacao or "Venda de Mercadorias",
                nova_nota.serie or "1",
                None,
                db=db,
            )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    db.commit()
    db.refresh(nova_nota)
    background_tasks.add_task(nfe_service.emitir_nota_background, nova_nota.id, empresa.id, payload)
    return nova_nota


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

    try:
        return await nfe_service.cancelar_nota(db, nota, empresa, dados.motivo)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
