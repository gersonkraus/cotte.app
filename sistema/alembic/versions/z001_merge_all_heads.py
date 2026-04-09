"""merge all heads

Merge migration para resolver os multiplos heads criados por branches paralelas.

Revision ID: z001_merge_all_heads
Revises: 9999999999999, b633b63e31e4, d60f6d62a957
Create Date: 2026-03-20 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'z001_merge_all_heads'
down_revision: Union[str, Sequence[str], None] = ('9999999999999', 'b633b63e31e4', 'd60f6d62a957')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass