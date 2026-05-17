"""Utility for indexing the database schema into pgvector."""
from __future__ import annotations

import logging
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.database import Base
from app.ai.rag.service import SemanticRAGService

logger = logging.getLogger(__name__)

async def index_all_tables(db: Session):
    """Iterates over all SQLAlchemy models and indexes them."""
    logger.info("Starting database schema indexing...")
    
    # Get all tables registered in the Base
    for table_name, table in Base.metadata.tables.items():
        # Skip internal or irrelevant tables
        if table_name.startswith("alembic_") or table_name in ["ai_database_schema_index", "ai_documentos_conhecimento"]:
            continue
            
        columns = []
        for column in table.columns:
            col_info = {
                "name": column.name,
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "foreign_keys": [str(fk.target_fullname) for fk in column.foreign_keys]
            }
            columns.append(col_info)
            
        # Try to get a description (we can use docstrings or a manual map)
        description = table.comment or f"Tabela {table_name} contendo dados do sistema COTTE."
        
        schema_info = {
            "table": table_name,
            "columns": columns,
            "comment": table.comment
        }
        
        logger.info(f"Indexing table: {table_name}")
        await SemanticRAGService.index_table_schema(
            db=db,
            table_name=table_name,
            description=description,
            schema_info=schema_info
        )
        
    logger.info("Database schema indexing completed.")

def get_schema_summary(db: Session) -> str:
    """Returns a textual summary of the schema for LLM context."""
    from app.models.models import AIDatabaseSchemaIndex
    
    indexes = db.query(AIDatabaseSchemaIndex).all()
    summary = []
    for idx in indexes:
        cols = [c["name"] for m in [idx.schema_json] for c in m.get("columns", [])]
        summary.append(f"Table: {idx.table_name}. Description: {idx.description}. Columns: {', '.join(cols)}")
        
    return "\n".join(summary)
