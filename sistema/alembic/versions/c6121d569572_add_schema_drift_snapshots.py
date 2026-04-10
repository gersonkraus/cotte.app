"""add schema drift snapshots

Revision ID: c6121d569572
Revises: 3344d22be19b
Create Date: 2026-04-10 12:40:23.201462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6121d569572'
down_revision: Union[str, None] = '3344d22be19b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schema_drift_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("app_version", sa.String(length=50), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="manual_admin"),
        sa.Column("status_ok", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("missing_tables_json", sa.JSON(), nullable=True),
        sa.Column("missing_columns_json", sa.JSON(), nullable=True),
        sa.Column("extra_columns_json", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_schema_drift_snapshots_criado_em",
        "schema_drift_snapshots",
        ["criado_em"],
    )
    op.create_index(
        "ix_schema_drift_snapshots_source",
        "schema_drift_snapshots",
        ["source"],
    )
    op.create_index(
        "ix_schema_drift_snapshots_status_ok",
        "schema_drift_snapshots",
        ["status_ok"],
    )


def downgrade() -> None:
    op.drop_index("ix_schema_drift_snapshots_status_ok", table_name="schema_drift_snapshots")
    op.drop_index("ix_schema_drift_snapshots_source", table_name="schema_drift_snapshots")
    op.drop_index("ix_schema_drift_snapshots_criado_em", table_name="schema_drift_snapshots")
    op.drop_table("schema_drift_snapshots")
