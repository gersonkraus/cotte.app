"""fix: add missing columns to orcamento_documentos

Revision ID: ba10b6a06e17
Revises: a60e82cc379b
Create Date: 2026-03-23 21:17:24.876882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba10b6a06e17'
down_revision: Union[str, None] = 'a60e82cc379b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona conteudo_html se não existir (para snapshots de documentos HTML)
    op.add_column('orcamento_documentos', sa.Column('conteudo_html', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('orcamento_documentos', 'conteudo_html')
