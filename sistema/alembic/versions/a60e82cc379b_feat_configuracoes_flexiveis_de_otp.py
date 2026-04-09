"""feat: configuracoes flexiveis de otp

Revision ID: a60e82cc379b
Revises: 1913bf78d9a7
Create Date: 2026-03-23 20:43:16.719653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a60e82cc379b'
down_revision: Union[str, None] = '1913bf78d9a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Empresa: valor mínimo para o gatilho automático de OTP
    op.add_column('empresas', sa.Column('otp_valor_minimo', sa.Numeric(precision=10, scale=2), server_default=sa.text('0'), nullable=False))
    # Orcamento: override manual (exigir ou não para este orçamento específico)
    op.add_column('orcamentos', sa.Column('exigir_otp', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column('orcamentos', 'exigir_otp')
    op.drop_column('empresas', 'otp_valor_minimo')
