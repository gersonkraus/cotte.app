"""fix missing lead_score column for legacy commercial_leads schemas

Migration defensiva para bancos legados onde `commercial_leads` existe,
mas sem a coluna `lead_score` (e/ou sem o tipo enum `leadscore`).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f123456789ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "commercial_leads" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("commercial_leads")}
    if "lead_score" in columns:
        return

    # Garante o tipo enum no PostgreSQL antes de adicionar a coluna.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leadscore') THEN
                CREATE TYPE leadscore AS ENUM ('QUENTE', 'MORNO', 'FRIO');
            END IF;
        END$$;
        """
    )

    op.add_column(
        "commercial_leads",
        sa.Column(
            "lead_score",
            sa.Enum("QUENTE", "MORNO", "FRIO", name="leadscore"),
            nullable=True,
            server_default="FRIO",
        ),
    )


def downgrade() -> None:
    # Não removemos em downgrade para evitar regressão em bancos legados.
    pass

