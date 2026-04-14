"""Retriever RAG por tenant integrado ao assistente."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.services.rag.chunking import compact_join
from app.services.rag.ingestion_service import TenantRAGIngestionService
from app.services.rag.vector_store import TenantVectorStore


class TenantRAGService:
    _store = TenantVectorStore()
    _refresh_state: dict[int, datetime] = {}
    _refresh_ttl_seconds = 180

    @classmethod
    def is_enabled(cls) -> bool:
        return os.getenv("ENABLE_TENANT_RAG", "true").lower() == "true"

    @classmethod
    def _should_refresh(cls, empresa_id: int) -> bool:
        now = datetime.now(timezone.utc)
        last = cls._refresh_state.get(empresa_id)
        if last is None:
            return True
        return (now - last) > timedelta(seconds=cls._refresh_ttl_seconds)

    @classmethod
    def refresh_empresa_if_needed(cls, *, db: Session, empresa_id: int) -> None:
        if not cls._should_refresh(empresa_id):
            return
        docs = TenantRAGIngestionService.build_documents_for_empresa(
            db=db, empresa_id=empresa_id
        )
        cls._store.upsert_many(empresa_id=empresa_id, docs=docs)
        cls._refresh_state[empresa_id] = datetime.now(timezone.utc)

    @classmethod
    def build_prompt_context(
        cls,
        *,
        db: Session,
        empresa_id: int,
        query: str,
        top_k: int = 4,
        max_chars: int = 2400,
    ) -> dict:
        if not cls.is_enabled() or not empresa_id:
            return {}
        cls.refresh_empresa_if_needed(db=db, empresa_id=empresa_id)
        hits = cls._store.similarity_search(
            empresa_id=empresa_id,
            query=query,
            top_k=top_k,
        )
        if not hits:
            return {}

        sources = []
        parts = []
        for hit in hits:
            src = hit.source
            if src == "documento_empresa":
                src = f"documento:{hit.metadata.get('doc_nome') or hit.metadata.get('doc_id')}"
            sources.append(src)
            parts.append(hit.text)

        return {
            "sources": sources,
            "context": compact_join(parts, max_chars=max_chars),
            "top_k": top_k,
        }

