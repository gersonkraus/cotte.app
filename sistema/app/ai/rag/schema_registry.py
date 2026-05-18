"""Schema Registry — singleton para indexação e busca semântica do schema do banco.

Indexado no startup via SchemaRegistry.initialize(db). Expõe
get_relevant_tables(query, db) para injeção de contexto no DataAgent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

_EXCLUDED_TABLES: frozenset[str] = frozenset({
    "ai_database_schema_index",
    "ai_documentos_conhecimento",
})
_EXCLUDED_PREFIXES = ("alembic_",)

# Colunas sensíveis nunca expostas ao LLM
_SENSITIVE_COLUMNS: frozenset[str] = frozenset({
    "senha_hash", "password_hash", "reset_token", "api_key",
    "refresh_token", "token_hash", "secret", "private_key",
})


@dataclass
class TableSchema:
    table: str
    columns: List[str]
    description: str

    def to_prompt_line(self) -> str:
        cols = ", ".join(self.columns[:15])  # limita colunas exibidas
        return f"- {self.table}({cols}): {self.description}"


class SchemaRegistry:
    _initialized: bool = False

    @classmethod
    async def initialize(cls, db) -> None:
        """Indexa todas as tabelas no pgvector. Chamado no startup do FastAPI.

        Tolerante a falha — um erro não bloqueia o startup.
        """
        from app.core.database import Base
        from app.ai.rag.service import SemanticRAGService

        count = 0
        errors = 0
        for table_name, table in Base.metadata.tables.items():
            if table_name in _EXCLUDED_TABLES:
                continue
            if any(table_name.startswith(p) for p in _EXCLUDED_PREFIXES):
                continue

            safe_columns = [
                {"name": col.name, "type": str(col.type), "nullable": col.nullable}
                for col in table.columns
                if col.name not in _SENSITIVE_COLUMNS
            ]

            description = table.comment or f"Tabela {table_name} do sistema COTTE."
            schema_info = {"table": table_name, "columns": safe_columns}

            try:
                await SemanticRAGService.index_table_schema(
                    db=db,
                    table_name=table_name,
                    description=description,
                    schema_info=schema_info,
                )
                count += 1
            except Exception as exc:
                logger.warning("[SchemaRegistry] Falha ao indexar %s: %s", table_name, exc)
                errors += 1

        cls._initialized = True
        logger.info("[SchemaRegistry] Indexação concluída: %d tabelas, %d erros.", count, errors)

    @classmethod
    async def get_relevant_tables(
        cls, query: str, *, top_k: int = 5, db=None
    ) -> List[TableSchema]:
        """Retorna tabelas mais relevantes para a query via pgvector cosine similarity."""
        if db is None:
            return []
        try:
            from app.ai.rag.service import SemanticRAGService

            results = await SemanticRAGService.search_schema(db=db, query=query, top_k=top_k)
            tables = []
            for idx in results:
                schema_info = idx.schema_json or {}
                columns = [c["name"] for c in schema_info.get("columns", [])]
                tables.append(
                    TableSchema(
                        table=idx.table_name,
                        columns=columns,
                        description=idx.description or "",
                    )
                )
            return tables
        except Exception as exc:
            logger.warning("[SchemaRegistry] Falha na busca de schema: %s", exc)
            return []

    @classmethod
    def format_schema_context(cls, tables: List[TableSchema]) -> str:
        """Formata tabelas em bloco de texto para injeção no system prompt do DataAgent."""
        if not tables:
            return ""
        lines = [
            "### Schema relevante (use para construir SQL):",
        ]
        for t in tables:
            lines.append(t.to_prompt_line())
        lines.append(
            "\nREGRA OBRIGATÓRIA: Todo SQL deve incluir `empresa_id = :empresa_id` "
            "no WHERE ou JOIN. O executor faz bind automático do valor correto."
        )
        return "\n".join(lines)
