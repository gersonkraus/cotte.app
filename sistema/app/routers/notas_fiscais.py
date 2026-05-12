"""
notas_fiscais.py — Endpoints para emissão e gestão de NF-e/NFC-e/NFS-e.
"""

import logging
import httpx
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile
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
    NotaFiscalEmitirRequest,
    NotaFiscalOut,
    NotaFiscalListOut,
    NotaFiscalPrepararRequest,
    NotaFiscalPrepararOut,
)
from app.services import nfe_service
from app.services.fiscal_ai_service import sugerir_dados_fiscais

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notas-fiscais", tags=["Notas Fiscais"])


def _get_empresa_com_nfe(db: Session, usuario) -> Empresa:
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")
    if not settings.FOCUS_TOKEN:
        raise HTTPException(422, "Token Focus NFe não configurado. Contate o suporte.")
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
            dados.codigo_servico_lc116 or "170600",
            dados.aliquota_iss or 0,
        )
    else:
        payload = await nfe_service._montar_payload_nfe(
            empresa, orcamento, dados.tipo,
            dados.natureza_operacao, dados.serie,
            dados.itens_override,
            db=db,
        )

    db.commit()
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
    """Pré-valida o orçamento para emissão de NF-e. Não cria nota, não acessa Notaas."""
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

    bloqueios: list[str] = []
    avisos: list[str] = []

    # Valida empresa
    if not empresa.cnpj:
        bloqueios.append("CNPJ da empresa não configurado (Configurações → Fiscal)")
    if not settings.FOCUS_TOKEN:
        bloqueios.append("Token Focus NFe não configurado — contate o suporte")
    if not empresa.endereco_cidade:
        avisos.append("Endereço da empresa incompleto — pode causar rejeição")

    if dados.tipo in ("nfe", "nfce") and empresa:
        ie_emp = (empresa.inscricao_estadual or "").strip()
        if not ie_emp:
            avisos.append(
                "Inscrição estadual da empresa não preenchida em Configurações → Fiscal. "
                "Sem IE coerente com o CNPJ e a UF, a SEFAZ pode rejeitar a NF-e (ex.: cStat 209 — IE do emitente inválida)."
            )

    # Valida cliente/destinatário
    cliente = orcamento.cliente
    if cliente:
        from app.services.nfe_service import _limpar_doc
        limpo_cnpj = _limpar_doc(cliente.cnpj or "")
        limpo_cpf = _limpar_doc(cliente.cpf or "")
        if not limpo_cnpj and not limpo_cpf:
            bloqueios.append(f"Cliente '{cliente.nome or cliente.razao_social}' sem CPF ou CNPJ cadastrado")
    else:
        bloqueios.append("Orçamento sem cliente associado")

    # Verifica itens e dados fiscais
    itens_sem_ncm = []
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

    if dados.tipo in ("nfe", "nfce") and cliente:
        b_nfe, a_nfe = await nfe_service.coletar_bloqueios_avisos_preparacao_nfe(empresa, orcamento)
        bloqueios.extend(b_nfe)
        avisos.extend(a_nfe)

    # Monta payload preview (apenas se não houver bloqueios) — alinhado ao que o emitirá usar
    payload_preview = None
    emitente_preview = None
    if not bloqueios:
        try:
            if dados.tipo == "nfse":
                cod_lc = (dados.codigo_servico_lc116 or "170600").strip() or "170600"
                aliq = dados.aliquota_iss if dados.aliquota_iss is not None else Decimal("0")
                payload_preview = nfe_service._montar_payload_nfse(
                    empresa, orcamento, cod_lc, aliq
                )
            else:
                natureza = (dados.natureza_operacao or "Venda de Mercadorias").strip() or "Venda de Mercadorias"
                serie_val = (dados.serie or "1").strip() or "1"
                payload_preview = await nfe_service._montar_payload_nfe(
                    empresa, orcamento, dados.tipo,
                    natureza, serie_val,
                    None,
                    db=db,
                )
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

    return NotaFiscalPrepararOut(
        pronto=len(bloqueios) == 0,
        resumo=resumo,
        avisos=avisos,
        bloqueios=bloqueios,
        payload_preview=payload_preview,
        emitente_preview=emitente_preview,
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
        "token_configurado": bool(settings.FOCUS_TOKEN),
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
        raise HTTPException(503, "FOCUS_TOKEN não configurado no servidor.")

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
        raise HTTPException(400, resultado.get("erro", "Erro desconhecido na Focus NFe"))

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

    token_ok = bool(settings.FOCUS_TOKEN)
    conectado = False

    if token_ok:
        try:
            async with nfe_service._get_client() as client:
                r = await client.get("/v2/nfe/ref-ping-teste-cotte")
                conectado = r.status_code in (200, 404, 422)
        except Exception:
            conectado = False

    return {
        "configurado": token_ok,
        "conectado": conectado,
        "ambiente": settings.FOCUS_AMBIENTE,
        "nfe_ambiente_empresa": empresa.nfe_ambiente or "homologacao",
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
    if not nfe_service.verificar_token_webhook_focus(authorization or "", settings.FOCUS_TOKEN):
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

    # Extrai campos do erro Notaas (quando é JSON estruturado)
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
        acao = nfe_service.sugerir_acao_campo_erro_notaas(campo) or _MAPA_SUGESTOES.get(campo)
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
            acao_geral = nfe_service.sugerir_acao_mensagem_erro_notaas(erro_texto)
            if not acao_geral:
                acao_geral = f"Erro recebido da SEFAZ/Notaas: {erro_texto[:300]}"
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
    )
    db.add(nova_nota)
    db.flush()

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

    db.commit()
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

    return await nfe_service.cancelar_nota(db, nota, empresa, dados.motivo)
