from __future__ import annotations

import asyncio
import logging
import secrets
import hashlib
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Cliente,
    HistoricoEdicao,
    IntegracaoMercadoLivre,
    Orcamento,
    Servico,
    StatusOrcamento,
    Usuario,
)
from app.repositories.mercadolivre_repository import MercadoLivreRepository
from app.services.orcamento_core_service import criar_orcamento_core

logger = logging.getLogger(__name__)

RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_SECONDS = 0.6


def _gerar_pkce_s256() -> Tuple[str, str]:
    """Gera par (code_verifier, code_challenge) para OAuth PKCE método S256 (RFC 7636)."""
    verifier = secrets.token_urlsafe(32)
    if len(verifier) < 43:
        verifier = (verifier + secrets.token_urlsafe(32))[:128]
    elif len(verifier) > 128:
        verifier = verifier[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


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
        code_verifier, code_challenge = _gerar_pkce_s256()
        self.repo.set_oauth_state(
            empresa_id=empresa_id,
            state=state,
            expira_em=expira_em,
            oauth_code_verifier=code_verifier,
        )
        self.db.commit()

        escopo = (settings.ML_OAUTH_SCOPE or "").strip() or "offline_access read write"
        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.ML_CLIENT_ID,
                "redirect_uri": settings.ML_REDIRECT_URI,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "scope": escopo,
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

    async def _exchange_authorization_code(
        self, code: str, code_verifier: str
    ) -> TokenExchangeResult:
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.ML_CLIENT_ID,
            "client_secret": settings.ML_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.ML_REDIRECT_URI,
            "code_verifier": code_verifier,
        }
        response = await self._request_token(payload)
        access = str(response.get("access_token") or "").strip()
        refresh = str(response.get("refresh_token") or "").strip()
        exp_raw = response.get("expires_in")
        if exp_raw is None and response.get("expires") is not None:
            try:
                exp_raw = int(float(response.get("expires")))
            except (TypeError, ValueError):
                exp_raw = 0
        expires_in = int(exp_raw or 0)
        uid = response.get("user_id")
        if not access or not refresh:
            logger.warning(
                "OAuth ML: token incompleto após POST /oauth/token; keys=%s scope_retornado=%s",
                sorted(response.keys()),
                response.get("scope"),
            )
        return TokenExchangeResult(
            access_token=access,
            refresh_token=refresh,
            token_type=str(response.get("token_type") or "bearer"),
            scope=str(response.get("scope") or ""),
            expires_in=expires_in,
            user_id=str(uid) if uid is not None and uid != "" else None,
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
                try:
                    data = response.json()
                except ValueError:
                    logger.warning(
                        "OAuth ML: resposta 200 não é JSON (primeiros 120 chars): %s",
                        (response.text or "")[:120],
                    )
                    raise HTTPException(
                        status_code=502,
                        detail="Resposta inválida do Mercado Livre ao trocar o código (JSON esperado).",
                    )
                if not isinstance(data, dict):
                    raise HTTPException(
                        status_code=502,
                        detail="Resposta OAuth Mercado Livre em formato inesperado.",
                    )
                return data
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

        code_verifier_plain = (integracao.oauth_code_verifier or "").strip()
        if not code_verifier_plain:
            raise HTTPException(
                status_code=400,
                detail="PKCE: sessão de autorização incompleta. Clique em Conectar Mercado Livre e tente novamente.",
            )

        token = await self._exchange_authorization_code(code, code_verifier_plain)
        if not token.access_token:
            raise HTTPException(
                status_code=400,
                detail="Resposta OAuth: access_token ausente. Verifique Client ID/Secret e se o código não foi reutilizado.",
            )
        if not token.refresh_token:
            logger.warning("OAuth ML: refresh_token ausente após troca (confirme escopo offline_access).")
            raise HTTPException(
                status_code=400,
                detail=(
                    "Resposta OAuth: refresh_token ausente. "
                    "No painel do Mercado Livre, garanta permissões de renovação e defina "
                    "ML_OAUTH_SCOPE (ex.: offline_access read write) se necessário; depois reconecte."
                ),
            )

        perfil = await self._fetch_ml_user(token.access_token)
        ml_user_id = token.user_id or (str(perfil.get("id")) if perfil.get("id") else None)
        ml_nickname = perfil.get("nickname") if isinstance(perfil.get("nickname"), str) else None

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(token.expires_in, 0))
        self.repo.save_tokens(
            empresa_id=empresa_id,
            access_token=self._encrypt_token(token.access_token),
            refresh_token=self._encrypt_token(token.refresh_token),
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
        refresh_plain = self._decrypt_token(integracao.refresh_token)
        if not refresh_plain:
            raise HTTPException(status_code=400, detail="Refresh token inválido para esta empresa.")

        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.ML_CLIENT_ID,
            "client_secret": settings.ML_CLIENT_SECRET,
            "refresh_token": refresh_plain,
        }
        response = await self._request_token(payload)

        expires_in = int(response.get("expires_in", 0) or 0)
        access_token = response.get("access_token")
        refresh_token = response.get("refresh_token")
        if not access_token or not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh de token retornou dados inválidos.")

        integracao.access_token = self._encrypt_token(access_token)
        integracao.refresh_token = self._encrypt_token(refresh_token)
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

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        return " ".join((texto or "").strip().lower().split())

    def _encrypt_token(self, valor: Optional[str]) -> Optional[str]:
        if not valor:
            return valor
        secret = (settings.ML_TOKEN_CRYPTO_SECRET or "").strip()
        if not secret:
            return valor
        key = hashlib.sha256(secret.encode("utf-8")).digest()
        raw = valor.encode("utf-8")
        crypt = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
        return "encv1:" + base64.urlsafe_b64encode(crypt).decode("ascii")

    def _decrypt_token(self, valor: Optional[str]) -> Optional[str]:
        if not valor:
            return valor
        if not str(valor).startswith("encv1:"):
            return valor
        secret = (settings.ML_TOKEN_CRYPTO_SECRET or "").strip()
        if not secret:
            return valor
        key = hashlib.sha256(secret.encode("utf-8")).digest()
        encoded = str(valor)[6:]
        raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
        plain = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
        return plain.decode("utf-8")

    @staticmethod
    def _status_ml_para_orcamento(status_ml: Optional[str]) -> Optional[StatusOrcamento]:
        mapa = {
            "paid": StatusOrcamento.APROVADO,
            "payment_required": StatusOrcamento.AGUARDANDO_PAGAMENTO,
            "cancelled": StatusOrcamento.RECUSADO,
            "confirmed": StatusOrcamento.ENVIADO,
            "processing": StatusOrcamento.EM_EXECUCAO,
        }
        if not status_ml:
            return None
        return mapa.get(str(status_ml).strip().lower())

    def _resolve_integration_user(self, empresa_id: int) -> Usuario:
        usuario = (
            self.db.query(Usuario)
            .filter(
                Usuario.empresa_id == empresa_id,
                Usuario.ativo == True,
            )
            .order_by(Usuario.is_gestor.desc(), Usuario.id.asc())
            .first()
        )
        if not usuario:
            raise HTTPException(
                status_code=400,
                detail="Não existe usuário ativo na empresa para registrar importação do Mercado Livre.",
            )
        return usuario

    def _resolver_cliente_ml(self, empresa_id: int, payload_pedido: Dict[str, Any]) -> Cliente:
        buyer = payload_pedido.get("buyer") if isinstance(payload_pedido, dict) else {}
        if not isinstance(buyer, dict):
            buyer = {}
        primeiro_nome = str(buyer.get("first_name") or "").strip()
        ultimo_nome = str(buyer.get("last_name") or "").strip()
        nome = " ".join(p for p in (primeiro_nome, ultimo_nome) if p).strip()
        if not nome:
            nome = str(buyer.get("nickname") or "").strip()
        if not nome:
            nome = f"Cliente ML {buyer.get('id') or 'Sem ID'}"

        email = str(buyer.get("email") or "").strip() or None
        telefone = None
        phone_obj = buyer.get("phone")
        if isinstance(phone_obj, dict):
            telefone = str(phone_obj.get("number") or "").strip() or None

        cliente = None
        buyer_id = buyer.get("id")
        marker = f"[ML_BUYER_ID:{buyer_id}]" if buyer_id else None
        if marker:
            cliente = (
                self.db.query(Cliente)
                .filter(
                    Cliente.empresa_id == empresa_id,
                    Cliente.observacoes.ilike(f"%{marker}%"),
                )
                .first()
            )
        if not cliente and email:
            cliente = (
                self.db.query(Cliente)
                .filter(
                    Cliente.empresa_id == empresa_id,
                    Cliente.email == email,
                )
                .first()
            )
        if not cliente:
            cliente = (
                self.db.query(Cliente)
                .filter(
                    Cliente.empresa_id == empresa_id,
                    Cliente.nome.ilike(nome),
                )
                .first()
            )
        if cliente:
            alterou = False
            if email and not cliente.email:
                cliente.email = email
                alterou = True
            if telefone and not cliente.telefone:
                cliente.telefone = telefone
                alterou = True
            if marker and marker not in (cliente.observacoes or ""):
                obs = (cliente.observacoes or "").strip()
                cliente.observacoes = f"{obs}\n{marker}".strip() if obs else marker
                alterou = True
            if alterou:
                self.db.add(cliente)
                self.db.flush()
            return cliente

        observacoes = marker or None
        novo = Cliente(
            empresa_id=empresa_id,
            nome=nome,
            email=email,
            telefone=telefone,
            observacoes=observacoes,
        )
        self.db.add(novo)
        self.db.flush()
        return novo

    def _match_servico_por_nome(self, empresa_id: int, titulo: str) -> Optional[Servico]:
        titulo_norm = self._normalizar_texto(titulo)
        if not titulo_norm:
            return None
        servicos = (
            self.db.query(Servico)
            .filter(
                Servico.empresa_id == empresa_id,
                Servico.ativo == True,
            )
            .all()
        )
        for servico in servicos:
            if self._normalizar_texto(servico.nome or "") == titulo_norm:
                return servico
        tokens = [t for t in titulo_norm.split() if len(t) >= 3]
        if not tokens:
            return None
        melhor = None
        melhor_score = 0.0
        for servico in servicos:
            nome_tokens = set(self._normalizar_texto(servico.nome or "").split())
            inter = nome_tokens.intersection(tokens)
            if not inter:
                continue
            score = len(inter) / max(len(tokens), 1)
            if score > melhor_score:
                melhor = servico
                melhor_score = score
        return melhor if melhor_score >= 0.6 else None

    def _montar_itens_orcamento_de_pedido(
        self, empresa_id: int, payload_pedido: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        order_items = payload_pedido.get("order_items")
        if not isinstance(order_items, list):
            return []
        itens: List[Dict[str, Any]] = []
        for linha in order_items:
            item = linha.get("item") if isinstance(linha, dict) else None
            if not isinstance(item, dict):
                continue
            titulo = str(item.get("title") or "Item Mercado Livre").strip()
            qtd_raw = linha.get("quantity", 1) if isinstance(linha, dict) else 1
            preco_raw = (
                linha.get("unit_price")
                if isinstance(linha, dict) and linha.get("unit_price") is not None
                else item.get("unit_price")
            )
            try:
                quantidade = max(Decimal(str(qtd_raw or 1)), Decimal("1"))
            except Exception:
                quantidade = Decimal("1")
            try:
                valor_unit = Decimal(str(preco_raw or 0))
            except Exception:
                valor_unit = Decimal("0")
            servico = self._match_servico_por_nome(empresa_id=empresa_id, titulo=titulo)
            itens.append(
                {
                    "descricao": titulo,
                    "quantidade": quantidade,
                    "valor_unit": valor_unit,
                    "servico_id": servico.id if servico else None,
                }
            )
        return itens

    def _importar_pedidos_snapshot_para_orcamentos(
        self, empresa_id: int, *, limit: int = 100
    ) -> Dict[str, int]:
        # Consulta explícita para manter legibilidade e evitar import circular local.
        from app.models.models import MercadoLivrePedidoSnapshot  # import local seguro

        snapshots = (
            self.db.query(MercadoLivrePedidoSnapshot)
            .filter(MercadoLivrePedidoSnapshot.empresa_id == empresa_id)
            .order_by(MercadoLivrePedidoSnapshot.atualizado_em_remoto.desc().nullslast())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        usuario = self._resolve_integration_user(empresa_id)
        criados = 0
        atualizados = 0
        ignorados = 0

        for snap in snapshots:
            payload = snap.payload_json if isinstance(snap.payload_json, dict) else {}
            ml_order_id = str(payload.get("id") or snap.resource_id or "").strip()
            if not ml_order_id:
                ignorados += 1
                continue

            status_ml = str(payload.get("status") or "").strip() or None
            status_destino = self._status_ml_para_orcamento(status_ml)
            vinculo = self.repo.get_pedido_vinculo(empresa_id=empresa_id, ml_order_id=ml_order_id)
            if vinculo:
                orc = (
                    self.db.query(Orcamento)
                    .filter(
                        Orcamento.id == vinculo.orcamento_id,
                        Orcamento.empresa_id == empresa_id,
                    )
                    .first()
                )
                if not orc:
                    self.repo.upsert_pedido_vinculo(
                        empresa_id=empresa_id,
                        ml_order_id=ml_order_id,
                        orcamento_id=vinculo.orcamento_id,
                        status_ml=status_ml,
                        status_sync="erro",
                        erro="Orçamento vinculado não encontrado.",
                    )
                    ignorados += 1
                    continue
                if status_destino and orc.status != status_destino:
                    orc.status = status_destino
                    self.db.add(
                        HistoricoEdicao(
                            orcamento_id=orc.id,
                            editado_por_id=usuario.id,
                            descricao=f"[MercadoLivre] Status sincronizado: {status_ml}",
                        )
                    )
                self.repo.upsert_pedido_vinculo(
                    empresa_id=empresa_id,
                    ml_order_id=ml_order_id,
                    orcamento_id=orc.id,
                    status_ml=status_ml,
                    status_sync="ok",
                )
                atualizados += 1
                continue

            cliente = self._resolver_cliente_ml(empresa_id, payload)
            itens = self._montar_itens_orcamento_de_pedido(empresa_id, payload)
            if not itens:
                itens = [
                    {
                        "descricao": f"Pedido Mercado Livre {ml_order_id}",
                        "quantidade": Decimal("1"),
                        "valor_unit": Decimal("0"),
                        "servico_id": None,
                    }
                ]
            observacoes = (
                f"[MercadoLivre] Pedido {ml_order_id} importado automaticamente."
            )
            orc = criar_orcamento_core(
                db=self.db,
                empresa=usuario.empresa,
                usuario_criador=usuario,
                cliente_id=cliente.id,
                itens=itens,
                origem="MercadoLivre",
                forma_pagamento="pix",
                validade_dias=7,
                observacoes=observacoes,
                desconto=Decimal("0"),
                desconto_tipo="percentual",
                agendamento_modo=None,
                regra_pagamento_id=None,
                mensagem_ia=None,
            )
            if status_destino:
                orc.status = status_destino
            self.repo.upsert_pedido_vinculo(
                empresa_id=empresa_id,
                ml_order_id=ml_order_id,
                orcamento_id=orc.id,
                status_ml=status_ml,
                status_sync="ok",
            )
            criados += 1
        self.db.flush()
        return {"importados_criados": criados, "importados_atualizados": atualizados, "importados_ignorados": ignorados}

    def _sync_catalogo_from_snapshots(
        self, empresa_id: int, *, limit: int = 200
    ) -> Dict[str, int]:
        from app.models.models import MercadoLivreAnuncioSnapshot  # import local seguro

        snapshots = (
            self.db.query(MercadoLivreAnuncioSnapshot)
            .filter(MercadoLivreAnuncioSnapshot.empresa_id == empresa_id)
            .order_by(MercadoLivreAnuncioSnapshot.atualizado_em_remoto.desc().nullslast())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        criados = 0
        atualizados = 0
        ignorados = 0
        for snap in snapshots:
            payload = snap.payload_json if isinstance(snap.payload_json, dict) else {}
            ml_item_id = str(payload.get("id") or snap.resource_id or "").strip()
            if not ml_item_id:
                ignorados += 1
                continue
            titulo = str(payload.get("title") or "").strip()
            if not titulo:
                ignorados += 1
                continue
            try:
                preco = Decimal(str(payload.get("price") or 0))
            except Exception:
                preco = Decimal("0")
            ativo_ml = str(payload.get("status") or "").lower() in {"active", "under_review", "paused"}

            vinculo = self.repo.get_item_vinculo_by_ml_item(empresa_id=empresa_id, ml_item_id=ml_item_id)
            servico = None
            if vinculo:
                servico = (
                    self.db.query(Servico)
                    .filter(Servico.id == vinculo.servico_id, Servico.empresa_id == empresa_id)
                    .first()
                )
            if not servico:
                servico = (
                    self.db.query(Servico)
                    .filter(
                        Servico.empresa_id == empresa_id,
                        or_(
                            Servico.nome.ilike(titulo),
                            Servico.nome.ilike(f"%{titulo}%"),
                        ),
                    )
                    .first()
                )
            if not servico:
                servico = Servico(
                    empresa_id=empresa_id,
                    nome=titulo,
                    descricao=str(payload.get("subtitle") or payload.get("warranty") or "").strip() or None,
                    preco_padrao=preco,
                    unidade="un",
                    ativo=ativo_ml,
                )
                self.db.add(servico)
                self.db.flush()
                criados += 1
            else:
                if not vinculo or vinculo.sync_mode != "cotte_only_push":
                    servico.nome = titulo
                    servico.preco_padrao = preco
                    servico.ativo = ativo_ml
                    self.db.add(servico)
                atualizados += 1

            vinculo = self.repo.upsert_item_vinculo(
                empresa_id=empresa_id,
                ml_item_id=ml_item_id,
                servico_id=servico.id,
                sync_mode=vinculo.sync_mode if vinculo else "ml_only_pull",
                allow_push_price=vinculo.allow_push_price if vinculo else False,
                allow_push_stock=vinculo.allow_push_stock if vinculo else False,
                allow_push_title=vinculo.allow_push_title if vinculo else False,
                allow_push_description=vinculo.allow_push_description if vinculo else False,
                source_of_truth=vinculo.source_of_truth if vinculo else "ml",
            )
            vinculo.last_pull_at = datetime.now(timezone.utc)
            self.db.add(vinculo)
        self.db.flush()
        return {"catalogo_criados": criados, "catalogo_atualizados": atualizados, "catalogo_ignorados": ignorados}

    async def _ml_put(
        self, *, endpoint: str, access_token: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = f"{settings.ML_API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {access_token}", "content-type": "application/json"}
        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.put(url, headers=headers, json=payload)
                if response.status_code == 429 and attempt < RETRY_MAX_ATTEMPTS:
                    await asyncio.sleep(RETRY_BASE_SECONDS * attempt)
                    continue
                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Erro Mercado Livre ({response.status_code}) em atualização de anúncio.",
                    )
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= RETRY_MAX_ATTEMPTS:
                    raise HTTPException(status_code=502, detail="Falha de rede ao atualizar anúncio no Mercado Livre.") from exc
                await asyncio.sleep(RETRY_BASE_SECONDS * attempt)
        raise HTTPException(status_code=502, detail="Falha inesperada ao atualizar anúncio no Mercado Livre.")

    async def _push_catalogo_updates(
        self, empresa_id: int, *, limit: int = 100
    ) -> Dict[str, int]:
        registro = await self._ensure_valid_token(empresa_id)
        access_token = self._decrypt_token(registro.access_token)
        if not access_token:
            raise HTTPException(status_code=401, detail="Token Mercado Livre inválido. Reconecte a conta.")
        from app.models.models import MercadoLivreItemVinculo  # import local seguro

        vinculos = (
            self.db.query(MercadoLivreItemVinculo)
            .filter(
                MercadoLivreItemVinculo.empresa_id == empresa_id,
                MercadoLivreItemVinculo.sync_mode.in_(["two_way", "cotte_only_push"]),
            )
            .order_by(MercadoLivreItemVinculo.atualizado_em.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        enviados = 0
        ignorados = 0
        falhas = 0
        for vinculo in vinculos:
            servico = (
                self.db.query(Servico)
                .filter(Servico.id == vinculo.servico_id, Servico.empresa_id == empresa_id)
                .first()
            )
            if not servico:
                ignorados += 1
                continue
            payload: Dict[str, Any] = {}
            if vinculo.allow_push_title:
                payload["title"] = servico.nome
            if vinculo.allow_push_price:
                payload["price"] = float(servico.preco_padrao or 0)
            if vinculo.allow_push_description and servico.descricao:
                payload["subtitle"] = servico.descricao[:120]
            if vinculo.allow_push_stock:
                payload["available_quantity"] = 1
            if not payload:
                ignorados += 1
                continue
            payload_hash = hashlib.sha256(
                str(sorted(payload.items())).encode("utf-8")
            ).hexdigest()
            if vinculo.last_push_hash == payload_hash:
                ignorados += 1
                continue
            try:
                await self._ml_put(
                    endpoint=f"/items/{vinculo.ml_item_id}",
                    access_token=access_token,
                    payload=payload,
                )
                vinculo.last_push_at = datetime.now(timezone.utc)
                vinculo.last_push_hash = payload_hash
                vinculo.ultimo_erro = None
                self.db.add(vinculo)
                enviados += 1
            except HTTPException as exc:
                vinculo.ultimo_erro = str(exc.detail)
                self.db.add(vinculo)
                falhas += 1
        self.db.flush()
        return {"push_enviados": enviados, "push_ignorados": ignorados, "push_falhas": falhas}

    async def sync_pedidos(self, empresa_id: int, limit: int = 50) -> Dict[str, Any]:
        registro = await self._ensure_valid_token(empresa_id)
        access_token = self._decrypt_token(registro.access_token)
        if not access_token:
            raise HTTPException(status_code=401, detail="Token Mercado Livre inválido. Reconecte a conta.")
        seller_id = registro.ml_user_id
        if not seller_id:
            raise HTTPException(status_code=400, detail="Conta Mercado Livre sem user_id vinculado.")

        limit = max(1, min(limit, 200))
        dados = await self._ml_get(
            endpoint="/orders/search/recent",
            access_token=access_token,
            params={"seller": seller_id, "sort": "date_desc", "limit": limit},
        )
        resultados = dados.get("results") if isinstance(dados.get("results"), list) else []
        consolidado = self.repo.upsert_pedidos(empresa_id, resultados)
        importacao = self._importar_pedidos_snapshot_para_orcamentos(empresa_id, limit=limit)
        self.repo.marcar_sync_pedidos(empresa_id)
        self.db.commit()
        return {"total_recebido": len(resultados), **consolidado, **importacao}

    async def sync_anuncios(self, empresa_id: int, limit: int = 50) -> Dict[str, Any]:
        registro = await self._ensure_valid_token(empresa_id)
        access_token = self._decrypt_token(registro.access_token)
        if not access_token:
            raise HTTPException(status_code=401, detail="Token Mercado Livre inválido. Reconecte a conta.")
        seller_id = registro.ml_user_id
        if not seller_id:
            raise HTTPException(status_code=400, detail="Conta Mercado Livre sem user_id vinculado.")

        limit = max(1, min(limit, 100))
        busca_ids = await self._ml_get(
            endpoint=f"/users/{seller_id}/items/search",
            access_token=access_token,
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
                access_token=access_token,
            )
            anuncios.append(detalhe)

        consolidado = self.repo.upsert_anuncios(empresa_id, anuncios)
        catalogo = self._sync_catalogo_from_snapshots(empresa_id, limit=limit)
        self.repo.marcar_sync_anuncios(empresa_id)
        self.db.commit()
        return {"total_recebido": len(anuncios), **consolidado, **catalogo}

    def list_pedido_vinculos(
        self, empresa_id: int, *, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        rows = self.repo.list_pedido_vinculos(empresa_id=empresa_id, limit=limit, offset=offset)
        items = [
            {
                "id": r.id,
                "ml_order_id": r.ml_order_id,
                "orcamento_id": r.orcamento_id,
                "status_ml": r.status_ml,
                "status_sync": r.status_sync,
                "erro": r.erro,
                "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
                "updated_at": r.atualizado_em.isoformat() if r.atualizado_em else None,
            }
            for r in rows
        ]
        return {"items": items, "count": len(items)}

    def list_item_vinculos(
        self, empresa_id: int, *, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        rows = self.repo.list_item_vinculos(empresa_id=empresa_id, limit=limit, offset=offset)
        items = [
            {
                "id": r.id,
                "ml_item_id": r.ml_item_id,
                "servico_id": r.servico_id,
                "sync_mode": r.sync_mode,
                "allow_push_price": bool(r.allow_push_price),
                "allow_push_stock": bool(r.allow_push_stock),
                "allow_push_title": bool(r.allow_push_title),
                "allow_push_description": bool(r.allow_push_description),
                "last_pull_at": r.last_pull_at.isoformat() if r.last_pull_at else None,
                "last_push_at": r.last_push_at.isoformat() if r.last_push_at else None,
                "last_error": r.ultimo_erro,
                "updated_at": r.atualizado_em.isoformat() if r.atualizado_em else None,
            }
            for r in rows
        ]
        return {"items": items, "count": len(items)}

    def list_sync_jobs(
        self, empresa_id: int, *, limit: int = 20, offset: int = 0
    ) -> Dict[str, Any]:
        rows = self.repo.list_sync_jobs(empresa_id=empresa_id, limit=limit, offset=offset)
        items = [
            {
                "id": r.id,
                "tipo": r.tipo,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "counters": r.counters_json,
                "error": r.erro,
                "trigger_source": r.trigger_source,
            }
            for r in rows
        ]
        return {"items": items, "count": len(items)}

    def configurar_item_vinculo(
        self,
        *,
        empresa_id: int,
        ml_item_id: str,
        servico_id: int,
        sync_mode: str,
        allow_push_price: bool,
        allow_push_stock: bool,
        allow_push_title: bool,
        allow_push_description: bool,
    ) -> Dict[str, Any]:
        modos_validos = {"ml_only_pull", "two_way", "cotte_only_push"}
        if sync_mode not in modos_validos:
            raise HTTPException(status_code=400, detail="sync_mode inválido.")

        servico = (
            self.db.query(Servico)
            .filter(Servico.id == servico_id, Servico.empresa_id == empresa_id)
            .first()
        )
        if not servico:
            raise HTTPException(status_code=404, detail="Serviço não encontrado.")

        vinculo = self.repo.upsert_item_vinculo(
            empresa_id=empresa_id,
            ml_item_id=ml_item_id,
            servico_id=servico_id,
            sync_mode=sync_mode,
            allow_push_price=allow_push_price,
            allow_push_stock=allow_push_stock,
            allow_push_title=allow_push_title,
            allow_push_description=allow_push_description,
            source_of_truth="ml" if sync_mode == "ml_only_pull" else "cotte",
        )
        self.db.commit()
        return {
            "id": vinculo.id,
            "ml_item_id": vinculo.ml_item_id,
            "servico_id": vinculo.servico_id,
            "sync_mode": vinculo.sync_mode,
            "allow_push_price": bool(vinculo.allow_push_price),
            "allow_push_stock": bool(vinculo.allow_push_stock),
            "allow_push_title": bool(vinculo.allow_push_title),
            "allow_push_description": bool(vinculo.allow_push_description),
        }

    def desvincular_item(self, *, empresa_id: int, servico_id: int) -> Dict[str, Any]:
        removido = self.repo.delete_item_vinculo(empresa_id=empresa_id, servico_id=servico_id)
        self.db.commit()
        return {"removed": bool(removido)}

    async def reprocessar_pedido(self, empresa_id: int, ml_order_id: str) -> Dict[str, Any]:
        from app.models.models import MercadoLivrePedidoSnapshot  # import local seguro

        snapshot = (
            self.db.query(MercadoLivrePedidoSnapshot)
            .filter(
                MercadoLivrePedidoSnapshot.empresa_id == empresa_id,
                MercadoLivrePedidoSnapshot.resource_id == str(ml_order_id),
            )
            .first()
        )
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot do pedido não encontrado.")
        resumo = self._importar_pedidos_snapshot_para_orcamentos(empresa_id, limit=1)
        self.db.commit()
        return {"ml_order_id": str(ml_order_id), **resumo}

    async def executar_sync_escopo(
        self, *, empresa_id: int, escopo: str, trigger_source: str = "manual"
    ) -> Dict[str, Any]:
        escopos_validos = {"pedidos", "catalogo_pull", "catalogo_push"}
        if escopo not in escopos_validos:
            raise HTTPException(status_code=400, detail="Escopo inválido.")

        lock_token = secrets.token_urlsafe(16)
        acquired = self.repo.acquire_lock(
            empresa_id=empresa_id,
            tipo=escopo,
            lock_token=lock_token,
            ttl_seconds=600,
        )
        if not acquired:
            raise HTTPException(
                status_code=409,
                detail=f"Já existe sincronização em andamento para o escopo {escopo}.",
            )
        self.db.commit()
        job = self.repo.create_sync_job(
            empresa_id=empresa_id,
            tipo=escopo,
            trigger_source=trigger_source,
        )
        self.db.commit()
        try:
            if escopo == "pedidos":
                counters = await self.sync_pedidos(empresa_id=empresa_id, limit=100)
            elif escopo == "catalogo_pull":
                counters = await self.sync_anuncios(empresa_id=empresa_id, limit=100)
            else:
                counters = await self._push_catalogo_updates(empresa_id=empresa_id, limit=200)
                self.db.commit()

            self.repo.finish_sync_job(
                job_id=job.id,
                status="success",
                counters_json=counters,
                erro=None,
            )
            self.db.commit()
            return {
                "job_id": job.id,
                "escopo": escopo,
                "status": "success",
                "counters": counters,
            }
        except Exception as exc:
            self.repo.finish_sync_job(
                job_id=job.id,
                status="error",
                counters_json=None,
                erro=str(exc),
            )
            self.db.commit()
            raise
        finally:
            self.repo.release_lock(
                empresa_id=empresa_id,
                tipo=escopo,
                lock_token=lock_token,
            )
            self.db.commit()

    async def executar_sync_periodico_empresas(self) -> Dict[str, Any]:
        if not settings.ML_SYNC_PERIODIC_ENABLED:
            return {"processed": 0, "success": 0, "errors": 0, "details": []}

        integracoes = (
            self.db.query(IntegracaoMercadoLivre)
            .filter(
                IntegracaoMercadoLivre.conectado == True,
                IntegracaoMercadoLivre.access_token.isnot(None),
            )
            .all()
        )
        details: List[Dict[str, Any]] = []
        success = 0
        errors = 0
        for integ in integracoes:
            try:
                result = await self.executar_sync_escopo(
                    empresa_id=integ.empresa_id,
                    escopo="pedidos",
                    trigger_source="periodic",
                )
                details.append(
                    {
                        "empresa_id": integ.empresa_id,
                        "status": "success",
                        "job_id": result.get("job_id"),
                    }
                )
                success += 1
            except Exception as exc:
                details.append(
                    {
                        "empresa_id": integ.empresa_id,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                errors += 1
                self.db.rollback()
        return {
            "processed": len(integracoes),
            "success": success,
            "errors": errors,
            "details": details,
        }

    async def processar_notificacao_webhook(
        self, notificacoes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        processadas = 0
        ignoradas = 0
        erros = 0

        for notif in notificacoes:
            topic = str(notif.get("topic") or "").strip().lower()
            resource = str(notif.get("resource") or "").strip()
            user_id = str(notif.get("user_id") or "").strip()

            if topic not in ("orders", "items") or not resource or not user_id:
                ignoradas += 1
                continue

            integracao = self.repo.get_integracao_by_ml_user_id(user_id)
            if not integracao:
                ignoradas += 1
                logger.warning("Notificação ML: integracao não encontrada para ml_user_id=%s", user_id)
                continue

            empresa_id = integracao.empresa_id

            try:
                registro = await self._ensure_valid_token(empresa_id)
                access_token = self._decrypt_token(registro.access_token)
                if not access_token:
                    erros += 1
                    continue

                if topic == "orders":
                    await self._processar_notificacao_pedido(
                        empresa_id=empresa_id,
                        resource=resource,
                        access_token=access_token,
                    )
                elif topic == "items":
                    await self._processar_notificacao_anuncio(
                        empresa_id=empresa_id,
                        resource=resource,
                        access_token=access_token,
                    )

                processadas += 1
            except Exception as exc:
                erros += 1
                logger.error(
                    "Erro ao processar notificação ML topic=%s resource=%s: %s",
                    topic,
                    resource,
                    exc,
                )
                try:
                    self.db.rollback()
                except Exception:
                    pass

        return {
            "total": len(notificacoes),
            "processadas": processadas,
            "ignoradas": ignoradas,
            "erros": erros,
        }

    async def _processar_notificacao_pedido(
        self, *, empresa_id: int, resource: str, access_token: str
    ) -> None:
        order_id = resource.rsplit("/", 1)[-1] if "/" in resource else resource
        if not order_id:
            return

        dados = await self._ml_get(
            endpoint=f"/orders/{order_id}",
            access_token=access_token,
        )
        if not dados or not dados.get("id"):
            return

        self.repo.upsert_pedidos(empresa_id, [dados])
        self._importar_pedidos_snapshot_para_orcamentos(empresa_id, limit=10)
        self.repo.marcar_sync_pedidos(empresa_id)
        self.db.commit()

    async def _processar_notificacao_anuncio(
        self, *, empresa_id: int, resource: str, access_token: str
    ) -> None:
        item_id = resource.rsplit("/", 1)[-1] if "/" in resource else resource
        if not item_id:
            return

        dados = await self._ml_get(
            endpoint=f"/items/{item_id}",
            access_token=access_token,
        )
        if not dados or not dados.get("id"):
            return

        self.repo.upsert_anuncios(empresa_id, [dados])
        self._sync_catalogo_from_snapshots(empresa_id, limit=10)
        self.repo.marcar_sync_anuncios(empresa_id)
        self.db.commit()
