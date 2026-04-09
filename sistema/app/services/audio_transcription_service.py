"""
[INOVAÇÃO] Transcrição de áudio para o canal WhatsApp do operador.

Fluxo:
1. Baixa o áudio da Evolution API (base64)
2. Envia para a API Whisper da OpenAI (usando AI_API_KEY existente)
3. Retorna o texto transcrito para o pipeline normal do assistente

Por que isso importa:
- Pequenos empresários "em trânsito" preferem mandar áudio
- Um operador dirigindo pode criar orçamentos por voz
- Zero nova infraestrutura — reutiliza o AI_API_KEY do sistema
"""
import base64
import io
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tamanho máximo de áudio suportado (25MB limite da Whisper API)
MAX_AUDIO_BYTES = 24 * 1024 * 1024


async def transcrever_audio_wpp(
    message_data: dict,
    instancia: str | None = None,
) -> str | None:
    """
    Baixa e transcreve um áudio do WhatsApp.

    Args:
        message_data: dict com a mensagem original do webhook Evolution
                      (precisa ter "key" e "message" para o download)
        instancia: nome da instância Evolution (usa padrão se None)

    Returns:
        Texto transcrito ou None se não foi possível transcrever.
    """
    if not settings.AI_API_KEY:
        logger.warning("[AudioTranscrição] AI_API_KEY não configurado — transcrição de voz desabilitada")
        return None

    # 1. Baixar áudio da Evolution API
    audio_bytes = await _baixar_audio_evolution(message_data, instancia)
    if not audio_bytes:
        return None

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        logger.warning("[AudioTranscrição] Áudio muito grande: %d bytes", len(audio_bytes))
        return None

    # 2. Transcrever via Whisper
    return await _transcrever_whisper(audio_bytes)


async def _baixar_audio_evolution(
    message_data: dict,
    instancia: str | None = None,
) -> bytes | None:
    """Baixa o áudio da Evolution API e retorna os bytes."""
    inst = instancia or settings.EVOLUTION_INSTANCE
    url = f"{settings.EVOLUTION_API_URL.rstrip('/')}/chat/getBase64FromMediaMessage/{inst}"

    payload = {"message": message_data}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                url,
                json=payload,
                headers={
                    "apikey": settings.EVOLUTION_API_KEY,
                    "Content-Type": "application/json",
                },
            )
            if r.status_code not in (200, 201):
                logger.warning("[AudioTranscrição] Falha ao baixar áudio: HTTP %s", r.status_code)
                return None

            data = r.json()
            b64 = data.get("base64") or data.get("data")
            if not b64:
                logger.warning("[AudioTranscrição] Resposta sem base64: %s", list(data.keys()))
                return None

            return base64.b64decode(b64)
    except Exception as e:
        logger.warning("[AudioTranscrição] Erro ao baixar áudio: %s", e)
        return None


async def _transcrever_whisper(audio_bytes: bytes) -> str | None:
    """Envia áudio para a API Whisper (OpenAI) e retorna a transcrição."""
    url = "https://api.openai.com/v1/audio/transcriptions"

    # Whisper aceita ogg, mp3, wav, mp4, webm etc. — Evolution envia ogg/opus
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.ogg"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                files={"file": ("audio.ogg", audio_file, "audio/ogg")},
                data={"model": "whisper-1", "language": "pt"},
            )
            if r.status_code != 200:
                logger.warning("[AudioTranscrição] Whisper retornou HTTP %s: %s", r.status_code, r.text[:200])
                return None

            resultado = r.json()
            texto = (resultado.get("text") or "").strip()
            if texto:
                logger.info("[AudioTranscrição] Transcrição OK: %d chars", len(texto))
            return texto or None
    except Exception as e:
        logger.error("[AudioTranscrição] Erro ao chamar Whisper: %s", e)
        return None


def mensagem_voz_nao_configurada() -> str:
    """Mensagem amigável quando a transcrição não está disponível."""
    return (
        "🎤 Recebi seu áudio!\n\n"
        "Para ativar comandos por voz, configure o *AI_API_KEY* nas variáveis de ambiente do sistema.\n\n"
        "Por enquanto, envie seu pedido por texto. Exemplo:\n"
        "_orçamento de pintura para João, R$ 800_"
    )
