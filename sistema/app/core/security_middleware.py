"""
Middleware de segurança para bloquear requisições suspeitas e ataques comuns.
Inclui proteção contra scanners de WordPress, paths administrativos expostos, etc.
"""
import re
import time
from typing import Callable, Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware de segurança que:
    1. Bloqueia caminhos suspeitos (WordPress, painéis administrativos expostos)
    2. Implementa rate limiting básico com whitelist
    3. Bloqueia user agents maliciosos conhecidos
    4. Registra tentativas de ataque
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Padrões de caminhos suspeitos para bloquear
        self.suspicious_paths = [
            # WordPress paths
            r'^/wp-',
            r'^/wordpress',
            r'^/wp\.php',
            r'^/wp-admin',
            r'^/wp-content',
            r'^/wp-includes',
            r'^/xmlrpc\.php',
            r'^/wp-cron\.php',
            r'^/wp-login\.php',
            
            # Painéis administrativos comuns (mais específicos para não bloquear API)
            r'^/admin/login',
            r'^/admin/config',
            r'^/admin/settings',
            r'^/admin/setup',
            r'^/admin/install',
            r'^/administrator',
            r'^/backend',
            r'^/cpanel',
            r'^/phpmyadmin',
            r'^/mysql',
            r'^/myadmin',
            r'^/pma',
            
            # Configurações e arquivos sensíveis
            r'^/\.env',
            r'^/\.git',
            r'^/\.svn',
            r'^/\.htaccess',
            r'^/\.htpasswd',
            r'^/config\.',
            r'^/configuration\.',
            r'^/setup\.',
            r'^/install\.',
            
            # Backups e arquivos de log
            r'^/backup',
            r'^/dump',
            r'^/sql',
            r'^/database',
            r'^/\.bak',
            r'^/\.old',
            r'^/\.log',
            
            # Shells e webshells comuns
            r'^/shell\.',
            r'^/cmd\.',
            r'^/c99\.',
            r'^/r57\.',
            r'^/wso\.',
        ]
        
        # Compilar padrões regex
        self.suspicious_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.suspicious_paths]
        
        # User agents maliciosos conhecidos (apenas os principais)
        self.malicious_user_agents = [
            'sqlmap', 'nikto', 'nessus', 'acunetix', 'netsparker', 'w3af',
            'dirbuster', 'gobuster', 'wfuzz', 'burpsuite', 'zap', 'arachni',
            'skipfish', 'wpscan', 'joomscan', 'drupalscan', 'whatweb',
            'nmap', 'masscan', 'hydra', 'medusa', 'patator', 'metasploit',
            'havij', 'pangolin', 'sqlninja', 'sqlsus', 'sqid', 'bsqlbf',
        ]
        
        # Rate limiting: armazena requisições por IP
        self.request_counts: Dict[str, List[float]] = defaultdict(list)
        self.rate_limit_window = settings.SECURITY_RATE_LIMIT_WINDOW_SECONDS
        self.rate_limit_max = settings.SECURITY_RATE_LIMIT_MAX
        
        # Whitelist de IPs (localhost por padrão)
        self.whitelist = [ip.strip() for ip in settings.SECURITY_RATE_LIMIT_WHITELIST.split(",")]
        
        # IPs bloqueados temporariamente
        self.blocked_ips: Dict[str, datetime] = {}
        self.block_duration = 300  # 5 minutos

    @staticmethod
    def _is_rate_limit_exempt_path(path: str) -> bool:
        """
        Assets do frontend não devem consumir o contador: um carregamento de página
        dispara dezenas de GET em /app e /static e esgotava o limite global (429).
        O rate limit continua valendo para /api, HTML público, etc.
        """
        if path == "/static" or path.startswith("/static/"):
            return True
        if path == "/app" or path.startswith("/app/"):
            return True
        if path.startswith("/favicon"):
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processa a requisição com verificações de segurança.
        """
        client_ip = self._get_real_ip(request)
        path = request.url.path
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Verifica se IP está na whitelist (pula todas as verificações de bloqueio/rate limit)
        if client_ip in self.whitelist:
            return await call_next(request)
        
        # Verifica se IP está bloqueado
        if self._is_ip_blocked(client_ip):
            logger.warning(
                "Blocked request from blocked IP",
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "user_agent": user_agent,
                    "reason": "IP temporarily blocked"
                }
            )
            # Re-lança 429 para IPs bloqueados
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."}
            )
        
        # Rate limiting (exceto assets estáticos — ver _is_rate_limit_exempt_path)
        if not self._is_rate_limit_exempt_path(path):
            if not self._check_rate_limit(client_ip):
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_ip": client_ip,
                        "path": path,
                        "user_agent": user_agent,
                        "reason": "Rate limit exceeded",
                    },
                )
                self._block_ip(client_ip)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests. Please try again later."},
                )
        
        # Verifica caminhos suspeitos
        if self._is_suspicious_path(path):
            logger.warning(
                "Blocked suspicious path access",
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "user_agent": user_agent,
                    "reason": "Suspicious path pattern"
                }
            )
            # Retorna 404 em vez de 403 para não dar informações
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"}
            )
        
        # Verifica user agent malicioso
        if self._is_malicious_user_agent(user_agent):
            logger.warning(
                "Blocked malicious user agent",
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "user_agent": user_agent,
                    "reason": "Malicious user agent detected"
                }
            )
            self._block_ip(client_ip)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access Forbidden"}
            )
        
        # Processa a requisição normalmente
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Re-lança exceções HTTP
            raise
        except Exception as exc:
            # Log de erro interno
            logger.error(
                "Internal server error",
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                exc_info=True
            )
            raise
    
    def _get_real_ip(self, request: Request) -> str:
        """Extrai o IP real do cliente, respeitando headers de proxy (Railway, CloudFlare)."""
        for header in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
            val = request.headers.get(header)
            if val:
                return val.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_suspicious_path(self, path: str) -> bool:
        """Verifica se o caminho corresponde a padrões suspeitos."""
        for pattern in self.suspicious_patterns:
            if pattern.search(path):
                return True
        return False
    
    def _is_malicious_user_agent(self, user_agent: str) -> bool:
        """Verifica se o user agent é malicioso conhecido."""
        if not user_agent:
            return False
        
        user_agent_lower = user_agent.lower()
        for malicious_ua in self.malicious_user_agents:
            if malicious_ua in user_agent_lower:
                return True
        return False
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Verifica rate limiting para um IP."""
        now = time.time()
        
        # Limpa requisições antigas
        self.request_counts[client_ip] = [
            timestamp for timestamp in self.request_counts[client_ip]
            if now - timestamp < self.rate_limit_window
        ]
        
        # Adiciona requisição atual
        self.request_counts[client_ip].append(now)
        
        # Verifica se excedeu o limite
        return len(self.request_counts[client_ip]) <= self.rate_limit_max
    
    def _block_ip(self, client_ip: str) -> None:
        """Bloqueia um IP temporariamente."""
        self.blocked_ips[client_ip] = datetime.now()
    
    def _is_ip_blocked(self, client_ip: str) -> bool:
        """Verifica se um IP está bloqueado."""
        if client_ip not in self.blocked_ips:
            return False
        
        block_time = self.blocked_ips[client_ip]
        if datetime.now() - block_time > timedelta(seconds=self.block_duration):
            # Remove bloqueio expirado
            del self.blocked_ips[client_ip]
            return False
        
        return True
    
    def cleanup_old_data(self):
        """Limpa dados antigos (chamado periodicamente)."""
        now = time.time()
        old_time = now - self.rate_limit_window
        
        # Limpa contagens de rate limiting
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                timestamp for timestamp in self.request_counts[ip]
                if timestamp > old_time
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]
        
        # Limpa IPs bloqueados expirados
        now_dt = datetime.now()
        for ip in list(self.blocked_ips.keys()):
            if now_dt - self.blocked_ips[ip] > timedelta(seconds=self.block_duration):
                del self.blocked_ips[ip]