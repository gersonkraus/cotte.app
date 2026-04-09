"""feat: regras de pagamento — campos em formas, snapshot no orçamento, tipo_lancamento em contas

Revision ID: f002_payment_rules
Revises: f001_modulo_financeiro
Create Date: 2026-03-15 10:00:00.000000

Adiciona:
  - formas_pagamento_config: descricao, padrao, exigir_entrada_na_aprovacao,
                              percentual_entrada, metodo_entrada,
                              percentual_saldo, metodo_saldo,
                              dias_vencimento_saldo, updated_at
  - orcamentos: regra_pagamento_id (FK), regra_pagamento_nome, regra_entrada_percentual,
                regra_entrada_metodo, regra_saldo_percentual, regra_saldo_metodo,
                contas_receber_geradas_em
  - contas_financeiras: metodo_previsto, tipo_lancamento
"""

from alembic import op
import sqlalchemy as sa

revision = "f002_payment_rules"
down_revision = "f001_modulo_financeiro"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── formas_pagamento_config ───────────────────────────────────────────────
    op.add_column("formas_pagamento_config",
        sa.Column("descricao", sa.Text(), nullable=True))
    op.add_column("formas_pagamento_config",
        sa.Column("padrao", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("formas_pagamento_config",
        sa.Column("exigir_entrada_na_aprovacao", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("formas_pagamento_config",
        sa.Column("percentual_entrada", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("formas_pagamento_config",
        sa.Column("metodo_entrada", sa.String(30), nullable=True))
    op.add_column("formas_pagamento_config",
        sa.Column("percentual_saldo", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("formas_pagamento_config",
        sa.Column("metodo_saldo", sa.String(30), nullable=True))
    op.add_column("formas_pagamento_config",
        sa.Column("dias_vencimento_saldo", sa.Integer(), nullable=True))
    op.add_column("formas_pagamento_config",
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=True))

    # ── orcamentos ────────────────────────────────────────────────────────────
    op.add_column("orcamentos",
        sa.Column("regra_pagamento_id", sa.Integer(), nullable=True))
    op.add_column("orcamentos",
        sa.Column("regra_pagamento_nome", sa.String(150), nullable=True))
    op.add_column("orcamentos",
        sa.Column("regra_entrada_percentual", sa.Numeric(5, 2), nullable=True))
    op.add_column("orcamentos",
        sa.Column("regra_entrada_metodo", sa.String(30), nullable=True))
    op.add_column("orcamentos",
        sa.Column("regra_saldo_percentual", sa.Numeric(5, 2), nullable=True))
    op.add_column("orcamentos",
        sa.Column("regra_saldo_metodo", sa.String(30), nullable=True))
    op.add_column("orcamentos",
        sa.Column("contas_receber_geradas_em", sa.DateTime(timezone=True), nullable=True))

    # FK: orcamentos.regra_pagamento_id → formas_pagamento_config.id
    op.create_foreign_key(
        "fk_orcamentos_regra_pagamento_id",
        "orcamentos", "formas_pagamento_config",
        ["regra_pagamento_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── contas_financeiras ────────────────────────────────────────────────────
    op.add_column("contas_financeiras",
        sa.Column("metodo_previsto", sa.String(30), nullable=True))
    op.add_column("contas_financeiras",
        sa.Column("tipo_lancamento", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("contas_financeiras", "tipo_lancamento")
    op.drop_column("contas_financeiras", "metodo_previsto")

    op.drop_constraint("fk_orcamentos_regra_pagamento_id", "orcamentos", type_="foreignkey")
    op.drop_column("orcamentos", "contas_receber_geradas_em")
    op.drop_column("orcamentos", "regra_saldo_metodo")
    op.drop_column("orcamentos", "regra_saldo_percentual")
    op.drop_column("orcamentos", "regra_entrada_metodo")
    op.drop_column("orcamentos", "regra_entrada_percentual")
    op.drop_column("orcamentos", "regra_pagamento_nome")
    op.drop_column("orcamentos", "regra_pagamento_id")

    op.drop_column("formas_pagamento_config", "updated_at")
    op.drop_column("formas_pagamento_config", "dias_vencimento_saldo")
    op.drop_column("formas_pagamento_config", "metodo_saldo")
    op.drop_column("formas_pagamento_config", "percentual_saldo")
    op.drop_column("formas_pagamento_config", "metodo_entrada")
    op.drop_column("formas_pagamento_config", "percentual_entrada")
    op.drop_column("formas_pagamento_config", "exigir_entrada_na_aprovacao")
    op.drop_column("formas_pagamento_config", "padrao")
    op.drop_column("formas_pagamento_config", "descricao")
