"""add campos fiscais ao cliente (tipo_pessoa, cpf, cnpj, razao_social, etc)

Revision ID: o001_add_campos_fiscais_cliente
Revises: n001_merge_1548_and_m001
Create Date: 2026-03-22

Adiciona campos necessários para emissão de notas fiscais via API fiscal.
Todos os campos são nullable para compatibilidade com registros existentes.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "o001_add_campos_fiscais_cliente"
down_revision: Union[str, Sequence[str], None] = "n001_merge_1548_and_m001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("tipo_pessoa",         sa.String(2),   nullable=True, server_default="PF"))
    op.add_column("clientes", sa.Column("cpf",                 sa.String(14),  nullable=True))
    op.add_column("clientes", sa.Column("cnpj",                sa.String(18),  nullable=True))
    op.add_column("clientes", sa.Column("razao_social",        sa.String(200), nullable=True))
    op.add_column("clientes", sa.Column("nome_fantasia",       sa.String(200), nullable=True))
    op.add_column("clientes", sa.Column("inscricao_estadual",  sa.String(20),  nullable=True))
    op.add_column("clientes", sa.Column("inscricao_municipal", sa.String(20),  nullable=True))


def downgrade() -> None:
    op.drop_column("clientes", "inscricao_municipal")
    op.drop_column("clientes", "inscricao_estadual")
    op.drop_column("clientes", "nome_fantasia")
    op.drop_column("clientes", "razao_social")
    op.drop_column("clientes", "cnpj")
    op.drop_column("clientes", "cpf")
    op.drop_column("clientes", "tipo_pessoa")
