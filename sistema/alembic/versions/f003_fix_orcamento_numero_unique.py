"""fix: remove unique constraint global em orcamentos.numero e cria index por empresa

Revision ID: f003_fix_orcamento_numero_unique
Revises: f002_payment_rules
Create Date: 2026-03-15 21:00:00.000000

O número de orçamento (ex: ORC-1-26) deve ser único apenas dentro da mesma
empresa, não globalmente. Este fix remove qualquer índice/constraint único
em 'numero' sozinho e cria um índice único composto (empresa_id, numero).
"""

from alembic import op


revision = "f003_fix_orcamento_numero_unique"
down_revision = "f002_payment_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Dropa o índice único em 'numero' sozinho (pode já ser não-único, IF EXISTS é seguro)
    op.execute("DROP INDEX IF EXISTS ix_orcamentos_numero")

    # 2. Dropa qualquer unique constraint separada em 'numero' sozinho
    #    (gerada por Column(..., unique=True) no SQLAlchemy)
    op.execute("""
        DO $$
        DECLARE
            cname TEXT;
        BEGIN
            SELECT tc.constraint_name INTO cname
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
             AND tc.table_schema    = ccu.table_schema
            WHERE tc.table_name       = 'orcamentos'
              AND tc.constraint_type  = 'UNIQUE'
              AND ccu.column_name     = 'numero'
            -- garante que é só a coluna 'numero' (não composta com empresa_id)
              AND (
                SELECT COUNT(*) FROM information_schema.constraint_column_usage c2
                WHERE c2.constraint_name = tc.constraint_name
              ) = 1
            LIMIT 1;

            IF cname IS NOT NULL THEN
                EXECUTE 'ALTER TABLE orcamentos DROP CONSTRAINT ' || quote_ident(cname);
            END IF;
        END
        $$;
    """)

    # 3. Recria índice simples não-único em 'numero' para buscas
    op.execute("CREATE INDEX IF NOT EXISTS ix_orcamentos_numero ON orcamentos (numero)")

    # 4. Cria índice único composto (empresa_id, numero) — correto por empresa
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_orcamentos_empresa_numero
        ON orcamentos (empresa_id, numero)
        WHERE numero IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_orcamentos_empresa_numero")
    op.execute("DROP INDEX IF EXISTS ix_orcamentos_numero")
    op.execute("CREATE UNIQUE INDEX ix_orcamentos_numero ON orcamentos (numero)")
