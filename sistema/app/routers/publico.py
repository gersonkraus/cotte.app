from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
import io
from typing import Literal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.models.models import (
    Orcamento,
    ItemOrcamento,
    Notificacao,
    StatusOrcamento,
    ModoAgendamentoOrcamento,
    HistoricoEdicao,
    Empresa,
    OrcamentoDocumento,
    DocumentoEmpresa,
    TipoConteudoDocumento,
    Agendamento,
    ConfigAgendamento,
    StatusAgendamento,
)
from app.schemas.schemas import OrcamentoPublicoOut
from app.services.whatsapp_service import (
    notificar_operador_visualizacao,
    notificar_operador_recusa,
    enviar_mensagem_texto,
)
from app.services.otp_service import otp_service
from app.services.pdf_service import gerar_pdf_orcamento
from app.services.quote_notification_service import handle_quote_status_changed
from app.services.email_service import (
    enviar_email_confirmacao_aceite,
    email_habilitado,
    enviar_otp_aceite,
)
from app.services.rate_limit_service import public_endpoint_rate_limiter
from app.services.pix_service import gerar_qrcode_pix, gerar_payload_pix
from app.services.documentos_service import montar_nome_download, resolver_arquivo_path
from app.services import financeiro_service as fin_svc
from app.utils.orcamento_utils import renomear_numero_aprovado

from app.utils.pdf_utils import get_orcamento_dict_for_pdf, get_empresa_dict_for_pdf

router = APIRouter(prefix="/o", tags=["Público"])

logger = logging.getLogger(__name__)


def _get_orcamento_publico(
    link: str, db: Session, for_update: bool = False
) -> Orcamento:
    q = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.itens).joinedload(ItemOrcamento.servico),
            joinedload(Orcamento.empresa),
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.documentos),
        )
        .filter(Orcamento.link_publico == link)
    )
    if for_update:
        # of=Orcamento: trava apenas a tabela orcamentos, não os LEFT OUTER JOINs
        # (PostgreSQL não permite FOR UPDATE no lado nullable de outer join)
        q = q.with_for_update(of=Orcamento)
    orc = q.first()
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    return orc


@router.get("/{link_publico}/pdf")
def download_pdf_orcamento(
    link_publico: str,
    db: Session = Depends(get_db),
):
    """Gera e serve o PDF do orçamento on-the-fly, sem salvar em disco."""
    orc = _get_orcamento_publico(link_publico, db)
    
    orc_dict = get_orcamento_dict_for_pdf(orc, db)
    empresa_dict = get_empresa_dict_for_pdf(orc.empresa)

    try:
        logger.info(f"Iniciando geração de PDF para orçamento {link_publico}")
        pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
        
        if not pdf_bytes or len(pdf_bytes) < 100:
            logger.error(f"PDF gerado é inválido ou vazio para {link_publico}")
            raise ValueError("PDF vazio")

        filename = f"Orcamento-{orc.numero.replace('/', '-')}.pdf"
        logger.info(f"PDF gerado com sucesso ({len(pdf_bytes)} bytes). Retornando resposta.")
        
        # Usando Response direto para evitar problemas com StreamingResponse em alguns ambientes
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )
    except Exception as e:
        logger.exception("Erro fatal ao gerar PDF público para %s", link_publico)
        # Retorna erro com mais detalhes para ajudar no debug (temporário)
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno ao gerar o arquivo PDF: {str(e)}"
        )


def _check_rate_limit(request: Request, action: str, link: str) -> None:
    """Verifica rate limit por IP para endpoints públicos de escrita.
    Levanta 429 se o limite for excedido."""
    client_ip = (request.client.host if request.client else None) or "unknown"
    result = public_endpoint_rate_limiter.check(f"{action}:{link}:{client_ip}")
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Tente novamente em alguns minutos.",
            headers={"Retry-After": str(result.retry_after_seconds)},
        )


