"""Adiciona focus_certificado_configurado e focus_certificado_validade a empresas

Revision ID: z033_focus_certificado_empresa
Revises: z032_focus_nfe_migration
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "z033_focus_certificado_empresa"
down_revision = "z032_focus_nfe_migration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column(
            "focus_certificado_configurado",
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "empresas",
        sa.Column(
            "focus_certificado_validade",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("empresas", "focus_certificado_validade")
    op.drop_column("empresas", "focus_certificado_configurado")
