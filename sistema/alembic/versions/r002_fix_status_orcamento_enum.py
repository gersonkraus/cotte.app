"""fix: corrige valores do enum statusorcamento para maiusculo

Revision ID: r002_fix_status_orcamento_enum
Revises: r001_add_status_intermediarios
Create Date: 2026-04-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'r002_fix_status_orcamento_enum'
down_revision = 'r001_add_status_intermediarios'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No PostgreSQL não podemos alterar valores de enum dentro de um bloco de transação normal
    # Usamos execute com autocommit para não falhar a migration
    op.execute("COMMIT")
    op.execute("ALTER TYPE statusorcamento ADD VALUE IF NOT EXISTS 'EM_EXECUCAO'")
    op.execute("ALTER TYPE statusorcamento ADD VALUE IF NOT EXISTS 'AGUARDANDO_PAGAMENTO'")
    op.execute("ALTER TYPE statusorcamento ADD VALUE IF NOT EXISTS 'CONCLUIDO'")
    
    # Atualiza os registros existentes que possam estar com os valores antigos em minúsculas
    # e garante que o banco reconhece a mudança antes.
    op.execute("BEGIN")
    op.execute("UPDATE orcamentos SET status = 'EM_EXECUCAO' WHERE status::text = 'em_execucao'")
    op.execute("UPDATE orcamentos SET status = 'AGUARDANDO_PAGAMENTO' WHERE status::text = 'aguardando_pagamento'")
    op.execute("UPDATE orcamentos SET status = 'CONCLUIDO' WHERE status::text = 'concluido'")


def downgrade() -> None:
    # Como o PostgreSQL não suporta DROP VALUE de enum, na conversão
    # revertemos os valores que foram atualizados para voltar para o estado anterior
    op.execute("UPDATE orcamentos SET status = 'em_execucao' WHERE status::text = 'EM_EXECUCAO'")
    op.execute("UPDATE orcamentos SET status = 'aguardando_pagamento' WHERE status::text = 'AGUARDANDO_PAGAMENTO'")
    op.execute("UPDATE orcamentos SET status = 'concluido' WHERE status::text = 'CONCLUIDO'")
