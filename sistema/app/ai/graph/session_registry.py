"""Session Registry para LangGraph.

Mantém db/current_user acessíveis por thread_id sem serializar no estado do grafo.
TTL padrão de 5 minutos cobre a duração de qualquer requisição SSE.
"""
from __future__ import annotations

import threading
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 300  # 5 minutos


class SessionRegistry:
    _store: dict[str, dict[str, Any]] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def register(
        cls,
        thread_id: str,
        *,
        db: Any,
        current_user: Any,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        """Registra db e current_user para um thread_id com TTL."""
        with cls._lock:
            cls._cleanup_expired()
            cls._store[thread_id] = {
                "db": db,
                "current_user": current_user,
                "expires_at": time.monotonic() + ttl_seconds,
            }
        logger.debug("[SessionRegistry] Sessão registrada: %s", thread_id)

    @classmethod
    def get(cls, thread_id: str) -> Optional[tuple[Any, Any]]:
        """Retorna (db, current_user) ou None se não existir/expirado."""
        with cls._lock:
            entry = cls._store.get(thread_id)
            if entry is None:
                return None
            if time.monotonic() > entry["expires_at"]:
                del cls._store[thread_id]
                logger.debug("[SessionRegistry] Sessão expirada: %s", thread_id)
                return None
            return entry["db"], entry["current_user"]

    @classmethod
    def _cleanup_expired(cls) -> None:
        now = time.monotonic()
        expired = [k for k, v in cls._store.items() if now > v["expires_at"]]
        for k in expired:
            del cls._store[k]
