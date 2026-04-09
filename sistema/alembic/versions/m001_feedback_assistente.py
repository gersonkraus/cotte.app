"""Cria tabela feedback_assistente para avaliações do assistente IA.

Revision ID: m001_feedback_assistente
Revises: z005_status_pipeline_missing
Create Date: 2026-03-21
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "m001_feedback_assistente"
down_revision: Union[str, None] = "z005_status_pipeline_missing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_assistente",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("sessao_id", sa.String(64), nullable=True),
        sa.Column("pergunta", sa.Text(), nullable=False),
        sa.Column("resposta", sa.Text(), nullable=False),
        sa.Column("avaliacao", sa.String(10), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("modulo_origem", sa.String(50), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("feedback_assistente")
