"""feat: pagamentos — empresa_id, chave de idempotência e índice único

Revision ID: w004_pagto_idemp_empresa
Revises: w003_unique_padrao_pix
Create Date: 2026-03-27
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "w004_pagto_idemp_empresa"
down_revision: Union[str, None] = "w003_unique_padrao_pix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column(
        "pagamentos_financeiros",
        sa.Column("empresa_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pagamentos_financeiros",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_foreign_key(
        "fk_pagamentos_financeiros_empresa_id",
        "pagamentos_financeiros",
        "empresas",
        ["empresa_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_pagamentos_financeiros_empresa_id",
        "pagamentos_financeiros",
        ["empresa_id"],
    )

    # Backfill empresa_id a partir do orçamento ou da conta
    bind.execute(
        sa.text("""
            UPDATE pagamentos_financeiros AS pf
            SET empresa_id = o.empresa_id
            FROM orcamentos AS o
            WHERE pf.orcamento_id = o.id AND pf.empresa_id IS NULL
        """)
    )
    bind.execute(
        sa.text("""
            UPDATE pagamentos_financeiros AS pf
            SET empresa_id = c.empresa_id
            FROM contas_financeiras AS c
            WHERE pf.conta_id = c.id AND pf.empresa_id IS NULL
        """)
    )

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX uq_pagamento_fin_empresa_idempotency
                ON pagamentos_financeiros (empresa_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL AND empresa_id IS NOT NULL
                """
            )
        )
    else:
        # SQLite (testes): índice único parcial
        op.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX uq_pagamento_fin_empresa_idempotency
                ON pagamentos_financeiros (empresa_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL AND empresa_id IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS uq_pagamento_fin_empresa_idempotency"))
    else:
        op.execute(sa.text("DROP INDEX IF EXISTS uq_pagamento_fin_empresa_idempotency"))

    op.drop_index("ix_pagamentos_financeiros_empresa_id", table_name="pagamentos_financeiros")
    op.drop_constraint("fk_pagamentos_financeiros_empresa_id", "pagamentos_financeiros", type_="foreignkey")
    op.drop_column("pagamentos_financeiros", "idempotency_key")
    op.drop_column("pagamentos_financeiros", "empresa_id")
