"""add_cupom_kiwify_to_empresa

Revision ID: 25a618cb66f6
Revises: i001
Create Date: 2026-03-17 11:49:20.108488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25a618cb66f6'
down_revision: Union[str, None] = 'i001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('empresas', sa.Column('cupom_kiwify', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('empresas', 'cupom_kiwify')
