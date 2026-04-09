"""add obrigatorio to orcamento_documentos

Revision ID: z002_obrigatorio_doc (curto: alembic_version.version_num costuma ser VARCHAR(32))
Revises: z001_merge_all_heads
Create Date: 2026-03-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z002_obrigatorio_doc"
down_revision: Union[str, Sequence[str], None] = 'z001_merge_all_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'orcamento_documentos',
        sa.Column('obrigatorio', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('orcamento_documentos', 'obrigatorio')
