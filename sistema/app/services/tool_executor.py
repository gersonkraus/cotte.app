"""Executor central de tools (Tool Use / function calling).

Único ponto autorizado a invocar handlers do `ai_tools.REGISTRY`. Responsável por:

- Lookup no REGISTRY (`unknown_tool`)
- Validação Pydantic dos argumentos (`invalid_input`)
- Permissão via `exigir_permissao(recurso, acao)` (`forbidden`)
- Gating de confirmação para ações destrutivas (`pending` + `confirmation_token`)
- Execução do handler com captura de exceção
- Persistência em `ToolCallLog` (mesmo em erro)

Importar handlers fora deste módulo é proibido por convenção (sem guardrails).
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import exigir_permissao
from app.models.models import ToolCallLog, Usuario
from app.services.ai_tools import REGISTRY
from app.services.assistant_engine_registry import get_engine_policy
from app.services.tenant_guard import ensure_scoped_empresa_id

logger = logging.getLogger(__name__)


# ── Confirmation tokens em memória ────────────────────────────────────────
# Mapa: token -> {tool_name, args_dict, args_hash, empresa_id, expires_at}
# Persistimos os args completos para que a confirmação execute exatamente
# a mesma ação proposta — sem reinvocar o LLM (que poderia chutar args novos).
_PENDING_TOKENS: dict[str, dict[str, Any]] = {}
_TOKEN_TTL_MINUTES = 5


def _semantic_key(value: Any) -> str:
    """Normaliza valor textual para comparação semântica estável."""
    if value is None:
        return ""
    txt = str(value).strip()
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.upper()
    txt = re.sub(r"[^A-Z0-9]+", "_", txt).strip("_")
    return txt


def _normalize_tool_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Camada central de normalização semântica de filtros antes das tools."""
    if not isinstance(args, dict):
        return {}
    normalized = dict(args)

    if tool_name == "listar_orcamentos":
        status_raw = normalized.get("status")
        if isinstance(status_raw, str) and status_raw.strip():
            aliases = {
                "PENDENTE": "ENVIADO",
                "PENDENTES": "ENVIADO",
                "EM_ABERTO": "ENVIADO",
                "ABERTO": "ENVIADO",
                "ABERTOS": "ENVIADO",
                "A_RECEBER": "APROVADO",
                "RECEBER": "APROVADO",
            }
            status_key = _semantic_key(status_raw)
            normalized["status"] = aliases.get(status_key, status_key)

        # Evita ValidationError comum do LLM (dias=0, limit>50, etc.)
        if normalized.get("dias") is not None:
            try:
                d_int = int(float(normalized["dias"]))
                normalized["dias"] = max(1, min(365, d_int))
            except (TypeError, ValueError):
                normalized.pop("dias", None)
        if normalized.get("limit") is not None:
            try:
                lim_int = int(float(normalized["limit"]))
                normalized["limit"] = max(1, min(50, lim_int))
            except (TypeError, ValueError):
                normalized.pop("limit", None)

        try:
            from zoneinfo import ZoneInfo

            br_tz = ZoneInfo("America/Sao_Paulo")
        except Exception:
            br_tz = timezone(timedelta(hours=-3))
        hoje_br = datetime.now(br_tz).date()
        ontem_br = hoje_br - timedelta(days=1)

        for _key in ("aprovado_em_de", "aprovado_em_ate"):
            v = normalized.get(_key)
            if v is None or isinstance(v, (date, datetime)):
                continue
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    normalized.pop(_key, None)
                    continue
                low = s.lower()
                if low in ("ontem", "yesterday"):
                    normalized[_key] = ontem_br.isoformat()
                elif low in ("hoje", "today"):
                    normalized[_key] = hoje_br.isoformat()
                elif "T" in s:
                    normalized[_key] = s.split("T", 1)[0].strip()

    return normalized


