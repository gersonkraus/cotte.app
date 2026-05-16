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
    logger.info("[AudioTranscrição] Iniciando processo de transcrição. AI_API_KEY presente: %s", bool(settings.AI_API_KEY))
    
    if not settings.AI_API_KEY:
        logger.warning("[AudioTranscrição] AI_API_KEY não configurado — transcrição de voz desabilitada")
        return None

    # 1. Baixar áudio da Evolution API
    audio_bytes = await _baixar_audio_evolution(message_data, instancia)
    if not audio_bytes:
        logger.warning("[AudioTranscrição] Falha ao baixar bytes do áudio")
        return None

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        logger.warning("[AudioTranscrição] Áudio muito grande: %d bytes", len(audio_bytes))
        return None

    logger.info("[AudioTranscrição] Áudio baixado com sucesso (%d bytes). Enviando para transcrição...", len(audio_bytes))

    # 2. Transcrever via LLM Multimodal (mais robusto que Whisper via Proxy)
    return await _transcrever_via_llm(audio_bytes)


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


async def _transcrever_via_llm(audio_bytes: bytes) -> str | None:
    """Transcreve áudio usando o motor multimodal do Gemini (via LiteLLM/OpenRouter)."""
    import base64
    from app.services.ia_service import ia_service
    
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

    # Prompt instruindo a IA a ser apenas um transcritor
    transcription_prompt = (
        "Você é um transcritor de áudio profissional. "
        "Transcreva o áudio em anexo exatamente como falado, sem adicionar comentários ou saudações. "
        "Se o áudio estiver vazio ou incompreensível, retorne apenas uma string vazia."
    )

    # Formato multimodal compatível com LiteLLM (que traduz para Gemini inline_data)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": transcription_prompt},
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": b64_audio,
                        "format": "ogg"
                    }
                }
            ]
        }
    ]

    try:
        logger.info("[AudioTranscrição] Enviando para Transcritor Gemini...")
        
        # Usamos o modelo padrão (Gemini Flash) que é excelente para isso
        response = await ia_service.chat(
            messages=messages, 
            max_tokens=500,
            temperature=0.0
        )
        
        if not response or "choices" not in response:
            return None
            
        texto = response["choices"][0]["message"]["content"].strip()
        
        if texto:
            logger.info("[AudioTranscrição] Transcrição OK: %d chars", len(texto))
            return texto
            
        return None

    except Exception as e:
        logger.error("[AudioTranscrição] Erro ao transcrever via LLM: %s", e)
        return None


def mensagem_voz_nao_configurada() -> str:
    """Mensagem amigável quando a transcrição não está disponível."""
    return (
        "🎤 Recebi seu áudio!\n\n"
        "Para ativar comandos por voz, configure o *AI_API_KEY* nas variáveis de ambiente do sistema.\n\n"
        "Por enquanto, envie seu pedido por texto. Exemplo:\n"
        "_orçamento de pintura para João, R$ 800_"
    )
