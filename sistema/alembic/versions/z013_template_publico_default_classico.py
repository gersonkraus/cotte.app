"""Set template_publico default to classico.

Revision ID: z013_template_publico_default_classico
Revises: z012_template_publico
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "z013_template_publico_default_classico"
down_revision = "z012a_widen_alembic_ver"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "empresas",
        "template_publico",
        existing_type=sa.String(length=50),
        server_default="classico",
        existing_nullable=True,
    )
    op.execute(
        "UPDATE empresas SET template_publico = 'classico' WHERE template_publico IS NULL"
    )


def downgrade():
    op.alter_column(
        "empresas",
        "template_publico",
        existing_type=sa.String(length=50),
        server_default="moderno",
        existing_nullable=True,
    )
