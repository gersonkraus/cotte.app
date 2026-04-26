"""add schema drift snapshots

Revision ID: c6121d569572
Revises: 3344d22be19b
Create Date: 2026-04-10 12:40:23.201462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c6121d569572'
down_revision: Union[str, None] = '3344d22be19b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "schema_drift_snapshots"

    def has_table() -> bool:
        return table_name in set(inspector.get_table_names())

    def has_index(index_name: str) -> bool:
        if not has_table():
            return False
        return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table_name)}

    if not has_table():
        op.create_table(
            table_name,
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
    if not has_index("ix_schema_drift_snapshots_criado_em"):
        op.create_index(
            "ix_schema_drift_snapshots_criado_em",
            table_name,
            ["criado_em"],
        )
    if not has_index("ix_schema_drift_snapshots_source"):
        op.create_index(
            "ix_schema_drift_snapshots_source",
            table_name,
            ["source"],
        )
    if not has_index("ix_schema_drift_snapshots_status_ok"):
        op.create_index(
            "ix_schema_drift_snapshots_status_ok",
            table_name,
            ["status_ok"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "schema_drift_snapshots"

    if table_name not in set(inspector.get_table_names()):
        return

    index_names = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if "ix_schema_drift_snapshots_status_ok" in index_names:
        op.drop_index("ix_schema_drift_snapshots_status_ok", table_name=table_name)
    if "ix_schema_drift_snapshots_source" in index_names:
        op.drop_index("ix_schema_drift_snapshots_source", table_name=table_name)
    if "ix_schema_drift_snapshots_criado_em" in index_names:
        op.drop_index("ix_schema_drift_snapshots_criado_em", table_name=table_name)
    op.drop_table(table_name)
