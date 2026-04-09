"""Adiciona SUBSTITUIDA ao enum statusproposta (reenvio forçado)

Revision ID: e9021f88a7c2
Revises: 823ca6b022cd
Create Date: 2026-04-04

O endpoint POST .../propostas?force=true marca envios anteriores como SUBSTITUIDA.
Sem este valor no tipo PostgreSQL, o commit falha com 500.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e9021f88a7c2"
down_revision: Union[str, None] = "823ca6b022cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # ADD VALUE não pode rodar dentro da transação padrão do Alembic em PG < 12.
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                """
DO $do$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'statusproposta' AND e.enumlabel = 'SUBSTITUIDA'
    ) THEN
        ALTER TYPE statusproposta ADD VALUE 'SUBSTITUIDA';
    END IF;
END
$do$;
"""
            )
        )


def downgrade() -> None:
    # Remover valor de enum nativo no PostgreSQL é inviável sem recriar o tipo.
    pass
