"""add direcao and message_id to commercial interactions

Adiciona:
- direcao (enviado/recebido) para distinguir mensagens outbound de respostas do lead
- message_id para deduplicar webhooks duplicados da Evolution API

Revision ID: tc010_add_direcao_message_id_to_interactions
Revises: tc009_add_anexo_to_commercial_templates, tc008_add_anexo_to_tenant_templates
Create Date: 2026-05-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "tc010_add_direcao_message_id_to_interactions"
down_revision: Union[str, Sequence[str]] = (
    "tc009_add_anexo_to_commercial_templates",
    "tc008_add_anexo_to_tenant_templates",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela principal (CRM interno do COTTE / superadmin)
    with op.batch_alter_table("commercial_interactions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "direcao",
                sa.String(length=10),
                nullable=False,
                server_default="enviado",
            )
        )
        batch_op.add_column(
            sa.Column("message_id", sa.String(length=100), nullable=True)
        )
        batch_op.create_index(
            "ix_commercial_interactions_message_id", ["message_id"]
        )

    # Tabela tenant (CRM multi-tenant)
    with op.batch_alter_table("tenant_commercial_interactions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "direcao",
                sa.String(length=10),
                nullable=False,
                server_default="enviado",
            )
        )
        batch_op.add_column(
            sa.Column("message_id", sa.String(length=100), nullable=True)
        )
        batch_op.create_index(
            "ix_tenant_commercial_interactions_message_id", ["message_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("tenant_commercial_interactions") as batch_op:
        batch_op.drop_index("ix_tenant_commercial_interactions_message_id")
        batch_op.drop_column("message_id")
        batch_op.drop_column("direcao")

    with op.batch_alter_table("commercial_interactions") as batch_op:
        batch_op.drop_index("ix_commercial_interactions_message_id")
        batch_op.drop_column("message_id")
        batch_op.drop_column("direcao")
