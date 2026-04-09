"""Add agendamento_escolha_obrigatoria to empresas.

Revision ID: z016_agendamento_escolha_obrigatoria
Revises: z015_auto_status_orcamento
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "z016_agendamento_escolha_obrigatoria"
down_revision: Union[str, None] = "z015_auto_status_orcamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column(
            "agendamento_escolha_obrigatoria",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresas", "agendamento_escolha_obrigatoria")
