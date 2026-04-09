"""tool_call_log

Revision ID: tc001_tool_call_log
Revises: e9021f88a7c2
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tc001_tool_call_log"
down_revision: Union[str, Sequence[str], None] = "e9021f88a7c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tool_call_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "empresa_id",
            sa.Integer(),
            sa.ForeignKey("empresas.id"),
            nullable=True,
        ),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("sessao_id", sa.String(length=64), nullable=True),
        sa.Column("tool", sa.String(length=100), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=True),
        sa.Column("resultado_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("latencia_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tool_call_log_empresa_id", "tool_call_log", ["empresa_id"])
    op.create_index("ix_tool_call_log_usuario_id", "tool_call_log", ["usuario_id"])
    op.create_index("ix_tool_call_log_sessao_id", "tool_call_log", ["sessao_id"])
    op.create_index("ix_tool_call_log_tool", "tool_call_log", ["tool"])
    op.create_index("ix_tool_call_log_status", "tool_call_log", ["status"])
    op.create_index("ix_tool_call_log_criado_em", "tool_call_log", ["criado_em"])


def downgrade() -> None:
    op.drop_index("ix_tool_call_log_criado_em", table_name="tool_call_log")
    op.drop_index("ix_tool_call_log_status", table_name="tool_call_log")
    op.drop_index("ix_tool_call_log_tool", table_name="tool_call_log")
    op.drop_index("ix_tool_call_log_sessao_id", table_name="tool_call_log")
    op.drop_index("ix_tool_call_log_usuario_id", table_name="tool_call_log")
    op.drop_index("ix_tool_call_log_empresa_id", table_name="tool_call_log")
    op.drop_table("tool_call_log")
