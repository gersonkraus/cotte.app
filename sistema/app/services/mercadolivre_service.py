from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import IntegracaoMercadoLivre
from app.repositories.mercadolivre_repository import MercadoLivreRepository

logger = logging.getLogger(__name__)

RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_SECONDS = 0.6


@dataclass
class TokenExchangeResult:
    access_token: str
    refresh_token: str
    token_type: str
    scope: str
    expires_in: int
    user_id: Optional[str]


class MercadoLivreService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MercadoLivreRepository(db)

    def _ensure_credentials_configured(self) -> None:
        if not settings.ML_CLIENT_ID or not settings.ML_CLIENT_SECRET:
            raise HTTPException(
                status_code=503,
                detail="Integração Mercado Livre indisponível: ML_CLIENT_ID/ML_CLIENT_SECRET não configurados.",
            )
        if not settings.ML_REDIRECT_URI:
            raise HTTPException(
                status_code=503,
                detail="Integração Mercado Livre indisponível: ML_REDIRECT_URI não configurado.",
            )

    def build_auth_url(self, empresa_id: int) -> Dict[str, Any]:
        self._ensure_credentials_configured()

        nonce = secrets.token_urlsafe(24)
        state = f"{empresa_id}:{nonce}"
        expira_em = datetime.now(timezone.utc) + timedelta(minutes=15)
        self.repo.set_oauth_state(empresa_id=empresa_id, state=state, expira_em=expira_em)
        self.db.commit()

        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.ML_CLIENT_ID,
                "redirect_uri": settings.ML_REDIRECT_URI,
                "state": state,
            }
        )
        authorization_url = f"{settings.ML_AUTH_URL}?{query}"
        return {
            "authorization_url": authorization_url,
            "state": state,
            "expira_em": expira_em.isoformat(),
        }

    def _parse_state(self, state: str) -> Tuple[int, str]:
        partes = (state or "").split(":", 1)
        if len(partes) != 2:
            raise HTTPException(status_code=400, detail="State OAuth inválido.")
        empresa_id_raw, nonce = partes
        try:
            empresa_id = int(empresa_id_raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="State OAuth inválido.") from exc
        return empresa_id, nonce

    async def _exchange_authorization_code(self, code: str) -> TokenExchangeResult:
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.ML_CLIENT_ID,
            "client_secret": settings.ML_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.ML_REDIRECT_URI,
        }
        response = await self._request_token(payload)
        return TokenExchangeResult(
            access_token=response.get("access_token", ""),
            refresh_token=response.get("refresh_token", ""),
            token_type=response.get("token_type", "bearer"),
            scope=response.get("scope", ""),
            expires_in=int(response.get("expires_in", 0) or 0),
            user_id=str(response.get("user_id")) if response.get("user_id") else None,
        )

    async def _request_token(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{settings.ML_API_BASE_URL.rstrip('/')}/oauth/token"
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }

        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(url, data=payload, headers=headers)
                if response.status_code == 429 and attempt < RETRY_MAX_ATTEMPTS:
                    await asyncio.sleep(RETRY_BASE_SECONDS * attempt)
                    continue
                if response.status_code >= 400:
                    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_code = body.get("error") or "oauth_error"
                    error_desc = body.get("error_description") or response.text
                    raise HTTPException(
                        status_code=400,
                        detail=f"Falha OAuth Mercado Livre ({error_code}): {error_desc}",
                    )
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= RETRY_MAX_ATTEMPTS:
                    raise HTTPException(
                        status_code=502,
                        detail="Falha de rede ao autenticar com Mercado Livre.",
                    ) from exc
                await asyncio.sleep(RETRY_BASE_SECONDS * attempt)

        raise HTTPException(status_code=502, detail="Falha inesperada ao autenticar com Mercado Livre.")

    async def _fetch_ml_user(self, access_token: str) -> Dict[str, Any]:
        url = f"{settings.ML_API_BASE_URL.rstrip('/')}/users/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers)
        if response.status_code >= 400:
            return {}
        return response.json()

    async def process_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        self._ensure_credentials_configured()
        empresa_id, _ = self._parse_state(state)

        integracao = self.repo.get_integracao(empresa_id)
        if not integracao or integracao.oauth_state != state:
            raise HTTPException(status_code=400, detail="State OAuth inválido ou expirado.")
        if (
            integracao.oauth_state_expira_em
            and integracao.oauth_state_expira_em < datetime.now(timezone.utc)
        ):
            raise HTTPException(status_code=400, detail="State OAuth expirado.")

        token = await self._exchange_authorization_code(code)
        if not token.access_token or not token.refresh_token:
            raise HTTPException(status_code=400, detail="Resposta OAuth inválida: token ausente.")

        perfil = await self._fetch_ml_user(token.access_token)
        ml_user_id = token.user_id or (str(perfil.get("id")) if perfil.get("id") else None)
        ml_nickname = perfil.get("nickname") if isinstance(perfil.get("nickname"), str) else None

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(token.expires_in, 0))
        self.repo.save_tokens(
            empresa_id=empresa_id,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            scope=token.scope,
            expires_at=expires_at,
            ml_user_id=ml_user_id,
            ml_nickname=ml_nickname,
        )
        self.db.commit()

        return {
            "empresa_id": empresa_id,
            "ml_user_id": ml_user_id,
            "ml_nickname": ml_nickname,
            "token_expires_at": expires_at.isoformat(),
        }

    def get_status(self, empresa_id: int) -> Dict[str, Any]:
        registro = self.repo.get_integracao(empresa_id)
        if not registro:
            return {
                "connected": False,
                "ml_user_id": None,
                "ml_nickname": None,
                "token_expires_at": None,
                "last_sync_pedidos_at": None,
                "last_sync_anuncios_at": None,
                "last_error": None,
            }
        return {
            "connected": bool(registro.conectado and registro.access_token),
            "ml_user_id": registro.ml_user_id,
            "ml_nickname": registro.ml_nickname,
            "token_expires_at": registro.token_expires_at.isoformat() if registro.token_expires_at else None,
            "last_sync_pedidos_at": registro.ultimo_sync_pedidos_em.isoformat() if registro.ultimo_sync_pedidos_em else None,
            "last_sync_anuncios_at": registro.ultimo_sync_anuncios_em.isoformat() if registro.ultimo_sync_anuncios_em else None,
            "last_error": registro.ultimo_erro,
        }

    def disconnect(self, empresa_id: int) -> Dict[str, Any]:
        self.repo.desconectar(empresa_id)
        self.db.commit()
        return {
            "connected": False,
            "message": "Conta Mercado Livre desconectada com sucesso.",
        }

    async def _refresh_access_token(
        self, integracao: IntegracaoMercadoLivre
    ) -> IntegracaoMercadoLivre:
        if not integracao.refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token não encontrado para esta empresa.")

        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.ML_CLIENT_ID,
            "client_secret": settings.ML_CLIENT_SECRET,
            "refresh_token": integracao.refresh_token,
        }
        response = await self._request_token(payload)

        expires_in = int(response.get("expires_in", 0) or 0)
        access_token = response.get("access_token")
        refresh_token = response.get("refresh_token")
        if not access_token or not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh de token retornou dados inválidos.")

        integracao.access_token = access_token
        integracao.refresh_token = refresh_token
        integracao.token_type = response.get("token_type", integracao.token_type)
        integracao.token_scope = response.get("scope", integracao.token_scope)
        integracao.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in, 0))
        integracao.ultimo_erro = None
        integracao.conectado = True
        self.db.add(integracao)
        self.db.flush()
        return integracao

    async def _ensure_valid_token(self, empresa_id: int) -> IntegracaoMercadoLivre:
        registro = self.repo.get_integracao(empresa_id)
        if not registro or not registro.conectado or not registro.access_token:
            raise HTTPException(status_code=400, detail="Empresa não conectada ao Mercado Livre.")

        expira_em = registro.token_expires_at
        margem = datetime.now(timezone.utc) + timedelta(seconds=60)
        if expira_em and expira_em > margem:
            return registro
        atualizado = await self._refresh_access_token(registro)
        self.db.commit()
        return atualizado

    async def _ml_get(
        self,
        *,
        endpoint: str,
        access_token: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{settings.ML_API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {access_token}"}

        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=25) as client:
                    response = await client.get(url, headers=headers, params=params)
                if response.status_code == 429 and attempt < RETRY_MAX_ATTEMPTS:
                    await asyncio.sleep(RETRY_BASE_SECONDS * attempt)
                    continue
                if response.status_code in (401, 403):
                    raise HTTPException(
                        status_code=401,
                        detail="Token Mercado Livre inválido ou sem permissão. Reconecte a conta.",
                    )
                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Erro Mercado Livre ({response.status_code}) ao consultar {endpoint}.",
                    )
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= RETRY_MAX_ATTEMPTS:
                    raise HTTPException(
                        status_code=502,
                        detail="Falha de rede ao consultar Mercado Livre.",
                    ) from exc
                await asyncio.sleep(RETRY_BASE_SECONDS * attempt)

        raise HTTPException(status_code=502, detail="Erro inesperado em consulta Mercado Livre.")

    async def sync_pedidos(self, empresa_id: int, limit: int = 50) -> Dict[str, Any]:
        registro = await self._ensure_valid_token(empresa_id)
        seller_id = registro.ml_user_id
        if not seller_id:
            raise HTTPException(status_code=400, detail="Conta Mercado Livre sem user_id vinculado.")

        limit = max(1, min(limit, 200))
        dados = await self._ml_get(
            endpoint="/orders/search/recent",
            access_token=registro.access_token,
            params={"seller": seller_id, "sort": "date_desc", "limit": limit},
        )
        resultados = dados.get("results") if isinstance(dados.get("results"), list) else []
        consolidado = self.repo.upsert_pedidos(empresa_id, resultados)
        self.repo.marcar_sync_pedidos(empresa_id)
        self.db.commit()
        return {"total_recebido": len(resultados), **consolidado}

    async def sync_anuncios(self, empresa_id: int, limit: int = 50) -> Dict[str, Any]:
        registro = await self._ensure_valid_token(empresa_id)
        seller_id = registro.ml_user_id
        if not seller_id:
            raise HTTPException(status_code=400, detail="Conta Mercado Livre sem user_id vinculado.")

        limit = max(1, min(limit, 100))
        busca_ids = await self._ml_get(
            endpoint=f"/users/{seller_id}/items/search",
            access_token=registro.access_token,
            params={"limit": limit},
        )
        item_ids: List[str] = [
            str(item_id)
            for item_id in (busca_ids.get("results") or [])
            if isinstance(item_id, str)
        ]

        anuncios: List[Dict[str, Any]] = []
        for item_id in item_ids:
            detalhe = await self._ml_get(
                endpoint=f"/items/{item_id}",
                access_token=registro.access_token,
            )
            anuncios.append(detalhe)

        consolidado = self.repo.upsert_anuncios(empresa_id, anuncios)
        self.repo.marcar_sync_anuncios(empresa_id)
        self.db.commit()
        return {"total_recebido": len(anuncios), **consolidado}
