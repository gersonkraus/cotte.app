import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import HistoricoEdicao, Notificacao, Orcamento, StatusOrcamento, Usuario
from app.schemas.notifications import SendResult
from app.services.whatsapp_service import send_whatsapp_message
from app.utils.phone import normalize_phone_number

logger = logging.getLogger(__name__)


def _context(quote: Orcamento, event_type: str, user_id: int | None = None) -> dict:
    return {
        "quote_id": quote.id,
        "company_id": quote.empresa_id,
        "user_id": user_id,
        "event_type": event_type,
    }


def _normalize_approval_channel(source: str | None) -> str:
    raw = str(source or "").strip().lower()
    if not raw:
        return "manual"
    if "whatsapp" in raw or raw == "bot":
        return "whatsapp"
    if "public" in raw:
        return "publico"
    if "assistente" in raw or raw == "ia":
        return "ia"
    if "bot_command" in raw or "manual" in raw:
        return "manual"
    return raw[:20] or "manual"


def ensure_quote_approval_metadata(quote: Orcamento, source: str = "unknown") -> bool:
    """
    Garante metadados mínimos de aprovação em qualquer fluxo.

    Retorna True se alterou algo.
    """
    changed = False
    if quote.aprovado_em is None:
        quote.aprovado_em = quote.aceite_em or datetime.now(timezone.utc)
        changed = True
    if not (quote.aprovado_canal or "").strip():
        quote.aprovado_canal = _normalize_approval_channel(source)
        changed = True
    return changed


async def handle_quote_status_changed(
    db: Session,
    quote: Orcamento,
    old_status: StatusOrcamento | None,
    new_status: StatusOrcamento | None,
    source: str = "unknown",
) -> None:
    if old_status == new_status:
        return

    if new_status == StatusOrcamento.APROVADO:
        await notify_quote_approved(db, quote, source=source)
    elif new_status == StatusOrcamento.EXPIRADO:
        notify_quote_expired(db, quote, source=source)

    # Reverter efeitos da aprovação se estiver saindo de APROVADO
    if old_status == StatusOrcamento.APROVADO and new_status != StatusOrcamento.APROVADO:
        await handle_quote_unapproved(db, quote)


async def handle_quote_unapproved(db: Session, quote: Orcamento) -> None:
    """Reverte efeitos colaterais da aprovação (ex: deletar contas pendentes)."""
    from app.models.models import ContaFinanceira, StatusConta
    logger.info("quote unapproved | quote_id=%s", quote.id)

    # 1. Deletar contas a receber geradas na aprovação que ainda estão PENDENTES
    # Se já tiver valor pago, mantemos por segurança (ou o operador deve estornar antes)
    contas_pendentes = db.query(ContaFinanceira).filter(
        ContaFinanceira.orcamento_id == quote.id,
        ContaFinanceira.status == StatusConta.PENDENTE,
        ContaFinanceira.valor_pago == 0
    ).all()

    for conta in contas_pendentes:
        db.delete(conta)

    # 2. Resetar flags de aprovação no orçamento
    quote.contas_receber_geradas_em = None
    quote.aceite_em = None
    quote.aceite_ip = None
    quote.aceite_usuario_agente = None
    quote.approved_notification_sent_at = None
    quote.aprovado_canal = None
    quote.aprovado_em = None
    quote.agendamento_opcoes_pendente_liberacao = False
    quote.agendamento_opcoes_liberado_em = None
    quote.agendamento_opcoes_liberado_por_id = None
    quote.observacao_liberacao_agendamento = None

    db.flush()


