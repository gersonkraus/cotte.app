"""expand_ml_token_scope_text — Mercado Livre pode devolver scope com URNs longas.

Revision ID: ml004_expand_ml_token_scope_text
Revises: ml003_integracao_ml_oauth_pkce_verifier
Create Date: 2026-05-10 01:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ml004_expand_ml_token_scope_text"
down_revision: Union[str, None] = "ml003_integracao_ml_oauth_pkce_verifier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "integracoes_mercadolivre"):
        return
    op.alter_column(
        "integracoes_mercadolivre",
        "token_scope",
        existing_type=sa.String(length=200),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "integracoes_mercadolivre"):
        return
    op.alter_column(
        "integracoes_mercadolivre",
        "token_scope",
        existing_type=sa.Text(),
        type_=sa.String(length=200),
        existing_nullable=True,
    )
