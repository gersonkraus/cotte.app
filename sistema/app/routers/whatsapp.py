from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Empresa
from app.schemas.schemas import WebhookZAPI, WebhookEvolution, IAInterpretacaoRequest
from app.services.whatsapp_service import (
    get_status,
    get_qrcode,
    desconectar,
)
from app.services.whatsapp_bot_service import processar_mensagem
from app.utils.whatsapp_sanitizer import sanitizar_telefone, sanitizar_mensagem
from app.services.rate_limit_service import (
    webhook_rate_limiter,
    ia_interpretar_rate_limiter,
)
from app.services.ia_service import interpretar_mensagem
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


def _extrair_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "") or request.headers.get("authorization", "")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def _validar_autenticacao_webhook(request: Request, provider: str) -> None:
    if provider == "evolution":
        secret = (getattr(settings, "EVOLUTION_API_KEY", "") or "").strip()
        if not secret:
            raise HTTPException(status_code=503, detail="Webhook Evolution nao configurado")
        token = (
            request.headers.get("apikey", "")
            or request.headers.get("Apikey", "")
            or request.query_params.get("apikey", "")
            or _extrair_bearer_token(request)
        )
        if not token or not secrets.compare_digest(token.strip(), secret):
            raise HTTPException(status_code=401, detail="Webhook nao autorizado")
        return

    secret = (getattr(settings, "ZAPI_CLIENT_TOKEN", "") or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook Z-API nao configurado")
    token = (
        request.headers.get("Client-Token", "")
        or request.headers.get("client-token", "")
        or request.headers.get("X-Client-Token", "")
        or _extrair_bearer_token(request)
    )
    if not token or not secrets.compare_digest(token.strip(), secret):
        raise HTTPException(status_code=401, detail="Webhook nao autorizado")


@router.get("/status")
async def status_conexao():
    return await get_status()


@router.get("/qrcode")
async def qrcode_conexao():
    data = await get_qrcode()
    if "error" in data:
        raise HTTPException(status_code=503, detail=data["error"])
    return data


@router.delete("/desconectar")
async def desconectar_whatsapp():
    ok = await desconectar()
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao desconectar")
    return {"status": "disconnected"}


@router.post("/webhook")
async def webhook_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    instance: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    client_ip = (request.client.host if request.client else None) or "unknown"
    rl = webhook_rate_limiter.check(f"webhook:{client_ip}")
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Muitas requisicoes. Tente novamente em instantes.",
            headers={"Retry-After": str(rl.retry_after_seconds)},
        )

    provider = settings.WHATSAPP_PROVIDER.lower().strip()
    _validar_autenticacao_webhook(request, provider)
    raw_body = await request.json()

    empresa_instancia: Empresa | None = None
    if instance:
        empresa_instancia = (
            db.query(Empresa).filter(Empresa.evolution_instance == instance).first()
        )

    try:
        if provider == "evolution":
            return await _webhook_evolution(raw_body, background_tasks, db, empresa_instancia)
        else:
            return await _webhook_zapi(raw_body, background_tasks, db)
    except Exception as e:
        logger.warning("[webhook] Erro ao parsear payload (%s): %s", provider, e)
        return {"status": "parse_error"}


async def _webhook_zapi(raw_body: dict, background_tasks: BackgroundTasks, db: Session):
    payload = WebhookZAPI(**raw_body)
    if payload.fromMe or payload.isGroup or payload.isNewsletter:
        return {"status": "ignored"}

    telefone = sanitizar_telefone(payload.phone)
    mensagem = sanitizar_mensagem(payload.mensagem_texto)
    if not telefone or not mensagem:
        return {"status": "ignored"}

    background_tasks.add_task(processar_mensagem, telefone, mensagem)
    return {"status": "ok"}


