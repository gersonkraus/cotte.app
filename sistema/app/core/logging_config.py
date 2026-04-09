"""
Configuração de logging estruturado para a aplicação.
Fornece logs consistentes em todas as camadas com contexto rico.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class StructuredLogger(logging.Logger):
    """Logger personalizado com métodos para logs estruturados."""
    
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
    
    def _structured_log(
        self,
        level: int,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[bool] = None,
        stack_info: bool = False
    ):
        """
        Log estruturado com contexto adicional.
        
        Args:
            level: Nível do log
            msg: Mensagem do log
            extra: Dicionário com contexto adicional
            exc_info: Informações de exceção
            stack_info: Informações de stack trace
        """
        if extra is None:
            extra = {}
        
        # Adiciona contexto padrão
        structured_extra = {
            "timestamp": datetime.utcnow().isoformat(),
            "logger": self.name,
            "message": msg,
            **extra
        }
        
        super().log(level, msg, extra=structured_extra, exc_info=exc_info, stack_info=stack_info)
    
    def info_structured(self, msg: str, **kwargs):
        """Log de informação estruturado."""
        self._structured_log(logging.INFO, msg, kwargs)
    
    def warning_structured(self, msg: str, **kwargs):
        """Log de aviso estruturado."""
        self._structured_log(logging.WARNING, msg, kwargs)
    
    def error_structured(self, msg: str, **kwargs):
        """Log de erro estruturado."""
        self._structured_log(logging.ERROR, msg, kwargs)
    
    def debug_structured(self, msg: str, **kwargs):
        """Log de debug estruturado."""
        self._structured_log(logging.DEBUG, msg, kwargs)
    
    def critical_structured(self, msg: str, **kwargs):
        """Log crítico estruturado."""
        self._structured_log(logging.CRITICAL, msg, kwargs)
    
    def audit(self, action: str, resource: str, user_id: Optional[int] = None, **kwargs):
        """
        Log de auditoria para ações importantes.
        
        Args:
            action: Ação realizada (ex: "create", "update", "delete")
            resource: Recurso afetado (ex: "orcamento", "cliente")
            user_id: ID do usuário que realizou a ação
            **kwargs: Contexto adicional
        """
        audit_context = {
            "audit_action": action,
            "audit_resource": resource,
            "audit_user_id": user_id,
            **kwargs
        }
        self.info_structured(f"Audit: {action} on {resource}", **audit_context)
    
    def performance(self, operation: str, duration_ms: float, **kwargs):
        """
        Log de performance para operações.
        
        Args:
            operation: Nome da operação
            duration_ms: Duração em milissegundos
            **kwargs: Contexto adicional
        """
        perf_context = {
            "performance_operation": operation,
            "performance_duration_ms": duration_ms,
            **kwargs
        }
        self.info_structured(f"Performance: {operation} took {duration_ms:.2f}ms", **perf_context)


class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    """Formatter JSON para logs estruturados."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fmt="%(timestamp)s %(level)s %(name)s %(message)s %(extra)s",
            **kwargs
        )
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Garante campos padrão
        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.utcnow().isoformat()
        
        if not log_record.get("level"):
            log_record["level"] = record.levelname
        
        if not log_record.get("name"):
            log_record["name"] = record.name
        
        # Extrai contexto estruturado do extra
        if hasattr(record, "extra"):
            for key, value in record.extra.items():
                log_record[key] = value


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None
):
    """
    Configura o sistema de logging da aplicação.
    
    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Usar formato JSON para logs
        log_file: Caminho para arquivo de log (opcional)
    """
    # Configura nível
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Remove handlers existentes
    logging.getLogger().handlers.clear()
    
    # Configura logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if json_format:
        formatter = StructuredJsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Handler para arquivo (se especificado)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Substitui a classe Logger padrão pela nossa
    logging.setLoggerClass(StructuredLogger)
    
    # Configura loggers específicos
    configure_module_loggers()
    
    logging.info(f"Logging configurado - nível: {level}, formato: {'JSON' if json_format else 'TEXT'}")


def configure_module_loggers():
    """Configura níveis específicos para módulos."""
    # Loggers para camadas da aplicação
    module_levels = {
        "app.api": logging.INFO,
        "app.routers": logging.INFO,
        "app.services": logging.INFO,
        "app.repositories": logging.DEBUG,  # Mais detalhado para debug de queries
        "app.core": logging.INFO,
        "sqlalchemy.engine": logging.WARNING,  # Reduz log do SQLAlchemy
    }
    
    for module, level in module_levels.items():
        logging.getLogger(module).setLevel(level)


def get_logger(name: str) -> StructuredLogger:
    """
    Obtém um logger estruturado.
    
    Args:
        name: Nome do logger
        
    Returns:
        Instância de StructuredLogger
    """
    return logging.getLogger(name)


# Contexto de log para injeção em dependências
class LogContext:
    """Contexto de log para rastreamento de requisições."""
    
    def __init__(self, request_id: str, user_id: Optional[int] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.start_time = datetime.utcnow()
    
    def get_context_dict(self) -> Dict[str, Any]:
        """Retorna dicionário com contexto para logs."""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "duration_ms": (datetime.utcnow() - self.start_time).total_seconds() * 1000
        }


# Logger padrão para uso rápido
logger = get_logger(__name__)