"""feat: agendamento_modo em orcamentos e usa_agendamento em config_agendamento

Adiciona:
- orcamentos.agendamento_modo (enum: nao_usa | opcional | obrigatorio, default: nao_usa)
- config_agendamento.usa_agendamento (bool, default: false)

Revision ID: w002_agendamento_modo_orcamento
Revises: w001_merge_all_heads_agendamento
Create Date: 2026-03-26
"""

from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "w002_agendamento_modo_orcamento"
down_revision: Union[str, None] = "w001_merge_all_heads_agendamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cria o tipo enum no PostgreSQL
    modoagendamento_enum = sa.Enum(
        "NAO_USA",
        "OPCIONAL",
        "OBRIGATORIO",
        name="modoagendamentoorcamento",
    )
    modoagendamento_enum.create(op.get_bind(), checkfirst=True)

    # Adiciona coluna em orcamentos
    op.add_column(
        "orcamentos",
        sa.Column(
            "agendamento_modo",
            sa.Enum(
                "NAO_USA", "OPCIONAL", "OBRIGATORIO", name="modoagendamentoorcamento"
            ),
            nullable=False,
            server_default="NAO_USA",
        ),
    )

    # Adiciona coluna em config_agendamento
    op.add_column(
        "config_agendamento",
        sa.Column(
            "usa_agendamento", sa.Boolean(), nullable=False, server_default="false"
        ),
    )


def downgrade() -> None:
    op.drop_column("config_agendamento", "usa_agendamento")
    op.drop_column("orcamentos", "agendamento_modo")

    # Remove o tipo enum do PostgreSQL
    sa.Enum(name="modoagendamentoorcamento").drop(op.get_bind(), checkfirst=True)
