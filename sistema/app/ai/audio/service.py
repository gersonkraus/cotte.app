"""Audio Service for Speech-to-Text (STT) and Text-to-Speech (TTS)."""
from __future__ import annotations

import base64
import logging
from typing import Optional
import httpx

from app.core.config import settings
from app.ai.service import ia_service

logger = logging.getLogger(__name__)

class AudioService:
    """Service for handling multimodal audio interactions."""
    
    @staticmethod
    async def transcribe_blob(audio_blob: bytes, format: str = "webm") -> Optional[str]:
        """Transcribes an audio blob from the web frontend."""
        if not audio_blob:
            return None
            
        b64_audio = base64.b64encode(audio_blob).decode("utf-8")
        
        transcription_prompt = (
            "Você é um transcritor de áudio profissional. "
            "Transcreva o áudio em anexo exatamente como falado, sem adicionar comentários ou saudações. "
            "Se o áudio estiver vazio ou incompreensível, retorne apenas uma string vazia."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": transcription_prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": b64_audio,
                            "format": format
                        }
                    }
                ]
            }
        ]

        try:
            # Use Gemini Flash or similar multimodal model
            response = await ia_service.chat(
                messages=messages, 
                max_tokens=1000,
                temperature=0.0
            )
            
            if not response or "choices" not in response:
                return None
                
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Error in STT: {e}")
            return None

    @staticmethod
    async def text_to_speech(text: str, provider: str = "openai") -> Optional[str]:
        """Converts text to speech and returns a base64 encoded audio or a URL."""
        if not text:
            return None
            
        # Implementation for OpenAI TTS or ElevenLabs
        # For now, let's use OpenAI TTS as a default if API key is present
        api_key = settings.AI_API_KEY
        if not api_key:
            return None
            
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "tts-1",
                        "input": text,
                        "voice": "alloy",
                    }
                )
                if response.status_code == 200:
                    audio_content = response.content
                    return base64.b64encode(audio_content).decode("utf-8")
                else:
                    logger.error(f"TTS Provider error: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error in TTS: {e}")
            return None
