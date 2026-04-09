"""Add utilizar_agendamento_automatico to empresas.

Revision ID: z017_utilizar_agendamento_automatico
Revises: z016_agendamento_escolha_obrigatoria
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "z017_utilizar_agendamento_automatico"
down_revision: Union[str, None] = "z016_agendamento_escolha_obrigatoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column(
            "utilizar_agendamento_automatico",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresas", "utilizar_agendamento_automatico")
