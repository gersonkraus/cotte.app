"""Add template_orcamento to empresa

Revision ID: 9d9578b69335
Revises: z018_pre_agendamento_fila
Create Date: 2026-04-03 20:38:20.738389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9d9578b69335'
down_revision: Union[str, None] = 'z018_pre_agendamento_fila'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('empresas', sa.Column('template_orcamento', sa.String(length=50), nullable=True, server_default='classico'))
    op.execute("UPDATE empresas SET template_orcamento = 'classico' WHERE template_orcamento IS NULL")


def downgrade() -> None:
    op.drop_column('empresas', 'template_orcamento')