async def notify_quote_approved(db: Session, quote: Orcamento, source: str = "unknown") -> None:
    logger.info(
        "quote approved notification started | source=%s | ctx=%s",
        source,
        _context(quote, "quote_approved_internal_whatsapp"),
    )

    # Garante criação de contas a receber em QUALQUER caminho de aprovação.
    # Idempotente via orc.contas_receber_geradas_em — seguro chamar múltiplas vezes.
    # A exceção PROPAGA — se falhar, deve aparecer no log como erro, não ser silenciada.
    from app.services import financeiro_service as _fin_svc
    from sqlalchemy.ext.asyncio import AsyncSession

    if isinstance(db, AsyncSession):
        async with db.begin_nested():
            _fin_svc.criar_contas_receber_aprovacao(quote, quote.empresa_id, db)
    else:
        with db.begin_nested():
            _fin_svc.criar_contas_receber_aprovacao(quote, quote.empresa_id, db)

    if has_quote_approval_notification_been_sent(quote):
        logger.info(
            "quote approved notification skipped (already sent) | ctx=%s",
            _context(quote, "quote_approved_internal_whatsapp"),
        )
        return

    user = resolve_quote_responsible_user(db, quote)
    if not user:
        logger.warning(
            "responsible user not found | ctx=%s",
            _context(quote, "quote_approved_internal_whatsapp"),
        )
        return

    logger.info(
        "responsible user resolved | ctx=%s",
        _context(quote, "quote_approved_internal_whatsapp", user.id),
    )

    to_phone = resolve_responsible_phone(quote, user)
    if not to_phone:
        logger.warning(
            "user has no phone number | ctx=%s",
            _context(quote, "quote_approved_internal_whatsapp", user.id),
        )
        return

    message = _build_quote_approved_message(quote)
    result = await send_internal_quote_approved_whatsapp(quote, user, to_phone, message)

    if result.success:
        mark_quote_approval_notification_sent(quote)
        _registrar_historico_notificacao(db, quote, user)
        db.commit()
        logger.info(
            "whatsapp notification sent successfully | ctx=%s",
            _context(quote, "quote_approved_internal_whatsapp", user.id),
        )
        return

    logger.error(
        "whatsapp notification failed | error=%s | ctx=%s",
        result.error,
        _context(quote, "quote_approved_internal_whatsapp", user.id),
    )


def notify_quote_expired(db: Session, quote: Orcamento, source: str = "unknown") -> None:
    logger.info(
        "quote expired | source=%s | ctx=%s",
        source,
        _context(quote, "quote_expired"),
    )
    try:
        cliente_nome = quote.cliente.nome if getattr(quote, "cliente", None) else "—"
        db.add(Notificacao(
            empresa_id=quote.empresa_id,
            orcamento_id=quote.id,
            tipo="expirado",
            titulo=f"⏰ Orçamento {quote.numero or quote.id} expirou",
            mensagem=f"O orçamento de {cliente_nome} expirou sem resposta.",
        ))
        db.commit()
    except SQLAlchemyError:
        logger.exception("Erro ao criar notificação de expiração | ctx=%s", _context(quote, "quote_expired"))


async def send_internal_quote_approved_whatsapp(
    quote: Orcamento,
    user: Usuario,
    to_phone: str,
    message: str,
) -> SendResult:
    if not _is_whatsapp_config_available():
        logger.warning(
            "whatsapp config missing | ctx=%s",
            _context(quote, "quote_approved_internal_whatsapp", user.id),
        )
        return SendResult(success=False, error="whatsapp config missing")

    return await send_whatsapp_message(
        to_phone=to_phone,
        message=message,
        context=_context(quote, "quote_approved_internal_whatsapp", user.id),
        empresa=quote.empresa,
    )


def resolve_quote_responsible_user(db: Session, quote: Orcamento) -> Usuario | None:
    # 1) Dono do orçamento (se existir no modelo atual/futuro)
    owner_id = getattr(quote, "owner_user_id", None) or getattr(quote, "usuario_dono_id", None)
    owner_rel = getattr(quote, "owner_user", None) or getattr(quote, "usuario_dono", None)
    if owner_rel and _user_ativo(owner_rel):
        return owner_rel
    if owner_id:
        owner = _buscar_usuario_ativo(db, quote.empresa_id, owner_id)
        if owner:
            return owner

    # 2) Atendente responsável vinculado
    attendant_id = getattr(quote, "responsavel_id", None) or getattr(quote, "atendente_id", None)
    attendant_rel = getattr(quote, "responsavel", None) or getattr(quote, "atendente", None)
    if attendant_rel and _user_ativo(attendant_rel):
        return attendant_rel
    if attendant_id:
        attendant = _buscar_usuario_ativo(db, quote.empresa_id, attendant_id)
        if attendant:
            return attendant

    # 3) Usuário criador do orçamento
    if getattr(quote, "criado_por", None) and _user_ativo(quote.criado_por):
        return quote.criado_por
    created_by_id = getattr(quote, "criado_por_id", None)
    if created_by_id:
        created_by = _buscar_usuario_ativo(db, quote.empresa_id, created_by_id)
        if created_by:
            return created_by

    # 4) Usuário principal da conta (gestor) ou primeiro ativo da empresa
    gestor = (
        db.query(Usuario)
        .filter(
            Usuario.empresa_id == quote.empresa_id,
            Usuario.ativo.is_(True),
            Usuario.is_gestor.is_(True),
        )
        .order_by(Usuario.id.asc())
        .first()
    )
    if gestor:
        return gestor

    return (
        db.query(Usuario)
        .filter(Usuario.empresa_id == quote.empresa_id, Usuario.ativo.is_(True))
        .order_by(Usuario.id.asc())
        .first()
    )


