"""add assistente prompts empresa

Revision ID: d4a8fbb2a901
Revises: c6121d569572
Create Date: 2026-04-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4a8fbb2a901"
down_revision: Union[str, None] = "c6121d569572"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistente_prompts_empresa",
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
    op.create_index(
        "ix_assistente_prompts_empresa_empresa_id",
        "assistente_prompts_empresa",
        ["empresa_id"],
    )
    op.create_index(
        "ix_assistente_prompts_empresa_categoria_only",
        "assistente_prompts_empresa",
        ["categoria"],
    )
    op.create_index(
        "ix_assistente_prompts_empresa_categoria",
        "assistente_prompts_empresa",
        ["empresa_id", "categoria"],
    )
    op.create_index(
        "ix_assistente_prompts_empresa_favorito_ativo",
        "assistente_prompts_empresa",
        ["empresa_id", "favorito", "ativo"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistente_prompts_empresa_favorito_ativo",
        table_name="assistente_prompts_empresa",
    )
    op.drop_index(
        "ix_assistente_prompts_empresa_categoria",
        table_name="assistente_prompts_empresa",
    )
    op.drop_index(
        "ix_assistente_prompts_empresa_categoria_only",
        table_name="assistente_prompts_empresa",
    )
    op.drop_index(
        "ix_assistente_prompts_empresa_empresa_id",
        table_name="assistente_prompts_empresa",
    )
    op.drop_table("assistente_prompts_empresa")
