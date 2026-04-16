from fastapi import FastAPI, Request, Response, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from pathlib import Path
import datetime as _dt
import os

# Preenchido no startup_event; usado pelo endpoint /api/v1/version
_app_started_at: str = ""

_BASE_DIR = Path(__file__).parent.parent

# Configuração de logging estruturado
from app.core.logging_config import setup_logging
from app.core.logging_middleware import LoggingMiddleware
from app.core.security_middleware import SecurityMiddleware
from app.core.static_cache_middleware import (
    StaticCacheControlMiddleware,
    VersioningMiddleware,
)
from app.core.exceptions import register_exception_handlers

# Configura logging estruturado
setup_logging(
    level="INFO",
    json_format=False,  # Pode ser True para produção com ELK/CloudWatch
    log_file=None,  # Pode definir caminho para arquivo de log
)

import logging

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.database import engine, Base
from sqlalchemy import select
from app.services.schema_drift_service import (
    check_critical_schema_drift,
    analyze_schema_drift,
    save_schema_drift_snapshot,
)

# Imports dos routers
from app.routers.auth_clientes import auth_router
from app.routers.clientes import router as clientes_router
from app.routers.orcamentos import router as orcamentos_router
from app.routers.whatsapp import router as whatsapp_router
from app.routers.empresa import router as empresa_router
from app.routers.admin import router as admin_router
from app.routers.monitor_ai import router as monitor_ai_router
from app.routers.catalogo import router as catalogo_router
from app.routers.relatorios import router as relatorios_router
from app.routers.notificacoes import router as notificacoes_router
from app.routers.publico import router as publico_router
from app.routers.webhooks import router as webhooks_router
from app.routers.config import router as config_router
from app.routers.comercial import router as comercial_router
from app.routers.comercial_campaigns import router as comercial_campaigns_router
from app.routers.comercial_import import router as comercial_import_router
from app.routers.comercial_leads import router as comercial_leads_router
from app.routers.comercial_pipeline import router as comercial_pipeline_router
from app.routers.comercial_interacoes import router as comercial_interacoes_router
from app.routers.comercial_config import router as comercial_config_router
from app.routers.comercial_propostas import router as comercial_propostas_router
from app.routers.comercial_templates import router as comercial_templates_router
from app.routers.publico_propostas import router as publico_propostas_router
from app.routers.docs import router as docs_router
from app.routers.documentos import router as documentos_router
from app.routers.financeiro import router as financeiro_router
from app.routers.ai_hub import router as ai_hub_router
from app.routers.admin_planos import router as admin_planos_router
from app.routers.papeis import router as papeis_router
from app.routers.agendamentos import router as agendamentos_router


# Rotas serão importadas e incluídas dinamicamente para facilitar os testes.

# Schema do banco: aplicar com 'alembic upgrade head'. Banco já existente: 'alembic stamp head'.
# Ver sistema/DEPLOY-RAILWAY.md e alembic/README.

TAGS_METADATA = [
    {"name": "Health", "description": "Endpoints de verificação de saúde da API."},
    {"name": "Autenticacao", "description": "Login, registro e recuperação de senha."},
    {
        "name": "Empresa",
        "description": "Gestão da empresa: dados, logo, usuários, WhatsApp próprio e PIX.",
    },
    {"name": "Clientes", "description": "Cadastro e gestão de clientes."},
    {"name": "Catalogo", "description": "Catálogo de serviços e categorias."},
    {
        "name": "Orcamentos",
        "description": "Criação, edição, envio e acompanhamento de orçamentos.",
    },
    {
        "name": "Documentos",
        "description": "Upload e gestão de documentos vinculados a orçamentos.",
    },
    {
        "name": "Publico",
        "description": "Links públicos para clientes visualizarem e aceitarem orçamentos.",
    },
    {
        "name": "Financeiro",
        "description": "Contas a pagar/receber, fluxo de caixa, categorias e configurações financeiras.",
    },
    {
        "name": "WhatsApp",
        "description": "Integração com WhatsApp (status, QR code, webhook).",
    },
    {
        "name": "AI",
        "description": "Assistente de IA: interpretação de orçamentos, análises financeiras e comercial.",
    },
    {
        "name": "Comercial",
        "description": "CRM: leads, pipeline, campanhas, templates e importação.",
    },
    {
        "name": "Comercial - Templates",
        "description": "Templates de mensagens para campanhas comerciais.",
    },
    {"name": "Comercial - Importacao", "description": "Importação em massa de leads."},
    {
        "name": "Comercial - Campanhas",
        "description": "Criação e gestão de campanhas de disparo.",
    },
    {"name": "Relatorios", "description": "Relatórios e resumos do sistema."},
    {"name": "Notificacoes", "description": "Notificações internas do sistema."},
    {
        "name": "Agendamentos",
        "description": "Agendamento de entregas e serviços, integração com orçamentos e WhatsApp.",
    },
    {
        "name": "Config Publica",
        "description": "Endpoints públicos de configuração e pricing.",
    },
    {"name": "Webhooks", "description": "Webhooks externos (Kiwify, etc)."},
    {"name": "Documentacao", "description": "Informações e exemplos da API."},
    {
        "name": "Admin",
        "description": "Painel administrativo: empresas, usuários, broadcasts e configurações globais.",
    },
    {
        "name": "Admin - Pacotes",
        "description": "Gestão de módulos e planos do sistema.",
    },
]

