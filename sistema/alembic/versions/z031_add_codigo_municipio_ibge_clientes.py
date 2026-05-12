"""add codigo_municipio_ibge to clientes

Revision ID: z031_add_codigo_municipio_ibge_clientes
Revises: z030_merge_fiscal_and_head
Create Date: 2026-05-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "z031_add_codigo_municipio_ibge_clientes"
down_revision: Union[str, Sequence[str]] = "z030_merge_fiscal_and_head"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("codigo_municipio_ibge", sa.String(7), nullable=True))


def downgrade() -> None:
    op.drop_column("clientes", "codigo_municipio_ibge")