def _args_hash(args: dict[str, Any]) -> str:
    """Hash determinístico dos args para vincular um token a uma chamada específica."""
    return json.dumps(args, sort_keys=True, default=str, ensure_ascii=False)


def _prune_tokens() -> None:
    now = datetime.now(timezone.utc)
    expired = [t for t, rec in _PENDING_TOKENS.items() if rec["expires_at"] < now]
    for t in expired:
        del _PENDING_TOKENS[t]


def _issue_token(
    tool_name: str, args: dict[str, Any], *, empresa_id: Optional[int] = None
) -> str:
    _prune_tokens()
    token = secrets.token_urlsafe(16)
    _PENDING_TOKENS[token] = {
        "tool_name": tool_name,
        "args_dict": args,
        "args_hash": _args_hash(args),
        "empresa_id": empresa_id,
        "expires_at": datetime.now(timezone.utc)
        + timedelta(minutes=_TOKEN_TTL_MINUTES),
    }
    return token


def _consume_token(token: str, tool_name: str, args: dict[str, Any]) -> bool:
    _prune_tokens()
    rec = _PENDING_TOKENS.get(token)
    if not rec:
        return False
    if rec["tool_name"] != tool_name or rec["args_hash"] != _args_hash(args):
        return False
    del _PENDING_TOKENS[token]
    return True


def peek_pending(token: str) -> Optional[dict[str, Any]]:
    """Retorna {tool_name, args_dict, empresa_id} sem consumir o token. None se inválido/expirado."""
    _prune_tokens()
    rec = _PENDING_TOKENS.get(token)
    if not rec:
        return None
    return {
        "tool_name": rec["tool_name"],
        "args_dict": rec["args_dict"],
        "empresa_id": rec["empresa_id"],
    }


def pop_pending(token: str) -> Optional[dict[str, Any]]:
    """Igual a peek_pending, mas remove o token (uso único)."""
    rec = peek_pending(token)
    if rec is not None:
        _PENDING_TOKENS.pop(token, None)
    return rec


# ── Cache em memória para tools read-only ─────────────────────────────────
# Key: (empresa_id, tool_name, args_hash) -> (data_dict, expires_at)
# Escopo por empresa é obrigatório para não vazar dados entre tenants.
# Só cacheia `status == ok` de tools NÃO destrutivas com `cacheable_ttl > 0`.
_TOOL_CACHE: dict[tuple[int, str, str], tuple[dict[str, Any], datetime]] = {}
_CACHE_MAX_ENTRIES = 512  # soft cap — evita crescimento indefinido

# ── Idempotência de envios críticos ───────────────────────────────────────
# Protege contra reenvio duplicado acidental (ex.: retry/duplo clique no fluxo).
_SEND_TOOLS = {"enviar_orcamento_whatsapp", "enviar_orcamento_email"}
_SEND_IDEMPOTENCY: dict[tuple[int, str, str], tuple[dict[str, Any], datetime]] = {}


def _send_idempotency_ttl() -> int:
    try:
        return max(30, int(os.getenv("TOOL_SEND_IDEMPOTENCY_TTL_SECONDS", "300")))
    except Exception:
        return 300


def _send_idempotency_get(
    empresa_id: Optional[int], tool_name: str, args: dict[str, Any]
) -> Optional[dict[str, Any]]:
    if empresa_id is None:
        return None
    key = (empresa_id, tool_name, _args_hash(args))
    rec = _SEND_IDEMPOTENCY.get(key)
    if rec is None:
        return None
    data, exp = rec
    if exp < datetime.now(timezone.utc):
        _SEND_IDEMPOTENCY.pop(key, None)
        return None
    return data


def _send_idempotency_put(
    empresa_id: Optional[int],
    tool_name: str,
    args: dict[str, Any],
    data: dict[str, Any],
) -> None:
    if empresa_id is None:
        return
    key = (empresa_id, tool_name, _args_hash(args))
    _SEND_IDEMPOTENCY[key] = (
        data,
        datetime.now(timezone.utc) + timedelta(seconds=_send_idempotency_ttl()),
    )


