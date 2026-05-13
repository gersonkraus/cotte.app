"""Preenche criado_em nulo em notas_fiscais (legado).

Revision ID: z035_backfill_notas_fiscais_criado_em
Revises: z034_notas_fiscais_focus_extras
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "z035_backfill_notas_fiscais_criado_em"
down_revision = "z034_notas_fiscais_focus_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE notas_fiscais
                SET criado_em = COALESCE(emitida_em, timezone('utc', now()))
                WHERE criado_em IS NULL
                """
            )
        )
    else:
        op.execute(
            sa.text(
                """
                UPDATE notas_fiscais
                SET criado_em = COALESCE(emitida_em, datetime('now'))
                WHERE criado_em IS NULL
                """
            )
        )


def downgrade() -> None:
    pass
