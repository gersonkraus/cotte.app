"""add scheduling fields to tenant_commercial_campaigns

Revision ID: z028_campanha_agendamento
Revises: tc009_add_anexo_to_commercial_templates
Create Date: 2026-05-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "z028_campanha_agendamento"
down_revision: Union[str, Sequence[str]] = "tc009_add_anexo_to_commercial_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_commercial_campaigns",
        sa.Column("data_agendamento", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_commercial_campaigns",
        sa.Column("recorrencia", sa.String(20), nullable=False, server_default="nenhuma"),
    )
    op.add_column(
        "tenant_commercial_campaigns",
        sa.Column("ultima_execucao", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_commercial_campaigns", "ultima_execucao")
    op.drop_column("tenant_commercial_campaigns", "recorrencia")
    op.drop_column("tenant_commercial_campaigns", "data_agendamento")
