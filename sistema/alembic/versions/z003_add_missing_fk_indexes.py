"""add missing FK indexes for performance

Revision ID: z003_add_missing_fk_indexes
Revises: z002_obrigatorio_doc
Create Date: 2026-03-20 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'z003_add_missing_fk_indexes'
down_revision: Union[str, Sequence[str], None] = 'z002_obrigatorio_doc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_orcamentos_cliente_id', 'orcamentos', ['cliente_id'], unique=False)
    op.create_index('ix_itens_orcamento_orcamento_id', 'itens_orcamento', ['orcamento_id'], unique=False)
    op.create_index('ix_historico_edicoes_orcamento_id', 'historico_edicoes', ['orcamento_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_historico_edicoes_orcamento_id', table_name='historico_edicoes')
    op.drop_index('ix_itens_orcamento_orcamento_id', table_name='itens_orcamento')
    op.drop_index('ix_orcamentos_cliente_id', table_name='orcamentos')