@router.post("/{link_publico}/pix/gerar")
def gerar_pix_publico(
    link_publico: str,
    dados: dict,
    db: Session = Depends(get_db),
):
    """Gera QR Code PIX para o saldo devedor do orçamento público."""
    orc = _get_orcamento_publico(link_publico, db)

    valor = dados.get("valor")
    if not valor or valor <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido")

    if not orc.pix_chave:
        raise HTTPException(
            status_code=400,
            detail=f"PIX não configurado neste orçamento. chave={orc.pix_chave}, empresa_id={orc.empresa_id}",
        )

    try:
        from app.schemas.schemas import PixGerarResponse

        payload = gerar_payload_pix(orc.pix_chave, orc.pix_titular or "", valor=valor)
        qrcode = gerar_qrcode_pix(orc.pix_chave, orc.pix_titular or "", valor=valor)

        return PixGerarResponse(
            qrcode=qrcode,
            payload=payload,
            valor=valor,
        )
    except Exception as e:
        logger.exception("Erro ao gerar PIX público para %s: %s", link_publico, str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PIX: {str(e)}")


@router.get("/{link_publico}", response_model=OrcamentoPublicoOut)
async def ver_orcamento_publico(link_publico: str, db: Session = Depends(get_db)):
    """Retorna dados do orçamento para o cliente (sem autenticação).
    Registra a visualização e notifica o operador na primeira abertura."""
    # with_for_update: lock de linha em PostgreSQL — previne race condition
    # quando dois clientes abrem simultaneamente (evita notificações duplicadas)
    orc = _get_orcamento_publico(link_publico, db, for_update=True)

    primeira_visualizacao = orc.visualizado_em is None

    # Registra visualização
    orc.visualizacoes = (orc.visualizacoes or 0) + 1
    if primeira_visualizacao:
        orc.visualizado_em = datetime.now(timezone.utc)

        # Cria notificação in-app
        db.add(
            Notificacao(
                empresa_id=orc.empresa_id,
                orcamento_id=orc.id,
                tipo="visualizado",
                titulo=f"📬 {orc.cliente.nome} abriu o orçamento {orc.numero}",
                mensagem=f"O cliente {orc.cliente.nome} visualizou o orçamento {orc.numero} pela primeira vez.",
            )
        )

    db.commit()
    db.refresh(orc)

    # Registra visualização na linha do tempo do orçamento
    if primeira_visualizacao:
        try:
            db.add(
                HistoricoEdicao(
                    orcamento_id=orc.id,
                    editado_por_id=None,
                    descricao="Proposta visualizada pelo cliente via link público.",
                )
            )
            db.commit()
        except Exception:
            db.rollback()

    # Notifica operador via WhatsApp apenas se o toggle estiver ativo
    notif_ativa = getattr(orc.empresa, "notif_whats_visualizacao", True)
    if primeira_visualizacao and notif_ativa and orc.empresa.telefone_operador:
        try:
            await notificar_operador_visualizacao(
                orc.empresa.telefone_operador,
                orc.numero,
                orc.cliente.nome,
            )
        except Exception:
            logger.exception(
                "Falha ao notificar visualização (orcamento_id=%s)", orc.id
            )

    # Fallback: auto-aplicar PIX da empresa em orçamentos aprovados que ainda não têm PIX
    # Cobre aceites anteriores ao deploy do recurso e falhas silenciosas no endpoint de aceite
    if (
        orc.status == StatusOrcamento.APROVADO
        and not orc.pix_chave
        and orc.empresa
        and getattr(orc.empresa, "pix_chave_padrao", None)
    ):
        try:
            orc.pix_chave = orc.empresa.pix_chave_padrao
            orc.pix_tipo = orc.empresa.pix_tipo_padrao
            orc.pix_titular = orc.empresa.pix_titular_padrao
            orc.pix_informado_em = datetime.now(timezone.utc)
            orc.pix_payload = gerar_payload_pix(
                orc.pix_chave, orc.pix_titular or "", valor=orc.total
            )
            orc.pix_qrcode = gerar_qrcode_pix(
                orc.pix_chave, orc.pix_titular or "", valor=orc.total
            )
            db.commit()
            db.refresh(orc)
        except Exception:
            db.rollback()
            logger.exception(
                "Falha ao auto-aplicar PIX no público (orcamento_id=%s)", orc.id
            )

    if hasattr(OrcamentoPublicoOut, "model_validate"):
        out = OrcamentoPublicoOut.model_validate(orc)
    else:
        out = OrcamentoPublicoOut.from_orm(orc)
    # Informa ao frontend se há agendamento aguardando escolha do cliente
    out.has_agendamento_pendente = any(
        a.status == StatusAgendamento.AGUARDANDO_ESCOLHA
        for a in (getattr(orc, "agendamentos", []) or [])
    )
    out.documentos = [
        d
        for d in (getattr(orc, "documentos", []) or [])
        if getattr(d, "exibir_no_portal", False)
    ]
    # Expõe pagamentos confirmados para barra de progresso financeira (v10)
    from app.schemas.schemas import PagamentoPublicoOut, ContaPublicoOut

    pagamentos = getattr(orc, "pagamentos_financeiros", []) or []
    out.pagamentos_financeiros = [
        PagamentoPublicoOut(
            id=p.id,
            valor=p.valor,
            tipo=p.tipo.value if hasattr(p.tipo, "value") else str(p.tipo),
            data_pagamento=p.data_pagamento,
            status=p.status.value if hasattr(p.status, "value") else str(p.status),
            forma_pagamento_nome=p.forma_pagamento_config.nome
            if p.forma_pagamento_config
            else None,
            forma_pagamento_icone=p.forma_pagamento_config.icone
            if p.forma_pagamento_config
            else None,
        )
        for p in pagamentos
    ]
    # Expõe contas a receber (parcelas) para tabela na proposta pública (i001)
    from app.models.models import TipoConta

    contas = [
        c
        for c in (getattr(orc, "contas_financeiras", []) or [])
        if c.tipo == TipoConta.RECEBER
    ]
    out.contas_financeiras_publico = [
        ContaPublicoOut(
            id=c.id,
            descricao=c.descricao,
            valor=c.valor,
            valor_pago=c.valor_pago or 0,
            status=c.status.value if hasattr(c.status, "value") else str(c.status),
            data_vencimento=c.data_vencimento,
            tipo_lancamento=c.tipo_lancamento,
            numero_parcela=c.numero_parcela,
            total_parcelas=c.total_parcelas,
        )
        for c in contas
    ]
    return out


@router.get("/{link_publico}/documentos/{orcamento_documento_id}")
def baixar_documento_publico(
    link_publico: str,
    orcamento_documento_id: int,
    db: Session = Depends(get_db),
    download: bool = False,
):
    orc = _get_orcamento_publico(link_publico, db)
    vinc = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.id == orcamento_documento_id,
            OrcamentoDocumento.orcamento_id == orc.id,
        )
        .first()
    )
    if not vinc or not vinc.exibir_no_portal:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if download and not vinc.permite_download:
        raise HTTPException(
            status_code=403, detail="Download não permitido para este documento"
        )

    # Prioriza o snapshot de HTML se disponível no vínculo
    if (vinc.conteudo_html or "").strip():
        return HTMLResponse(
            content=vinc.conteudo_html,
            media_type="text/html; charset=utf-8",
        )

    path_vazio = not (vinc.arquivo_path and str(vinc.arquivo_path).strip())
    if path_vazio and vinc.documento_id:
        doc_emp = (
            db.query(DocumentoEmpresa)
            .filter(
                DocumentoEmpresa.id == vinc.documento_id,
                DocumentoEmpresa.empresa_id == orc.empresa_id,
                DocumentoEmpresa.deletado_em.is_(None),
            )
            .first()
        )
        if (
            doc_emp
            and doc_emp.tipo_conteudo == TipoConteudoDocumento.HTML
            and (doc_emp.conteudo_html or "").strip()
        ):
            return HTMLResponse(
                content=doc_emp.conteudo_html,
                media_type="text/html; charset=utf-8",
            )
    if path_vazio:
        raise HTTPException(status_code=404, detail="Documento não disponível")

    arquivo_path_ou_url = resolver_arquivo_path(vinc.arquivo_path)

    # Se é URL do R2, gerar URL temporária (presigned) para acesso público
    if arquivo_path_ou_url.startswith("http://") or arquivo_path_ou_url.startswith(
        "https://"
    ):
        from app.services.r2_service import r2_service

        # Verifica se é URL do R2 e se o R2 está configurado com client ativo
        if (
            r2_service.client
            and r2_service.public_url
            and arquivo_path_ou_url.startswith(r2_service.public_url)
        ):
            key = arquivo_path_ou_url.replace(r2_service.public_url + "/", "")
            try:
                temp_url = r2_service.get_presigned_url(key)
                logger.info("Generated presigned URL for key: %s", key)
                return RedirectResponse(url=temp_url, status_code=302)
            except Exception as e:
                logger.error(
                    "Erro ao gerar URL temporária para documento R2: %s", str(e)
                )
                # Se falhar, tenta redirect direto como fallback
                return RedirectResponse(url=arquivo_path_ou_url, status_code=302)

        # Fallback: redirecionamento direto para outras URLs (não R2 ou R2 não config)
        return RedirectResponse(url=arquivo_path_ou_url, status_code=302)

    # Fallback: arquivo local legado
    filename = montar_nome_download(
        vinc.documento_nome, vinc.documento_versao, ext=".pdf"
    )
    dispo = "attachment" if download else "inline"
    return FileResponse(
        arquivo_path_ou_url,
        media_type=vinc.mime_type or "application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'{dispo}; filename="{filename}"'},
    )


