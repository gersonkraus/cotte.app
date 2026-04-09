"""Pre-agendamento: fila, canal de aprovação, liberação manual.

Revision ID: z018_pre_agendamento_fila
Revises: z017_utilizar_agendamento_automatico
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "z018_pre_agendamento_fila"
down_revision: Union[str, None] = "z017_utilizar_agendamento_automatico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column(
            "agendamento_opcoes_somente_apos_liberacao",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column("orcamentos", sa.Column("aprovado_canal", sa.String(20), nullable=True))
    op.add_column(
        "orcamentos",
        sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orcamentos",
        sa.Column(
            "agendamento_opcoes_pendente_liberacao",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "orcamentos",
        sa.Column("agendamento_opcoes_liberado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orcamentos",
        sa.Column("agendamento_opcoes_liberado_por_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "orcamentos",
        sa.Column("observacao_liberacao_agendamento", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orcamentos_agendamento_liberado_por",
        "orcamentos",
        "usuarios",
        ["agendamento_opcoes_liberado_por_id"],
        ["id"],
    )
    op.create_index(
        "ix_orcamentos_empresa_pendente_liberacao",
        "orcamentos",
        ["empresa_id", "agendamento_opcoes_pendente_liberacao"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_orcamentos_empresa_pendente_liberacao", table_name="orcamentos")
    op.drop_constraint("fk_orcamentos_agendamento_liberado_por", "orcamentos", type_="foreignkey")
    op.drop_column("orcamentos", "observacao_liberacao_agendamento")
    op.drop_column("orcamentos", "agendamento_opcoes_liberado_por_id")
    op.drop_column("orcamentos", "agendamento_opcoes_liberado_em")
    op.drop_column("orcamentos", "agendamento_opcoes_pendente_liberacao")
    op.drop_column("orcamentos", "aprovado_em")
    op.drop_column("orcamentos", "aprovado_canal")
    op.drop_column("empresas", "agendamento_opcoes_somente_apos_liberacao")
