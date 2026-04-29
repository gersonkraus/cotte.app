"""add endereco to tenant commercial leads

Revision ID: tc006_add_endereco_tenant
Revises: fix_sistema_enum
Create Date: 2026-04-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "tc006_add_endereco_tenant"
down_revision: Union[str, tuple[str, str], None] = "fix_sistema_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_commercial_leads",
        sa.Column("endereco", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_commercial_leads", "endereco")
