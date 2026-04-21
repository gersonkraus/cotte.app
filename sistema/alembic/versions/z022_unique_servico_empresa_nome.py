"""Adiciona UniqueConstraint (empresa_id, nome) em servicos.

Revision ID: z022_unique_servico
Revises: 8aa701096665
Create Date: 2026-04-21
"""
from typing import Sequence, Union
from alembic import op

revision: str = "z022_unique_servico"
down_revision: Union[str, Sequence[str], None] = "8aa701096665"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Para cada par (empresa_id, nome) duplicado, mantém o maior id.
    # Antes de deletar os menores, redireciona as FKs em itens_orcamento.
    op.execute("""
        UPDATE itens_orcamento
        SET servico_id = keepers.max_id
        FROM (
            SELECT id, MAX(id) OVER (PARTITION BY empresa_id, nome) AS max_id
            FROM servicos
        ) AS keepers
        WHERE itens_orcamento.servico_id = keepers.id
          AND keepers.id != keepers.max_id
    """)
    op.execute("""
        DELETE FROM servicos
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM servicos
            GROUP BY empresa_id, nome
        )
    """)
    op.create_unique_constraint(
        "uq_servicos_empresa_nome",
        "servicos",
        ["empresa_id", "nome"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_servicos_empresa_nome", "servicos", type_="unique")
