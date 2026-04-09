"""
Webhook Kiwify → COTTE
--------------------
Kiwify dispara POST neste endpoint quando uma venda é aprovada,
reembolsada ou uma assinatura é cancelada/expirada.

Configure em: Kiwify → Produto → Webhooks → URL: https://seu-dominio.com/webhooks/kiwify
Token (secret): defina KIWIFY_TOKEN no .env do Railway

Em produção (ENVIRONMENT=production ou prod), KIWIFY_TOKEN é obrigatório: sem ele o
endpoint responde 401 e nenhum evento é processado (evita alteração de assinatura por
payloads não autenticados).
"""

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import text
from fastapi import Depends
from datetime import datetime, timezone, timedelta
import logging
import secrets
import hmac
import hashlib
import json

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Empresa, Usuario, WebhookEvent

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

logger = logging.getLogger(__name__)

_KIWIFY_ENV_PRODUCAO = frozenset({"production", "prod"})


def _kiwify_producao_sem_token_configurado() -> bool:
    """True se o ambiente exige segredo Kiwify e ele está vazio."""
    env_raw = getattr(settings, "ENVIRONMENT", "") or ""
    env = env_raw.strip().lower() if isinstance(env_raw, str) else str(env_raw).strip().lower()
    if env not in _KIWIFY_ENV_PRODUCAO:
        return False
    token_raw = getattr(settings, "KIWIFY_TOKEN", "") or ""
    token = token_raw.strip() if isinstance(token_raw, str) else str(token_raw).strip()
    return not token


# Eventos Kiwify que ativam a assinatura
_EVENTOS_ATIVAR = {"order_approved", "sale_approved", "subscription_renewed"}
# Eventos que desativam
_EVENTOS_DESATIVAR = {
    "order_refunded", "sale_refunded",
    "order_chargeback", "sale_chargeback",
    "subscription_canceled", "subscription_cancelled",
    "subscription_expired",
    "subscription_payment_failed",  # pagamento falhou → bloquear imediatamente
    "subscription_suspended",       # alguns providers usam este nome
}

# Mapeamento: trecho do nome do plano Kiwify → plano COTTE
_PLANO_MAP = [
    ("business", "business"),
    ("empresa",  "business"),
    ("pro",      "pro"),
    ("starter",  "starter"),
    ("basico",   "starter"),
    ("basic",    "starter"),
]

def _detectar_plano(nome_plano: str) -> str:
    nome = (nome_plano or "").lower()
    for trecho, plano in _PLANO_MAP:
        if trecho in nome:
            return plano
    return "pro"  # fallback


def _first_str(*values: object) -> str:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _extrair_token(body: dict, request: Request) -> str:
    token_body = body.get("token") if isinstance(body, dict) else ""
    token_header = request.headers.get("X-Kiwify-Token", "") or request.headers.get("x-kiwify-token", "")
    auth = request.headers.get("Authorization", "") or request.headers.get("authorization", "")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        auth = auth.split(" ", 1)[1].strip()
    else:
        auth = ""
    return _first_str(token_body, token_header, auth)


def _extrair_evento(body: dict) -> str:
    raw = _first_str(body.get("event"), body.get("type"))
    return raw.lower()


def _extrair_data(body: dict) -> dict:
    data = body.get("data")
    if isinstance(data, dict):
        return data
    return body if isinstance(body, dict) else {}


def _extrair_email(data: dict) -> str:
    customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}
    buyer = data.get("buyer") if isinstance(data.get("buyer"), dict) else {}
    client = data.get("client") if isinstance(data.get("client"), dict) else {}
    return _first_str(
        customer.get("email"),
        buyer.get("email"),
        client.get("email"),
        data.get("email"),
    )


def _extrair_nome_plano(data: dict) -> str:
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    product = data.get("product") if isinstance(data.get("product"), dict) else {}
    offer = data.get("offer") if isinstance(data.get("offer"), dict) else {}
    return _first_str(
        plan.get("name"),
        product.get("name"),
        offer.get("name"),
        data.get("plan_name"),
        data.get("product_name"),
    )


