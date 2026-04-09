"""add performance indices orcamentos_empresa_criado and notificacoes_empresa_lida

Revision ID: 60754c29faf4
Revises: w004_pagto_idemp_empresa
Create Date: 2026-03-28 20:26:26.432310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60754c29faf4'
down_revision: Union[str, None] = 'w004_pagto_idemp_empresa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create performance indices for multi-tenant queries
    # ix_orcamentos_empresa_criado: enables fast listing of quotes by company
    op.execute("CREATE INDEX IF NOT EXISTS ix_orcamentos_empresa_criado ON orcamentos (empresa_id, criado_em)")

    # ix_notificacoes_empresa_lida: enables fast filtering unread notifications
    op.execute("CREATE INDEX IF NOT EXISTS ix_notificacoes_empresa_lida ON notificacoes (empresa_id, lida)")


def downgrade() -> None:
    # Drop performance indices
    op.drop_index('ix_notificacoes_empresa_lida', table_name='notificacoes')
    op.drop_index('ix_orcamentos_empresa_criado', table_name='orcamentos')
