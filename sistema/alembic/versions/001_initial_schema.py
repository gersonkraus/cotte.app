"""Initial schema (baseline) — create_all a partir dos models atuais.

Banco já existente (produção): use 'alembic stamp head' para marcar como aplicado.
Banco novo: use 'alembic upgrade head' para criar todas as tabelas.

Revision ID: 001_initial
Revises:
Create Date: 2025-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria todas as tabelas a partir de Base.metadata (models atuais)."""
    from app.core.database import Base
    from app.models import models  # noqa: F401 — registra tabelas no metadata

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Remove todas as tabelas (ordem inversa de dependências)."""
    from app.core.database import Base
    from app.models import models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
