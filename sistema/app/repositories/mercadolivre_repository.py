from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.models import (
    IntegracaoMercadoLivre,
    MercadoLivreAnuncioSnapshot,
    MercadoLivrePedidoSnapshot,
)


class MercadoLivreRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_integracao(self, empresa_id: int) -> Optional[IntegracaoMercadoLivre]:
        return (
            self.db.query(IntegracaoMercadoLivre)
            .filter(IntegracaoMercadoLivre.empresa_id == empresa_id)
            .first()
        )

    def get_or_create_integracao(self, empresa_id: int) -> IntegracaoMercadoLivre:
        existente = self.get_integracao(empresa_id)
        if existente:
            return existente
        nova = IntegracaoMercadoLivre(empresa_id=empresa_id, conectado=False)
        self.db.add(nova)
        self.db.flush()
        return nova

    def save_tokens(
        self,
        *,
        empresa_id: int,
        access_token: str,
        refresh_token: str,
        token_type: str,
        scope: str,
        expires_at: datetime,
        ml_user_id: Optional[str],
        ml_nickname: Optional[str],
    ) -> IntegracaoMercadoLivre:
        registro = self.get_or_create_integracao(empresa_id)
        registro.access_token = access_token
        registro.refresh_token = refresh_token
        registro.token_type = token_type
        registro.token_scope = scope
        registro.token_expires_at = expires_at
        registro.ml_user_id = ml_user_id
        registro.ml_nickname = ml_nickname
        registro.conectado = True
        registro.ultimo_erro = None
        registro.oauth_state = None
        registro.oauth_state_expira_em = None
        self.db.add(registro)
        self.db.flush()
        return registro

    def set_oauth_state(
        self, empresa_id: int, state: str, expira_em: datetime
    ) -> IntegracaoMercadoLivre:
        registro = self.get_or_create_integracao(empresa_id)
        registro.oauth_state = state
        registro.oauth_state_expira_em = expira_em
        self.db.add(registro)
        self.db.flush()
        return registro

    def marcar_erro(self, empresa_id: int, mensagem: str) -> None:
        registro = self.get_or_create_integracao(empresa_id)
        registro.ultimo_erro = mensagem
        self.db.add(registro)
        self.db.flush()

    def marcar_sync_pedidos(self, empresa_id: int) -> None:
        registro = self.get_or_create_integracao(empresa_id)
        registro.ultimo_sync_pedidos_em = datetime.now(timezone.utc)
        self.db.add(registro)
        self.db.flush()

    def marcar_sync_anuncios(self, empresa_id: int) -> None:
        registro = self.get_or_create_integracao(empresa_id)
        registro.ultimo_sync_anuncios_em = datetime.now(timezone.utc)
        self.db.add(registro)
        self.db.flush()

    def desconectar(self, empresa_id: int) -> IntegracaoMercadoLivre:
        registro = self.get_or_create_integracao(empresa_id)
        registro.access_token = None
        registro.refresh_token = None
        registro.token_type = None
        registro.token_scope = None
        registro.token_expires_at = None
        registro.ml_user_id = None
        registro.ml_nickname = None
        registro.conectado = False
        registro.oauth_state = None
        registro.oauth_state_expira_em = None
        registro.ultimo_erro = None
        self.db.add(registro)
        self.db.flush()
        return registro

    @staticmethod
    def _hash_payload(payload: Dict[str, Any]) -> str:
        serializado = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serializado.encode("utf-8")).hexdigest()

    def upsert_pedidos(
        self, empresa_id: int, pedidos: Iterable[Dict[str, Any]]
    ) -> Dict[str, int]:
        inseridos = 0
        atualizados = 0
        ignorados = 0

        for pedido in pedidos:
            resource_id = str(pedido.get("id") or "").strip()
            if not resource_id:
                ignorados += 1
                continue

            payload_hash = self._hash_payload(pedido)
            existente = (
                self.db.query(MercadoLivrePedidoSnapshot)
                .filter(
                    MercadoLivrePedidoSnapshot.empresa_id == empresa_id,
                    MercadoLivrePedidoSnapshot.resource_id == resource_id,
                )
                .first()
            )

            atualizado_em_remoto = None
            date_closed = pedido.get("date_closed")
            if isinstance(date_closed, str) and date_closed:
                try:
                    atualizado_em_remoto = datetime.fromisoformat(
                        date_closed.replace("Z", "+00:00")
                    )
                except ValueError:
                    atualizado_em_remoto = None

            status = pedido.get("status")
            if existente:
                if existente.payload_hash == payload_hash:
                    ignorados += 1
                    continue
                existente.payload_hash = payload_hash
                existente.payload_json = pedido
                existente.status = str(status) if status else None
                existente.atualizado_em_remoto = atualizado_em_remoto
                atualizados += 1
                continue

            novo = MercadoLivrePedidoSnapshot(
                empresa_id=empresa_id,
                resource_id=resource_id,
                status=str(status) if status else None,
                atualizado_em_remoto=atualizado_em_remoto,
                payload_hash=payload_hash,
                payload_json=pedido,
            )
            self.db.add(novo)
            inseridos += 1

        return {"inseridos": inseridos, "atualizados": atualizados, "ignorados": ignorados}

    def upsert_anuncios(
        self, empresa_id: int, anuncios: Iterable[Dict[str, Any]]
    ) -> Dict[str, int]:
        inseridos = 0
        atualizados = 0
        ignorados = 0

        for anuncio in anuncios:
            resource_id = str(anuncio.get("id") or "").strip()
            if not resource_id:
                ignorados += 1
                continue

            payload_hash = self._hash_payload(anuncio)
            existente = (
                self.db.query(MercadoLivreAnuncioSnapshot)
                .filter(
                    MercadoLivreAnuncioSnapshot.empresa_id == empresa_id,
                    MercadoLivreAnuncioSnapshot.resource_id == resource_id,
                )
                .first()
            )

            atualizado_em_remoto = None
            last_updated = anuncio.get("last_updated")
            if isinstance(last_updated, str) and last_updated:
                try:
                    atualizado_em_remoto = datetime.fromisoformat(
                        last_updated.replace("Z", "+00:00")
                    )
                except ValueError:
                    atualizado_em_remoto = None

            status = anuncio.get("status")
            if existente:
                if existente.payload_hash == payload_hash:
                    ignorados += 1
                    continue
                existente.payload_hash = payload_hash
                existente.payload_json = anuncio
                existente.status = str(status) if status else None
                existente.atualizado_em_remoto = atualizado_em_remoto
                atualizados += 1
                continue

            novo = MercadoLivreAnuncioSnapshot(
                empresa_id=empresa_id,
                resource_id=resource_id,
                status=str(status) if status else None,
                atualizado_em_remoto=atualizado_em_remoto,
                payload_hash=payload_hash,
                payload_json=anuncio,
            )
            self.db.add(novo)
            inseridos += 1

        return {"inseridos": inseridos, "atualizados": atualizados, "ignorados": ignorados}
