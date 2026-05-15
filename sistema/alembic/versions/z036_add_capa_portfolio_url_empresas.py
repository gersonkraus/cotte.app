"""add capa_portfolio_url to empresas

Revision ID: z036_capa_portfolio
Revises: cb1bf41ded7b
Create Date: 2026-05-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z036_capa_portfolio"
down_revision: Union[str, None] = "cb1bf41ded7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column("capa_portfolio_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("empresas", "capa_portfolio_url")
