"""add categoria_id to servicos

Revision ID: 20260323_categoria_id_servicos
Revises: 20260323_merge_heads
Create Date: 2026-03-23 14:53:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_categoria_id_servicos"
down_revision = "20260323_merge_heads"
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


def _fk_existe(nome: str) -> bool:
    """Verifica se uma foreign key já existe."""
    bind = op.get_bind()
    result = sa.text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = :nome AND constraint_type = 'FOREIGN KEY'"
    ).bindparams(nome=nome)
    return bind.execute(result).scalar() is not None


def upgrade():
    if not _coluna_existe("servicos", "categoria_id"):
        op.add_column(
            "servicos", sa.Column("categoria_id", sa.Integer(), nullable=True)
        )

    if not _fk_existe("fk_servicos_categoria_id"):
        op.create_foreign_key(
            "fk_servicos_categoria_id",
            "servicos",
            "categorias_catalogo",
            ["categoria_id"],
            ["id"],
        )


def downgrade():
    op.drop_constraint("fk_servicos_categoria_id", "servicos", type_="foreignkey")
    op.drop_column("servicos", "categoria_id")
