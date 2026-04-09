"""Paths isentos de rate limit no SecurityMiddleware."""

from starlette.applications import Starlette

from app.core.security_middleware import SecurityMiddleware


def _mw() -> SecurityMiddleware:
    return SecurityMiddleware(Starlette())


def test_exempt_app_and_static_paths() -> None:
    m = _mw()
    assert m._is_rate_limit_exempt_path("/app/")
    assert m._is_rate_limit_exempt_path("/app/js/api.js")
    assert m._is_rate_limit_exempt_path("/app")
    assert m._is_rate_limit_exempt_path("/static/logos/x.png")
    assert m._is_rate_limit_exempt_path("/static")
    assert m._is_rate_limit_exempt_path("/favicon.svg")


def test_api_paths_not_exempt() -> None:
    m = _mw()
    assert not m._is_rate_limit_exempt_path("/api/v1/health")
    assert not m._is_rate_limit_exempt_path("/api/v1/orcamentos/")
