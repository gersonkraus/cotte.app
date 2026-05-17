"""feat: pgvector RAG infrastructure

Revision ID: z037_pgvector_rag
Revises: z036_capa_portfolio
Create Date: 2026-05-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "z037_pgvector_rag"
down_revision: Union[str, None] = "7a32aaef5122"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ativar extensão pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Tabela de Documentos de Conhecimento (Multi-tenant)
    op.create_table(
        "ai_documentos_conhecimento",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True), # Placeholder
        sa.Column("fonte", sa.String(length=200), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Cast para Vector(1536)
    op.execute("ALTER TABLE ai_documentos_conhecimento ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector")

    # 3. Tabela de Indexação de Schema do Banco (Global/Admin)
    op.create_table(
        "ai_database_schema_index",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("table_name", sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=True), # Placeholder
        sa.Column("schema_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.execute("ALTER TABLE ai_database_schema_index ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector")

    # 4. Índices de busca vetorial (HNSW para performance)
    op.execute("CREATE INDEX idx_ai_docs_embedding ON ai_documentos_conhecimento USING hnsw (embedding vector_cosine_ops)")
    op.execute("CREATE INDEX idx_ai_schema_embedding ON ai_database_schema_index USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.drop_table("ai_database_schema_index")
    op.drop_table("ai_documentos_conhecimento")
    # Não removemos a extensão por segurança (pode ser usada por outras tabelas futuras)
