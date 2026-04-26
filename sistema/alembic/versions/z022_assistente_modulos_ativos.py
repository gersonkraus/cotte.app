"""add modulos_ativos to assistente_preferencias_usuario

Revision ID: z022_assistente_modulos_ativos
Revises: z021_ai_chat_sessoes
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "z022_assistente_modulos_ativos"
down_revision = "z021_ai_chat_sessoes"
branch_labels = None
depends_on = None

_DEFAULT = '{"clientes":true,"financeiro":true,"catalogo":true,"orcamentos":true}'


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "assistente_preferencias_usuario"

    if table_name not in set(inspector.get_table_names()):
        return

    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    if "modulos_ativos" not in column_names:
        op.add_column(
            table_name,
            sa.Column(
                "modulos_ativos",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=_DEFAULT,
                nullable=False,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "assistente_preferencias_usuario"

    if table_name not in set(inspector.get_table_names()):
        return

    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    if "modulos_ativos" in column_names:
        op.drop_column(table_name, "modulos_ativos")
