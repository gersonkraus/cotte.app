from pydantic_settings import BaseSettings
from typing import Optional
import subprocess


import time


def _compute_version() -> str:
    """Usa o hash curto do último commit git como versão. Fallback: 'dev'."""
    try:
        # Se estiver em desenvolvimento, usa timestamp para forçar cache bust a cada reinício
        import os

        version_env = os.getenv("RAILWAY_GIT_COMMIT_SHA")
        if version_env:
            return version_env[:7]

        if os.getenv("ENVIRONMENT") == "development":
            return str(int(time.time()))

        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except Exception:
        return "dev"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "COTTE"
    APP_URL: str = "https://cotte.app"
    ENVIRONMENT: str = "development"
    # Versão usada no cache-busting de assets JS/CSS.
    # Gerada automaticamente a partir do hash do commit; pode ser sobrescrita via env var APP_VERSION.
    APP_VERSION: str = _compute_version()
    CORS_ALLOWED_ORIGINS: str = "https://cotte.app,https://www.cotte.app,http://localhost:8000,http://127.0.0.1:8000"

    # Banco de dados
    DATABASE_URL: str

    # Segurança
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 dias

    # Presença (get_usuario_atual): evita UPDATE+COMMIT em toda requisição autenticada
    ULTIMA_ATIVIDADE_COMMIT_INTERVAL_SECONDS: int = 120

    # Anthropic (Claude AI)
    # ANTHROPIC_API_KEY: str

    # === IA - LiteLLM + GPT-4o-mini ===
    AI_PROVIDER: str = "openrouter"
    AI_MODEL: str = "openai/gpt-4o-mini"
    AI_TECHNICAL_MODEL: str = "anthropic/claude-3.5-sonnet"
    AI_API_KEY: Optional[str] = None

    # ── Provider WhatsApp ─────────────────────────────────────────────────────
    # Escolha o provider: "evolution" (padrão) ou "zapi"
    WHATSAPP_PROVIDER: str = "evolution"

    # Z-API (WhatsApp) — usado quando WHATSAPP_PROVIDER=zapi
    ZAPI_INSTANCE_ID: str = ""
    ZAPI_TOKEN: str = ""
    ZAPI_CLIENT_TOKEN: str = ""
    ZAPI_BASE_URL: str = "https://api.z-api.io/instances"

    # Evolution API — usado quando WHATSAPP_PROVIDER=evolution
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = "cotte"

    # Admin
    ADMIN_SETUP_KEY: str

    # Kiwify (webhook de assinaturas)
    KIWIFY_TOKEN: str = ""

    # E-mail — use API Brevo (recomendado na Railway) ou SMTP
    # API Brevo: funciona na Railway (porta 443). Obtenha em https://app.brevo.com/settings/keys/api
    BREVO_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""  # ex: "COTTE <noreply@seudominio.com>"
    REDIS_URL: str = ""

    # Rate limit para recuperação de senha
    RESET_RATE_LIMIT_WINDOW_SECONDS: int = 900
    RESET_RATE_LIMIT_MAX_PER_IP: int = 10
    RESET_RATE_LIMIT_MAX_PER_EMAIL: int = 5
    RESET_RATE_LIMIT_BLOCK_SECONDS: int = 1800

    # Rate limit de segurança (SecurityMiddleware): só conta rotas fora de /app e /static
    SECURITY_RATE_LIMIT_MAX: int = 200
    SECURITY_RATE_LIMIT_WINDOW_SECONDS: int = 60
    SECURITY_RATE_LIMIT_WHITELIST: str = "127.0.0.1,localhost"

    # Cloudflare R2 (armazenamento de arquivos)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_URL: str = ""

    # Notion
    NOTION_API_KEY: str = ""
    NOTION_PAGE_ID: str = ""

    # Prefixo da API (alguns módulos usam /api/v1, outros usam /)
    API_V1_STR: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