def _extrair_cupom(data: dict) -> str:
    coupon = data.get("coupon") if isinstance(data.get("coupon"), dict) else {}
    order  = data.get("order")  if isinstance(data.get("order"),  dict) else {}
    return _first_str(
        coupon.get("code"),
        coupon.get("name"),
        order.get("coupon_code"),
        data.get("coupon_code"),
    )


def _extrair_validade(data: dict) -> datetime:
    subscription = data.get("subscription") if isinstance(data.get("subscription"), dict) else {}
    raw = subscription.get("current_period_end") or subscription.get("next_charge_at") or data.get("current_period_end")

    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 1_000_000_000_000:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc) + timedelta(days=31)

    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc) + timedelta(days=31)

    return datetime.now(timezone.utc) + timedelta(days=31)


def _extrair_signature(request: Request) -> str:
    sig = request.query_params.get("signature", "") or request.query_params.get("sig", "")
    if isinstance(sig, str):
        return sig.strip()
    return ""


def _validar_signature(signature: str, secret: str, raw_body: bytes) -> bool:
    if not signature:
        return False
    if not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha1).hexdigest()
    return secrets.compare_digest(signature.lower(), expected.lower())


def _gerar_event_id(body: dict, raw_body: bytes) -> str:
    """Gera identificador único para o evento.
    
    Prioriza o campo webhook_id / id do payload (idempotência do provedor).
    Se ausente, gera SHA-256 do body bruto.
    """
    for field in ("webhook_id", "id", "notification_id"):
        val = body.get(field)
        if isinstance(val, (str, int)) and str(val).strip():
            return f"kiwify:{val}"
    # fallback: hash do body bruto
    return f"kiwify:hash:{hashlib.sha256(raw_body).hexdigest()}"


def _tentar_registrar_evento(db: Session, event_id: str, payload_hash: str) -> bool:
    """Tenta inserir registro de idempotência atomicamente.

    Retorna True se o evento é novo (inserção bem-sucedida).
    Retorna False se o evento já foi registrado (chave duplicada).
    Usa INSERT … ON CONFLICT DO NOTHING para eliminar race conditions.
    """
    result = db.execute(
        text(
            "INSERT INTO webhook_events (event_id, provider, payload_hash) "
            "VALUES (:eid, 'kiwify', :ph) "
            "ON CONFLICT (event_id) DO NOTHING"
        ),
        {"eid": event_id, "ph": payload_hash},
    )
    db.flush()
    # rowcount == 1 se o INSERT aconteceu; == 0 se o conflito foi ignorado
    return result.rowcount > 0


