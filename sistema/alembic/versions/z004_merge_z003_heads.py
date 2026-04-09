"""merge z003 FK indexes head with z003 merge head

Revision ID: z004_merge_z003_heads
Revises: z003_add_missing_fk_indexes, z003_merge_z002_and_9d6276
Create Date: 2026-03-20

Fecha o grafo quando z003_add_missing_fk_indexes e z003_merge_z002_and_9d6276
foram criados em paralelo a partir de z002. Sem alteração de schema.
"""
from typing import Sequence, Union

revision: str = "z004_merge_z003_heads"
down_revision: Union[str, Sequence[str], None] = (
    "z003_add_missing_fk_indexes",
    "z003_merge_z002_and_9d6276",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
