"""Add agendamento_modo_padrao to empresas.

Reutiliza o enum PostgreSQL modoagendamentoorcamento (w002).

Revision ID: z014_empresa_agendamento_modo_padrao
Revises: z013_template_publico_default_classico
Create Date: 2026-03-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "z014_empresa_agendamento_modo_padrao"
down_revision: Union[str, None] = "z013_template_publico_default_classico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    modo_enum = sa.Enum(
        "NAO_USA",
        "OPCIONAL",
        "OBRIGATORIO",
        name="modoagendamentoorcamento",
    )
    modo_enum.create(bind, checkfirst=True)

    op.add_column(
        "empresas",
        sa.Column(
            "agendamento_modo_padrao",
            sa.Enum(
                "NAO_USA",
                "OPCIONAL",
                "OBRIGATORIO",
                name="modoagendamentoorcamento",
            ),
            nullable=False,
            server_default="NAO_USA",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresas", "agendamento_modo_padrao")