async def _webhook_evolution(
    raw_body: dict,
    background_tasks: BackgroundTasks,
    db: Session,
    empresa_instancia: Empresa | None = None,
):
    event = raw_body.get("event", "")

    if event in ("connection.update", "CONNECTION_UPDATE") and empresa_instancia:
        await _tratar_connection_update(raw_body, empresa_instancia, db)
        return {"status": "ok", "event": event}

    if event not in ("messages.upsert", "MESSAGES_UPSERT"):
        return {"status": "ignored", "event": event}

    payload = WebhookEvolution(**raw_body)
    if payload.fromMe or payload.isGroup:
        return {"status": "ignored"}

    telefone = sanitizar_telefone(payload.phone)
    mensagem = sanitizar_mensagem(payload.mensagem_texto)
    empresa_id = empresa_instancia.id if empresa_instancia else None

    # Áudio (PTT ou audioMessage) — tenta transcrever para operadores
    if not mensagem and payload.audio_message_data:
        background_tasks.add_task(
            _processar_audio_operador,
            telefone,
            payload.audio_message_data,
            empresa_id,
        )
        return {"status": "ok", "type": "audio"}

    if not telefone or not mensagem:
        return {"status": "ignored"}

    background_tasks.add_task(processar_mensagem, telefone, mensagem, empresa_id)
    return {"status": "ok"}


async def _processar_audio_operador(
    telefone: str,
    audio_message_data: dict,
    empresa_id: int | None,
) -> None:
    """
    [INOVAÇÃO] Background task: transcreve áudio do WhatsApp via Whisper
    e encaminha o texto transcrito ao assistente do operador.
    """
    from app.core.database import SessionLocal
    from app.models.models import Empresa
    from app.services.whatsapp_bot_service import _usuario_por_telefone_operador
    from app.services.whatsapp_service import enviar_mensagem_texto
    from app.services.audio_transcription_service import (
        transcrever_audio_wpp,
        mensagem_voz_nao_configurada,
    )

    db = SessionLocal()
    try:
        # Só processa áudio de operadores individuais cadastrados
        operador = _usuario_por_telefone_operador(telefone, db)
        if not operador:
            return  # áudio de cliente — ignora

        empresa = db.query(Empresa).filter(Empresa.id == operador.empresa_id).first()
        if not empresa:
            return

        # Indica que está processando o áudio
        await enviar_mensagem_texto(
            telefone, "🎤 _Processando seu áudio..._", empresa=empresa
        )

        transcricao = await transcrever_audio_wpp(audio_message_data)

        if not transcricao:
            await enviar_mensagem_texto(
                telefone, mensagem_voz_nao_configurada(), empresa=empresa
            )
            return

        # Log para auditoria
        import logging
        logging.getLogger(__name__).info(
            "[AudioWPP] %s transcreveu: %s", telefone, transcricao[:100]
        )

        # Encaminha o texto ao pipeline normal do operador
        from app.services.operador_wpp_service import processar_operador_wpp
        await processar_operador_wpp(
            telefone=telefone,
            mensagem=transcricao,
            operador=operador,
            db=db,
            empresa=empresa,
        )
    finally:
        db.close()


async def _tratar_connection_update(raw_body: dict, empresa: Empresa, db: Session):
    data = raw_body.get("data", {}) or {}
    state = data.get("state", "") or raw_body.get("state", "")

    empresa_db = db.query(Empresa).filter(Empresa.id == empresa.id).first()
    if not empresa_db:
        return

    if state == "open":
        empresa_db.whatsapp_conectado = True
        me = data.get("me") or {}
        if isinstance(me, dict):
            jid = me.get("id", "") or me.get("jid", "")
            if jid:
                numero = jid.split(":")[0].split("@")[0]
                if numero.isdigit():
                    empresa_db.whatsapp_numero = numero
    elif state in ("close", "closed"):
        empresa_db.whatsapp_conectado = False

    db.commit()


@router.post("/interpretar")
async def interpretar_texto(dados: IAInterpretacaoRequest, request: Request):
    client_ip = (request.client.host if request.client else None) or "unknown"
    rl = ia_interpretar_rate_limiter.check(f"interpretar:{client_ip}")
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Limite de requisicoes atingido. Tente novamente mais tarde.",
            headers={"Retry-After": str(rl.retry_after_seconds)},
        )
    resultado = await interpretar_mensagem(dados.mensagem)
    return resultado
