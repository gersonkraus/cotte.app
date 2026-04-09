"""Add template_publico to empresas

Revision ID: z012_template_publico
Revises: 60754c29faf4
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "z012_template_publico"
down_revision = "60754c29faf4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "empresas",
        sa.Column("template_publico", sa.String(50), server_default="moderno"),
    )


def downgrade():
    op.drop_column("empresas", "template_publico")
