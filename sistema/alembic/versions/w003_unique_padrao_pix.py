"""feat: unique constraint parcial para padrao_pix por empresa

Garante que apenas um banco_pix por empresa tenha padrao_pix=true.
1. Backfill: desmarca os mais antigos, mantendo apenas o mais recente
2. Cria unique constraint parcial (empresa_id, padrao_pix=true)

Revision ID: w003_unique_padrao_pix
Revises: w002_agendamento_modo_orcamento
Create Date: 2026-03-26
"""

from typing import Union
import sqlalchemy as sa
from alembic import op


revision: str = "w003_unique_padrao_pix"
down_revision: Union[str, None] = "w002_agendamento_modo_orcamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Backfill: para cada empresa com múltiplos padrao_pix=true,
    #    manter apenas o registro mais recente (maior id)
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text("""
            WITH duplicados AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY empresa_id
                           ORDER BY id DESC
                       ) AS rn
                FROM bancos_pix_empresa
                WHERE padrao_pix = true
            )
            UPDATE bancos_pix_empresa b
            SET padrao_pix = false
            FROM duplicados d
            WHERE b.id = d.id AND d.rn > 1;
        """)
        )
    else:
        # SQLite
        bind.execute(
            sa.text("""
            UPDATE bancos_pix_empresa
            SET padrao_pix = 0
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM bancos_pix_empresa
                WHERE padrao_pix = 1
                GROUP BY empresa_id
            ) AND padrao_pix = 1;
        """)
        )

    # 2) Criar constraint parcial de unicidade via índice único condicional
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text("""
            CREATE UNIQUE INDEX uq_bancos_pix_empresa_one_padrao
            ON bancos_pix_empresa (empresa_id)
            WHERE padrao_pix = true;
        """)
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text("""
            DROP INDEX IF EXISTS uq_bancos_pix_empresa_one_padrao;
        """)
        )
