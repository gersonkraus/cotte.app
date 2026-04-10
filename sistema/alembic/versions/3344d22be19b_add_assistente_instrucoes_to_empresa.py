"""add assistente_instrucoes to empresa

Revision ID: 3344d22be19b
Revises: z021_ai_chat_sessoes
Create Date: 2026-04-10 11:54:26.567346

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3344d22be19b'
down_revision: Union[str, None] = 'z021_ai_chat_sessoes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE empresas
        ADD COLUMN IF NOT EXISTS assistente_instrucoes TEXT
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE empresas
        DROP COLUMN IF EXISTS assistente_instrucoes
        """
    )
