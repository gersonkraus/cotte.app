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
    op.create_unique_constraint(
        "uq_servicos_empresa_nome",
        "servicos",
        ["empresa_id", "nome"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_servicos_empresa_nome", "servicos", type_="unique")
