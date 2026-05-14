from pathlib import Path

import time

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import subprocess


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


def _dotenv_paths() -> tuple[str, ...]:
    """Ordem: `.env` no cwd primeiro, depois `sistema/.env` (o último sobrescreve chaves iguais).

    Assim o token definido em `sistema/.env` prevalece sobre um `.env` vazio na raiz do projeto.
    Arquivos inexistentes são ignorados pelo pydantic-settings.
    """
    paths: list[str] = []
    cwd_env = Path.cwd() / ".env"
    if cwd_env.is_file():
        paths.append(str(cwd_env))
    sistema_env = Path(__file__).resolve().parents[2] / ".env"
    if sistema_env.is_file():
        if not paths or Path(paths[-1]).resolve() != sistema_env.resolve():
            paths.append(str(sistema_env))
    return tuple(paths) if paths else (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_dotenv_paths(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # === IA - LiteLLM ===
    AI_PROVIDER: str = "openrouter"
    AI_MODEL: str = "openai/gpt-4o-mini"
    # Usado quando AI_MODEL está vazio ou é o placeholder "default" (antes de normalizar para LiteLLM).
    # Slug curto (ex.: gpt-4o-mini) funciona bem com AI_PROVIDER=openrouter; ou use openrouter/...
    AI_MODEL_FALLBACK: str = "gpt-4o-mini"
    # Padrão via OpenRouter + LiteLLM (OPENROUTER_API_KEY); não exige ANTHROPIC_API_KEY nativa.
    AI_TECHNICAL_MODEL: str = "openrouter/anthropic/claude-3.5-sonnet"
    AI_API_KEY: Optional[str] = None
    # Se true: AI_MODEL / overrides vão ao LiteLLM sem reescrever prefixos (só vazio/default e google/→gemini/).
    # Use quando quiser um roteamento que ainda não está na heurística do backend.
    AI_LITELLM_RAW: bool = False

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
    # Chave enviada pela Evolution nos headers do webhook (pode ser igual à API key).
    # Se não configurada, usa EVOLUTION_API_KEY como fallback.
    EVOLUTION_WEBHOOK_SECRET: str = ""
    EVOLUTION_INSTANCE: str = "cotte"
    EVOLUTION_INSTANCE_COMERCIAL: str = "cotte-comercial"

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

    # Mercado Livre (aplicação integradora)
    ML_CLIENT_ID: str = ""
    ML_CLIENT_SECRET: str = ""
    ML_REDIRECT_URI: str = ""
    ML_APP_ID: str = ""
    ML_AUTH_URL: str = "https://auth.mercadolivre.com.br/authorization"
    ML_API_BASE_URL: str = "https://api.mercadolibre.com"
    ML_SYNC_CRON_TOKEN: str = ""
    ML_SYNC_PERIODIC_ENABLED: bool = False
    ML_SYNC_PERIODIC_INTERVAL_MINUTES: int = 15
    ML_TOKEN_CRYPTO_SECRET: str = ""
    FOCUS_TOKEN: str = ""
    # Token de Homologação (Painel API → Tokens). Homologação na Focus não aceita o token de produção/principal.
    FOCUS_TOKEN_HOMOLOGACAO: str = ""
    FOCUS_AMBIENTE: str = "homologacao"  # "homologacao" | "producao"

    @field_validator("FOCUS_TOKEN", "FOCUS_TOKEN_HOMOLOGACAO", mode="before")
    @classmethod
    def _strip_focus_token(cls, v):
        """Evita 401 na Focus por BOM, aspas ou espaços ao copiar o token no .env / Railway."""
        if v is None:
            return ""
        s = str(v).replace("\ufeff", "").strip()
        if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
            s = s[1:-1].strip()
        return s

    @field_validator("FOCUS_AMBIENTE", mode="before")
    @classmethod
    def _norm_focus_ambiente(cls, v):
        if v is None:
            return "homologacao"
        s = str(v).replace("\ufeff", "").strip().lower()
        if s in ("producao", "prod", "production", "produção"):
            return "producao"
        return "homologacao"

    # OAuth: offline_access é necessário para o Mercado Livre devolver refresh_token na troca do code.
    ML_OAUTH_SCOPE: str = "offline_access read write"

    # Prefixo da API (alguns módulos usam /api/v1, outros usam /)
    API_V1_STR: str = ""


settings = Settings()
