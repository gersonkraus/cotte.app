"""
Define Cache-Control nas respostas de arquivos estáticos (/app, /static).

Objetivo: permitir cache no navegador e em CDN (ex.: Cloudflare) sem servir
HTML desatualizado após deploy e sem cache longo indevido em logos/PDFs
que podem ser substituídos no mesmo caminho.

Política:
- /app: páginas HTML (e rotas sem extensão de asset) → no-cache
- /app: JS, CSS, fontes, imagens → max-age 1 dia + stale-while-revalidate
- /static/logos|pdfs|images: conteúdo frequentemente dinâmico → cache curto
- demais /static: cache moderado (config e similares)
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Assets versionados implicitamente pelo deploy (mesmo nome de arquivo troca no deploy)
_APP_ASSET_SUFFIXES: tuple[str, ...] = (
    ".js",
    ".mjs",
    ".css",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".map",
)


def _policy_for_path(path: str) -> str | None:
    """Retorna valor de Cache-Control ou None se a rota não for estática montada."""
    if path.startswith("/static/"):
        if path.startswith(
            ("/static/logos/", "/static/pdfs/", "/static/images/")
        ):
            return "private, max-age=300, stale-while-revalidate=3600"
        return "public, max-age=3600, stale-while-revalidate=86400"

    if path == "/app" or path.startswith("/app/"):
        lower = path.lower()
        if any(lower.endswith(sfx) for sfx in _APP_ASSET_SUFFIXES):
            return "public, max-age=86400, stale-while-revalidate=604800"
        return "no-cache, private"

    return None


class StaticCacheControlMiddleware(BaseHTTPMiddleware):
    """Acrescenta Cache-Control em respostas de /app e /static."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if response.status_code not in (200, 206):
            return response
        if response.headers.get("cache-control"):
            return response

        policy = _policy_for_path(request.url.path)
        if policy is not None:
            response.headers["Cache-Control"] = policy

        return response
