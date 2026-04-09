"""Add enviar_pdf_whatsapp to empresa

Revision ID: b4255a56f865
Revises: 9d9578b69335
Create Date: 2026-04-03 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b4255a56f865'
down_revision: Union[str, None] = '9d9578b69335'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('empresas', sa.Column('enviar_pdf_whatsapp', sa.Boolean(), nullable=True, server_default='false'))
    op.execute("UPDATE empresas SET enviar_pdf_whatsapp = false WHERE enviar_pdf_whatsapp IS NULL")


def downgrade() -> None:
    op.drop_column('empresas', 'enviar_pdf_whatsapp')
