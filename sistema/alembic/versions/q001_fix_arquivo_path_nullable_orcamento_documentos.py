"""fix: orcamento_documentos.arquivo_path nullable para documentos HTML

Revision ID: q001_fix_arquivo_path_nullable
Revises: z011_numero_personalizavel
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = "q001_fix_arquivo_path_nullable"
down_revision = "z011_numero_personalizavel"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "orcamento_documentos",
        "arquivo_path",
        existing_type=sa.String(length=500),
        nullable=True,
    )


def downgrade():
    # Limpa NULLs antes de reverter (documentos HTML usavam "")
    op.execute(
        "UPDATE orcamento_documentos SET arquivo_path = '' WHERE arquivo_path IS NULL"
    )
    op.alter_column(
        "orcamento_documentos",
        "arquivo_path",
        existing_type=sa.String(length=500),
        nullable=False,
    )
