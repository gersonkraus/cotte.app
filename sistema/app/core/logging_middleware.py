"""
Middleware para logging estruturado de requisições HTTP.
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import get_logger, LogContext

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging estruturado de requisições."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processa a requisição com logging.
        
        Args:
            request: Requisição HTTP
            call_next: Próximo middleware/handler
            
        Returns:
            Resposta HTTP
        """
        # Gera ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Obtém informações do usuário (se autenticado)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "id", None)
        
        # Cria contexto de log
        log_context = LogContext(request_id=request_id, user_id=user_id)
        
        # Adiciona contexto à requisição
        request.state.log_context = log_context
        
        # Log da requisição recebida
        logger.info(
            "Request received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "user_id": user_id,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        # Mede tempo de processamento
        start_time = time.time()
        
        try:
            # Processa requisição
            response = await call_next(request)
            
            # Calcula duração
            duration_ms = (time.time() - start_time) * 1000
            
            # Log da resposta
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "user_id": user_id
                }
            )
            
            # Adiciona headers de rastreamento
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as exc:
            # Log de erro
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                exc_info=True
            )
            
            raise
    
    @staticmethod
    def get_request_logger(request: Request) -> LogContext:
        """
        Obtém o contexto de log da requisição atual.
        
        Args:
            request: Requisição HTTP
            
        Returns:
            Contexto de log
        """
        return getattr(request.state, "log_context", None)


# Middleware para injeção de logger em dependências
def get_request_logger(request: Request) -> LogContext:
    """
    Dependência FastAPI para obter contexto de log da requisição.
    
    Args:
        request: Requisição HTTP
        
    Returns:
        Contexto de log
    """
    return LoggingMiddleware.get_request_logger(request)