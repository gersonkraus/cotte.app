"""add fiscal fields to servicos

Revision ID: z029_add_fiscal_fields_servicos
Revises: z028_campanha_agendamento
Create Date: 2026-05-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "z029_add_fiscal_fields_servicos"
down_revision: Union[str, Sequence[str]] = "z028_campanha_agendamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("servicos", sa.Column("ncm", sa.String(8), nullable=True))
    op.add_column("servicos", sa.Column("cfop", sa.String(4), nullable=True))
    op.add_column("servicos", sa.Column("csosn", sa.String(4), nullable=True))
    op.add_column("servicos", sa.Column("origem", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("servicos", sa.Column("unidade_fiscal", sa.String(6), nullable=True))
    op.add_column("servicos", sa.Column("dados_fiscais_ok", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("servicos", "dados_fiscais_ok")
    op.drop_column("servicos", "unidade_fiscal")
    op.drop_column("servicos", "origem")
    op.drop_column("servicos", "csosn")
    op.drop_column("servicos", "cfop")
    op.drop_column("servicos", "ncm")
