"""RAG Service with pgvector support for semantic search."""
from __future__ import annotations

import logging
from typing import Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.models import AIDocumentoConhecimento, AIDatabaseSchemaIndex
from app.ai.service import ia_service

logger = logging.getLogger(__name__)

class SemanticRAGService:
    """Service for semantic search and indexing using pgvector."""
    
    @staticmethod
    async def index_document(
        db: Session, 
        empresa_id: int, 
        conteudo: str, 
        fonte: str = "manual",
        metadata: dict | None = None
    ) -> AIDocumentoConhecimento:
        """Indexes a document by generating its embedding and saving to DB."""
        embedding = await ia_service.get_embedding(conteudo)
        
        doc = AIDocumentoConhecimento(
            empresa_id=empresa_id,
            conteudo=conteudo,
            embedding=embedding,
            fonte=fonte,
            metadata_json=metadata or {}
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    async def search_documents(
        db: Session, 
        empresa_id: int, 
        query: str, 
        top_k: int = 4
    ) -> List[AIDocumentoConhecimento]:
        """Performs semantic search restricted to a single empresa."""
        if not query:
            return []
            
        embedding = await ia_service.get_embedding(query)
        
        # pgvector similarity search
        # <-> is L2 distance, <=> is cosine distance
        # We use cosine distance (lower is better)
        stmt = (
            select(AIDocumentoConhecimento)
            .filter(AIDocumentoConhecimento.empresa_id == empresa_id)
            .order_by(AIDocumentoConhecimento.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        
        result = db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def index_table_schema(
        db: Session, 
        table_name: str, 
        description: str,
        schema_info: dict
    ) -> AIDatabaseSchemaIndex:
        """Indexes a database table schema for the DataAgent."""
        # Combine table name and description for embedding
        text_to_embed = f"Table: {table_name}. Description: {description}"
        embedding = await ia_service.get_embedding(text_to_embed)
        
        # Check if already exists
        idx = db.query(AIDatabaseSchemaIndex).filter_by(table_name=table_name).first()
        if not idx:
            idx = AIDatabaseSchemaIndex(table_name=table_name)
            db.add(idx)
            
        idx.description = description
        idx.embedding = embedding
        idx.schema_json = schema_info
        
        db.commit()
        db.refresh(idx)
        return idx

    @staticmethod
    async def search_schema(db: Session, query: str, top_k: int = 3) -> List[AIDatabaseSchemaIndex]:
        """Finds relevant tables for a given query."""
        embedding = await ia_service.get_embedding(query)
        
        stmt = (
            select(AIDatabaseSchemaIndex)
            .order_by(AIDatabaseSchemaIndex.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        
        result = db.execute(stmt)
        return result.scalars().all()
