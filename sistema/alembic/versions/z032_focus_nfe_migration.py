"""Migração Notaas → Focus NFe: remove colunas notaas_*, adiciona focus_ref e denegada

Revision ID: z032_focus_nfe_migration
Revises: z031_add_codigo_municipio_ibge_clientes
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "z032_focus_nfe_migration"
down_revision = "z031_add_codigo_municipio_ibge_clientes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remover colunas Notaas da tabela empresas
    op.drop_column("empresas", "notaas_project_id")
    op.drop_column("empresas", "notaas_api_key")
    op.drop_column("empresas", "notaas_ambiente")
    op.drop_column("empresas", "notaas_webhook_secret")

    # Remover colunas Notaas da tabela notas_fiscais
    op.drop_column("notas_fiscais", "notaas_invoice_id")
    op.drop_column("notas_fiscais", "notaas_delivery_id")

    # Adicionar novos campos Focus
    op.add_column("notas_fiscais", sa.Column("focus_ref", sa.String(120), nullable=True))
    op.add_column("notas_fiscais", sa.Column("denegada", sa.Boolean(), nullable=True, server_default=sa.false()))

    # Adicionar nfe_ambiente na tabela empresas
    op.add_column("empresas", sa.Column("nfe_ambiente", sa.String(20), nullable=True, server_default="homologacao"))

    # Índice para busca por focus_ref
    op.create_index("ix_notas_fiscais_focus_ref", "notas_fiscais", ["focus_ref"])


def downgrade() -> None:
    op.drop_index("ix_notas_fiscais_focus_ref", "notas_fiscais")
    op.drop_column("notas_fiscais", "denegada")
    op.drop_column("notas_fiscais", "focus_ref")
    op.drop_column("empresas", "nfe_ambiente")
    op.add_column("notas_fiscais", sa.Column("notaas_delivery_id", sa.String(100), nullable=True))
    op.add_column("notas_fiscais", sa.Column("notaas_invoice_id", sa.String(100), nullable=True))
    op.add_column("empresas", sa.Column("notaas_webhook_secret", sa.String(200), nullable=True))
    op.add_column("empresas", sa.Column("notaas_ambiente", sa.String(20), server_default="homologacao"))
    op.add_column("empresas", sa.Column("notaas_api_key", sa.String(200), nullable=True))
    op.add_column("empresas", sa.Column("notaas_project_id", sa.String(100), nullable=True))
