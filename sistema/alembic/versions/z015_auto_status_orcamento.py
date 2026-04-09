"""feat: automação de status de orçamento — colunas empresa

Revision ID: z015_auto_status_orcamento
Revises: z014_empresa_agendamento_modo_padrao
Create Date: 2026-03-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "z015_auto_status_orcamento"
down_revision: Union[str, None] = "z014_empresa_agendamento_modo_padrao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column(
            "auto_status_orcamento", sa.Boolean(), nullable=True, server_default="true"
        ),
    )
    op.add_column(
        "empresas",
        sa.Column(
            "agendamento_exige_pagamento_100",
            sa.Boolean(),
            nullable=True,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresas", "agendamento_exige_pagamento_100")
    op.drop_column("empresas", "auto_status_orcamento")
