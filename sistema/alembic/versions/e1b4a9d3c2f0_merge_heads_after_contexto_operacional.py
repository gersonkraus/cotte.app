"""merge heads after contexto_operacional

Revision ID: e1b4a9d3c2f0
Revises: 899e50f244c5, c8f2d1a9b401
Create Date: 2026-04-28 00:00:01.000000
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "e1b4a9d3c2f0"
down_revision: Union[str, None] = ("899e50f244c5", "c8f2d1a9b401")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
