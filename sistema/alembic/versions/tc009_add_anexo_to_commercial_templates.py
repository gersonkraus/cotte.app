"""add anexo fields to commercial_templates

Revision ID: tc009_add_anexo_to_commercial_templates
Revises: ml004_expand_ml_token_scope_text
Create Date: 2026-05-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "tc009_add_anexo_to_commercial_templates"
down_revision: Union[str, Sequence[str]] = "ml004_expand_ml_token_scope_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("commercial_templates", sa.Column("anexo_arquivo_path", sa.String(500), nullable=True))
    op.add_column("commercial_templates", sa.Column("anexo_nome_original", sa.String(255), nullable=True))
    op.add_column("commercial_templates", sa.Column("anexo_mime_type", sa.String(120), nullable=True))
    op.add_column("commercial_templates", sa.Column("anexo_tamanho_bytes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("commercial_templates", "anexo_tamanho_bytes")
    op.drop_column("commercial_templates", "anexo_mime_type")
    op.drop_column("commercial_templates", "anexo_nome_original")
    op.drop_column("commercial_templates", "anexo_arquivo_path")
