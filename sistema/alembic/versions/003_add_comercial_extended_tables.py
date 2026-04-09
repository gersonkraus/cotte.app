"""Add commercial segments, lead sources, templates, reminders, config tables
and extend commercial_leads with segmento_id, origem_lead_id, lead_score, ativo.

Revision ID: 003_add_comercial_extended
Revises: 002_add_comercial_tables
Create Date: 2025-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_add_comercial_extended"
down_revision: Union[str, None] = "002_add_comercial_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabelas auxiliares e estende commercial_leads."""

    # ── Segmentos ─────────────────────────────────────────────────────────
    op.create_table(
        "commercial_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome", name="uq_commercial_segments_nome"),
    )
    op.create_index(op.f("ix_commercial_segments_id"), "commercial_segments", ["id"], unique=False)

    # ── Origens de lead ───────────────────────────────────────────────────
    op.create_table(
        "commercial_lead_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome", name="uq_commercial_lead_sources_nome"),
    )
    op.create_index(op.f("ix_commercial_lead_sources_id"), "commercial_lead_sources", ["id"], unique=False)

    # ── Templates ─────────────────────────────────────────────────────────
    op.create_table(
        "commercial_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("tipo", sa.Enum("MENSAGEM_INICIAL", "FOLLOWUP", "PROPOSTA_COMERCIAL", "EMAIL_COMERCIAL", name="tipotemplate"), nullable=False),
        sa.Column("canal", sa.Enum("WHATSAPP", "EMAIL", "AMBOS", name="canaltemplate"), nullable=False),
        sa.Column("assunto", sa.String(200), nullable=True),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_templates_id"), "commercial_templates", ["id"], unique=False)

    # ── Lembretes ─────────────────────────────────────────────────────────
    op.create_table(
        "commercial_reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("PENDENTE", "CONCLUIDO", "ATRASADO", name="statuslembrete"), nullable=False, server_default="PENDENTE"),
        sa.Column("canal_sugerido", sa.Enum("WHATSAPP", "EMAIL", "LIGACAO", "REUNIAO", name="canalsugerido"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["commercial_leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_reminders_id"), "commercial_reminders", ["id"], unique=False)
    op.create_index(op.f("ix_commercial_reminders_lead_id"), "commercial_reminders", ["lead_id"], unique=False)

    # ── Configurações ─────────────────────────────────────────────────────
    op.create_table(
        "commercial_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link_demo", sa.String(300), nullable=True),
        sa.Column("link_proposta", sa.String(300), nullable=True),
        sa.Column("assinatura_comercial", sa.Text(), nullable=True),
        sa.Column("canal_preferencial", sa.String(20), nullable=False, server_default="whatsapp"),
        sa.Column("textos_auxiliares", sa.Text(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_config_id"), "commercial_config", ["id"], unique=False)

    # ── Novos campos em commercial_leads ──────────────────────────────────
    op.add_column("commercial_leads", sa.Column("segmento_id", sa.Integer(), nullable=True))
    op.add_column("commercial_leads", sa.Column("origem_lead_id", sa.Integer(), nullable=True))
    op.add_column("commercial_leads", sa.Column("lead_score", sa.Enum("QUENTE", "MORNO", "FRIO", name="leadscore"), nullable=True, server_default="FRIO"))
    op.add_column("commercial_leads", sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    op.create_foreign_key("fk_leads_segmento", "commercial_leads", "commercial_segments", ["segmento_id"], ["id"])
    op.create_foreign_key("fk_leads_origem", "commercial_leads", "commercial_lead_sources", ["origem_lead_id"], ["id"])


def downgrade() -> None:
    """Remove tabelas e colunas adicionadas."""
    op.drop_constraint("fk_leads_origem", "commercial_leads", type_="foreignkey")
    op.drop_constraint("fk_leads_segmento", "commercial_leads", type_="foreignkey")

    op.drop_column("commercial_leads", "ativo")
    op.drop_column("commercial_leads", "lead_score")
    op.drop_column("commercial_leads", "origem_lead_id")
    op.drop_column("commercial_leads", "segmento_id")

    op.drop_index(op.f("ix_commercial_config_id"), table_name="commercial_config")
    op.drop_table("commercial_config")

    op.drop_index(op.f("ix_commercial_reminders_lead_id"), table_name="commercial_reminders")
    op.drop_index(op.f("ix_commercial_reminders_id"), table_name="commercial_reminders")
    op.drop_table("commercial_reminders")

    op.drop_index(op.f("ix_commercial_templates_id"), table_name="commercial_templates")
    op.drop_table("commercial_templates")

    op.drop_index(op.f("ix_commercial_lead_sources_id"), table_name="commercial_lead_sources")
    op.drop_table("commercial_lead_sources")

    op.drop_index(op.f("ix_commercial_segments_id"), table_name="commercial_segments")
    op.drop_table("commercial_segments")

    op.execute("DROP TYPE IF EXISTS canalsugerido")
    op.execute("DROP TYPE IF EXISTS statuslembrete")
    op.execute("DROP TYPE IF EXISTS canaltemplate")
    op.execute("DROP TYPE IF EXISTS tipotemplate")
    op.execute("DROP TYPE IF EXISTS leadscore")
