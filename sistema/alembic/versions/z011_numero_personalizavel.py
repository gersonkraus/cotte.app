"""feat: número de orçamento personalizável por empresa

Adiciona:
- Empresa: numero_prefixo, numero_incluir_ano, numero_prefixo_aprovado
- Orcamento: sequencial_numero (com backfill do valor existente)

Revision ID: z011_numero_personalizavel
Revises: 20260323_categoria_id_servicos
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = "z011_numero_personalizavel"
down_revision = "20260323_categoria_id_servicos"
branch_labels = None
depends_on = None


def upgrade():
    # ── Empresa: 3 campos de configuração de número ─────────────────────────
    with op.batch_alter_table("empresas") as batch_op:
        batch_op.add_column(
            sa.Column("numero_prefixo", sa.String(20), nullable=True, server_default="ORC")
        )
        batch_op.add_column(
            sa.Column("numero_incluir_ano", sa.Boolean(), nullable=True, server_default=sa.text("true"))
        )
        batch_op.add_column(
            sa.Column("numero_prefixo_aprovado", sa.String(20), nullable=True)
        )

    # Preenche com defaults explícitos nas linhas existentes
    op.execute("UPDATE empresas SET numero_prefixo = 'ORC' WHERE numero_prefixo IS NULL")
    op.execute("UPDATE empresas SET numero_incluir_ano = true WHERE numero_incluir_ano IS NULL")

    # ── Orcamento: sequencial_numero ────────────────────────────────────────
    with op.batch_alter_table("orcamentos") as batch_op:
        batch_op.add_column(
            sa.Column("sequencial_numero", sa.Integer(), nullable=True)
        )

    # Backfill: extrai sequencial do campo numero (formato ORC-{N}-{ano} ou {PREFIXO}-{N}-{ano})
    # split_part(numero, '-', 2) extrai o N do meio
    op.execute(
        """
        UPDATE orcamentos
        SET sequencial_numero = CAST(split_part(numero, '-', 2) AS INTEGER)
        WHERE numero ~ '^[A-Z]+-[0-9]+-[0-9]+$'
        """
    )


def downgrade():
    with op.batch_alter_table("orcamentos") as batch_op:
        batch_op.drop_column("sequencial_numero")

    with op.batch_alter_table("empresas") as batch_op:
        batch_op.drop_column("numero_prefixo_aprovado")
        batch_op.drop_column("numero_incluir_ano")
        batch_op.drop_column("numero_prefixo")
