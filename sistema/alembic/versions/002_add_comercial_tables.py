"""Add commercial leads and interactions tables

Revision ID: 002_add_comercial_tables
Revises: 001_initial
Create Date: 2025-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_comercial_tables"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabelas commercial_leads e commercial_interactions."""
    
    # Tabela de leads comerciais
    # Usar native_enum=False para evitar problemas com enums PostgreSQL
    op.create_table(
        "commercial_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome_responsavel", sa.String(100), nullable=False),
        sa.Column("nome_empresa", sa.String(150), nullable=False),
        sa.Column("whatsapp", sa.String(20), nullable=True),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("cidade", sa.String(100), nullable=True),
        sa.Column("segmento", sa.Enum("INSTALADOR_AR", "ELETRICISTA", "PINTOR", "MANUTENCAO", "OUTRO", name="segmentolead", native_enum=False), nullable=True),
        sa.Column("origem_lead", sa.Enum("INDICACAO", "SITE", "WHATSAPP", "EMAIL", "REDES_SOCIAIS", "LIGACAO", "EVENTO", "OUTRO", name="origemlead", native_enum=False), nullable=False, server_default="OUTRO"),
        sa.Column("interesse_plano", sa.Enum("TRIAL", "STARTER", "PRO", "BUSINESS", name="interesseplano", native_enum=False), nullable=True),
        sa.Column("valor_proposto", sa.Float(), nullable=True),
        sa.Column("status_pipeline", sa.Enum("NOVO", "CONTATO_INICIADO", "PROPOSTA_ENVIADA", "NEGOCIACAO", "FECHADO_GANHO", "FECHADO_PERDIDO", name="statuspipeline", native_enum=False), nullable=False, server_default="NOVO"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ultimo_contato_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proximo_contato_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_leads_id"), "commercial_leads", ["id"], unique=False)
    
    # Tabela de interações comerciais
    op.create_table(
        "commercial_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.Enum("OBSERVACAO", "WHATSAPP", "EMAIL", "PROPOSTA", "MUDANCA_STATUS", "LEMBRETE", name="tipointeracao", native_enum=False), nullable=False),
        sa.Column("canal", sa.Enum("WHATSAPP", "EMAIL", "LIGACAO", "REUNIAO", "OUTRO", name="canalinteracao", native_enum=False), nullable=True),
        sa.Column("conteudo", sa.Text(), nullable=True),
        sa.Column("status_envio", sa.String(20), nullable=False, server_default="enviado"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["commercial_leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_interactions_id"), "commercial_interactions", ["id"], unique=False)
    op.create_index(op.f("ix_commercial_interactions_lead_id"), "commercial_interactions", ["lead_id"], unique=False)


def downgrade() -> None:
    """Remove tabelas commercial_interactions e commercial_leads."""
    op.drop_index(op.f("ix_commercial_interactions_lead_id"), table_name="commercial_interactions")
    op.drop_index(op.f("ix_commercial_interactions_id"), table_name="commercial_interactions")
    op.drop_table("commercial_interactions")
    
    op.drop_index(op.f("ix_commercial_leads_id"), table_name="commercial_leads")
    op.drop_table("commercial_leads")
    
    # Remover enums criados
    op.execute("DROP TYPE IF EXISTS canalinteracao")
    op.execute("DROP TYPE IF EXISTS tipointeracao")
    op.execute("DROP TYPE IF EXISTS statuspipeline")
    op.execute("DROP TYPE IF EXISTS interesseplano")
    op.execute("DROP TYPE IF EXISTS origemlead")
    op.execute("DROP TYPE IF EXISTS segmentolead")
