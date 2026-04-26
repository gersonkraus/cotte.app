"""agendamento_opcoes.escolhida; remove agendamentos.opcao_escolhida_id (quebra ciclo FK)

Revision ID: z023_agendamento_opcao_escolhida
Revises: z022_assistente_modulos_ativos, d4a8fbb2a901
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "z023_agendamento_opcao_escolhida"
down_revision: Union[str, None, tuple] = (
    "z022_assistente_modulos_ativos",
    "d4a8fbb2a901",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_table(table_name: str) -> bool:
        return table_name in set(inspector.get_table_names())

    def has_column(table_name: str, column_name: str) -> bool:
        if not has_table(table_name):
            return False
        return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}

    def has_index(table_name: str, index_name: str) -> bool:
        if not has_table(table_name):
            return False
        return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table_name)}

    def has_fk(table_name: str, constraint_name: str) -> bool:
        if not has_table(table_name):
            return False
        return constraint_name in {fk["name"] for fk in inspect(bind).get_foreign_keys(table_name) if fk.get("name")}

    if has_table("agendamento_opcoes") and not has_column("agendamento_opcoes", "escolhida"):
        op.add_column(
            "agendamento_opcoes",
            sa.Column(
                "escolhida",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if has_table("agendamento_opcoes") and has_table("agendamentos") and has_column("agendamento_opcoes", "escolhida") and has_column("agendamentos", "opcao_escolhida_id"):
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

    if has_fk("agendamentos", "fk_agendamentos_opcao_escolhida"):
        op.drop_constraint(
            "fk_agendamentos_opcao_escolhida", "agendamentos", type_="foreignkey"
        )
    if has_column("agendamentos", "opcao_escolhida_id"):
        op.drop_column("agendamentos", "opcao_escolhida_id")

    if has_table("agendamento_opcoes") and not has_index("agendamento_opcoes", "uq_agendamento_opcao_uma_escolhida"):
        op.create_index(
            "uq_agendamento_opcao_uma_escolhida",
            "agendamento_opcoes",
            ["agendamento_id"],
            unique=True,
            postgresql_where=sa.text("escolhida IS TRUE"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_table(table_name: str) -> bool:
        return table_name in set(inspector.get_table_names())

    def has_column(table_name: str, column_name: str) -> bool:
        if not has_table(table_name):
            return False
        return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}

    def has_index(table_name: str, index_name: str) -> bool:
        if not has_table(table_name):
            return False
        return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table_name)}

    def has_fk(table_name: str, constraint_name: str) -> bool:
        if not has_table(table_name):
            return False
        return constraint_name in {fk["name"] for fk in inspect(bind).get_foreign_keys(table_name) if fk.get("name")}

    if has_index("agendamento_opcoes", "uq_agendamento_opcao_uma_escolhida"):
        op.drop_index(
            "uq_agendamento_opcao_uma_escolhida",
            table_name="agendamento_opcoes",
            postgresql_where=sa.text("escolhida IS TRUE"),
        )

    if has_table("agendamentos") and not has_column("agendamentos", "opcao_escolhida_id"):
        op.add_column(
            "agendamentos",
            sa.Column("opcao_escolhida_id", sa.Integer(), nullable=True),
        )
    if has_table("agendamentos") and has_table("agendamento_opcoes") and has_column("agendamentos", "opcao_escolhida_id") and not has_fk("agendamentos", "fk_agendamentos_opcao_escolhida"):
        op.create_foreign_key(
            "fk_agendamentos_opcao_escolhida",
            "agendamentos",
            "agendamento_opcoes",
            ["opcao_escolhida_id"],
            ["id"],
        )

    if has_table("agendamentos") and has_table("agendamento_opcoes") and has_column("agendamentos", "opcao_escolhida_id") and has_column("agendamento_opcoes", "escolhida"):
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

    if has_column("agendamento_opcoes", "escolhida"):
        op.drop_column("agendamento_opcoes", "escolhida")
