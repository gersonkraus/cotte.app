"""
Factory de provider WhatsApp.

Todo o código de negócio (routers, background tasks, etc.) importa deste módulo.
A escolha entre Z-API e Evolution API é feita pela variável de ambiente
WHATSAPP_PROVIDER ("evolution" ou "zapi"). Basta trocar no .env e reiniciar.

Para envios multi-tenant, use get_provider_para_empresa(empresa) que retorna
automaticamente a instância própria da empresa quando disponível, ou o provider
global da plataforma como fallback.
"""
import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.config import settings
from app.schemas.notifications import SendResult
from app.utils.phone import normalize_phone_number
from app.services.whatsapp_base import WhatsAppProvider

if TYPE_CHECKING:
    from app.models.models import Empresa


@lru_cache(maxsize=1)
def get_provider() -> WhatsAppProvider:
    """
    Retorna a instância singleton do provider global da plataforma.
    O cache garante que o objeto seja criado apenas uma vez por processo.
    """
    provider = settings.WHATSAPP_PROVIDER.lower().strip()

    if provider == "evolution":
        from app.services.whatsapp_evolution import EvolutionProvider
        return EvolutionProvider()

    if provider == "zapi":
        from app.services.whatsapp_zapi import ZAPIProvider
        return ZAPIProvider()

    raise ValueError(
        f"WHATSAPP_PROVIDER inválido: '{provider}'. "
        "Use 'zapi' ou 'evolution'."
    )


def get_provider_para_empresa(empresa: "Empresa | None") -> WhatsAppProvider:
    """
    Retorna o provider correto para a empresa.
    - Se a empresa tiver WhatsApp próprio habilitado, conectado e com instância,
      usa a instância Evolution da empresa.
    - Caso contrário, usa o provider global da plataforma (fallback transparente).
    """
    if empresa is not None:
        from app.services.plano_service import whatsapp_proprio_habilitado
        if (
            whatsapp_proprio_habilitado(empresa)
            and getattr(empresa, "whatsapp_proprio_ativo", False)
            and getattr(empresa, "evolution_instance", None)
            and getattr(empresa, "whatsapp_conectado", False)
        ):
            from app.services.whatsapp_evolution import EvolutionProvider
            return EvolutionProvider(instance=empresa.evolution_instance)
    return get_provider()


def _provider_name() -> str:
    return settings.WHATSAPP_PROVIDER.lower().strip()


def _whatsapp_config_ok() -> bool:
    provider = _provider_name()
    if provider == "evolution":
        return bool(settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY)
    if provider == "zapi":
        return bool(settings.ZAPI_BASE_URL and settings.ZAPI_INSTANCE_ID and settings.ZAPI_TOKEN)
    return False


# ── Atalhos de compatibilidade ─────────────────────────────────────────────
# Todos aceitam `empresa` opcional — quando fornecido, usam a instância própria.

async def get_status() -> dict:
    return await get_provider().get_status()

async def get_qrcode() -> dict:
    return await get_provider().get_qrcode()

async def desconectar() -> bool:
    return await get_provider().desconectar()

async def enviar_mensagem_texto(
    telefone: str, mensagem: str, empresa: "Empresa | None" = None
) -> bool:
    return await get_provider_para_empresa(empresa).enviar_mensagem_texto(telefone, mensagem)


async def send_whatsapp_message(
    to_phone: str,
    message: str,
    context: dict | None = None,
    empresa: "Empresa | None" = None,
) -> SendResult:
    """
    Envio defensivo de WhatsApp com retorno estruturado.
    Não lança exceções para o caller.
    """
    provider = _provider_name()
    if not _whatsapp_config_ok():
        return SendResult(
            success=False,
            provider=provider,
            error="whatsapp config missing",
            context=context,
        )

    normalized_phone = normalize_phone_number(to_phone)
    if not normalized_phone:
        return SendResult(
            success=False,
            provider=provider,
            error="invalid phone number",
            context=context,
        )

    try:
        ok = await get_provider_para_empresa(empresa).enviar_mensagem_texto(
            normalized_phone,
            message,
        )
        if ok:
            return SendResult(
                success=True,
                provider=provider,
                normalized_phone=normalized_phone,
                context=context,
            )
        return SendResult(
            success=False,
            provider=provider,
            normalized_phone=normalized_phone,
            error="provider returned unsuccessful status",
            context=context,
        )
    except Exception as exc:
        logging.exception("Falha no envio de WhatsApp (%s): %s", provider, exc)
        return SendResult(
            success=False,
            provider=provider,
            normalized_phone=normalized_phone,
            error=str(exc),
            context=context,
        )

async def enviar_pdf(
    telefone: str, pdf_bytes: bytes, numero: str, caption: str = "",
    empresa: "Empresa | None" = None,
) -> bool:
    return await get_provider_para_empresa(empresa).enviar_pdf(telefone, pdf_bytes, numero, caption)

async def enviar_orcamento_completo(
    telefone: str, orcamento: dict, pdf_bytes: bytes = b"",
    empresa: "Empresa | None" = None,
) -> bool:
    return await get_provider_para_empresa(empresa).enviar_orcamento_completo(
        telefone, orcamento, pdf_bytes
    )

async def notificar_operador_visualizacao(
    telefone_operador: str, numero: str, cliente_nome: str,
    empresa: "Empresa | None" = None,
) -> bool:
    return await get_provider_para_empresa(empresa).notificar_operador_visualizacao(
        telefone_operador, numero, cliente_nome
    )

async def notificar_operador_aceite(
    telefone_operador: str,
    numero: str,
    cliente_nome: str,
    aceite_nome: str,
    total: float,
    mensagem: str | None = None,
    empresa: "Empresa | None" = None,
) -> bool:
    return await get_provider_para_empresa(empresa).notificar_operador_aceite(
        telefone_operador, numero, cliente_nome, aceite_nome, total, mensagem
    )

async def notificar_operador_recusa(
    telefone_operador: str,
    numero: str,
    cliente_nome: str,
    motivo: str | None = None,
    empresa: "Empresa | None" = None,
) -> bool:
    return await get_provider_para_empresa(empresa).notificar_operador_recusa(
        telefone_operador, numero, cliente_nome, motivo
    )

async def enviar_lembrete_cliente(
    telefone_cliente: str,
    cliente_nome: str,
    numero_orc: str,
    link_publico: str,
    empresa_nome: str,
    base_url: str = "",
    lembrete_texto: str | None = None,
    empresa: "Empresa | None" = None,
) -> bool:
    return await get_provider_para_empresa(empresa).enviar_lembrete_cliente(
        telefone_cliente, cliente_nome, numero_orc, link_publico, empresa_nome, base_url, lembrete_texto
    )
