"""add modulos_ativos to assistente_preferencias_usuario

Revision ID: z022_assistente_modulos_ativos
Revises: z021_ai_chat_sessoes
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "z022_assistente_modulos_ativos"
down_revision = "z021_ai_chat_sessoes"
branch_labels = None
depends_on = None

_DEFAULT = '{"clientes":true,"financeiro":true,"catalogo":true,"orcamentos":true}'


def upgrade() -> None:
    op.add_column(
        "assistente_preferencias_usuario",
        sa.Column(
            "modulos_ativos",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=_DEFAULT,
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("assistente_preferencias_usuario", "modulos_ativos")
