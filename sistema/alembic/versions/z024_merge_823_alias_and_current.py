"""merge legacy and current propostas publicas revisions

Revision ID: z024_merge_823_alias
Revises: 8237a0c4e1d0, 823ca6b022cd
Create Date: 2026-04-25

Une a revisão legada/perdida com a revisão atual para que bancos marcados
em qualquer um dos dois pontos possam continuar a cadeia normalmente.
Não altera schema.
"""

from typing import Sequence, Union


revision: str = "z024_merge_823_alias"
down_revision: Union[str, tuple[str, str], None] = ("8237a0c4e1d0", "823ca6b022cd")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
