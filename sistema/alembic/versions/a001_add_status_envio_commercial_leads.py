"""add_status_envio_commercial_leads

Adiciona coluna status_envio à tabela commercial_leads se não existir.

Revision ID: a001_add_status_envio
Revises: z001_merge_all_heads
Create Date: 2026-03-20 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'a001_add_status_envio'
down_revision: Union[str, None] = 'z001_merge_all_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona coluna status_envio se não existir."""
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'commercial_leads' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('commercial_leads')]
        
        if 'status_envio' not in columns:
            op.add_column(
                'commercial_leads',
                sa.Column('status_envio', sa.String(20), server_default='nao_enviado', nullable=True)
            )
            # Atualizar registros existentes
            op.execute("UPDATE commercial_leads SET status_envio = 'nao_enviado' WHERE status_envio IS NULL")


def downgrade() -> None:
    """Remove coluna status_envio."""
    connection = op.get_bind()
    inspector = inspect(connection)

    if 'commercial_leads' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('commercial_leads')]
        
        if 'status_envio' in columns:
            op.drop_column('commercial_leads', 'status_envio')
