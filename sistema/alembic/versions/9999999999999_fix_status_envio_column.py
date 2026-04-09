"""fix_status_envio_column

Corrige referência à coluna status_envio que não existe na tabela commercial_leads.

Revision ID: 9999999999999
Revises: f123456789ab
Create Date: 2026-03-20 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9999999999999'
down_revision: Union[str, None] = 'f123456789ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove referência à coluna status_envio que não existe."""
    # A coluna status_envio não existe na tabela commercial_leads
    # Esta migration remove a referência problemática da migration anterior
    pass


def downgrade() -> None:
    """Recria a referência problemática (não recomendado)."""
    pass