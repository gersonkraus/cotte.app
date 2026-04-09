"""add_agendamento_opcoes

Revision ID: 9efd81e17334
Revises: a90994237bcc
Create Date: 2026-03-25 22:19:11.393249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9efd81e17334'
down_revision: Union[str, None] = 'a90994237bcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar tabela de opções
    op.create_table('agendamento_opcoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agendamento_id', sa.Integer(), nullable=False),
        sa.Column('data_hora', sa.DateTime(timezone=True), nullable=False),
        sa.Column('disponivel', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agendamento_id'], ['agendamentos.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agendamento_opcoes_id'), 'agendamento_opcoes', ['id'], unique=False)
    op.create_index(op.f('ix_agendamento_opcoes_agendamento_id'), 'agendamento_opcoes', ['agendamento_id'], unique=False)

    # 2. Tornar data_agendada nullable (cliente ainda não escolheu)
    op.alter_column('agendamentos', 'data_agendada',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True)

    # 3. Adicionar opcao_escolhida_id em agendamentos
    op.add_column('agendamentos', sa.Column('opcao_escolhida_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_agendamentos_opcao_escolhida', 'agendamentos', 'agendamento_opcoes', ['opcao_escolhida_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_agendamentos_opcao_escolhida', 'agendamentos', type_='foreignkey')
    op.drop_column('agendamentos', 'opcao_escolhida_id')
    op.alter_column('agendamentos', 'data_agendada',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False)
    op.drop_index(op.f('ix_agendamento_opcoes_agendamento_id'), table_name='agendamento_opcoes')
    op.drop_index(op.f('ix_agendamento_opcoes_id'), table_name='agendamento_opcoes')
    op.drop_table('agendamento_opcoes')
