"""agendamento_opcoes.escolhida; remove agendamentos.opcao_escolhida_id (quebra ciclo FK)

Revision ID: z023_agendamento_opcao_escolhida
Revises: z022_assistente_modulos_ativos, d4a8fbb2a901
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "z023_agendamento_opcao_escolhida"
down_revision: Union[str, None, tuple] = (
    "z022_assistente_modulos_ativos",
    "d4a8fbb2a901",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agendamento_opcoes",
        sa.Column(
            "escolhida",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE agendamento_opcoes ao
            SET escolhida = true
            FROM agendamentos ag
            WHERE ag.opcao_escolhida_id IS NOT NULL
              AND ao.id = ag.opcao_escolhida_id
              AND ao.agendamento_id = ag.id
            """
        )
    )

    op.drop_constraint(
        "fk_agendamentos_opcao_escolhida", "agendamentos", type_="foreignkey"
    )
    op.drop_column("agendamentos", "opcao_escolhida_id")

    op.create_index(
        "uq_agendamento_opcao_uma_escolhida",
        "agendamento_opcoes",
        ["agendamento_id"],
        unique=True,
        postgresql_where=sa.text("escolhida IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_agendamento_opcao_uma_escolhida",
        table_name="agendamento_opcoes",
        postgresql_where=sa.text("escolhida IS TRUE"),
    )

    op.add_column(
        "agendamentos",
        sa.Column("opcao_escolhida_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_agendamentos_opcao_escolhida",
        "agendamentos",
        "agendamento_opcoes",
        ["opcao_escolhida_id"],
        ["id"],
    )

    op.execute(
        sa.text(
            """
            UPDATE agendamentos ag
            SET opcao_escolhida_id = ao.id
            FROM agendamento_opcoes ao
            WHERE ao.agendamento_id = ag.id
              AND ao.escolhida IS TRUE
            """
        )
    )

    op.drop_column("agendamento_opcoes", "escolhida")
