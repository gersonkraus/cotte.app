"""add preco_custo to servicos

Revision ID: 20260323_preco_custo
Revises: 20260323_doc_tracking
Create Date: 2026-03-23 14:50:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_preco_custo"
down_revision = "20260323_doc_tracking"
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
    if not _coluna_existe("servicos", "preco_custo"):
        op.add_column(
            "servicos", sa.Column("preco_custo", sa.Numeric(10, 2), nullable=True)
        )


def downgrade():
    op.drop_column("servicos", "preco_custo")
