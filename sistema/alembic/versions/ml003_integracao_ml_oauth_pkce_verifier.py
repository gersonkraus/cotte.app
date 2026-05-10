"""integracao_ml_oauth_pkce_verifier

Revision ID: ml003_integracao_ml_oauth_pkce_verifier
Revises: ml002_add_mercadolivre_domain_tables
Create Date: 2026-05-09 14:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ml003_integracao_ml_oauth_pkce_verifier"
down_revision: Union[str, None] = "ml002_add_mercadolivre_domain_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(c["name"] == column_name for c in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _column_exists(inspector, "integracoes_mercadolivre", "oauth_code_verifier"):
        return
    op.add_column(
        "integracoes_mercadolivre",
        sa.Column("oauth_code_verifier", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _column_exists(inspector, "integracoes_mercadolivre", "oauth_code_verifier"):
        return
    op.drop_column("integracoes_mercadolivre", "oauth_code_verifier")
