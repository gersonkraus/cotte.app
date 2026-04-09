"""financeiro: parcelamento real, despesas, historico cobrancas, config financeira

Revision ID: i001
Revises: h002
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'i001'
down_revision = 'h002'
branch_labels = None
depends_on = None


def upgrade():
    # ── contas_financeiras: +6 campos para parcelamento e despesas ──────────
    op.add_column('contas_financeiras',
        sa.Column('numero_parcela', sa.Integer(), nullable=True))
    op.add_column('contas_financeiras',
        sa.Column('total_parcelas', sa.Integer(), nullable=True))
    op.add_column('contas_financeiras',
        sa.Column('grupo_parcelas_id', sa.String(36), nullable=True))
    op.add_column('contas_financeiras',
        sa.Column('favorecido', sa.String(200), nullable=True))
    op.add_column('contas_financeiras',
        sa.Column('categoria_slug', sa.String(50), nullable=True))
    op.add_column('contas_financeiras',
        sa.Column('data_competencia', sa.Date(), nullable=True))

    # ── formas_pagamento_config: +2 campos para parcelamento do saldo ───────
    op.add_column('formas_pagamento_config',
        sa.Column('numero_parcelas_saldo', sa.Integer(), nullable=True,
                  server_default='1'))
    op.add_column('formas_pagamento_config',
        sa.Column('intervalo_dias_parcela', sa.Integer(), nullable=True,
                  server_default='30'))

    # ── historico_cobrancas (IF NOT EXISTS — pode já existir em dev) ─────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS historico_cobrancas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            conta_id INTEGER REFERENCES contas_financeiras(id),
            enviado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            canal VARCHAR(20) NOT NULL,
            destinatario VARCHAR(200),
            status VARCHAR(20) NOT NULL,
            erro TEXT,
            mensagem_corpo TEXT
        )
    """)

    # ── configuracoes_financeiras (IF NOT EXISTS — pode já existir em dev) ───
    op.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes_financeiras (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL UNIQUE REFERENCES empresas(id),
            dias_vencimento_padrao INTEGER NOT NULL DEFAULT 7,
            gerar_contas_ao_aprovar BOOLEAN NOT NULL DEFAULT true,
            automacoes_ativas BOOLEAN NOT NULL DEFAULT false,
            dias_lembrete_antes INTEGER NOT NULL DEFAULT 2,
            dias_lembrete_apos INTEGER NOT NULL DEFAULT 3,
            categorias_despesa TEXT,
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)


def downgrade():
    op.drop_table('configuracoes_financeiras')
    op.drop_table('historico_cobrancas')

    op.drop_column('formas_pagamento_config', 'intervalo_dias_parcela')
    op.drop_column('formas_pagamento_config', 'numero_parcelas_saldo')

    op.drop_column('contas_financeiras', 'data_competencia')
    op.drop_column('contas_financeiras', 'categoria_slug')
    op.drop_column('contas_financeiras', 'favorecido')
    op.drop_column('contas_financeiras', 'grupo_parcelas_id')
    op.drop_column('contas_financeiras', 'total_parcelas')
    op.drop_column('contas_financeiras', 'numero_parcela')
