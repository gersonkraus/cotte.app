"""feat: adiciona status em_execucao e aguardando_pagamento ao StatusOrcamento

Revision ID: r001_add_status_intermediarios
Revises: ba10b6a06e17
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'r001_add_status_intermediarios'
down_revision: Union[str, None] = 'ba10b6a06e17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE statusorcamento ADD VALUE IF NOT EXISTS 'em_execucao'")
    op.execute("ALTER TYPE statusorcamento ADD VALUE IF NOT EXISTS 'aguardando_pagamento'")


def downgrade() -> None:
    # PostgreSQL não suporta remover valores de enum nativamente.
    # Para reverter, seria necessário recriar o tipo — não é feito automaticamente.
    pass
