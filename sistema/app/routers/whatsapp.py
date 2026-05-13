from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from sqlalchemy.orm import Session
from typing import Optional, Literal
from pydantic import BaseModel
import secrets

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Empresa, Orcamento
from app.schemas.schemas import (
    WebhookZAPI,
    WebhookEvolution,
    IAInterpretacaoRequest,
    desembrulhar_mensagem_baileys,
)
from app.services.whatsapp_service import (
    get_status,
    get_qrcode,
    desconectar,
)
from app.services.whatsapp_bot_service import processar_mensagem
from app.services.tenant_commercial_service import registrar_interacao_whatsapp
from app.utils.whatsapp_sanitizer import sanitizar_telefone, sanitizar_mensagem
from app.services.rate_limit_service import (
    webhook_rate_limiter,
    ia_interpretar_rate_limiter,
)
from app.services.ia_service import interpretar_mensagem
from app.core.auth import get_superadmin, exigir_permissao
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


def _normalizar_query_instance(instance: Optional[str]) -> Optional[str]:
    """
    Evolution API v2.x pode chamar o webhook com URL incorreta, por exemplo:
    .../webhook?instance=empresa-5/messages-upsert
    O FastAPI interpreta instance='empresa-5/messages-upsert' e não encontra a empresa.
    Mantém só o segmento antes da primeira barra.
    """
    if not instance or not isinstance(instance, str):
        return None
    s = instance.strip()
    if "/" in s:
        parte = s.split("/", 1)[0].strip()
        logger.warning(
            "[WA Webhook] Query 'instance' vinha com sufixo de evento; normalizado %r -> %r",
            s,
            parte,
        )
        s = parte
    return s or None


def _extrair_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "") or request.headers.get("authorization", "")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def _extrair_token_evolution_webhook(request: Request) -> str:
    """Headers/query aceitos pela Evolution API e proxies comuns."""
    return (
        (
            request.headers.get("apikey", "")
            or request.headers.get("Apikey", "")
            or request.headers.get("x-api-key", "")
            or request.headers.get("X-API-Key", "")
            or request.headers.get("X-Api-Key", "")
            or request.query_params.get("apikey", "")
            or _extrair_bearer_token(request)
        )
        or ""
    ).strip()


def _validar_autenticacao_webhook(request: Request, provider: str) -> None:
    if provider == "evolution":
        secret = (getattr(settings, "EVOLUTION_API_KEY", "") or "").strip()
        if not secret:
            raise HTTPException(status_code=503, detail="Webhook Evolution nao configurado")
        token = _extrair_token_evolution_webhook(request)
        if not token:
            logger.warning(
                "[WA Webhook] 401: nenhum token recebido (esperado header apikey ou "
                "x-api-key, query apikey, ou Authorization Bearer igual a EVOLUTION_API_KEY)"
            )
            raise HTTPException(status_code=401, detail="Webhook nao autorizado")
        if not secrets.compare_digest(token, secret):
            logger.warning(
                "[WA Webhook] 401: token recebido nao confere com EVOLUTION_API_KEY do servidor "
                "(alinhar a mesma chave na Evolution e no Railway / .env do COTTE)"
            )
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


def _resumir_mensagem_para_timeline_evolution(payload: WebhookEvolution, raw_body: dict) -> str | None:
    """
    Extrai uma representação textual mínima para timeline do CRM.
    Prioriza texto real e, quando não houver, registra placeholders de mídias/eventos
    para não perder a evidência da interação do cliente.
    """
    texto = sanitizar_mensagem(payload.mensagem_texto)
    if texto:
        return texto

    data = raw_body.get("data") if isinstance(raw_body, dict) else {}
    if not isinstance(data, dict):
        return None
    msg = data.get("message") or {}
    if isinstance(msg, dict):
        msg = desembrulhar_mensagem_baileys(msg)
    if not isinstance(msg, dict):
        return None

    if msg.get("audioMessage") or msg.get("pttMessage"):
        return "[audio recebido]"
    if msg.get("imageMessage"):
        return "[imagem recebida]"
    if msg.get("videoMessage"):
        return "[video recebido]"
    if msg.get("documentMessage"):
        return "[documento recebido]"
    if msg.get("stickerMessage"):
        return "[sticker recebido]"
    if msg.get("locationMessage"):
        return "[localizacao recebida]"
    if msg.get("contactMessage"):
        return "[contato recebido]"

    if msg.get("listResponseMessage"):
        row_id = payload.list_response_row_id
        if row_id:
            return f"[resposta de lista: {row_id}]"
        return "[resposta de lista recebida]"

    if msg.get("buttonsResponseMessage"):
        b = msg.get("buttonsResponseMessage") or {}
        selected_id = b.get("selectedButtonId") or b.get("selectedDisplayText")
        if selected_id:
            return f"[resposta de botao: {selected_id}]"
        return "[resposta de botao recebida]"

    msg_type = (data.get("messageType") or "").strip()
    if msg_type:
        return f"[mensagem recebida sem texto: {msg_type}]"
    return "[mensagem recebida sem texto]"


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

    instance = _normalizar_query_instance(instance)

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


