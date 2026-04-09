"""
Interface abstrata para providers de WhatsApp.

Qualquer provider (Z-API, Evolution API, etc.) deve herdar de WhatsAppProvider
e implementar todos os métodos abstratos. O código de negócio nunca importa
um provider diretamente — usa get_provider() para obter a instância correta.
"""
import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)

# Configuração de retry para falhas transitórias de rede
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 1  # segundos


async def _retry_async(func, *args, **kwargs):
    """
    Executa uma coroutine com retry em caso de falhas transitárias de rede.

    Tenta até RETRY_MAX_ATTEMPTS vezes com backoff exponencial (1s, 2s, 4s…).
    Falhas transitórias: httpx.NetworkError, httpx.TimeoutException.
    Retorna False imediatamente se a última tentativa falhar.
    """
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            return await func(*args, **kwargs)
        except (httpx.NetworkError, httpx.TimeoutException) as exc:
            if attempt < RETRY_MAX_ATTEMPTS:
                wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "WhatsApp retry %d/%d em %.1fs — %s: %s",
                    attempt, RETRY_MAX_ATTEMPTS, wait,
                    type(exc).__name__, exc,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "WhatsApp retry esgotado (%d tentativas) — %s: %s",
                    RETRY_MAX_ATTEMPTS, type(exc).__name__, exc,
                )
    return False


class WhatsAppProvider(ABC):
    """Contrato que todo provider de WhatsApp deve cumprir."""

    # ── Conexão ────────────────────────────────────────────────────────────

    @abstractmethod
    async def get_status(self) -> dict:
        """Retorna o status de conexão da instância (deve incluir chave 'connected': bool)."""
        ...

    @abstractmethod
    async def get_qrcode(self) -> dict:
        """Retorna o QR Code para conectar o WhatsApp (chave 'qrcode' em base64)."""
        ...

    @abstractmethod
    async def desconectar(self) -> bool:
        """Desconecta a instância. Retorna True em caso de sucesso."""
        ...

    # ── Envio de mensagens ─────────────────────────────────────────────────

    @abstractmethod
    async def enviar_mensagem_texto(self, telefone: str, mensagem: str) -> bool:
        """Envia texto simples. Retorna True em caso de sucesso."""
        ...

    @abstractmethod
    async def enviar_pdf(
        self, telefone: str, pdf_bytes: bytes, numero: str, caption: str = ""
    ) -> bool:
        """Envia um arquivo PDF como anexo. Retorna True em caso de sucesso."""
        ...

    @abstractmethod
    async def enviar_orcamento_completo(
        self, telefone: str, orcamento: dict, pdf_bytes: bytes = b""
    ) -> bool:
        """
        Envia o orçamento ao cliente (link clicável + PDF).
        O dict 'orcamento' contém: numero, total, validade_dias, cliente_nome,
        empresa_nome, vendedor_nome, link_publico, itens.
        """
        ...

    # ── Notificações ao operador ───────────────────────────────────────────

    @abstractmethod
    async def notificar_operador_visualizacao(
        self, telefone_operador: str, numero: str, cliente_nome: str
    ) -> bool:
        """Notifica o operador quando o cliente abre o orçamento pela primeira vez."""
        ...

    @abstractmethod
    async def notificar_operador_aceite(
        self,
        telefone_operador: str,
        numero: str,
        cliente_nome: str,
        aceite_nome: str,
        total: float,
        mensagem: str | None = None,
    ) -> bool:
        """Notifica o operador quando o cliente aceita o orçamento."""
        ...

    @abstractmethod
    async def notificar_operador_recusa(
        self,
        telefone_operador: str,
        numero: str,
        cliente_nome: str,
        motivo: str | None = None,
    ) -> bool:
        """Notifica o operador quando o cliente recusa o orçamento."""
        ...

    @abstractmethod
    async def enviar_lembrete_cliente(
        self,
        telefone_cliente: str,
        cliente_nome: str,
        numero_orc: str,
        link_publico: str,
        empresa_nome: str,
        base_url: str = "",
        lembrete_texto: str | None = None,
    ) -> bool:
        """Envia lembrete automático ao cliente sobre orçamento pendente."""
        ...

    # ── Helpers utilitários ────────────────────────────────────────────────

    @staticmethod
    def normalizar_telefone(telefone: str) -> str:
        """Garante DDI 55 nos dígitos: 5548999887766"""
        digits = "".join(filter(str.isdigit, telefone))
        if not digits.startswith("55"):
            digits = "55" + digits
        return digits

    @staticmethod
    def formatar_brl(valor: float) -> str:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _calcular_data_validade(dias: int) -> str:
        """Calcula a data de validade a partir de hoje + dias, retorna no formato DD/MM/AAAA."""
        from datetime import datetime, timedelta
        data_validade = datetime.now() + timedelta(days=dias)
        return data_validade.strftime("%d/%m/%Y")
