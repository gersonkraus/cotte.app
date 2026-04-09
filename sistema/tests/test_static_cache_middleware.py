"""Testes do Cache-Control em /app e /static (middleware isolado)."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.testclient import TestClient
import pytest

from app.core.static_cache_middleware import StaticCacheControlMiddleware, VersioningMiddleware


@pytest.fixture
def static_cache_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(StaticCacheControlMiddleware)

    @app.get("/app/test.js")
    def app_js() -> PlainTextResponse:
        return PlainTextResponse("x")

    @app.get("/app/login.html")
    def app_html() -> PlainTextResponse:
        return PlainTextResponse("<html/>")

    @app.get("/static/config/a.json")
    def static_cfg() -> PlainTextResponse:
        return PlainTextResponse("{}")

    @app.get("/static/logos/x.png")
    def static_logo() -> PlainTextResponse:
        return PlainTextResponse("bin")

    @app.get("/api/v1/health")
    def api_health() -> PlainTextResponse:
        return PlainTextResponse("ok")

    with TestClient(app) as c:
        yield c


def test_app_js_gets_long_cache(static_cache_client: TestClient) -> None:
    r = static_cache_client.get("/app/test.js")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "max-age=86400" in cc
    assert "stale-while-revalidate=604800" in cc


def test_app_html_gets_no_cache(static_cache_client: TestClient) -> None:
    r = static_cache_client.get("/app/login.html")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "").lower()
    assert "no-cache" in cc


def test_static_config_moderate_cache(static_cache_client: TestClient) -> None:
    r = static_cache_client.get("/static/config/a.json")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "max-age=3600" in cc


def test_static_user_uploads_short_cache(static_cache_client: TestClient) -> None:
    r = static_cache_client.get("/static/logos/x.png")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "max-age=300" in cc


def test_api_paths_not_modified(static_cache_client: TestClient) -> None:
    r = static_cache_client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.headers.get("cache-control") is None


# ── VersioningMiddleware ──────────────────────────────────────────────────────

_VERSION = "abc1234"

_HTML_SIMPLE = """<!DOCTYPE html>
<html><head>
<link rel="stylesheet" href="/css/style.css">
<script src="/js/main.js"></script>
</head><body></body></html>"""

_HTML_EXISTING_QUERY = """<!DOCTYPE html>
<html><head>
<link rel="stylesheet" href="/css/style.css?v=old">
<script src="/js/main.js?v=old"></script>
</head><body></body></html>"""

_HTML_EXTERNAL = """<!DOCTYPE html>
<html><head>
<script src="https://cdn.example.com/lib.js"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/style.css">
</head><body></body></html>"""


@pytest.fixture
def versioning_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(VersioningMiddleware, version=_VERSION)

    @app.get("/page")
    def page() -> HTMLResponse:
        return HTMLResponse(_HTML_SIMPLE)

    @app.get("/page-existing-query")
    def page_existing() -> HTMLResponse:
        return HTMLResponse(_HTML_EXISTING_QUERY)

    @app.get("/page-external")
    def page_external() -> HTMLResponse:
        return HTMLResponse(_HTML_EXTERNAL)

    @app.get("/api/data")
    def api_data() -> PlainTextResponse:
        return PlainTextResponse('{"ok": true}', media_type="application/json")

    with TestClient(app) as c:
        yield c


def test_versioning_injects_version_in_js(versioning_client: TestClient) -> None:
    r = versioning_client.get("/page")
    assert r.status_code == 200
    assert f'src="/js/main.js?v={_VERSION}"' in r.text


def test_versioning_injects_version_in_css(versioning_client: TestClient) -> None:
    r = versioning_client.get("/page")
    assert f'href="/css/style.css?v={_VERSION}"' in r.text


def test_versioning_replaces_existing_query(versioning_client: TestClient) -> None:
    r = versioning_client.get("/page-existing-query")
    assert f'?v={_VERSION}"' in r.text
    assert "?v=old" not in r.text


def test_versioning_skips_external_urls(versioning_client: TestClient) -> None:
    r = versioning_client.get("/page-external")
    # URLs externas não devem ter ?v= adicionado
    assert f"cdn.example.com/lib.js?v=" not in r.text
    assert f"googleapis.com/style.css?v=" not in r.text


def test_versioning_skips_non_html_responses(versioning_client: TestClient) -> None:
    r = versioning_client.get("/api/data")
    assert r.status_code == 200
    # JSON não deve ser modificado
    assert r.text == '{"ok": true}'
