"""fix: permite superadmin sem empresa vinculada (empresa_id nullable em usuarios)

Revision ID: s002_superadmin_empresa_nullable
Revises: s001_papeis_rbac
Create Date: 2026-03-24
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "s002_superadmin_empresa_nullable"
down_revision: Union[str, None] = "s001_papeis_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "usuarios",
        "empresa_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Antes de tornar NOT NULL de volta, zere os superadmins sem empresa
    op.execute(
        "UPDATE usuarios SET empresa_id = (SELECT id FROM empresas ORDER BY id LIMIT 1) "
        "WHERE empresa_id IS NULL AND is_superadmin = TRUE"
    )
    op.alter_column(
        "usuarios",
        "empresa_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
