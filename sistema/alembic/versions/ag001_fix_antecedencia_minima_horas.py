"""fix_antecedencia_minima_horas_default

Revision ID: ag001_fix_antecedencia
Revises: 2420bef5d6a4
Create Date: 2026-03-26

Reduz antecedencia_minima_horas de 24 para 1 em todas as empresas que
ainda têm o valor padrão antigo (24h). Com 24h, era impossível criar
agendamentos para o mesmo dia ou próximas horas.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'ag001_fix_antecedencia'
down_revision: Union[str, None] = '2420bef5d6a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE config_agendamento
        SET antecedencia_minima_horas = 1
        WHERE antecedencia_minima_horas = 24
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE config_agendamento
        SET antecedencia_minima_horas = 24
        WHERE antecedencia_minima_horas = 1
    """)