def _cache_prune() -> None:
    now = datetime.now(timezone.utc)
    expired = [k for k, (_, exp) in _TOOL_CACHE.items() if exp < now]
    for k in expired:
        _TOOL_CACHE.pop(k, None)
    # Se ainda estiver acima do cap, descarta os mais antigos
    if len(_TOOL_CACHE) > _CACHE_MAX_ENTRIES:
        items = sorted(_TOOL_CACHE.items(), key=lambda kv: kv[1][1])
        for k, _ in items[: len(_TOOL_CACHE) - _CACHE_MAX_ENTRIES]:
            _TOOL_CACHE.pop(k, None)


def _cache_get(
    empresa_id: Optional[int], tool_name: str, args: dict[str, Any]
) -> Optional[dict[str, Any]]:
    if empresa_id is None:
        return None
    key = (empresa_id, tool_name, _args_hash(args))
    rec = _TOOL_CACHE.get(key)
    if rec is None:
        return None
    data, exp = rec
    if exp < datetime.now(timezone.utc):
        _TOOL_CACHE.pop(key, None)
        return None
    return data


def _cache_put(
    empresa_id: Optional[int],
    tool_name: str,
    args: dict[str, Any],
    data: dict[str, Any],
    ttl_seconds: int,
) -> None:
    if empresa_id is None or ttl_seconds <= 0:
        return
    _cache_prune()
    key = (empresa_id, tool_name, _args_hash(args))
    _TOOL_CACHE[key] = (
        data,
        datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
    )


# ── Rate limiting por empresa ─────────────────────────────────────────────
# Configurável por env var; defaults pensados pra evitar loop de tool calls
# do LLM sem atrapalhar uso normal.
def _rate_limits() -> tuple[int, int]:
    per_min = int(os.getenv("TOOL_RATE_LIMIT_PER_MIN", "30"))
    per_hour = int(os.getenv("TOOL_RATE_LIMIT_PER_HOUR", "300"))
    return per_min, per_hour


def _check_rate_limit(db: Session, empresa_id: Optional[int]) -> Optional[str]:
    """Retorna uma mensagem de erro se a empresa estourou a cota; None se ok.

    Usa `ToolCallLog.criado_em` (índice presente). Conta apenas execuções
    bem-sucedidas e erros — pending/invalid_input não contam (não chegam ao handler).
    """
    if empresa_id is None:
        return None
    per_min, per_hour = _rate_limits()
    if per_min <= 0 and per_hour <= 0:
        return None
    now = datetime.now(timezone.utc)
    try:
        if per_min > 0:
            desde_min = now - timedelta(minutes=1)
            count_min = (
                db.query(func.count(ToolCallLog.id))
                .filter(
                    ToolCallLog.empresa_id == empresa_id,
                    ToolCallLog.criado_em >= desde_min,
                    ToolCallLog.status.in_(("ok", "erro")),
                )
                .scalar()
                or 0
            )
            if count_min >= per_min:
                return f"Limite de {per_min} chamadas/minuto atingido. Aguarde 1 min."
        if per_hour > 0:
            desde_hora = now - timedelta(hours=1)
            count_hora = (
                db.query(func.count(ToolCallLog.id))
                .filter(
                    ToolCallLog.empresa_id == empresa_id,
                    ToolCallLog.criado_em >= desde_hora,
                    ToolCallLog.status.in_(("ok", "erro")),
                )
                .scalar()
                or 0
            )
            if count_hora >= per_hour:
                return f"Limite de {per_hour} chamadas/hora atingido. Aguarde."
    except Exception as e:  # nunca quebrar o assistente por causa do rate limit
        logger.warning("Falha ao checar rate limit: %s", e)
        return None
    return None


