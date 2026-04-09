"""add_missing_empresa_columns

Revision ID: p003_add_missing_empresa_columns
Revises: p002_add_criado_por_id_clientes
Create Date: 2026-03-23

Adiciona colunas de monitoramento SaaS que existem no model mas
não foram migradas para o banco de produção.
Usa ADD COLUMN IF NOT EXISTS para ser segura em qualquer estado do banco.
"""

from typing import Sequence, Union
from alembic import op


revision: str = "p003_add_missing_empresa_columns"
down_revision: Union[str, None] = "p002_add_criado_por_id_clientes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE empresas
            ADD COLUMN IF NOT EXISTS ultima_atividade_em TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS total_mensagens_ia INTEGER DEFAULT 0;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE empresas
            DROP COLUMN IF EXISTS ultima_atividade_em,
            DROP COLUMN IF EXISTS total_mensagens_ia;
    """)
