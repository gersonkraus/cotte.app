"""
Exceções personalizadas para a aplicação.
Fornece erros específicos de domínio com mensagens claras.
"""
from fastapi import HTTPException, status
from typing import Optional, Any


class AppException(HTTPException):
    """Exceção base da aplicação."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        extra: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


# ── Exceções de Domínio ─────────────────────────────────────────────────────

class NotFoundException(AppException):
    """Recurso não encontrado."""
    
    def __init__(self, resource: str, identifier: Any, detail: Optional[str] = None):
        if not detail:
            detail = f"{resource} com identificador '{identifier}' não encontrado"
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND"
        )


class ValidationException(AppException):
    """Erro de validação de dados."""
    
    def __init__(self, detail: str, field: Optional[str] = None):
        extra = {"field": field} if field else {}
        
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="VALIDATION_ERROR",
            extra=extra
        )


class BusinessRuleException(AppException):
    """Violação de regra de negócio."""
    
    def __init__(self, detail: str, rule: Optional[str] = None):
        extra = {"rule": rule} if rule else {}
        
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="BUSINESS_RULE_VIOLATION",
            extra=extra
        )


class UnauthorizedException(AppException):
    """Acesso não autorizado."""
    
    def __init__(self, detail: str = "Acesso não autorizado"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED"
        )


class ForbiddenException(AppException):
    """Acesso proibido."""
    
    def __init__(self, detail: str = "Acesso proibido"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class ConflictException(AppException):
    """Conflito de dados (ex: registro duplicado)."""
    
    def __init__(self, detail: str, resource: Optional[str] = None):
        extra = {"resource": resource} if resource else {}
        
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT",
            extra=extra
        )


class RateLimitException(AppException):
    """Limite de requisições excedido."""
    
    def __init__(self, detail: str = "Limite de requisições excedido"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED"
        )


# ── Exceções Específicas do Domínio ────────────────────────────────────────

class OrcamentoNotFoundException(NotFoundException):
    """Orçamento não encontrado."""
    
    def __init__(self, orcamento_id: int):
        super().__init__(
            resource="Orçamento",
            identifier=orcamento_id,
            detail=f"Orçamento com ID {orcamento_id} não encontrado"
        )


class ClienteNotFoundException(NotFoundException):
    """Cliente não encontrado."""
    
    def __init__(self, cliente_id: int):
        super().__init__(
            resource="Cliente",
            identifier=cliente_id,
            detail=f"Cliente com ID {cliente_id} não encontrado"
        )


class LimiteOrcamentosExcedidoException(BusinessRuleException):
    """Limite de orçamentos do plano excedido."""
    
    def __init__(self, limite: int):
        super().__init__(
            detail=f"Limite de {limite} orçamentos excedido para o plano atual",
            rule="LIMITE_ORCAMENTOS"
        )


class DescontoInvalidoException(ValidationException):
    """Desconto inválido aplicado."""
    
    def __init__(self, motivo: str, max_percent: Optional[int] = None):
        detail = f"Desconto inválido: {motivo}"
        if max_percent:
            detail += f" (máximo permitido: {max_percent}%)"
        
        super().__init__(detail=detail, field="desconto")


class StatusTransicaoInvalidaException(BusinessRuleException):
    """Transição de status inválida para orçamento."""
    
    def __init__(self, status_atual: str, novo_status: str):
        super().__init__(
            detail=f"Transição de status inválida: {status_atual} -> {novo_status}",
            rule="STATUS_TRANSICAO"
        )


class ClienteDuplicadoException(ConflictException):
    """Cliente duplicado (telefone ou email já existente)."""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            resource="Cliente"
        )


class EmpresaNotFoundException(NotFoundException):
    """Empresa não encontrada."""
    
    def __init__(self, empresa_id: int):
        super().__init__(
            resource="Empresa",
            identifier=empresa_id,
            detail=f"Empresa com ID {empresa_id} não encontrada"
        )


# ── Utilitários ───────────────────────────────────────────────────────────

def handle_app_exception(exc: AppException):
    """Handler padrão para exceções da aplicação."""
    return {
        "error": {
            "code": exc.error_code or "UNKNOWN_ERROR",
            "message": exc.detail,
            "details": exc.extra
        }
    }


def register_exception_handlers(app):
    """
    Registra handlers de exceção na aplicação FastAPI.
    
    Args:
        app: Instância do FastAPI
    """
    from fastapi.responses import JSONResponse
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=handle_app_exception(exc)
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "details": {}
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc: Exception):
        # Log do erro interno
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro interno não tratado: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Erro interno do servidor",
                    "details": {}
                }
            }
        )