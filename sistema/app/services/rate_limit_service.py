from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import threading

from app.core.config import settings

try:
    import redis
except (ImportError, ModuleNotFoundError):  # pragma: no cover - fallback sem dependência
    redis = None


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class ResetPasswordRateLimiter:
    """
    Rate limit para recuperação de senha.
    Prioriza Redis (quando configurado) e cai para memória local em caso de indisponibilidade.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mem_attempts = defaultdict(list)      # {key: [timestamps]}
        self._mem_blocked_until = {}                # {key: timestamp}
        self._redis_client = self._build_redis_client()

    def _build_redis_client(self):
        if not redis or not (settings.REDIS_URL or "").strip():
            return None
        try:
            client = redis.from_url(
                settings.REDIS_URL.strip(),
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            client.ping()
            return client
        except redis.RedisError as exc:
            logging.warning("Redis indisponível para rate limit, usando memória local: %s", exc)
            return None

    @staticmethod
    def _agora_ts() -> float:
        return datetime.now(timezone.utc).timestamp()

    def _check_key_mem(self, key: str, max_hits: int, window_seconds: int, block_seconds: int) -> RateLimitResult:
        now = self._agora_ts()
        with self._lock:
            blocked_until = self._mem_blocked_until.get(key, 0)
            if blocked_until > now:
                return RateLimitResult(False, int(blocked_until - now))

            if blocked_until:
                self._mem_blocked_until.pop(key, None)

            window_start = now - window_seconds
            attempts = [ts for ts in self._mem_attempts[key] if ts >= window_start]
            attempts.append(now)
            self._mem_attempts[key] = attempts

            if len(attempts) > max_hits:
                self._mem_blocked_until[key] = now + block_seconds
                return RateLimitResult(False, block_seconds)

        return RateLimitResult(True, 0)

    def _check_key_redis(self, key: str, max_hits: int, window_seconds: int, block_seconds: int) -> RateLimitResult:
        if not self._redis_client:
            return self._check_key_mem(key, max_hits, window_seconds, block_seconds)

        counter_key = f"rl:cnt:{key}"
        block_key = f"rl:blk:{key}"
        try:
            ttl_block = self._redis_client.ttl(block_key)
            if ttl_block and ttl_block > 0:
                return RateLimitResult(False, int(ttl_block))

            count = self._redis_client.incr(counter_key)
            if count == 1:
                self._redis_client.expire(counter_key, window_seconds)

            if count > max_hits:
                self._redis_client.setex(block_key, block_seconds, "1")
                return RateLimitResult(False, block_seconds)
        except redis.RedisError as exc:
            logging.warning("Falha no Redis rate limit, fallback memória: %s", exc)
            return self._check_key_mem(key, max_hits, window_seconds, block_seconds)

        return RateLimitResult(True, 0)

    def check_reset_limit(self, ip: str, email: str) -> RateLimitResult:
        window = max(60, int(settings.RESET_RATE_LIMIT_WINDOW_SECONDS or 900))
        max_ip = max(1, int(settings.RESET_RATE_LIMIT_MAX_PER_IP or 10))
        max_email = max(1, int(settings.RESET_RATE_LIMIT_MAX_PER_EMAIL or 5))
        block_seconds = max(60, int(settings.RESET_RATE_LIMIT_BLOCK_SECONDS or 1800))

        email_norm = (email or "").strip().lower()
        ip_key = f"reset:ip:{ip or 'unknown'}"
        email_key = f"reset:email:{email_norm or 'none'}"

        ip_result = self._check_key_redis(ip_key, max_ip, window, block_seconds)
        if not ip_result.allowed:
            return ip_result

        email_result = self._check_key_redis(email_key, max_email, window, block_seconds)
        if not email_result.allowed:
            return email_result

        return RateLimitResult(True, 0)


reset_password_rate_limiter = ResetPasswordRateLimiter()


class PublicEndpointRateLimiter:
    """
    Rate limit para endpoints públicos sem autenticação (aceitar/recusar/ajuste).
    Limita por chave composta (ação + link + IP): 10 tentativas/minuto,
    bloqueio de 5 minutos após exceder.
    Usa Redis se disponível, senão memória local.
    """

    MAX_CALLS = 10
    WINDOW_SEC = 60
    BLOCK_SEC = 300

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mem_attempts: dict[str, list] = defaultdict(list)
        self._mem_blocked_until: dict[str, float] = {}
        self._redis_client = self._build_redis_client()

    def _build_redis_client(self):
        if not redis or not (settings.REDIS_URL or "").strip():
            return None
        try:
            client = redis.from_url(
                settings.REDIS_URL.strip(),
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            client.ping()
            return client
        except redis.RedisError as exc:
            logging.warning("Redis indisponível para rate limit público, usando memória: %s", exc)
            return None

    @staticmethod
    def _now() -> float:
        return datetime.now(timezone.utc).timestamp()

    def _check_mem(self, key: str) -> RateLimitResult:
        now = self._now()
        with self._lock:
            blocked_until = self._mem_blocked_until.get(key, 0)
            if blocked_until > now:
                return RateLimitResult(False, int(blocked_until - now))
            if blocked_until:
                self._mem_blocked_until.pop(key, None)

            window_start = now - self.WINDOW_SEC
            attempts = [t for t in self._mem_attempts[key] if t >= window_start]
            attempts.append(now)
            self._mem_attempts[key] = attempts

            if len(attempts) > self.MAX_CALLS:
                self._mem_blocked_until[key] = now + self.BLOCK_SEC
                return RateLimitResult(False, self.BLOCK_SEC)
        return RateLimitResult(True, 0)

    def _check_redis(self, key: str) -> RateLimitResult:
        if not self._redis_client:
            return self._check_mem(key)
        counter_key = f"pub:cnt:{key}"
        block_key = f"pub:blk:{key}"
        try:
            ttl_block = self._redis_client.ttl(block_key)
            if ttl_block and ttl_block > 0:
                return RateLimitResult(False, int(ttl_block))
            count = self._redis_client.incr(counter_key)
            if count == 1:
                self._redis_client.expire(counter_key, self.WINDOW_SEC)
            if count > self.MAX_CALLS:
                self._redis_client.setex(block_key, self.BLOCK_SEC, "1")
                return RateLimitResult(False, self.BLOCK_SEC)
        except redis.RedisError as exc:
            logging.warning("Falha no Redis (rate limit público), fallback memória: %s", exc)
            return self._check_mem(key)
        return RateLimitResult(True, 0)

    def check(self, key: str) -> RateLimitResult:
        return self._check_redis(key)


public_endpoint_rate_limiter = PublicEndpointRateLimiter()


class WebhookRateLimiter(PublicEndpointRateLimiter):
    """
    Rate limit para o webhook WhatsApp (POST /whatsapp/webhook).
    Limite mais generoso pois mensagens legítimas podem chegar em rajadas.
    30 requisições/minuto por IP; bloqueio de 2 minutos.
    """

    MAX_CALLS = 30
    WINDOW_SEC = 60
    BLOCK_SEC = 120

    def _check_mem(self, key: str) -> RateLimitResult:
        now = self._now()
        with self._lock:
            blocked_until = self._mem_blocked_until.get(key, 0)
            if blocked_until > now:
                return RateLimitResult(False, int(blocked_until - now))
            if blocked_until:
                self._mem_blocked_until.pop(key, None)

            window_start = now - self.WINDOW_SEC
            attempts = [t for t in self._mem_attempts[key] if t >= window_start]
            attempts.append(now)
            self._mem_attempts[key] = attempts

            if len(attempts) > self.MAX_CALLS:
                self._mem_blocked_until[key] = now + self.BLOCK_SEC
                return RateLimitResult(False, self.BLOCK_SEC)
        return RateLimitResult(True, 0)

    def _check_redis(self, key: str) -> RateLimitResult:
        if not self._redis_client:
            return self._check_mem(key)
        counter_key = f"wh:cnt:{key}"
        block_key = f"wh:blk:{key}"
        try:
            ttl_block = self._redis_client.ttl(block_key)
            if ttl_block and ttl_block > 0:
                return RateLimitResult(False, int(ttl_block))
            count = self._redis_client.incr(counter_key)
            if count == 1:
                self._redis_client.expire(counter_key, self.WINDOW_SEC)
            if count > self.MAX_CALLS:
                self._redis_client.setex(block_key, self.BLOCK_SEC, "1")
                return RateLimitResult(False, self.BLOCK_SEC)
        except redis.RedisError as exc:
            logging.warning("Falha no Redis (rate limit webhook), fallback memória: %s", exc)
            return self._check_mem(key)
        return RateLimitResult(True, 0)


class IaInterpretarRateLimiter(PublicEndpointRateLimiter):
    """
    Rate limit para POST /whatsapp/interpretar (endpoint de teste sem autenticação).
    Muito restritivo: 5 requisições/minuto por IP; bloqueio de 10 minutos.
    """

    MAX_CALLS = 5
    WINDOW_SEC = 60
    BLOCK_SEC = 600

    def _check_mem(self, key: str) -> RateLimitResult:
        now = self._now()
        with self._lock:
            blocked_until = self._mem_blocked_until.get(key, 0)
            if blocked_until > now:
                return RateLimitResult(False, int(blocked_until - now))
            if blocked_until:
                self._mem_blocked_until.pop(key, None)

            window_start = now - self.WINDOW_SEC
            attempts = [t for t in self._mem_attempts[key] if t >= window_start]
            attempts.append(now)
            self._mem_attempts[key] = attempts

            if len(attempts) > self.MAX_CALLS:
                self._mem_blocked_until[key] = now + self.BLOCK_SEC
                return RateLimitResult(False, self.BLOCK_SEC)
        return RateLimitResult(True, 0)

    def _check_redis(self, key: str) -> RateLimitResult:
        if not self._redis_client:
            return self._check_mem(key)
        counter_key = f"ia:cnt:{key}"
        block_key = f"ia:blk:{key}"
        try:
            ttl_block = self._redis_client.ttl(block_key)
            if ttl_block and ttl_block > 0:
                return RateLimitResult(False, int(ttl_block))
            count = self._redis_client.incr(counter_key)
            if count == 1:
                self._redis_client.expire(counter_key, self.WINDOW_SEC)
            if count > self.MAX_CALLS:
                self._redis_client.setex(block_key, self.BLOCK_SEC, "1")
                return RateLimitResult(False, self.BLOCK_SEC)
        except redis.RedisError as exc:
            logging.warning("Falha no Redis (rate limit IA), fallback memória: %s", exc)
            return self._check_mem(key)
        return RateLimitResult(True, 0)


webhook_rate_limiter = WebhookRateLimiter()
ia_interpretar_rate_limiter = IaInterpretarRateLimiter()