@router.post("/webhook-comercial")
async def webhook_comercial(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Webhook dedicado para a instância Evolution 'cotte-comercial'.
    Captura respostas recebidas dos leads do CRM e registra em CommercialInteraction.

    Configurar no painel da Evolution API:
      URL: <base_url>/api/v1/whatsapp/webhook-comercial
      Eventos: messages.upsert
    """
    client_ip = (request.client.host if request.client else None) or "unknown"
    rl = webhook_rate_limiter.check(f"webhook-comercial:{client_ip}")
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Muitas requisicoes. Tente novamente em instantes.",
            headers={"Retry-After": str(rl.retry_after_seconds)},
        )

    # Valida autenticação pelo EVOLUTION_API_KEY (mesma chave da instância comercial)
    secret = (getattr(settings, "EVOLUTION_API_KEY", "") or "").strip()
    if secret:
        token = _extrair_token_evolution_webhook(request)
        if not token or not secrets.compare_digest(token, secret):
            raise HTTPException(status_code=401, detail="Webhook nao autorizado")

    try:
        raw_body = await request.json()
    except Exception:
        return {"status": "invalid_json"}

    background_tasks.add_task(_processar_webhook_comercial, raw_body)
    return {"status": "ok"}


async def _processar_webhook_comercial(raw_body: dict) -> None:
    """
    Background task: processa evento da instância comercial.
    Filtra apenas mensagens recebidas dos leads (fromMe=false) e as grava
    em CommercialInteraction com direcao='recebido'.
    """
    from app.core.database import SessionLocal
    from app.models.models import CommercialLead, CommercialInteraction, TipoInteracao, CanalInteracao
    from app.utils.whatsapp_sanitizer import sanitizar_telefone, sanitizar_mensagem

    event = raw_body.get("event", "")
    if event not in ("messages.upsert", "MESSAGES_UPSERT"):
        return

    data = raw_body.get("data") or {}
    if not isinstance(data, dict):
        return

    # Ignorar mensagens enviadas pelo sistema (fromMe=true) e grupos
    key = data.get("key") or {}
    from_me = key.get("fromMe", False)
    remote_jid = key.get("remoteJid", "") or ""
    remote_jid_alt = key.get("remoteJidAlt", "") or ""
    is_group = "@g.us" in remote_jid
    if from_me or is_group:
        return

    # Extrair número e texto (PN alternativo quando o JID principal é @lid)
    jid_numero = remote_jid
    if "@lid" in remote_jid and remote_jid_alt:
        jid_numero = remote_jid_alt
    phone_raw = jid_numero.split("@")[0].split(":")[0]
    telefone = sanitizar_telefone(phone_raw)
    if not telefone:
        return

    # Extrair conteúdo de texto
    msg_obj = data.get("message") or {}
    msg_inner = desembrulhar_mensagem_baileys(msg_obj if isinstance(msg_obj, dict) else {})
    texto = (
        msg_inner.get("conversation")
        or (msg_inner.get("extendedTextMessage") or {}).get("text")
        or (msg_inner.get("imageMessage") or {}).get("caption")
        or (msg_inner.get("videoMessage") or {}).get("caption")
        or (msg_inner.get("documentMessage") or {}).get("caption")
        or (msg_inner.get("documentWithCaptionMessage") or {}).get("caption")
        or ""
    )
    mensagem = sanitizar_mensagem(texto)

    # Extrair message_id para deduplicação
    message_id = key.get("id", "")

    # Tipos de mídia sem texto (ignorar silenciosamente por ora)
    if not mensagem:
        logger.debug("[webhook-comercial] Mensagem sem texto de %s — ignorando", telefone)
        return

    db = SessionLocal()
    try:
        # Deduplicação: se já existe interação com esse message_id, ignorar
        if message_id:
            existe = (
                db.query(CommercialInteraction)
                .filter(CommercialInteraction.message_id == message_id)
                .first()
            )
            if existe:
                logger.debug("[webhook-comercial] Duplicata ignorada: message_id=%s", message_id)
                return

        # Buscar lead pelo número de WhatsApp
        lead = (
            db.query(CommercialLead)
            .filter(CommercialLead.whatsapp.ilike(f"%{telefone[-8:]}%"))
            .first()
        )
        if not lead:
            logger.info(
                "[webhook-comercial] Lead não encontrado para telefone %s — ignorando", telefone
            )
            return

        from datetime import datetime, timezone

        interacao = CommercialInteraction(
            lead_id=lead.id,
            tipo=TipoInteracao.WHATSAPP,
            canal=CanalInteracao.WHATSAPP,
            conteudo=mensagem,
            status_envio="recebido",
            direcao="recebido",
            message_id=message_id or None,
            criado_em=datetime.now(timezone.utc),
        )
        db.add(interacao)
        lead.ultimo_contato_em = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "[webhook-comercial] Resposta registrada: lead_id=%s telefone=%s msg='%s...'",
            lead.id, telefone, mensagem[:50],
        )
    except Exception:
        logger.exception("[webhook-comercial] Erro ao processar mensagem de %s", telefone)
        db.rollback()
    finally:
        db.close()




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
    instance_in_payload = raw_body.get("instance", "desconhecida")
    logger.info("[WA Webhook] Evento: %s | Instancia Payload: %s", event, instance_in_payload)


    if event in ("connection.update", "CONNECTION_UPDATE") and empresa_instancia:
        await _tratar_connection_update(raw_body, empresa_instancia, db)
        return {"status": "ok", "event": event}

    if event not in ("messages.upsert", "MESSAGES_UPSERT"):
        return {"status": "ignored", "event": event}

    payload = WebhookEvolution(**raw_body)
    
    # ── Registro de Histórico para Tenants (CRM Comercial) ──
    # Se a empresa não foi resolvida via Query Param, tenta pelo payload
    if not empresa_instancia and payload.instance:
        inst_name = payload.instance.strip()
        empresa_instancia = db.query(Empresa).filter(Empresa.evolution_instance == inst_name).first()
        
        # Fallback para as instâncias globais do sistema (Railway Variables)
        if not empresa_instancia:
            if inst_name in (settings.EVOLUTION_INSTANCE, settings.EVOLUTION_INSTANCE_COMERCIAL):
                # Tenta localizar a empresa 5 (cotte.app) ou a primeira empresa ativa
                empresa_instancia = db.query(Empresa).filter(Empresa.id == 5).first() or db.query(Empresa).first()
                if empresa_instancia:
                    logger.info("[WA Webhook] Fallback sistema: instancia %s -> empresa %s", inst_name, empresa_instancia.id)

    empresa_id = empresa_instancia.id if empresa_instancia else None

    telefone = sanitizar_telefone(payload.phone)
    mensagem_timeline = _resumir_mensagem_para_timeline_evolution(payload, raw_body)

    if telefone and mensagem_timeline and empresa_id and not payload.isGroup:
        direcao = "enviado" if payload.fromMe else "recebido"
        message_id = payload.data.get("key", {}).get("id") if isinstance(payload.data, dict) else None
        
        logger.info("[WA Webhook] Gravando interacao: empresa=%s telefone=%s direcao=%s", empresa_id, telefone, direcao)
        
        background_tasks.add_task(
            registrar_interacao_whatsapp,
            empresa_id=empresa_id,
            telefone=telefone,
            mensagem=mensagem_timeline,
            direcao=direcao,
            message_id=message_id
        )
    else:
        if not empresa_id and event in ("messages.upsert", "MESSAGES_UPSERT"):
            logger.warning("[WA Webhook] Empresa nao localizada para instancia: %s", payload.instance)


    if payload.fromMe or payload.isGroup:
        return {"status": "ignored"}

    telefone = sanitizar_telefone(payload.phone)
    empresa_id = empresa_instancia.id if empresa_instancia else None

    # Log de diagnóstico: tipo da mensagem recebida
    _data = raw_body.get("data") or {}
    _msg_type = _data.get("messageType", "") if isinstance(_data, dict) else ""
    _msg_keys = list((_data.get("message") or {}).keys()) if isinstance(_data, dict) else []
    logger.info("[webhook] Evolution msg de %s: messageType='%s' keys=%s", telefone, _msg_type, _msg_keys)

    # Lista interativa (listResponseMessage) — roteado pelo serviço interativo
    row_id = payload.list_response_row_id
    logger.info("[webhook] Evolution list_response_row_id=%r de %s", row_id, telefone)
    if row_id and telefone:
        background_tasks.add_task(
            _processar_lista_interativa,
            telefone,
            row_id,
            empresa_instancia,
        )
        return {"status": "ok", "type": "list_response"}

    mensagem = sanitizar_mensagem(payload.mensagem_texto)

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
        # A interação já pode ter sido registrada na timeline como placeholder.
        return {"status": "ignored"}

    background_tasks.add_task(processar_mensagem, telefone, mensagem, empresa_id)
    return {"status": "ok"}


async def _processar_lista_interativa(
    telefone: str,
    row_id: str,
    empresa_instancia: "Empresa | None",
) -> None:
    """Background task: processa seleção de lista interativa (cliente ou operador)."""
    from app.core.database import SessionLocal
    from app.services.whatsapp_interativo_service import processar_resposta_lista

    logger.info("[Interativo] Recebido rowId='%s' de %s (instância=%s)", row_id, telefone, getattr(empresa_instancia, "evolution_instance", None))
    db = SessionLocal()
    try:
        ok = await processar_resposta_lista(db, telefone, row_id, empresa_instancia)
        if not ok:
            logger.warning("[Interativo] processar_resposta_lista retornou False para %s (rowId=%s)", telefone, row_id)
    except Exception:
        logger.exception("[Interativo] Erro ao processar lista de %s (rowId=%s)", telefone, row_id)
    finally:
        db.close()


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


class EnviarMenuOrcamentoRequest(BaseModel):
    pass  # orcamento_id vem na URL


@router.post("/enviar-menu-orcamento/{orcamento_id}")
async def enviar_menu_interativo(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_permissao("orcamento", "escrita")),
):
    """Envia menu interativo de aprovação/recusa ao cliente do orçamento."""
    from app.services.whatsapp_interativo_service import enviar_menu_orcamento_cliente
    from app.models.models import StatusOrcamento

    orc = db.query(Orcamento).filter(
        Orcamento.id == orcamento_id,
        Orcamento.empresa_id == usuario.empresa_id,
    ).first()
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if not orc.cliente or not orc.cliente.telefone:
        raise HTTPException(status_code=422, detail="Cliente sem telefone cadastrado")

    _STATUS_VALIDOS = {StatusOrcamento.ENVIADO, StatusOrcamento.RASCUNHO}
    if orc.status not in _STATUS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"Status '{orc.status}' não permite envio de menu interativo. Use orçamentos com status 'rascunho' ou 'enviado'.",
        )

    ok = await enviar_menu_orcamento_cliente(db, orcamento_id, empresa)
    if not ok:
        raise HTTPException(
            status_code=502,
            detail="Falha ao enviar mensagem via Evolution API. Verifique os logs do servidor.",
        )

    return {"success": True, "message": f"Menu enviado ao cliente {orc.cliente.nome}"}


class TesteInterativoRequest(BaseModel):
    numero: str
    tipo: Literal["poll", "lista", "ambos"] = "ambos"


@router.post("/test-interactive")
async def testar_mensagens_interativas(
    dados: TesteInterativoRequest,
    _=Depends(get_superadmin),
):
    from app.services.whatsapp_evolution import EvolutionProvider

    provider = EvolutionProvider()
    resultados = []

    if dados.tipo in ("poll", "ambos"):
        ok = await provider.enviar_poll(
            telefone=dados.numero,
            pergunta="Qual o melhor horário para seu atendimento?",
            opcoes=["🌅 Manhã (8h–12h)", "☀️ Tarde (12h–18h)", "🌙 Noite (18h–20h)"],
        )
        resultados.append({"tipo": "poll", "sucesso": ok})

    if dados.tipo in ("lista", "ambos"):
        import httpx as _httpx
        from app.core.config import settings as _s
        _url = f"{_s.EVOLUTION_API_URL.rstrip('/')}/message/sendList/{_s.EVOLUTION_INSTANCE}"
        _payload = {
            "number": dados.numero,
            "title": "Serviços Disponíveis",
            "description": "Selecione um serviço para saber mais",
            "footerText": "",
            "buttonText": "Ver serviços",
            "sections": [
                {"title": "Acabamento", "rows": [
                    {"title": "Pintura Interna", "description": "Ambientes internos", "rowId": "pintura_int"},
                    {"title": "Pintura Externa", "description": "Fachadas e muros", "rowId": "pintura_ext"},
                ]},
                {"title": "Instalações", "rows": [
                    {"title": "Elétrica Residencial", "description": "Instalação e manutenção", "rowId": "eletrica"},
                    {"title": "Hidráulica", "description": "Encanamentos e reparos", "rowId": "hidraulica"},
                ]},
            ],
        }
        try:
            async with _httpx.AsyncClient(timeout=10) as _c:
                _r = await _c.post(_url, json=_payload, headers={"apikey": _s.EVOLUTION_API_KEY, "Content-Type": "application/json"})
            ok = _r.status_code in (200, 201)
            erro = None if ok else _r.text[:300]
        except Exception as _e:
            ok = False
            erro = str(_e)
        resultados.append({"tipo": "lista", "sucesso": ok, "erro": erro})

    todos_ok = all(r["sucesso"] for r in resultados)
    return {"success": todos_ok, "resultados": resultados}


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
