"""remove_orcamentos_agendamento_fk

Revision ID: a90994237bcc
Revises: 407429405c03
Create Date: 2026-03-25 20:50:34.106067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a90994237bcc'
down_revision: Union[str, None] = '407429405c03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove FK reversa de orcamentos → agendamentos (a FK vive em agendamentos.orcamento_id)
    op.drop_index('ix_orcamentos_agendamento_id', table_name='orcamentos')
    op.drop_constraint('fk_orcamentos_agendamento_id', 'orcamentos', type_='foreignkey')
    op.drop_column('orcamentos', 'agendamento_id')


def downgrade() -> None:
    op.add_column('orcamentos', sa.Column('agendamento_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_orcamentos_agendamento_id', 'orcamentos', 'agendamentos', ['agendamento_id'], ['id'])
    op.create_index('ix_orcamentos_agendamento_id', 'orcamentos', ['agendamento_id'], unique=False)
