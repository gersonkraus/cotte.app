"""merge all heads

Revision ID: z020_merge_all_heads
Revises: r002_fix_status_orcamento_enum, tc001_tool_call_log, z019_add_telefone_operador_to_usuario
Create Date: 2026-04-09

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision = 'z020_merge_all_heads'
down_revision = ('r002_fix_status_orcamento_enum', 'tc001_tool_call_log', 'z019_add_telefone_operador_to_usuario')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
