"""add SISTEMA to canalinteracao enum

Revision ID: fix_sistema_enum
Revises: e1b4a9d3c2f0
Create Date: 2026-04-28

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "fix_sistema_enum"
down_revision: Union[str, None] = "e1b4a9d3c2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    result = bind.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'SISTEMA' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'canalinteracao'))"
        )
    )
    if not result.scalar():
        bind.execute(text("ALTER TYPE canalinteracao ADD VALUE 'SISTEMA'"))


def downgrade() -> None:
    pass