# ── Resultado canônico ────────────────────────────────────────────────────
@dataclass
class ToolResult:
    status: str  # ok|erro|forbidden|pending|invalid_input|unknown_tool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    code: Optional[str] = None
    pending_action: Optional[dict[str, Any]] = None
    latencia_ms: int = 0
    tool_name: Optional[str] = None

    def to_llm_payload(self) -> dict[str, Any]:
        """Payload serializado para devolver ao LLM como `{"role":"tool",...}`.
        Versão compactada (fast-path) para evitar explosão de contexto com payloads grandes.
        """
        if self.status == "ok":
            if not isinstance(self.data, dict):
                return self.data or {}

            if self.data.get("_llm_disable_preview"):
                return {
                    k: v for k, v in self.data.items() if k != "_llm_disable_preview"
                }

            compressed: dict[str, Any] = {
                "_meta_notice": "Payload enxugado para raciocínio do LLM. O frontend exibe a lista completa."
            }
            has_large_list = False
            for k, v in self.data.items():
                if isinstance(v, list) and len(v) > 10:
                    has_large_list = True
                    compressed[k] = {
                        "total_items": len(v),
                        "rows_preview": v[:10],
                        "note": f"Exibindo 10 de {len(v)} itens. Evitando estouro de tokens.",
                    }
                else:
                    compressed[k] = v

            return compressed if has_large_list else self.data
        if self.status == "pending":
            return {
                "pending": True,
                "message": "Ação destrutiva requer confirmação do usuário.",
                "confirmation_token": (self.pending_action or {}).get(
                    "confirmation_token"
                ),
            }
        return {"error": self.error or self.status, "code": self.code or self.status}


