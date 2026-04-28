"""add contexto_operacional to ai_chat_sessoes

Revision ID: c8f2d1a9b401
Revises: 6f8002896a1d
Create Date: 2026-04-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8f2d1a9b401"
down_revision: Union[str, None] = "6f8002896a1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_chat_sessoes"):
        return
    cols = {c["name"] for c in insp.get_columns("ai_chat_sessoes")}
    if "contexto_operacional" not in cols:
        op.add_column("ai_chat_sessoes", sa.Column("contexto_operacional", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_chat_sessoes"):
        return
    cols = {c["name"] for c in insp.get_columns("ai_chat_sessoes")}
    if "contexto_operacional" in cols:
        op.drop_column("ai_chat_sessoes", "contexto_operacional")
