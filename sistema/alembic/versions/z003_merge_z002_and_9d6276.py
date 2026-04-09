"""merge z002 obrigatorio branch with pipeline/html arquivo_path head

Revision ID: z003_merge_z002_and_9d6276
Revises: z002_obrigatorio_doc, 9d6276e279b2
Create Date: 2026-03-20

Une dois heads criados em paralelo a partir de z001 (e da cadeia k001).
Nao altera schema — apenas fecha o grafo do Alembic.
"""
from typing import Sequence, Union

revision: str = "z003_merge_z002_and_9d6276"
down_revision: Union[str, Sequence[str], None] = (
    "z002_obrigatorio_doc",
    "9d6276e279b2",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
