"""merge p and e heads

Merge migration to resolve multiple heads: e11faf9b0ad1 and p003_add_missing_empresa_columns.

Revision ID: z_merge_p_and_e_heads
Revises: e11faf9b0ad1, p003_add_missing_empresa_columns
Create Date: 2026-03-23 11:27:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'z_merge_p_and_e_heads'
down_revision = ('e11faf9b0ad1', 'p003_add_missing_empresa_columns')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