@router.post("/kiwify")
async def kiwify_webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe eventos da Kiwify e gerencia assinaturas automaticamente."""
    raw_body = await request.body()
    try:
        body = json.loads(raw_body.decode("utf-8") if isinstance(raw_body, (bytes, bytearray)) else "")
    except Exception:
        raise HTTPException(status_code=400, detail="Payload inválido")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Payload inválido")

    evento_norm = _extrair_evento(body)
    logger.info("Kiwify webhook recebido: %s", evento_norm or "desconhecido")

    if _kiwify_producao_sem_token_configurado():
        logger.error(
            "Kiwify webhook recusado: KIWIFY_TOKEN obrigatório em produção (ENVIRONMENT=%s)",
            getattr(settings, "ENVIRONMENT", ""),
        )
        raise HTTPException(
            status_code=401,
            detail="KIWIFY_TOKEN obrigatório em produção para processar webhooks Kiwify.",
        )

    # ── 0. Idempotência — INSERT atômico (elimina race condition)
    event_id = _gerar_event_id(body, raw_body)
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    if not _tentar_registrar_evento(db, event_id, payload_hash):
        logger.info("Kiwify webhook ignorado (duplicado): event_id=%s", event_id)
        return {"ok": True, "acao": "duplicado", "event_id": event_id}

    # ── 1. Verificar token (se configurado)
    if settings.KIWIFY_TOKEN:
        signature = _extrair_signature(request)
        token_recebido = _extrair_token(body, request)
        token_ok = bool(token_recebido) and secrets.compare_digest(token_recebido, settings.KIWIFY_TOKEN)
        signature_ok = _validar_signature(signature, settings.KIWIFY_TOKEN, raw_body)
        if not (token_ok or signature_ok):
            logger.warning("Kiwify webhook: token inválido")
            raise HTTPException(status_code=401, detail="Token inválido")

    # ── 2. Extrair campos principais
    data = _extrair_data(body)

    email = _extrair_email(data)
    plano_nome = _extrair_nome_plano(data)
    assinatura_valida_ate = _extrair_validade(data)
    cupom = _extrair_cupom(data)

    if not email:
        # Atualizar registro já criado (evita reprocessar)
        db.execute(
            text("UPDATE webhook_events SET evento = :ev, empresa_id = NULL WHERE event_id = :eid"),
            {"ev": evento_norm or None, "eid": event_id},
        )
        db.commit()
        logger.warning("Kiwify webhook: e-mail do cliente ausente")
        return {"ok": False, "detalhe": "e-mail ausente"}

    # ── 3. Localizar empresa pelo e-mail do usuário admin
    usuario = db.query(Usuario).filter(
        func.lower(Usuario.email) == email,
        Usuario.is_superadmin == False,
    ).first()

    if not usuario:
        usuario = db.query(Usuario).filter(func.lower(Usuario.email) == email).first()

    # Fallback: o e-mail no Kiwify pode ser o e-mail da empresa (campo Empresa.email)
    if not usuario:
        usuario = (
            db.query(Usuario)
            .join(Empresa, Empresa.id == Usuario.empresa_id)
            .filter(
                Empresa.email == email,
                Usuario.is_gestor == True,
                Usuario.is_superadmin == False,
            )
            .first()
        )

    if not usuario:
        db.execute(
            text("UPDATE webhook_events SET evento = :ev, empresa_id = NULL WHERE event_id = :eid"),
            {"ev": evento_norm or None, "eid": event_id},
        )
        db.commit()
        logger.warning("Kiwify webhook: nenhum usuário com e-mail %s", email)
        return {"ok": False, "detalhe": f"usuário não encontrado: {email}"}

    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        db.execute(
            text("UPDATE webhook_events SET evento = :ev, empresa_id = NULL WHERE event_id = :eid"),
            {"ev": evento_norm or None, "eid": event_id},
        )
        db.commit()
        return {"ok": False, "detalhe": "empresa não encontrada"}

    # ── 4. Aplicar ação e atualizar registro de idempotência
    plano = _detectar_plano(plano_nome)

    if evento_norm in _EVENTOS_ATIVAR:
        empresa.plano                = plano
        empresa.assinatura_valida_ate = assinatura_valida_ate
        empresa.ativo                = True
        if cupom:
            empresa.cupom_kiwify = cupom
        db.execute(
            text("UPDATE webhook_events SET evento = :ev, empresa_id = :emp WHERE event_id = :eid"),
            {"ev": evento_norm, "emp": empresa.id, "eid": event_id},
        )
        db.commit()
        logger.info("Empresa %d ativada — plano=%s validade=%s", empresa.id, plano, assinatura_valida_ate)
        return {"ok": True, "acao": "ativada", "empresa_id": empresa.id, "plano": plano}

    if evento_norm in _EVENTOS_DESATIVAR:
        empresa.ativo = False
        db.execute(
            text("UPDATE webhook_events SET evento = :ev, empresa_id = :emp WHERE event_id = :eid"),
            {"ev": evento_norm, "emp": empresa.id, "eid": event_id},
        )
        db.commit()
        logger.info("Empresa %d desativada — evento=%s", empresa.id, evento_norm)
        return {"ok": True, "acao": "desativada", "empresa_id": empresa.id}

    # Evento desconhecido — atualizar registro já existente
    db.execute(
        text("UPDATE webhook_events SET evento = :ev, empresa_id = :emp WHERE event_id = :eid"),
        {"ev": evento_norm or None, "emp": empresa.id, "eid": event_id},
    )
    db.commit()
    logger.info("Kiwify webhook: evento ignorado (%s)", evento_norm)
    return {"ok": True, "acao": "ignorado", "evento": evento_norm}
