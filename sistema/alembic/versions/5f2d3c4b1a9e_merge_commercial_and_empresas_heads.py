"""merge commercial and empresas heads

Revision ID: 5f2d3c4b1a9e
Revises: 003_add_comercial_extended, 00b953ce3024
Create Date: 2026-03-14 02:10:00

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "5f2d3c4b1a9e"
down_revision: Union[str, Sequence[str], None] = ("003_add_comercial_extended", "00b953ce3024")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