# ── Persistência ──────────────────────────────────────────────────────────
def _log(
    db: Session,
    *,
    empresa_id: Optional[int],
    usuario_id: Optional[int],
    sessao_id: Optional[str],
    request_id: Optional[str],
    tool: str,
    args: dict[str, Any] | None,
    result: ToolResult,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> None:
    try:
        args_payload = dict(args or {})
        result_payload = result.to_llm_payload()
        existing_meta = (
            args_payload.get("_meta")
            if isinstance(args_payload.get("_meta"), dict)
            else {}
        )
        meta_payload = {
            "request_id": request_id,
            "sessao_id": sessao_id,
            "tool": tool,
        }
        meta_payload = {k: v for k, v in meta_payload.items() if v}
        if meta_payload:
            merged_meta = {**existing_meta, **meta_payload}
            args_payload["_meta"] = merged_meta
            if isinstance(result_payload, dict):
                result_payload = {**result_payload, "_meta": merged_meta}
        rec = ToolCallLog(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            sessao_id=sessao_id,
            tool=tool,
            args_json=args_payload,
            resultado_json=result_payload,
            status=result.status,
            latencia_ms=result.latencia_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        db.add(rec)
        db.commit()
    except Exception as e:  # nunca quebrar o fluxo do assistente por causa de log
        logger.warning("Falha ao gravar ToolCallLog: %s", e)
        try:
            db.rollback()
        except Exception:
            pass


# ── Execução principal ────────────────────────────────────────────────────
async def execute(
    tool_call: dict[str, Any],
    *,
    db: Session,
    current_user: Usuario,
    sessao_id: Optional[str] = None,
    request_id: Optional[str] = None,
    confirmation_token: Optional[str] = None,
    engine: Optional[str] = None,
) -> ToolResult:
    try:
        ensure_scoped_empresa_id(getattr(current_user, "empresa_id", None))
    except Exception:
        return ToolResult(
            status="forbidden",
            error="Usuário sem escopo de empresa para executar tools",
            code="tenant_scope_required",
        )

    """Executa uma tool_call no formato OpenAI/LiteLLM.

    `tool_call` segue: `{"id": "...", "function": {"name": "...", "arguments": "<json>"}}`.
    """
    t0 = time.perf_counter()
    fn = (tool_call or {}).get("function") or {}
    name = fn.get("name") or ""
    raw_args = fn.get("arguments") or "{}"

    # 0. Rate limit por empresa (proteção anti-loop do LLM)
    rl_msg = _check_rate_limit(db, current_user.empresa_id)
    if rl_msg:
        result = ToolResult(
            status="rate_limited",
            error=rl_msg,
            code="rate_limited",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            request_id=request_id,
            tool=name or "?",
            args=None,
            result=result,
        )
        return result

    # 1. Lookup
    spec = REGISTRY.get(name)
    if spec is None:
        result = ToolResult(
            status="unknown_tool",
            error=f"tool desconhecida: {name}",
            code="unknown_tool",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            request_id=request_id,
            tool=name or "?",
            args=None,
            result=result,
        )
        return result

    if engine:
        policy = get_engine_policy(engine)
        if name not in set(policy.allowed_tools):
            result = ToolResult(
                status="forbidden",
                error=f"A tool '{name}' não é permitida para a engine '{policy.key}'.",
                code="engine_tool_not_allowed",
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=None,
                result=result,
            )
            return result

    # 2. Parse + validação Pydantic
    try:
        args_dict = (
            json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        )
    except json.JSONDecodeError as e:
        result = ToolResult(
            status="invalid_input",
            error=f"arguments não é JSON válido: {e}",
            code="invalid_input",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            request_id=request_id,
            tool=name,
            args=None,
            result=result,
        )
        return result

    args_dict = _normalize_tool_args(name, args_dict)
    if engine:
        meta = (
            args_dict.get("_meta") if isinstance(args_dict.get("_meta"), dict) else {}
        )
        args_dict["_meta"] = {**meta, "engine": str(engine).strip().lower()}

    if name in _SEND_TOOLS:
        replay = _send_idempotency_get(current_user.empresa_id, name, args_dict)
        if replay is not None:
            payload = dict(replay)
            payload["idempotent_replay"] = True
            result = ToolResult(
                status="ok",
                data=payload,
                code="idempotent_replay",
                latencia_ms=int((time.perf_counter() - t0) * 1000),
                tool_name=name,
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    try:
        validated = spec.input_model(**args_dict)
    except ValidationError as e:
        result = ToolResult(
            status="invalid_input",
            error=e.errors(include_url=False, include_input=False).__repr__(),
            code="invalid_input",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            request_id=request_id,
            tool=name,
            args=args_dict,
            result=result,
        )
        return result

    # 3. Permissão
    if spec.permissao_recurso:
        validator = exigir_permissao(spec.permissao_recurso, spec.permissao_acao)
        try:
            validator(usuario=current_user)
        except HTTPException as e:
            result = ToolResult(
                status="forbidden",
                error=str(e.detail),
                code="forbidden",
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    # 3.1 Idempotência para envios críticos (retorna replay sem reexecutar)
    if name in _SEND_TOOLS:
        replay = _send_idempotency_get(current_user.empresa_id, name, args_dict)
        if replay is not None:
            payload = dict(replay)
            payload["idempotent_replay"] = True
            result = ToolResult(
                status="ok",
                data=payload,
                code="idempotent_replay",
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    # 4a. Cache hit para tools read-only cacheáveis (respeita RBAC já validado acima)
    if not spec.destrutiva and spec.cacheable_ttl and spec.cacheable_ttl > 0:
        cached = _cache_get(current_user.empresa_id, name, args_dict)
        if cached is not None:
            result = ToolResult(
                status="ok",
                data=cached,
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    # 4. Gating de destrutivas
    if spec.destrutiva:
        if not confirmation_token or not _consume_token(
            confirmation_token, name, args_dict
        ):
            token = _issue_token(name, args_dict, empresa_id=current_user.empresa_id)

            extras: dict = {}
            try:
                from app.services.ai_tools.destructive_preview import (
                    build_destructive_extras,
                )

                extras = await build_destructive_extras(
                    name, args_dict, db=db, current_user=current_user
                )
            except Exception:
                logger.debug(
                    "Falha ao montar preview de confirmação para tool=%s",
                    name,
                    exc_info=True,
                )

            result = ToolResult(
                status="pending",
                pending_action={
                    "tool": name,
                    "args": args_dict,
                    "description": spec.description,
                    "confirmation_token": token,
                    "confirmation_required": True,
                    "action_category": ("envio" if name in _SEND_TOOLS else "mutacao"),
                    "idempotency_window_seconds": (
                        _send_idempotency_ttl() if name in _SEND_TOOLS else None
                    ),
                    "extras": extras,
                },
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    # 5. Executa o handler
    try:
        data = await spec.handler(validated, db=db, current_user=current_user)
        if isinstance(data, dict) and data.get("error"):
            result = ToolResult(
                status="erro",
                data=data,
                error=str(data.get("error")),
                code=str(data.get("code") or "handler_error"),
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
        else:
            result = ToolResult(
                status="ok",
                data=data if isinstance(data, dict) else {"result": data},
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            # Guarda no cache apenas execuções ok de tools read-only
            if (
                not spec.destrutiva
                and spec.cacheable_ttl
                and spec.cacheable_ttl > 0
                and isinstance(result.data, dict)
            ):
                _cache_put(
                    current_user.empresa_id,
                    name,
                    args_dict,
                    result.data,
                    spec.cacheable_ttl,
                )
            if name in _SEND_TOOLS and isinstance(result.data, dict):
                _send_idempotency_put(
                    current_user.empresa_id, name, args_dict, result.data
                )
    except HTTPException as e:
        result = ToolResult(
            status="forbidden" if e.status_code == 403 else "erro",
            error=str(e.detail),
            code="forbidden" if e.status_code == 403 else "http_error",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
    except Exception as e:
        logger.exception("Erro executando tool %s", name)
        try:
            db.rollback()
        except Exception:
            pass
        result = ToolResult(
            status="erro",
            error=str(e),
            code="exception",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )

    _log(
        db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        sessao_id=sessao_id,
        request_id=request_id,
        tool=name,
        args=args_dict,
        result=result,
    )
    return result


# ── Execução por confirmation_token (bypass do LLM) ───────────────────────
async def execute_pending(
    confirmation_token: str,
    *,
    db: Session,
    current_user: Usuario,
    sessao_id: Optional[str] = None,
    request_id: Optional[str] = None,
    override_args: Optional[dict[str, Any]] = None,
    engine: Optional[str] = None,
) -> ToolResult:
    try:
        ensure_scoped_empresa_id(getattr(current_user, "empresa_id", None))
    except Exception:
        return ToolResult(
            status="forbidden",
            error="Usuário sem escopo de empresa para confirmar ação",
            code="tenant_scope_required",
        )

    """Executa uma ação destrutiva diretamente a partir do token, sem LLM.

    Esse caminho é usado quando o usuário clica "Confirmar" no card do frontend.
    Os args foram persistidos no momento em que o token foi emitido, então
    executamos exatamente a mesma ação proposta — não há risco de o LLM
    reinvocar a tool com argumentos diferentes.
    """
    t0 = time.perf_counter()

    # Rate limit também na confirmação (evita abuso de tokens válidos em loop)
    rl_msg = _check_rate_limit(db, current_user.empresa_id)
    if rl_msg:
        result = ToolResult(
            status="rate_limited",
            error=rl_msg,
            code="rate_limited",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            request_id=request_id,
            tool="?",
            args=None,
            result=result,
        )
        return result

    rec = pop_pending(confirmation_token)
    if rec is None:
        result = ToolResult(
            status="erro",
            error="Token de confirmação inválido ou expirado.",
            code="invalid_token",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            request_id=request_id,
            tool="?",
            args=None,
            result=result,
        )
        return result

    # Isolamento por empresa: o token só vale para a empresa que o emitiu.
    if rec["empresa_id"] != current_user.empresa_id:
        result = ToolResult(
            status="forbidden",
            error="Token pertence a outra empresa.",
            code="forbidden",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            request_id=request_id,
            tool=rec["tool_name"],
            args=None,
            result=result,
        )
        return result

    name = rec["tool_name"]
    args_dict = dict(rec["args_dict"])

    # Aplicar overrides permitidos (allowlist por tool)
    _ALLOWED_OVERRIDES: dict[str, set] = {
        "criar_orcamento": {"cadastrar_materiais_novos"},
    }
    if override_args:
        allowed = _ALLOWED_OVERRIDES.get(name, set())
        for k, v in override_args.items():
            if k in allowed:
                args_dict[k] = v
    args_dict = _normalize_tool_args(name, args_dict)
    if engine:
        meta = (
            args_dict.get("_meta") if isinstance(args_dict.get("_meta"), dict) else {}
        )
        args_dict["_meta"] = {**meta, "engine": str(engine).strip().lower()}

    # Replays de envios críticos também devem ser idempotentes no caminho
    # de confirmação direta por token (evita duplo envio com tokens duplicados).
    if name in _SEND_TOOLS:
        replay = _send_idempotency_get(current_user.empresa_id, name, args_dict)
        if replay is not None:
            payload = dict(replay)
            payload["idempotent_replay"] = True
            result = ToolResult(
                status="ok",
                data=payload,
                code="idempotent_replay",
                latencia_ms=int((time.perf_counter() - t0) * 1000),
                tool_name=name,
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    spec = REGISTRY.get(name)
    if spec is None:
        result = ToolResult(
            status="unknown_tool",
            error=f"tool desconhecida: {name}",
            code="unknown_tool",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
        _log(
            db,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            sessao_id=sessao_id,
            tool=name,
            args=args_dict,
            result=result,
        )
        return result

    if engine:
        policy = get_engine_policy(engine)
        if name not in set(policy.allowed_tools):
            result = ToolResult(
                status="forbidden",
                error=f"A tool '{name}' não é permitida para a engine '{policy.key}'.",
                code="engine_tool_not_allowed",
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    # Revalida permissão (o token não substitui RBAC).
    if spec.permissao_recurso:
        validator = exigir_permissao(spec.permissao_recurso, spec.permissao_acao)
        try:
            validator(usuario=current_user)
        except HTTPException as e:
            result = ToolResult(
                status="forbidden",
                error=str(e.detail),
                code="forbidden",
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
            _log(
                db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                sessao_id=sessao_id,
                request_id=request_id,
                tool=name,
                args=args_dict,
                result=result,
            )
            return result

    try:
        validated = spec.input_model(**args_dict)
        data = await spec.handler(validated, db=db, current_user=current_user)
        if isinstance(data, dict) and data.get("error"):
            result = ToolResult(
                status="erro",
                data=data,
                error=str(data.get("error")),
                code=str(data.get("code") or "handler_error"),
                latencia_ms=int((time.perf_counter() - t0) * 1000),
            )
        else:
            result = ToolResult(
                status="ok",
                data=data if isinstance(data, dict) else {"result": data},
                latencia_ms=int((time.perf_counter() - t0) * 1000),
                tool_name=name,
            )
            if name in _SEND_TOOLS and isinstance(result.data, dict):
                _send_idempotency_put(
                    current_user.empresa_id, name, args_dict, result.data
                )
    except HTTPException as e:
        result = ToolResult(
            status="forbidden" if e.status_code == 403 else "erro",
            error=str(e.detail),
            code="forbidden" if e.status_code == 403 else "http_error",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )
    except Exception as e:
        logger.exception("Erro executando tool %s via execute_pending", name)
        try:
            db.rollback()
        except Exception:
            pass
        result = ToolResult(
            status="erro",
            error=str(e),
            code="exception",
            latencia_ms=int((time.perf_counter() - t0) * 1000),
        )

    _log(
        db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        sessao_id=sessao_id,
        request_id=request_id,
        tool=name,
        args=args_dict,
        result=result,
    )
    return result
