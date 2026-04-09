"""Adiciona status_pipeline em commercial_leads se ausente (legado / DB parcial).

Revision ID: z005_status_pipeline_missing
Revises: z004_merge_z003_heads
Create Date: 2026-03-20

Corrige UndefinedColumn em produção quando a tabela existe sem a coluna
(p.ex. migrações antigas incompletas ou banco criado fora da cadeia 002).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z005_status_pipeline_missing"
down_revision: Union[str, Sequence[str], None] = "z004_merge_z003_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "commercial_leads" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("commercial_leads")}
    if "status_pipeline" in cols:
        return
    op.add_column(
        "commercial_leads",
        sa.Column(
            "status_pipeline",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'novo'"),
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "commercial_leads" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("commercial_leads")}
    if "status_pipeline" not in cols:
        return
    op.drop_column("commercial_leads", "status_pipeline")
