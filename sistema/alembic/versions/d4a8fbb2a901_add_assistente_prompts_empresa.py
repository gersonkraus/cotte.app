"""add assistente prompts empresa

Revision ID: d4a8fbb2a901
Revises: c6121d569572
Create Date: 2026-04-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d4a8fbb2a901"
down_revision: Union[str, None] = "c6121d569572"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "assistente_prompts_empresa"

    def has_table() -> bool:
        return table_name in set(inspector.get_table_names())

    def has_index(index_name: str) -> bool:
        if not has_table():
            return False
        return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table_name)}

    if not has_table():
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("titulo", sa.String(length=120), nullable=False),
            sa.Column("conteudo_prompt", sa.Text(), nullable=False),
            sa.Column("categoria", sa.String(length=40), nullable=False),
            sa.Column("favorito", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("uso_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_por_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_id", sa.Integer(), nullable=True),
            sa.Column(
                "criado_em",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["atualizado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        )
    if not has_index("ix_assistente_prompts_empresa_empresa_id"):
        op.create_index(
            "ix_assistente_prompts_empresa_empresa_id",
            table_name,
            ["empresa_id"],
        )
    if not has_index("ix_assistente_prompts_empresa_categoria_only"):
        op.create_index(
            "ix_assistente_prompts_empresa_categoria_only",
            table_name,
            ["categoria"],
        )
    if not has_index("ix_assistente_prompts_empresa_categoria"):
        op.create_index(
            "ix_assistente_prompts_empresa_categoria",
            table_name,
            ["empresa_id", "categoria"],
        )
    if not has_index("ix_assistente_prompts_empresa_favorito_ativo"):
        op.create_index(
            "ix_assistente_prompts_empresa_favorito_ativo",
            table_name,
            ["empresa_id", "favorito", "ativo"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_name = "assistente_prompts_empresa"

    if table_name not in set(inspector.get_table_names()):
        return

    index_names = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if "ix_assistente_prompts_empresa_favorito_ativo" in index_names:
        op.drop_index(
            "ix_assistente_prompts_empresa_favorito_ativo",
            table_name=table_name,
        )
    if "ix_assistente_prompts_empresa_categoria" in index_names:
        op.drop_index(
            "ix_assistente_prompts_empresa_categoria",
            table_name=table_name,
        )
    if "ix_assistente_prompts_empresa_categoria_only" in index_names:
        op.drop_index(
            "ix_assistente_prompts_empresa_categoria_only",
            table_name=table_name,
        )
    if "ix_assistente_prompts_empresa_empresa_id" in index_names:
        op.drop_index(
            "ix_assistente_prompts_empresa_empresa_id",
            table_name=table_name,
        )
    op.drop_table(table_name)
