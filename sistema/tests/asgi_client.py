from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

import anyio
import httpx


class SyncASGIClient:
    """Cliente síncrono para apps ASGI usando httpx>=0.28.

    Motivação:
    - `fastapi.testclient.TestClient` depende de uma integração antiga entre Starlette/HTTPX
      que quebra em alguns ambientes com httpx 0.28+.
    - Este wrapper mantém testes síncronos simples, mas executa requisições via
      `httpx.AsyncClient` com `httpx.ASGITransport`.
    """

    def __init__(
        self,
        app: Any,
        *,
        base_url: str = "http://testserver",
        raise_app_exceptions: bool = False,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._transport = httpx.ASGITransport(
            app=app,
            raise_app_exceptions=raise_app_exceptions,
        )
        self._base_url = base_url
        self._default_headers = dict(default_headers or {})

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        # Para compatibilidade com `TestClient`, seguimos redirects por padrão.
        kwargs.setdefault("follow_redirects", True)

        async def _do() -> httpx.Response:
            headers = dict(self._default_headers)
            extra_headers = kwargs.pop("headers", None)
            if extra_headers:
                headers.update(dict(extra_headers))

            async with httpx.AsyncClient(
                transport=self._transport,
                base_url=self._base_url,
                headers=headers,
            ) as client:
                resp = await client.request(method, url, **kwargs)
                # Garante que o corpo está lido antes de fechar o client
                await resp.aread()
                return resp

        return anyio.run(_do)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def __enter__(self) -> "SyncASGIClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None