app = FastAPI(
    title="COTTE API",
    description="Sistema de geração de orçamentos via WhatsApp com IA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=TAGS_METADATA,
)

ENV = os.getenv("ENVIRONMENT", "development")

if ENV == "production":
    allow_origins = ["https://cotte.app", "https://www.cotte.app"]
elif ENV == "development":
    allow_origins = ["*"]
else:
    allow_origins = _cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_origins() -> list[str]:
    """Monta a lista de origens CORS a partir do .env."""
    raw = settings.CORS_ALLOWED_ORIGINS or ""
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    if not origins:
        # Em desenvolvimento, permitir localhost
        return [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "https://cotte.app",
            "https://www.cotte.app",
        ]
    return origins


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    """Garante que erros 500 retornem JSON; não sobrescreve HTTPException (400, 401, 404)."""
    if isinstance(exc, HTTPException):
        raise exc
    logging.exception("Erro não tratado: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno. Tente novamente."},
    )


# Middleware de logging estruturado
app.add_middleware(LoggingMiddleware)

# Middleware de segurança (deve vir após logging)
app.add_middleware(SecurityMiddleware)

# Cache-Control para /app e /static (último na pilha = ajusta a resposta antes do cliente/CDN)
app.add_middleware(StaticCacheControlMiddleware)

# Cache-busting: injeta ?v=APP_VERSION em .js e .css dentro de HTML (deve vir após StaticCache)
app.add_middleware(VersioningMiddleware)

# Registra handlers de exceção personalizados
register_exception_handlers(app)

