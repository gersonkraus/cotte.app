"""Cria tabela config_global para configurações persistentes da plataforma.

Revision ID: z010_config_global
Revises: z009_cat_custo
Create Date: 2026-03-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "z010_config_global"
down_revision: Union[str, Sequence[str], None] = "z009_cat_custo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_global",
        sa.Column("chave", sa.String(100), primary_key=True),
        sa.Column("valor", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("config_global")
