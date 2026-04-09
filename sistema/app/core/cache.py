"""
Sistema de cache para repositórios e serviços.
Implementa cache com Redis (fallback: memória) para funcionar entre múltiplos workers.
"""

import time
import hashlib
import json
import logging
from typing import Any, Callable, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)

KEY_PREFIX = "cotte:"


def _build_redis_client():
    """Cria cliente Redis se REDIS_URL estiver configurado."""
    try:
        import redis
        from app.core.config import settings

        url = (settings.REDIS_URL or "").strip()
        if not url:
            return None
        client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        logger.info("Redis conectado para cache")
        return client
    except ImportError:
        logger.warning("redis package não instalado, usando cache em memória")
        return None
    except Exception as e:
        logger.warning(f"Redis indisponível, usando cache em memória: {e}")
        return None


class CacheManager:
    """Gerenciador de cache com Redis (fallback: memória)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._redis = _build_redis_client()
            cls._instance._local_cache: Dict[str, Dict[str, Any]] = {}
            cls._instance._default_ttl = 300
        return cls._instance

    def _prefix_key(self, key: str) -> str:
        return f"{KEY_PREFIX}{key}"

    def get(self, key: str) -> Optional[Any]:
        """Obtém um valor do cache."""
        prefixed = self._prefix_key(key)

        if self._redis:
            try:
                data = self._redis.get(prefixed)
                if data is not None:
                    logger.debug(f"Cache hit (redis) para chave: {key[:50]}...")
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Erro ao ler Redis: {e}")

        # Fallback memória
        item = self._local_cache.get(prefixed)
        if item and time.time() - item["timestamp"] <= item.get(
            "ttl", self._default_ttl
        ):
            logger.debug(f"Cache hit (memory) para chave: {key[:50]}...")
            return item["value"]

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Armazena um valor no cache."""
        prefixed = self._prefix_key(key)
        ttl = ttl or self._default_ttl

        if self._redis:
            try:
                self._redis.setex(prefixed, ttl, json.dumps(value, default=str))
                logger.debug(f"Cache set (redis) para chave: {key[:50]}...")
                return
            except Exception as e:
                logger.warning(f"Erro ao escrever Redis: {e}")

        # Fallback memória
        self._local_cache[prefixed] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl,
        }
        logger.debug(f"Cache set (memory) para chave: {key[:50]}...")

    def delete(self, key: str):
        """Remove um item do cache."""
        prefixed = self._prefix_key(key)

        if self._redis:
            try:
                self._redis.delete(prefixed)
            except Exception as e:
                logger.warning(f"Erro ao deletar no Redis: {e}")

        self._local_cache.pop(prefixed, None)
        logger.debug(f"Cache delete para chave: {key[:50]}...")

    def clear(self):
        """Limpa todo o cache."""
        if self._redis:
            try:
                for key in self._redis.scan_iter(f"{KEY_PREFIX}*"):
                    self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Erro ao limpar Redis: {e}")

        self._local_cache.clear()
        logger.info("Cache limpo")

    def invalidate_pattern(self, pattern: str):
        """Invalida todas as chaves que correspondem a um padrão."""
        if self._redis:
            try:
                for key in self._redis.scan_iter(f"{KEY_PREFIX}*{pattern}*"):
                    self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Erro ao invalidar pattern no Redis: {e}")

        # Invalidar local
        prefixed_pattern = f"{KEY_PREFIX}*{pattern}*"
        keys_to_delete = [k for k in self._local_cache if pattern in k]
        for k in keys_to_delete:
            del self._local_cache[k]

        if keys_to_delete:
            logger.debug(
                f"Cache invalidado (memory) para padrão: {pattern}, {len(keys_to_delete)} chaves removidas"
            )

    def stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do cache."""
        if self._redis:
            try:
                info = self._redis.info("memory")
                keys_count = len(list(self._redis.scan_iter(f"{KEY_PREFIX}*")))
                return {
                    "backend": "redis",
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "keys_count": keys_count,
                }
            except Exception as e:
                logger.warning(f"Erro ao obter stats do Redis: {e}")

        # Fallback memória
        total = len(self._local_cache)
        expired = sum(
            1
            for item in self._local_cache.values()
            if time.time() - item["timestamp"] > item.get("ttl", self._default_ttl)
        )
        return {
            "backend": "memory",
            "total_items": total,
            "expired_items": expired,
            "valid_items": total - expired,
        }

    @property
    def backend(self) -> str:
        """Retorna o backend atual: 'redis' ou 'memory'."""
        return "redis" if self._redis else "memory"


# Instância global do gerenciador de cache
cache_manager = CacheManager()


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Gera uma chave de cache única baseada nos argumentos."""
    args_str = json.dumps(args, default=str, sort_keys=True)
    kwargs_str = json.dumps(kwargs, default=str, sort_keys=True)
    content = f"{prefix}:{args_str}:{kwargs_str}"
    return f"{prefix}:{hashlib.md5(content.encode()).hexdigest()}"


def cached(ttl: int = 300, prefix: Optional[str] = None):
    """Decorador para cache de métodos."""

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_prefix = prefix or f"{func.__module__}.{func.__qualname__}"
            cache_key = generate_cache_key(cache_prefix, *args, **kwargs)

            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_prefix = prefix or f"{func.__module__}.{func.__qualname__}"
            cache_key = generate_cache_key(cache_prefix, *args, **kwargs)

            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)

            return result

        if func.__code__.co_flags & 0x80:
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache_for_model(model_name: str, model_id: Optional[int] = None):
    """Invalida cache para um modelo específico."""
    if model_id:
        pattern = f"{model_name}:id:{model_id}"
    else:
        pattern = f"{model_name}:"

    cache_manager.invalidate_pattern(pattern)
    logger.info(f"Cache invalidado para {pattern}")


# Cache para configurações frequentes
@cached(ttl=600)
async def get_cached_config(db, empresa_id: int, config_key: str) -> Optional[Any]:
    """Obtém configuração do banco com cache."""
    from app.models.models import ConfiguracaoFinanceira
    from sqlalchemy import select

    stmt = select(ConfiguracaoFinanceira).where(
        ConfiguracaoFinanceira.empresa_id == empresa_id
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config and hasattr(config, config_key):
        return getattr(config, config_key)

    return None
