"""Testes do Cache-Control em /app e /static (middleware isolado)."""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
import pytest

from app.core.static_cache_middleware import StaticCacheControlMiddleware


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