def resolve_responsible_phone(quote: Orcamento, user: Usuario) -> str | None:
    empresa = getattr(quote, "empresa", None)
    candidates = [
        getattr(empresa, "telefone_operador", None) if empresa else None,
        getattr(empresa, "telefone", None) if empresa else None,
    ]
    for value in candidates:
        normalized = normalize_phone_number(value)
        if normalized:
            return normalized
    return None


def has_quote_approval_notification_been_sent(quote: Orcamento) -> bool:
    return getattr(quote, "approved_notification_sent_at", None) is not None


def mark_quote_approval_notification_sent(quote: Orcamento) -> None:
    quote.approved_notification_sent_at = datetime.now(timezone.utc)


def _build_quote_approved_message(quote: Orcamento) -> str:
    numero = (quote.numero or "").strip()
    codigo = f"#{numero}" if numero else f"ID {quote.id}"
    cliente_nome = quote.cliente.nome if getattr(quote, "cliente", None) and quote.cliente.nome else "—"
    valor_total = _format_brl(float(quote.total or 0.0))

    aprovado_em = quote.aceite_em or datetime.now(timezone.utc)
    data_aprovacao = _format_datetime_br(aprovado_em)

    base = settings.APP_URL.rstrip("/")
    url_orcamento = f"{base}/app/orcamento-view.html?id={quote.id}" if quote.id else f"{base}/app/orcamentos.html"
    url_agendamento = f"{base}/app/agendamentos.html?orcamento_id={quote.id}" if quote.id else None

    linhas = [
        "✅ Orçamento aprovado!",
        "",
        f"Cliente: {cliente_nome}",
        f"Orçamento: {codigo}",
        f"Valor: {valor_total}",
        f"Aprovado em: {data_aprovacao}",
        "",
        "Veja os detalhes no sistema:",
        url_orcamento,
    ]

    # Sugestão de agendamento
    if url_agendamento and not getattr(quote, "agendamento_id", None):
        linhas += [
            "",
            "📅 Agende o serviço com o cliente:",
            url_agendamento,
        ]

    return "\n".join([l for l in linhas if l is not None])


def _registrar_historico_notificacao(db: Session, quote: Orcamento, user: Usuario) -> None:
    if not quote.id or not user.id:
        return
    db.add(
        HistoricoEdicao(
            orcamento_id=quote.id,
            editado_por_id=user.id,
            descricao="Notificação interna de aprovação enviada por WhatsApp para o atendente responsável.",
        )
    )


def _buscar_usuario_ativo(db: Session, empresa_id: int, user_id: int) -> Usuario | None:
    return (
        db.query(Usuario)
        .filter(
            Usuario.id == user_id,
            Usuario.empresa_id == empresa_id,
            Usuario.ativo.is_(True),
        )
        .first()
    )


def _user_ativo(user: Usuario | None) -> bool:
    return bool(user and getattr(user, "ativo", True))


def _is_whatsapp_config_available() -> bool:
    provider = (settings.WHATSAPP_PROVIDER or "").lower().strip()
    if provider == "evolution":
        return bool(settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY)
    if provider == "zapi":
        return bool(settings.ZAPI_BASE_URL and settings.ZAPI_INSTANCE_ID and settings.ZAPI_TOKEN)
    return False


def _format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_datetime_br(value: datetime) -> str:
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
