"""add empresa_id to commercial_leads

Revision ID: e6ac99cf785c
Revises: r001_add_status_intermediarios
Create Date: 2026-03-24 16:49:04.045337

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6ac99cf785c"
down_revision: Union[str, None] = "r001_add_status_intermediarios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commercial_leads", sa.Column("empresa_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "commercial_leads",
        sa.Column("conta_criada_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_commercial_leads_empresa_id"),
        "commercial_leads",
        ["empresa_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_commercial_leads_empresa_id"), table_name="commercial_leads")
    op.drop_column("commercial_leads", "conta_criada_em")
    op.drop_column("commercial_leads", "empresa_id")
