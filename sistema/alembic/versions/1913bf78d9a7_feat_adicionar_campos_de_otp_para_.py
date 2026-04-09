"""feat: adicionar campos de OTP para aceite público

Revision ID: 1913bf78d9a7
Revises: q001_fix_arquivo_path_nullable
Create Date: 2026-03-23 20:19:24.443042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1913bf78d9a7'
down_revision: Union[str, None] = 'q001_fix_arquivo_path_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Empresas: exigir_otp_aceite
    op.add_column('empresas', sa.Column('exigir_otp_aceite', sa.Boolean(), server_default=sa.false(), nullable=False))
    # Orcamentos: aceite_confirmado_otp
    op.add_column('orcamentos', sa.Column('aceite_confirmado_otp', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column('orcamentos', 'aceite_confirmado_otp')
    op.drop_column('empresas', 'exigir_otp_aceite')
