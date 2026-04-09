import logging
import random
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.core.config import settings

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

class OTPService:
    """
    Serviço para gerenciar códigos OTP (One-Time Password) para aceite de orçamentos.
    Usa Redis se disponível, senão cai para memória local.
    """
    
    TTL_SECONDS = 600  # 10 minutos

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mem_cache: Dict[str, dict] = {}  # {key: {"code": str, "expires_at": datetime}}
        self._redis_client = self._build_redis_client()

    def _build_redis_client(self):
        if not redis or not (settings.REDIS_URL or "").strip():
            return None
        try:
            client = redis.from_url(
                settings.REDIS_URL.strip(),
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            client.ping()
            return client
        except redis.RedisError as exc:
            logger.warning("Redis indisponível para OTPService, usando memória local: %s", exc)
            return None

    def _get_key(self, link_publico: str) -> str:
        return f"otp_aceite:{link_publico}"

    def gerar_codigo(self, link_publico: str) -> str:
        """Gera um código de 6 dígitos, salva e retorna."""
        codigo = f"{random.randint(100000, 999999)}"
        key = self._get_key(link_publico)
        
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.TTL_SECONDS)
        
        if self._redis_client:
            try:
                self._redis_client.setex(key, self.TTL_SECONDS, codigo)
                return codigo
            except redis.RedisError as exc:
                logger.warning("Falha ao salvar OTP no Redis: %s", exc)
        
        # Fallback para memória
        with self._lock:
            self._mem_cache[key] = {
                "code": codigo,
                "expires_at": expires_at
            }
            # Limpeza básica de expirados
            now = datetime.now(timezone.utc)
            self._mem_cache = {k: v for k, v in self._mem_cache.items() if v["expires_at"] > now}
            
        return codigo

    def validar_codigo(self, link_publico: str, codigo_informado: str) -> bool:
        """Valida se o código informado é o correto e não expirou. Remove após validar."""
        key = self._get_key(link_publico)
        
        if self._redis_client:
            try:
                codigo_salvo = self._redis_client.get(key)
                if codigo_salvo and codigo_salvo == str(codigo_informado):
                    self._redis_client.delete(key)
                    return True
                return False
            except redis.RedisError as exc:
                logger.warning("Falha ao validar OTP no Redis: %s", exc)
        
        # Fallback para memória
        with self._lock:
            data = self._mem_cache.get(key)
            if not data:
                return False
            
            now = datetime.now(timezone.utc)
            if data["expires_at"] < now:
                self._mem_cache.pop(key, None)
                return False
            
            if data["code"] == str(codigo_informado):
                self._mem_cache.pop(key, None)
                return True
                
        return False

otp_service = OTPService()
