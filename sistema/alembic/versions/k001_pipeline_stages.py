"""pipeline_stages: cria tabela e migra status_pipeline para VARCHAR

Revision ID: k001_pipeline_stages
Revises: z001_merge_all_heads, b0bac86d4955
Create Date: 2026-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'k001_pipeline_stages'
down_revision: Union[str, Sequence[str], None] = ('z001_merge_all_heads', 'b0bac86d4955')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_STAGES = [
    ("novo",             "Novo",      "#94a3b8", "🆕", 0, False),
    ("contato_iniciado", "Contato",   "#3b82f6", "📞", 1, False),
    ("proposta_enviada", "Proposta",  "#f59e0b", "📄", 2, False),
    ("negociacao",       "Negociação","#06b6d4", "🤝", 3, False),
    ("fechado_ganho",    "Ganho",     "#10b981", "✅", 4, True),
    ("fechado_perdido",  "Perdido",   "#ef4444", "❌", 5, True),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Criar tabela pipeline_stages (idempotente)
    if "pipeline_stages" not in tables:
        op.create_table(
            "pipeline_stages",
            sa.Column("id",        sa.Integer, primary_key=True),
            sa.Column("slug",      sa.String(50), unique=True, nullable=False),
            sa.Column("label",     sa.String(100), nullable=False),
            sa.Column("cor",       sa.String(20), server_default="#94a3b8"),
            sa.Column("emoji",     sa.String(10), server_default=""),
            sa.Column("ordem",     sa.Integer, server_default="0"),
            sa.Column("ativo",     sa.Boolean, server_default=sa.text("true")),
            sa.Column("fechado",   sa.Boolean, server_default=sa.text("false")),
            sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )

    # 2. Seed — ON CONFLICT DO NOTHING para ser idempotente
    for slug, label, cor, emoji, ordem, fechado in SEED_STAGES:
        conn.execute(
            sa.text(
                "INSERT INTO pipeline_stages (slug, label, cor, emoji, ordem, fechado) "
                "VALUES (:slug, :label, :cor, :emoji, :ordem, :fechado) "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {"slug": slug, "label": label, "cor": cor, "emoji": emoji,
             "ordem": ordem, "fechado": fechado},
        )

    # 3. Migrar status_pipeline de Enum → VARCHAR(50) (idempotente via data_type check)
    cols = {c["name"]: c for c in inspector.get_columns("commercial_leads")}
    col_type = str(cols.get("status_pipeline", {}).get("type", "")).upper()
    if "VARCHAR" not in col_type and "CHARACTER VARYING" not in col_type:
        op.execute(
            "ALTER TABLE commercial_leads "
            "ALTER COLUMN status_pipeline TYPE VARCHAR(50) "
            "USING status_pipeline::text"
        )

    # 4. Remover o tipo enum do PostgreSQL (se existir)
    # Usar CASCADE para remover dependências da coluna status_pipeline
    op.execute("DROP TYPE IF EXISTS statuspipeline CASCADE")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Recriar o enum e reverter coluna
    op.execute(
        "CREATE TYPE statuspipeline AS ENUM "
        "('novo','contato_iniciado','proposta_enviada','negociacao','fechado_ganho','fechado_perdido')"
    )
    op.execute(
        "ALTER TABLE commercial_leads "
        "ALTER COLUMN status_pipeline TYPE statuspipeline "
        "USING status_pipeline::statuspipeline"
    )

    tables = inspector.get_table_names()
    if "pipeline_stages" in tables:
        op.drop_table("pipeline_stages")
