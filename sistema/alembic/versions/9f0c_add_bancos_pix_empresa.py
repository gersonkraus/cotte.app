"""feat: adicionar tabela bancos_pix_empresa

Revision ID: 9f0c_add_bancos_pix_empresa
Revises: f004_indexes_multitenancy
Create Date: 2026-03-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f0c_add_bancos_pix_empresa"
down_revision: Union[str, None] = "f004_indexes_multitenancy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bancos_pix_empresa",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("nome_banco", sa.String(length=100), nullable=False),
        sa.Column("apelido", sa.String(length=100), nullable=True),
        sa.Column("agencia", sa.String(length=20), nullable=True),
        sa.Column("conta", sa.String(length=30), nullable=True),
        sa.Column("tipo_conta", sa.String(length=30), nullable=True),
        sa.Column("pix_tipo", sa.String(length=20), nullable=True),
        sa.Column("pix_chave", sa.String(length=200), nullable=True),
        sa.Column("pix_titular", sa.String(length=150), nullable=True),
        sa.Column("padrao_pix", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("bancos_pix_empresa")

