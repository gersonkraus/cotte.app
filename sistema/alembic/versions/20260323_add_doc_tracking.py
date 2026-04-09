"""Add document tracking fields to orcamento_documentos

Revision ID: 20260323_doc_tracking
Revises: 00b953ce3024
Create Date: 2026-03-23 14:35:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_doc_tracking"
down_revision = "00b953ce3024"
branch_labels = None
depends_on = None


def _coluna_existe(tabela: str, coluna: str) -> bool:
    """Verifica se uma coluna já existe na tabela."""
    bind = op.get_bind()
    result = sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :tabela AND column_name = :coluna"
    ).bindparams(tabela=tabela, coluna=coluna)
    return bind.execute(result).scalar() is not None


def upgrade():
    if not _coluna_existe("orcamento_documentos", "visualizado_em"):
        op.add_column(
            "orcamento_documentos",
            sa.Column("visualizado_em", sa.DateTime(timezone=True), nullable=True),
        )
    if not _coluna_existe("orcamento_documentos", "aceito_em"):
        op.add_column(
            "orcamento_documentos",
            sa.Column("aceito_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade():
    op.drop_column("orcamento_documentos", "aceito_em")
    op.drop_column("orcamento_documentos", "visualizado_em")
