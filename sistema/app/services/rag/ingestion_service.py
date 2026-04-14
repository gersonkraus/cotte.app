"""Ingestão de contexto por tenant para RAG."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.models import AIChatMensagem, AIChatSessao, DocumentoEmpresa
from app.services.rag.chunking import chunk_text
from app.services.rag.vector_store import TenantDocument


class TenantRAGIngestionService:
    @staticmethod
    def build_documents_for_empresa(
        *,
        db: Session,
        empresa_id: int,
        lookback_days: int = 120,
        max_chat_rows: int = 120,
        max_docs_rows: int = 60,
    ) -> list[TenantDocument]:
        docs: list[TenantDocument] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        chat_rows = (
            db.query(AIChatMensagem.content, AIChatMensagem.criado_em)
            .join(AIChatSessao, AIChatMensagem.sessao_id == AIChatSessao.id)
            .filter(
                AIChatSessao.empresa_id == empresa_id,
                AIChatMensagem.role == "user",
                AIChatMensagem.criado_em >= cutoff,
            )
            .order_by(AIChatMensagem.criado_em.desc())
            .limit(max_chat_rows)
            .all()
        )
        for row in chat_rows:
            text = (row.content or "").strip()
            if not text:
                continue
            docs.append(
                TenantDocument(
                    text=text[:1200],
                    source="chat_history",
                    metadata={
                        "created_at": str(getattr(row, "criado_em", "") or ""),
                        "boost": 0.4,
                    },
                )
            )

        doc_rows = (
            db.query(
                DocumentoEmpresa.id,
                DocumentoEmpresa.nome,
                DocumentoEmpresa.descricao,
                DocumentoEmpresa.conteudo_html,
            )
            .filter(
                DocumentoEmpresa.empresa_id == empresa_id,
                DocumentoEmpresa.deletado_em.is_(None),
            )
            .order_by(DocumentoEmpresa.id.desc())
            .limit(max_docs_rows)
            .all()
        )
        for row in doc_rows:
            base = " ".join(
                [
                    (row.nome or "").strip(),
                    (row.descricao or "").strip(),
                    (row.conteudo_html or "").strip(),
                ]
            ).strip()
            if not base:
                continue
            for part in chunk_text(base, chunk_size=800, overlap=160):
                docs.append(
                    TenantDocument(
                        text=part,
                        source="documento_empresa",
                        metadata={"doc_id": row.id, "doc_nome": row.nome, "boost": 0.2},
                    )
                )

        return docs