# ── ARQUIVOS ESTÁTICOS ─────────────────────────────────────────────────────
os.makedirs("static/pdfs", exist_ok=True)
os.makedirs("static/logos", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("static/config", exist_ok=True)
os.makedirs("uploads/empresas", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Servir página pública de propostas
@app.get("/p/{slug}")
async def proposta_publica(slug: str):
    return FileResponse("app/p/proposta.html", media_type="text/html")


# ── FRONTEND (pasta cotte-frontend) ────────────────────────────────────────
# Redireciona /app/index.html → /app/ antes que o StaticFiles intercepte
from fastapi.responses import RedirectResponse as _Redirect


@app.get("/app/index.html", include_in_schema=False)
def _redirect_index_html():
    return _Redirect("/app/", status_code=301)


# Redirecionamento global para links públicos legados ou sem prefixo /api/v1
@app.get("/o/{path:path}", include_in_schema=False)
@app.post("/o/{path:path}", include_in_schema=False)
async def redirect_public_link(path: str):
    return _Redirect(f"/api/v1/o/{path}")


app.mount(
    "/app",
    StaticFiles(directory=str(_BASE_DIR / "cotte-frontend"), html=True),
    name="frontend",
)


def include_routers(app: FastAPI):
    # Inclui todos os routers com prefixo /api/v1
    routers = [
        (auth_router, "/api/v1"),
        (clientes_router, "/api/v1"),
        (orcamentos_router, "/api/v1"),
        (whatsapp_router, "/api/v1"),
        (empresa_router, "/api/v1"),
        (admin_router, "/api/v1"),
        (monitor_ai_router, "/api/v1/superadmin/monitor-ai"),
        (catalogo_router, "/api/v1"),
        (relatorios_router, "/api/v1"),
        (notificacoes_router, "/api/v1"),
        (publico_router, "/api/v1"),
        (webhooks_router, "/api/v1"),
        (config_router, "/api/v1"),
        (comercial_router, "/api/v1"),
        (comercial_campaigns_router, "/api/v1"),
        (comercial_import_router, "/api/v1"),
        (comercial_leads_router, "/api/v1"),
        (comercial_pipeline_router, "/api/v1"),
        (comercial_interacoes_router, "/api/v1"),
        (comercial_config_router, "/api/v1"),
        (comercial_propostas_router, "/api/v1"),
        (comercial_templates_router, "/api/v1"),
        (publico_propostas_router, ""),  # Rotas públicas sem prefixo /api/v1
        (documentos_router, "/api/v1"),
        (financeiro_router, "/api/v1"),
        (docs_router, "/api/v1"),
        (ai_hub_router, "/api/v1"),
        (admin_planos_router, "/api/v1"),
        (papeis_router, "/api/v1"),
        (agendamentos_router, "/api/v1"),
    ]

    import logging

    logger = logging.getLogger(__name__)

    for router_obj, prefix in routers:
        try:
            # Log before including
            router_name = (
                router_obj.__class__.__name__
                if hasattr(router_obj, "__class__")
                else str(router_obj)
            )
            logger.info(f"Including router: {router_name}, prefix: {prefix}")

            if prefix:
                app.include_router(router_obj, prefix=prefix)
            else:
                app.include_router(router_obj)
            logger.info(
                f"Router {router_obj.prefix if hasattr(router_obj, 'prefix') else router_name} included successfully"
            )
        except Exception as e:
            logger.error(f"Failed to include router {router_obj}: {e}", exc_info=True)
            # Don't raise, just log the error
            # This allows other routers to be included even if one fails


# Incluir todos os routers
include_routers(app)


@app.on_event("startup")
async def startup_event():
    """Aplica migrations pendentes e garante que todas as tabelas existam."""
    global _app_started_at
    _app_started_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(str(_BASE_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(_BASE_DIR / "alembic"))
    try:
        command.upgrade(alembic_cfg, "heads")
        logging.info("Migrations aplicadas com sucesso")
    except Exception as exc:  # noqa: BLE001 — startup não deve quebrar a aplicação
        logging.error("Erro ao aplicar migrations: %s", exc)

    from app.models import models  # noqa: F401 - importa todos os models

    with engine.begin() as conn:
        Base.metadata.create_all(conn)

    logging.info("Tabelas verificadas/criadas com sucesso")
    critical_check = check_critical_schema_drift(engine, Base.metadata)
    if not critical_check["ok"]:
        colunas = ", ".join(critical_check["critical_missing"])
        raise RuntimeError(
            "Preflight de schema falhou. Divergência crítica detectada em: "
            f"{colunas}. Execute 'cd sistema && alembic upgrade head' e reinicie a aplicação."
        )
    try:
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            drift = analyze_schema_drift(engine, Base.metadata)
            save_schema_drift_snapshot(
                db,
                drift,
                source="startup",
                app_version=settings.APP_VERSION,
                environment=settings.ENVIRONMENT,
            )
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logging.warning("Schema drift snapshot (startup): erro ao salvar — %s", exc)

    await _sweep_assinaturas_expiradas()
    await _sweep_financeiro()
    await _sweep_agendamentos_followup()
    await _seed_modulos_padrao()


async def _sweep_assinaturas_expiradas():
    """Bloqueia empresas com assinatura expirada há mais de 3 dias (roda no startup)."""
    from datetime import datetime, timezone, timedelta
    from app.core.database import get_db
    from app.models.models import Empresa

    for db in get_db():
        try:
            prazo = datetime.now(timezone.utc) - timedelta(days=3)
            result = db.execute(
                select(Empresa).filter(
                    Empresa.assinatura_valida_ate < prazo,
                    Empresa.ativo == True,
                )
            )
            empresas_a_atualizar = result.scalars().all()

            for emp in empresas_a_atualizar:
                emp.ativo = False
                db.add(emp)

            db.commit()
            if empresas_a_atualizar:
                logging.warning(
                    "Sweep startup: %d empresa(s) bloqueada(s) por assinatura expirada",
                    len(empresas_a_atualizar),
                )
        except Exception as exc:  # noqa: BLE001 — startup não deve quebrar a aplicação
            logging.error("Sweep startup: erro ao verificar assinaturas — %s", exc)
            db.rollback()


async def _sweep_financeiro():
    """Atualiza status de contas vencidas no startup."""
    from app.core.database import get_db
    from app.services import financeiro_service as fin_svc

    db = next(get_db())
    try:
        resultado = fin_svc.sweep_contas_vencidas(db)
        db.commit()
        logging.info("Sweep financeiro: %s", resultado)
    except Exception as exc:
        logging.error("Sweep financeiro: erro — %s", exc)
        db.rollback()
    finally:
        db.close()


async def _seed_modulos_padrao():
    """Popula módulos, planos padrão e papéis por empresa (idempotente)."""
    from app.core.database import get_db
    from app.services.seed_modulos import seed_modulos_e_planos_padrao

    db = next(get_db())
    try:
        seed_modulos_e_planos_padrao(db)
        logging.info("Seed de módulos e papéis concluído")
    except Exception as exc:
        logging.error("Seed de módulos: erro — %s", exc)
    finally:
        db.close()


async def _sweep_agendamentos_followup():
    """Executa follow-up de agendamentos pendentes de escolha no startup."""
    from app.core.database import get_db
    from app.services import agendamento_service

    db = next(get_db())
    try:
        resultado = agendamento_service.processar_followups_pendentes(db)
        logging.info("Sweep agendamentos: %s", resultado)
    except Exception as exc:
        logging.error("Sweep agendamentos: erro — %s", exc)
        db.rollback()
    finally:
        db.close()


@app.get("/", tags=["Health"])
def root():
    return FileResponse(str(_BASE_DIR / "cotte-frontend" / "landing.html"))


@app.get("/favicon.svg", include_in_schema=False)
def favicon_svg():
    return FileResponse(
        str(_BASE_DIR / "cotte-frontend" / "favicon.svg"), media_type="image/svg+xml"
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico():
    from fastapi.responses import RedirectResponse

    return RedirectResponse("/favicon.svg", status_code=301)


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return FileResponse(
        str(_BASE_DIR / "cotte-frontend" / "manifest.json"),
        media_type="application/json",
    )


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(
        str(_BASE_DIR / "cotte-frontend" / "sw.js"), media_type="application/javascript"
    )


@app.get("/.well-known/assetlinks.json", include_in_schema=False)
async def get_assetlinks():
    # Este JSON deve ser atualizado com o seu SHA-256 gerado pelo Bubblewrap
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "app.cotte.twa",  # Substitua pelo seu package name
                "sha256_cert_fingerprints": [
                    "B5:26:B4:1B:DC:68:85:65:D5:DC:F0:AC:5C:EA:94:7D:DF:FD:31:AC:07:55:E5:98:BE:BA:2B:72:4E:02:92:84"
                ],
            },
        }
    ]


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    return FileResponse(
        str(_BASE_DIR / "cotte-frontend" / "sitemap.xml"), media_type="application/xml"
    )


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return FileResponse(
        str(_BASE_DIR / "cotte-frontend" / "robots.txt"), media_type="text/plain"
    )


@app.get("/termos", include_in_schema=False)
def termos():
    return FileResponse(str(_BASE_DIR / "cotte-frontend" / "termos.html"))


@app.get("/privacidade", include_in_schema=False)
def privacidade():
    return FileResponse(str(_BASE_DIR / "cotte-frontend" / "privacidade.html"))


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/api/v1/health", tags=["Health"])
def api_health():
    return {"status": "ok", "version": settings.APP_VERSION, "service": "cotte-api"}


@app.get("/api/v1/version", tags=["Health"])
def api_version():
    """Retorna a versão atual do deploy e o timestamp de startup.
    Usado pelo frontend para detectar novos deploys e exibir banner de atualização.
    """
    return {"version": settings.APP_VERSION, "started_at": _app_started_at}


if __name__ == "__main__":
    import uvicorn

    include_routers(app)
    uvicorn.run(app, host="0.0.0.0", port=8000)
