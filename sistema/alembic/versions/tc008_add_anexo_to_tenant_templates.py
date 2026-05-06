"""add anexo fields to tenant templates

Revision ID: tc008_add_anexo_to_tenant_templates
Revises: tc007_add_full_address_fields_to_tenant_leads
Create Date: 2026-05-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "tc008_add_anexo_to_tenant_templates"
down_revision = "tc007_add_full_address_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_commercial_templates",
        sa.Column("anexo_arquivo_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "tenant_commercial_templates",
        sa.Column("anexo_nome_original", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tenant_commercial_templates",
        sa.Column("anexo_mime_type", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "tenant_commercial_templates",
        sa.Column("anexo_tamanho_bytes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_commercial_templates", "anexo_tamanho_bytes")
    op.drop_column("tenant_commercial_templates", "anexo_mime_type")
    op.drop_column("tenant_commercial_templates", "anexo_nome_original")
    op.drop_column("tenant_commercial_templates", "anexo_arquivo_path")
