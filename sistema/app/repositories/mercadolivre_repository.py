from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional, List

from sqlalchemy.orm import Session

from app.models.models import (
    IntegracaoMercadoLivre,
    MercadoLivreAnuncioSnapshot,
    MercadoLivreItemVinculo,
    MercadoLivrePedidoSnapshot,
    MercadoLivrePedidoVinculo,
    MercadoLivreSyncJob,
    MercadoLivreSyncLock,
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

    def get_integracao_by_ml_user_id(self, ml_user_id: str) -> Optional[IntegracaoMercadoLivre]:
        return (
            self.db.query(IntegracaoMercadoLivre)
            .filter(
                IntegracaoMercadoLivre.ml_user_id == str(ml_user_id),
                IntegracaoMercadoLivre.conectado == True,
                IntegracaoMercadoLivre.access_token.isnot(None),
            )
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

    # ── VÍNCULOS DE PEDIDOS ────────────────────────────────────────────────

    def get_pedido_vinculo(
        self, empresa_id: int, ml_order_id: str
    ) -> Optional[MercadoLivrePedidoVinculo]:
        return (
            self.db.query(MercadoLivrePedidoVinculo)
            .filter(
                MercadoLivrePedidoVinculo.empresa_id == empresa_id,
                MercadoLivrePedidoVinculo.ml_order_id == str(ml_order_id),
            )
            .first()
        )

    def list_pedido_vinculos(
        self, empresa_id: int, *, limit: int = 50, offset: int = 0
    ) -> List[MercadoLivrePedidoVinculo]:
        return (
            self.db.query(MercadoLivrePedidoVinculo)
            .filter(MercadoLivrePedidoVinculo.empresa_id == empresa_id)
            .order_by(MercadoLivrePedidoVinculo.atualizado_em.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def upsert_pedido_vinculo(
        self,
        *,
        empresa_id: int,
        ml_order_id: str,
        orcamento_id: int,
        status_ml: Optional[str],
        status_sync: str = "ok",
        erro: Optional[str] = None,
    ) -> MercadoLivrePedidoVinculo:
        registro = self.get_pedido_vinculo(empresa_id=empresa_id, ml_order_id=ml_order_id)
        if not registro:
            registro = MercadoLivrePedidoVinculo(
                empresa_id=empresa_id,
                ml_order_id=str(ml_order_id),
                orcamento_id=orcamento_id,
            )
        registro.orcamento_id = orcamento_id
        registro.status_ml = status_ml
        registro.status_sync = status_sync
        registro.erro = erro
        registro.last_seen_at = datetime.now(timezone.utc)
        self.db.add(registro)
        self.db.flush()
        return registro

    # ── VÍNCULOS DE CATÁLOGO ───────────────────────────────────────────────

    def get_item_vinculo_by_ml_item(
        self, empresa_id: int, ml_item_id: str
    ) -> Optional[MercadoLivreItemVinculo]:
        return (
            self.db.query(MercadoLivreItemVinculo)
            .filter(
                MercadoLivreItemVinculo.empresa_id == empresa_id,
                MercadoLivreItemVinculo.ml_item_id == str(ml_item_id),
            )
            .first()
        )

    def get_item_vinculo_by_servico(
        self, empresa_id: int, servico_id: int
    ) -> Optional[MercadoLivreItemVinculo]:
        return (
            self.db.query(MercadoLivreItemVinculo)
            .filter(
                MercadoLivreItemVinculo.empresa_id == empresa_id,
                MercadoLivreItemVinculo.servico_id == servico_id,
            )
            .first()
        )

    def list_item_vinculos(
        self, empresa_id: int, *, limit: int = 100, offset: int = 0
    ) -> List[MercadoLivreItemVinculo]:
        return (
            self.db.query(MercadoLivreItemVinculo)
            .filter(MercadoLivreItemVinculo.empresa_id == empresa_id)
            .order_by(MercadoLivreItemVinculo.atualizado_em.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def upsert_item_vinculo(
        self,
        *,
        empresa_id: int,
        ml_item_id: str,
        servico_id: int,
        sync_mode: str = "ml_only_pull",
        allow_push_price: bool = False,
        allow_push_stock: bool = False,
        allow_push_title: bool = False,
        allow_push_description: bool = False,
        source_of_truth: str = "ml",
        last_push_hash: Optional[str] = None,
    ) -> MercadoLivreItemVinculo:
        registro = self.get_item_vinculo_by_ml_item(empresa_id=empresa_id, ml_item_id=ml_item_id)
        if not registro:
            registro = MercadoLivreItemVinculo(
                empresa_id=empresa_id,
                ml_item_id=str(ml_item_id),
                servico_id=servico_id,
            )
        registro.servico_id = servico_id
        registro.sync_mode = sync_mode
        registro.allow_push_price = bool(allow_push_price)
        registro.allow_push_stock = bool(allow_push_stock)
        registro.allow_push_title = bool(allow_push_title)
        registro.allow_push_description = bool(allow_push_description)
        registro.source_of_truth = source_of_truth
        if last_push_hash is not None:
            registro.last_push_hash = last_push_hash
        self.db.add(registro)
        self.db.flush()
        return registro

    def delete_item_vinculo(
        self, *, empresa_id: int, servico_id: int
    ) -> bool:
        registro = self.get_item_vinculo_by_servico(
            empresa_id=empresa_id,
            servico_id=servico_id,
        )
        if not registro:
            return False
        self.db.delete(registro)
        self.db.flush()
        return True

    # ── JOBS E LOCKS ───────────────────────────────────────────────────────

    def create_sync_job(
        self, *, empresa_id: int, tipo: str, trigger_source: str = "manual"
    ) -> MercadoLivreSyncJob:
        job = MercadoLivreSyncJob(
            empresa_id=empresa_id,
            tipo=tipo,
            status="running",
            trigger_source=trigger_source,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def finish_sync_job(
        self,
        *,
        job_id: int,
        status: str,
        counters_json: Optional[Dict[str, Any]] = None,
        erro: Optional[str] = None,
    ) -> Optional[MercadoLivreSyncJob]:
        job = self.db.query(MercadoLivreSyncJob).filter(MercadoLivreSyncJob.id == job_id).first()
        if not job:
            return None
        job.status = status
        job.finished_at = datetime.now(timezone.utc)
        job.counters_json = counters_json
        job.erro = erro
        self.db.add(job)
        self.db.flush()
        return job

    def list_sync_jobs(
        self, empresa_id: int, *, limit: int = 20, offset: int = 0
    ) -> List[MercadoLivreSyncJob]:
        return (
            self.db.query(MercadoLivreSyncJob)
            .filter(MercadoLivreSyncJob.empresa_id == empresa_id)
            .order_by(MercadoLivreSyncJob.started_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def acquire_lock(
        self, *, empresa_id: int, tipo: str, lock_token: str, ttl_seconds: int = 600
    ) -> bool:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=max(30, ttl_seconds))
        lock = (
            self.db.query(MercadoLivreSyncLock)
            .filter(
                MercadoLivreSyncLock.empresa_id == empresa_id,
                MercadoLivreSyncLock.tipo == tipo,
            )
            .first()
        )
        if lock and lock.expires_at and lock.expires_at > now and lock.lock_token != lock_token:
            return False
        if not lock:
            lock = MercadoLivreSyncLock(
                empresa_id=empresa_id,
                tipo=tipo,
                lock_token=lock_token,
                expires_at=expires_at,
            )
        else:
            lock.lock_token = lock_token
            lock.expires_at = expires_at
        self.db.add(lock)
        self.db.flush()
        return True

    def release_lock(self, *, empresa_id: int, tipo: str, lock_token: str) -> None:
        lock = (
            self.db.query(MercadoLivreSyncLock)
            .filter(
                MercadoLivreSyncLock.empresa_id == empresa_id,
                MercadoLivreSyncLock.tipo == tipo,
                MercadoLivreSyncLock.lock_token == lock_token,
            )
            .first()
        )
        if lock:
            self.db.delete(lock)
            self.db.flush()
