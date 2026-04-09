"""add_permissoes_column_usuario

Revision ID: p001_add_permissoes_column_usuario
Revises: b53c78511b78
Create Date: 2026-03-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = "p001_add_permissoes"
down_revision: Union[str, None] = "b53c78511b78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Usa SQL nativo para evitar erro se a coluna já existir
    op.execute("""
        ALTER TABLE usuarios
        ADD COLUMN IF NOT EXISTS permissoes JSONB;
    """)
    op.execute("UPDATE usuarios SET permissoes = '{}' WHERE permissoes IS NULL")


def downgrade() -> None:
    op.drop_column("usuarios", "permissoes")
