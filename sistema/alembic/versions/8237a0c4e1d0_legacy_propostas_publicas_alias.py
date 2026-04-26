"""legacy alias for propostas publicas revision

Revision ID: 8237a0c4e1d0
Revises: b4255a56f865
Create Date: 2026-04-25

Compatibiliza bancos que ficaram marcados com uma revisão antiga/perdida
equivalente ao ponto em que a cadeia de propostas públicas foi introduzida.
Não altera schema.
"""

from typing import Sequence, Union


revision: str = "8237a0c4e1d0"
down_revision: Union[str, None] = "b4255a56f865"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
