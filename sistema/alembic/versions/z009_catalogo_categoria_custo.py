"""Adiciona tabela categorias_catalogo e colunas categoria_id/preco_custo em servicos.

Revision ID: z009_cat_custo
Revises: z008_default_perms
Create Date: 2026-03-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "z009_cat_custo"
down_revision: Union[str, Sequence[str], None] = "z008_default_perms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categorias_catalogo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("nome", sa.String(100), nullable=False),
    )
    op.add_column("servicos", sa.Column("categoria_id", sa.Integer, sa.ForeignKey("categorias_catalogo.id"), nullable=True))
    op.add_column("servicos", sa.Column("preco_custo", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("servicos", "preco_custo")
    op.drop_column("servicos", "categoria_id")
    op.drop_table("categorias_catalogo")
