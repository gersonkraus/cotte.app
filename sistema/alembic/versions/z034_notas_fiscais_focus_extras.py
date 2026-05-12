"""Adiciona focus_extras (JSON) em notas_fiscais para eventos Focus (ex.: CC-e).

Revision ID: z034_notas_fiscais_focus_extras
Revises: z033_focus_certificado_empresa
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "z034_notas_fiscais_focus_extras"
down_revision = "z033_focus_certificado_empresa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notas_fiscais",
        sa.Column("focus_extras", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notas_fiscais", "focus_extras")
