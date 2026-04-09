"""backfill_notif_whats_visualizacao_default

Revision ID: 00b953ce3024
Revises: ac64aef565f2
Create Date: 2026-03-14 01:17:08.853907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00b953ce3024'
down_revision: Union[str, None] = 'ac64aef565f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Preenche registros existentes que ficaram com NULL
    op.execute("UPDATE empresas SET notif_whats_visualizacao = TRUE WHERE notif_whats_visualizacao IS NULL")
    # Adiciona server_default para novos registros
    op.alter_column('empresas', 'notif_whats_visualizacao',
                    server_default=sa.text('TRUE'),
                    nullable=False)


def downgrade() -> None:
    op.alter_column('empresas', 'notif_whats_visualizacao',
                    server_default=None,
                    nullable=True)
