"""add_status_aguardando_escolha

Revision ID: 2420bef5d6a4
Revises: 9efd81e17334
Create Date: 2026-03-25 22:35:00

"""
from typing import Sequence, Union
from alembic import op

revision: str = '2420bef5d6a4'
down_revision: Union[str, None] = '9efd81e17334'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE statusagendamento ADD VALUE IF NOT EXISTS 'AGUARDANDO_ESCOLHA'")


def downgrade() -> None:
    # PostgreSQL não suporta remover valores de enum
    pass
