"""feat: módulo financeiro — formas de pagamento, contas e pagamentos

Revision ID: f001_modulo_financeiro
Revises: e5b94f17c814
Create Date: 2026-03-14 21:00:00.000000

Cria as tabelas:
  - formas_pagamento_config
  - contas_financeiras
  - pagamentos_financeiros
  - templates_notificacao
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "f001_modulo_financeiro"
down_revision: Union[str, None] = "e5b94f17c814"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── formas_pagamento_config ────────────────────────────────────────────
    op.create_table(
        "formas_pagamento_config",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("icone", sa.String(10), nullable=True, server_default="💳"),
        sa.Column("cor", sa.String(7), nullable=True, server_default="#00e5a0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("aceita_parcelamento", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_parcelas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("taxa_percentual", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("gera_pix_qrcode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── contas_financeiras ─────────────────────────────────────────────────
    op.create_table(
        "contas_financeiras",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("orcamento_id", sa.Integer(), sa.ForeignKey("orcamentos.id"), nullable=True, index=True),
        sa.Column(
            "tipo",
            sa.Enum("receber", "pagar", name="tipoconta"),
            nullable=False,
            server_default="receber",
        ),
        sa.Column("descricao", sa.String(300), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_pago", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pendente", "parcial", "pago", "vencido", "cancelado", name="statusconta"),
            nullable=False,
            server_default="pendente",
        ),
        sa.Column("data_vencimento", sa.Date(), nullable=True),
        sa.Column("data_criacao", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("categoria", sa.String(100), nullable=True),
        sa.Column(
            "origem",
            sa.Enum("manual", "whatsapp", "assistente_ia", "webhook", "sistema", name="origemregistro"),
            nullable=False,
            server_default="sistema",
        ),
        sa.Column("metadata_ia", sa.Text(), nullable=True),
        sa.Column("ultima_cobranca_em", sa.DateTime(timezone=True), nullable=True),
    )

    # ── pagamentos_financeiros ─────────────────────────────────────────────
    op.create_table(
        "pagamentos_financeiros",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("orcamento_id", sa.Integer(), sa.ForeignKey("orcamentos.id"), nullable=True, index=True),
        sa.Column("conta_id", sa.Integer(), sa.ForeignKey("contas_financeiras.id"), nullable=True, index=True),
        sa.Column("forma_pagamento_id", sa.Integer(), sa.ForeignKey("formas_pagamento_config.id"), nullable=True),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum("sinal", "parcela", "quitacao", name="tipopagamento"),
            nullable=False,
            server_default="quitacao",
        ),
        sa.Column("data_pagamento", sa.Date(), nullable=False),
        sa.Column("confirmado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confirmado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("observacao", sa.String(500), nullable=True),
        sa.Column("comprovante_url", sa.String(500), nullable=True),
        sa.Column(
            "origem",
            sa.Enum("manual", "whatsapp", "assistente_ia", "webhook", "sistema", name="origemregistro"),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("metadata_ia", sa.Text(), nullable=True),
        sa.Column("confianca_ia", sa.Float(), nullable=True),
        sa.Column("parcela_numero", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("confirmado", "estornado", name="statuspagamentofinanceiro"),
            nullable=False,
            server_default="confirmado",
        ),
        sa.Column("txid_pix", sa.String(35), nullable=True),
    )

    # ── templates_notificacao ──────────────────────────────────────────────
    op.create_table(
        "templates_notificacao",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False, index=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("templates_notificacao")
    op.drop_table("pagamentos_financeiros")
    op.drop_table("contas_financeiras")
    op.drop_table("formas_pagamento_config")
    # Remover tipos ENUM criados (PostgreSQL)
    op.execute("DROP TYPE IF EXISTS statuspagamentofinanceiro")
    op.execute("DROP TYPE IF EXISTS tipopagamento")
    op.execute("DROP TYPE IF EXISTS origemregistro")
    op.execute("DROP TYPE IF EXISTS statusconta")
    op.execute("DROP TYPE IF EXISTS tipoconta")
