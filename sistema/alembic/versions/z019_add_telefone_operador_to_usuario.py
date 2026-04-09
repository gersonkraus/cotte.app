"""add_telefone_operador_to_usuario

Adiciona campo telefone_operador na tabela usuarios para suportar
múltiplos operadores individuais via WhatsApp.

Revision ID: z019_add_telefone_operador_to_usuario
Revises: z018_pre_agendamento_fila, z_merge_p_and_e_heads
Create Date: 2026-04-09
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = 'z019_add_telefone_operador_to_usuario'
down_revision: Union[str, tuple] = ('z018_pre_agendamento_fila', 'z_merge_p_and_e_heads')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'usuarios',
        sa.Column('telefone_operador', sa.String(20), nullable=True),
    )
    op.create_index(
        'ix_usuario_telefone_operador',
        'usuarios',
        ['telefone_operador'],
    )


def downgrade() -> None:
    op.drop_index('ix_usuario_telefone_operador', table_name='usuarios')
    op.drop_column('usuarios', 'telefone_operador')