class AceiteRequest(BaseModel):
    """Aceite digital: nome é autodeclarado. Se OTP exigido, valida o código."""

    nome: str
    mensagem: str | None = None  # E: comentário opcional do cliente no aceite
    codigo_otp: str | None = None  # f001: código de confirmação se exigido


class SolicitarOtpRequest(BaseModel):
    canal: Literal["whatsapp", "email", "ambos"]


def _exige_otp(orc: Orcamento) -> bool:
    """Centraliza a regra: exige OTP se marcado no orçamento OU se atingiu valor mínimo da empresa."""
    if orc.exigir_otp:
        return True
    if orc.empresa.exigir_otp_aceite:
        minimo = orc.empresa.otp_valor_minimo or 0
        if orc.total >= minimo:
            return True
    return False


@router.post("/{link_publico}/aceitar/solicitar-otp")
async def solicitar_otp(
    link_publico: str,
    dados: SolicitarOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Gera e envia um código OTP para o cliente confirmar o aceite.

    canais:
      - "whatsapp" — envia apenas por WhatsApp
      - "email"    — envia apenas por e-mail
      - "ambos"    — envia por WhatsApp (primário) e e-mail (fallback) simultaneamente
    """
    _check_rate_limit(request, "solicitar-otp", link_publico)
    orc = _get_orcamento_publico(link_publico, db)

    erro = _status_bloqueia_acao(orc)
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    canal = dados.canal
    codigo = otp_service.gerar_codigo(link_publico)

    resultados = {"whatsapp": None, "email": None}

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    if canal in ("whatsapp", "ambos"):
        telefone = orc.cliente.telefone
        if not telefone:
            resultados["whatsapp"] = {
                "enviado": False,
                "motivo": "Cliente não possui telefone cadastrado.",
            }
            if canal == "whatsapp":
                raise HTTPException(
                    status_code=400, detail=resultados["whatsapp"]["motivo"]
                )
        else:
            texto = f"Seu código de confirmação para aceitar o orçamento {orc.numero} é: *{codigo}*. Válido por 10 minutos."
            try:
                await enviar_mensagem_texto(telefone, texto, empresa=orc.empresa)
                resultados["whatsapp"] = {"enviado": True}
            except Exception:
                logger.exception("Falha ao enviar OTP via WhatsApp")
                resultados["whatsapp"] = {
                    "enviado": False,
                    "motivo": "Falha ao enviar código por WhatsApp.",
                }
                if canal == "whatsapp":
                    raise HTTPException(
                        status_code=500, detail=resultados["whatsapp"]["motivo"]
                    )

    # ── E-mail ────────────────────────────────────────────────────────────────
    if canal in ("email", "ambos"):
        email = orc.cliente.email
        if not email:
            resultados["email"] = {
                "enviado": False,
                "motivo": "Cliente não possui e-mail cadastrado.",
            }
            if canal == "email":
                raise HTTPException(
                    status_code=400, detail=resultados["email"]["motivo"]
                )
        elif not email_habilitado():
            resultados["email"] = {
                "enviado": False,
                "motivo": "Serviço de e-mail não configurado.",
            }
            if canal == "email":
                raise HTTPException(
                    status_code=500, detail=resultados["email"]["motivo"]
                )
        else:
            try:
                ok = enviar_otp_aceite(email, codigo, orc.numero, orc.empresa.nome)
                resultados["email"] = {"enviado": ok}
            except Exception:
                logger.exception("Falha ao enviar OTP via e-mail")
                resultados["email"] = {
                    "enviado": False,
                    "motivo": "Falha ao enviar código por e-mail.",
                }
                if canal == "email":
                    raise HTTPException(
                        status_code=500, detail=resultados["email"]["motivo"]
                    )

            if not ok and canal == "email":
                raise HTTPException(
                    status_code=500, detail="Falha ao enviar e-mail. Tente novamente."
                )

    # ── Resultado "ambos" ─────────────────────────────────────────────────────
    if canal == "ambos":
        wa_ok = resultados["whatsapp"] and resultados["whatsapp"]["enviado"]
        em_ok = resultados["email"] and resultados["email"]["enviado"]
        if not wa_ok and not em_ok:
            raise HTTPException(
                status_code=500,
                detail="Não foi possível enviar o código. Verifique se o cliente possui telefone e e-mail cadastrados.",
            )
        return {
            "enviado": True,
            "canal": "ambos",
            "resultados": resultados,
            "expira_em_minutos": 10,
        }

    return {
        "enviado": True,
        "canal": canal,
        "expira_em_minutos": 10,
    }


class RecusaRequest(BaseModel):
    motivo: str | None = None  # C: motivo opcional da recusa


class AjusteRequest(BaseModel):
    mensagem: str


def _status_bloqueia_acao(orc: Orcamento) -> str | None:
    """Retorna mensagem de erro se o orçamento não puder mais ser aceito/recusado."""
    if orc.status == StatusOrcamento.APROVADO:
        return "Este orçamento já foi aceito."
    if orc.status == StatusOrcamento.RECUSADO:
        return "Este orçamento já foi recusado."
    if orc.status == StatusOrcamento.EXPIRADO:
        return "Este orçamento está expirado e não pode mais ser aceito."
    if orc.status == StatusOrcamento.EM_EXECUCAO:
        return (
            "Este orçamento já está em execução e não pode ser alterado pelo cliente."
        )
    if orc.status == StatusOrcamento.AGUARDANDO_PAGAMENTO:
        return "Este orçamento já está aguardando pagamento e não pode ser alterado pelo cliente."
    return None


@router.post("/{link_publico}/aceitar", response_model=OrcamentoPublicoOut)
async def aceitar_orcamento(
    link_publico: str,
    dados: AceiteRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Cliente aceita o orçamento digitalmente (nome autodeclarado; valida OTP se exigido)."""
    _check_rate_limit(request, "aceitar", link_publico)
    # with_for_update: lock de linha em PostgreSQL — previne double-accept concorrente
    orc = _get_orcamento_publico(link_publico, db, for_update=True)

    erro = _status_bloqueia_acao(orc)
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    if orc.status != StatusOrcamento.ENVIADO:
        raise HTTPException(
            status_code=400, detail="Este orçamento não está disponível para aceite."
        )

    # Validação de OTP se exigido (regra flexível)
    if _exige_otp(orc):
        if not dados.codigo_otp:
            raise HTTPException(
                status_code=400, detail="Código de confirmação é obrigatório."
            )

        if not otp_service.validar_codigo(link_publico, dados.codigo_otp):
            raise HTTPException(
                status_code=400,
                detail="Código incorreto ou expirado. Verifique e tente novamente.",
            )

        orc.aceite_confirmado_otp = True

    nome = dados.nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe seu nome para aceitar.")

    old_status = orc.status
    orc.status = StatusOrcamento.APROVADO
    orc.aceite_nome = nome
    orc.aceite_mensagem = (dados.mensagem or "").strip() or None  # E: salva mensagem
    orc.aceite_em = datetime.now(timezone.utc)

    # Auto-aplicar PIX da empresa se o orçamento ainda não tem chave PIX configurada
    try:
        empresa = (
            orc.empresa
            or db.query(Empresa).filter(Empresa.id == orc.empresa_id).first()
        )
        renomear_numero_aprovado(orc, empresa)
        pix_padrao = getattr(empresa, "pix_chave_padrao", None) if empresa else None
        if not orc.pix_chave and pix_padrao:
            orc.pix_chave = empresa.pix_chave_padrao
            orc.pix_tipo = empresa.pix_tipo_padrao
            orc.pix_titular = empresa.pix_titular_padrao
            orc.pix_informado_em = datetime.now(timezone.utc)
            try:
                orc.pix_payload = gerar_payload_pix(
                    orc.pix_chave, orc.pix_titular or "", valor=orc.total
                )
                orc.pix_qrcode = gerar_qrcode_pix(
                    orc.pix_chave, orc.pix_titular or "", valor=orc.total
                )
            except Exception:
                logger.exception(
                    "Falha ao gerar payload/QR PIX no aceite público (orcamento_id=%s)",
                    orc.id,
                )
    except Exception:
        logger.exception(
            "Falha ao auto-aplicar PIX no aceite público (orcamento_id=%s)", orc.id
        )

    # Criar contas a receber (idempotente)
    # A exceção PROPAGA — se falhar, o orçamento NÃO deve ser aprovado sem parcelas.
    fin_svc.criar_contas_receber_aprovacao(orc, orc.empresa_id, db)

    # Agendamento automático ou fila de pré-agendamento
    agendamento_auto_alerta = None
    try:
        from app.services.agendamento_auto_service import (
            processar_agendamento_apos_aprovacao,
        )

        processar_agendamento_apos_aprovacao(db, orc, canal="publico")
    except Exception as exc:
        agendamento_auto_alerta = (
            "O orçamento foi aceito, mas houve falha na criação automática do agendamento."
        )
        db.add(
            Notificacao(
                empresa_id=orc.empresa_id,
                orcamento_id=orc.id,
                tipo="agendamento_erro",
                titulo=f"Falha no agendamento automático do orçamento {orc.numero}",
                mensagem=str(exc),
            )
        )
        logger.exception(
            "Falha ao criar agendamento automático (orcamento_id=%s)", orc.id
        )

    # Notificação in-app
    notif_msg = f"Aceite digital registrado por: {nome}."
    if orc.aceite_mensagem:
        notif_msg += f' Mensagem: "{orc.aceite_mensagem}"'
    db.add(
        Notificacao(
            empresa_id=orc.empresa_id,
            orcamento_id=orc.id,
            tipo="aprovado",
            titulo=f"✅ {orc.cliente.nome} aceitou o orçamento {orc.numero}!",
            mensagem=notif_msg,
        )
    )

    db.commit()
    db.refresh(orc)

    # Auditoria: registra no histórico com IP do cliente para rastreabilidade
    try:
        ip_cliente = (request.client.host if request.client else None) or "desconhecido"
        detalhes_otp = " (confirmado via OTP)" if orc.aceite_confirmado_otp else ""
        db.add(
            HistoricoEdicao(
                orcamento_id=orc.id,
                editado_por_id=None,
                descricao=f"Aceito pelo cliente via link público{detalhes_otp} (nome: {nome}, IP: {ip_cliente}).",
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Falha ao registrar histórico do aceite público (orcamento_id=%s)", orc.id
        )

    await handle_quote_status_changed(
        db=db,
        quote=orc,
        old_status=old_status,
        new_status=orc.status,
        source="public_link_accept",
    )

    empresa = getattr(orc, "empresa", None)
    empresa_nome = empresa.nome if empresa else "a empresa"

    # Confirmação ao cliente: WhatsApp se tiver telefone cadastrado
    telefone_cliente = getattr(orc.cliente, "telefone", None)
    if telefone_cliente:
        try:
            await enviar_mensagem_texto(
                telefone_cliente,
                f"✅ Seu aceite foi registrado!\n\n"
                f"Orçamento *{orc.numero}* confirmado por *{nome}*.\n"
                f"{empresa_nome} entrará em contato em breve. Obrigado!",
                empresa=empresa,
            )
        except Exception:
            logger.exception(
                "Falha ao enviar WhatsApp de confirmação do aceite (orcamento_id=%s)",
                orc.id,
            )

    # Confirmação ao cliente: e-mail em background (não bloqueia a resposta)
    email_cliente = getattr(orc.cliente, "email", None)
    if email_cliente and email_habilitado():
        background_tasks.add_task(
            enviar_email_confirmacao_aceite,
            destinatario=email_cliente,
            cliente_nome=orc.cliente.nome,
            aceite_nome=nome,
            numero_orcamento=orc.numero,
            empresa_nome=empresa_nome,
            valor_total=float(orc.total) if orc.total else None,
            contato_telefone=empresa.telefone_operador or empresa.telefone
            if empresa
            else None,
            contato_email_empresa=empresa.email if empresa else None,
            assinatura_email=getattr(empresa, "assinatura_email", None) or None,
        )

    if hasattr(OrcamentoPublicoOut, "model_validate"):
        out = OrcamentoPublicoOut.model_validate(orc)
    else:
        out = OrcamentoPublicoOut.from_orm(orc)
    # Informa ao frontend se há agendamento aguardando escolha do cliente
    out.has_agendamento_pendente = any(
        a.status == StatusAgendamento.AGUARDANDO_ESCOLHA
        for a in (getattr(orc, "agendamentos", []) or [])
    )
    out.agendamento_auto_alerta = agendamento_auto_alerta
    return out


@router.post("/{link_publico}/recusar", response_model=OrcamentoPublicoOut)
async def recusar_orcamento(
    link_publico: str,
    dados: RecusaRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """C: Cliente recusa o orçamento digitalmente."""
    _check_rate_limit(request, "recusar", link_publico)
    orc = _get_orcamento_publico(link_publico, db, for_update=True)

    erro = _status_bloqueia_acao(orc)
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    old_status = orc.status
    orc.status = StatusOrcamento.RECUSADO
    orc.recusa_motivo = (dados.motivo or "").strip() or None
    orc.recusa_em = datetime.now(timezone.utc)  # v7 — timeline

    # Notificação in-app
    notif_msg = "Cliente recusou o orçamento digitalmente."
    if orc.recusa_motivo:
        notif_msg += f' Motivo: "{orc.recusa_motivo}"'
    db.add(
        Notificacao(
            empresa_id=orc.empresa_id,
            orcamento_id=orc.id,
            tipo="recusado",
            titulo=f"❌ {orc.cliente.nome} recusou o orçamento {orc.numero}",
            mensagem=notif_msg,
        )
    )

    db.commit()
    db.refresh(orc)

    try:
        db.add(
            HistoricoEdicao(
                orcamento_id=orc.id,
                editado_por_id=None,
                descricao="Recusado pelo cliente via link público."
                + (f' Motivo: "{orc.recusa_motivo}"' if orc.recusa_motivo else ""),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Falha ao registrar histórico da recusa pública (orcamento_id=%s)", orc.id
        )

    # Notifica operador via WhatsApp
    if orc.empresa.telefone_operador:
        try:
            await notificar_operador_recusa(
                orc.empresa.telefone_operador,
                orc.numero,
                orc.cliente.nome,
                motivo=orc.recusa_motivo,
            )
        except Exception:
            logger.exception(
                "Falha ao notificar recusa via WhatsApp (orcamento_id=%s)", orc.id
            )

    await handle_quote_status_changed(
        db=db,
        quote=orc,
        old_status=old_status,
        new_status=orc.status,
        source="public_link_refuse",
    )

    return orc


@router.post("/{link_publico}/ajuste", status_code=200)
async def solicitar_ajuste(
    link_publico: str,
    dados: AjusteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cliente solicita ajuste no orçamento via link público."""
    _check_rate_limit(request, "ajuste", link_publico)
    orc = _get_orcamento_publico(link_publico, db)

    mensagem = dados.mensagem.strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail="Informe uma mensagem de ajuste.")

    if orc.status not in (StatusOrcamento.ENVIADO, StatusOrcamento.RASCUNHO):
        raise HTTPException(
            status_code=400,
            detail="Não é possível solicitar ajuste neste orçamento.",
        )

    cliente_nome = orc.cliente.nome if orc.cliente else "Cliente"

    # Notificação in-app
    db.add(
        Notificacao(
            empresa_id=orc.empresa_id,
            orcamento_id=orc.id,
            tipo="ajuste",
            titulo=f"✏️ {cliente_nome} solicitou ajuste no orçamento {orc.numero}",
            mensagem=f'Mensagem: "{mensagem}"',
        )
    )
    db.commit()

    # Notifica operador via WhatsApp
    if orc.empresa.telefone_operador:
        try:
            from app.core.config import settings

            base = settings.APP_URL.rstrip("/")
            url_orc = f"{base}/app/orcamento-view.html?id={orc.id}"
            texto = (
                f"✏️ Solicitação de ajuste no orçamento {orc.numero}\n\n"
                f"Cliente: {cliente_nome}\n"
                f'Mensagem: "{mensagem}"\n\n'
                f"Veja o orçamento:\n{url_orc}"
            )
            await enviar_mensagem_texto(
                orc.empresa.telefone_operador, texto, empresa=orc.empresa
            )
        except Exception:
            logger.exception(
                "Falha ao notificar solicitação de ajuste via WhatsApp (orcamento_id=%s)",
                orc.id,
            )

    return {"ok": True}


@router.post("/{link_publico}/documentos/{orcamento_documento_id}/ler", status_code=200)
def marcar_documento_lido(
    link_publico: str,
    orcamento_documento_id: int,
    db: Session = Depends(get_db),
):
    """Cliente marcou 'Li e aceito' em um documento obrigatório no portal público.
    Persiste visualizado_em (primeira vez) e aceito_em no vínculo."""
    orc = _get_orcamento_publico(link_publico, db)
    vinc = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.id == orcamento_documento_id,
            OrcamentoDocumento.orcamento_id == orc.id,
            OrcamentoDocumento.exibir_no_portal == True,
        )
        .first()
    )
    if not vinc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    now = datetime.now(timezone.utc)
    if not vinc.visualizado_em:
        vinc.visualizado_em = now
    vinc.aceito_em = now
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════════
# AGENDAMENTO PÚBLICO — cliente escolhe data/hora
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/{link_publico}/agendamento")
def ver_agendamento_publico(
    link_publico: str,
    db: Session = Depends(get_db),
):
    """Retorna agendamento vinculado ao orçamento público + opções de data."""
    from app.services.agendamento_service import (
        buscar_agendamento_publico_por_orcamento,
    )

    ag = buscar_agendamento_publico_por_orcamento(db, link_publico)
    if not ag:
        raise HTTPException(
            status_code=404, detail="Nenhum agendamento encontrado para este orçamento."
        )

    orc = db.query(Orcamento).filter(Orcamento.link_publico == link_publico).first()
    if not orc or orc.status != StatusOrcamento.APROVADO:
        raise HTTPException(
            status_code=400, detail="Orçamento precisa estar aprovado para agendar."
        )

    return ag


class EscolherOpcaoBody(BaseModel):
    opcao_id: int


@router.post("/{link_publico}/agendamento/escolher")
async def escolher_opcao_agendamento(
    link_publico: str,
    dados: EscolherOpcaoBody,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cliente escolhe uma opção de data/hora para o agendamento."""
    _check_rate_limit(request, "escolher-opcao", link_publico)

    from app.services.agendamento_service import (
        buscar_agendamento_publico_por_orcamento,
        escolher_opcao,
    )

    ag_publico = buscar_agendamento_publico_por_orcamento(db, link_publico)
    if not ag_publico:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")

    if ag_publico.get("status") != "aguardando_escolha":
        raise HTTPException(
            status_code=400, detail="Agendamento não está aguardando escolha."
        )

    ag, erro = escolher_opcao(
        db=db,
        agendamento_id=ag_publico["id"],
        opcao_id=dados.opcao_id,
    )
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    # Notificar operador via WhatsApp
    try:
        from app.services.whatsapp_service import send_whatsapp_message
        from app.core.config import settings

        orc = db.query(Orcamento).filter(Orcamento.link_publico == link_publico).first()
        if orc and orc.empresa.telefone_operador:
            base = settings.APP_URL.rstrip("/")
            data_fmt = (
                ag.data_agendada.strftime("%d/%m/%Y às %H:%M")
                if ag.data_agendada
                else "—"
            )
            texto = (
                f"📅 Agendamento escolhido!\n\n"
                f"Cliente: {orc.cliente.nome}\n"
                f"Orçamento: {orc.numero}\n"
                f"Data: {data_fmt}\n"
                f"Agendamento: {ag.numero}\n\n"
                f"Veja no painel: {base}/app/agendamentos.html"
            )
            await send_whatsapp_message(
                orc.empresa.telefone_operador,
                texto,
                context={"type": "agendamento_escolhido", "agendamento_id": ag.id},
                empresa=orc.empresa,
            )
    except Exception:
        logger.exception("Falha ao notificar operador sobre escolha de agendamento")

    # Notificar cliente via WhatsApp
    try:
        from app.services.whatsapp_service import send_whatsapp_message

        if orc and orc.cliente.telefone and ag.data_agendada:
            data_fmt = ag.data_agendada.strftime("%d/%m/%Y às %H:%M")
            config = (
                db.query(ConfigAgendamento)
                .filter(ConfigAgendamento.empresa_id == ag.empresa_id)
                .first()
            )
            msg = (
                config.mensagem_confirmacao
                if config and config.mensagem_confirmacao
                else (
                    f"✅ Agendamento confirmado!\n\n"
                    f"📅 {data_fmt}\n"
                    f"📋 {ag.numero}\n"
                    f"Empresa: {orc.empresa.nome}"
                )
            )
            msg = msg.replace("{cliente}", orc.cliente.nome or "")
            msg = msg.replace("{data}", data_fmt)
            msg = msg.replace("{empresa}", orc.empresa.nome or "")
            msg = msg.replace("{numero}", ag.numero or "")
            await send_whatsapp_message(
                orc.cliente.telefone,
                msg,
                context={"type": "agendamento_confirmado_cliente"},
                empresa=orc.empresa,
            )
    except Exception:
        logger.exception("Falha ao enviar confirmação de agendamento para cliente")

    return {"mensagem": "Opção escolhida com sucesso!", "agendamento_id": ag.id}
