"""add_criado_por_id_clientes

Revision ID: p002_add_criado_por_id_clientes
Revises: p001_add_permissoes_column_usuario
Create Date: 2026-03-22

Adiciona coluna criado_por_id à tabela clientes para suportar
o nível de permissão 'meus' (operador vê apenas seus próprios registros).
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "p002_add_criado_por_id_clientes"
down_revision: Union[str, None] = "p001_add_permissoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE clientes
        ADD COLUMN IF NOT EXISTS criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_clientes_criado_por_id ON clientes (criado_por_id);
    """)


def downgrade() -> None:
    op.drop_index("ix_clientes_criado_por_id", table_name="clientes")
    op.drop_column("clientes", "criado_por_id")
