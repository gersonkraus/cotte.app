"""add tenant comercial tables

Revision ID: tc002_add_tenant_comercial_tables
Revises: 6f8002896a1d
Create Date: 2026-04-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "tc002_add_tenant_comercial_tables"
down_revision: Union[str, None] = "6f8002896a1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_pipeline_etapas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=True),
        sa.Column("cor", sa.String(length=7), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_pipeline_etapas_empresa_id"),
        "tenant_pipeline_etapas",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_pipeline_etapas_id"),
        "tenant_pipeline_etapas",
        ["id"],
        unique=False,
    )

    op.create_table(
        "tenant_commercial_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("telefone", sa.String(length=20), nullable=True),
        sa.Column("segmento", sa.String(length=100), nullable=True),
        sa.Column("origem", sa.String(length=100), nullable=True),
        sa.Column("etapa_pipeline_id", sa.Integer(), nullable=True),
        sa.Column("valor_estimado", sa.Numeric(12, 2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsavel_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["etapa_pipeline_id"], ["tenant_pipeline_etapas.id"]),
        sa.ForeignKeyConstraint(["responsavel_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_commercial_leads_empresa_id"),
        "tenant_commercial_leads",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_commercial_leads_id"),
        "tenant_commercial_leads",
        ["id"],
        unique=False,
    )

    op.create_table(
        "tenant_propostas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("valor_total", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("enviada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["tenant_commercial_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_propostas_empresa_id"),
        "tenant_propostas",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_propostas_id"),
        "tenant_propostas",
        ["id"],
        unique=False,
    )

    op.create_table(
        "tenant_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_configs_empresa_id"),
        "tenant_configs",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_configs_id"),
        "tenant_configs",
        ["id"],
        unique=False,
    )

    op.create_table(
        "tenant_commercial_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "OBSERVACAO",
                "WHATSAPP",
                "EMAIL",
                "PROPOSTA",
                "MUDANCA_STATUS",
                "TAREFA",
                "LEMBRETE",
                "OUTRO",
                name="tipointeracao",
            ),
            nullable=False,
        ),
        sa.Column(
            "canal",
            sa.Enum(
                "WHATSAPP",
                "EMAIL",
                "SISTEMA",
                "LIGACAO",
                "REUNIAO",
                "OUTRO",
                name="canalinteracao",
            ),
            nullable=True,
        ),
        sa.Column("conteudo", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["tenant_commercial_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_commercial_interactions_empresa_id"),
        "tenant_commercial_interactions",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_commercial_interactions_id"),
        "tenant_commercial_interactions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_commercial_interactions_lead_id"),
        "tenant_commercial_interactions",
        ["lead_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tenant_commercial_interactions_lead_id"), table_name="tenant_commercial_interactions")
    op.drop_index(op.f("ix_tenant_commercial_interactions_id"), table_name="tenant_commercial_interactions")
    op.drop_index(op.f("ix_tenant_commercial_interactions_empresa_id"), table_name="tenant_commercial_interactions")
    op.drop_table("tenant_commercial_interactions")

    op.drop_index(op.f("ix_tenant_configs_id"), table_name="tenant_configs")
    op.drop_index(op.f("ix_tenant_configs_empresa_id"), table_name="tenant_configs")
    op.drop_table("tenant_configs")

    op.drop_index(op.f("ix_tenant_propostas_id"), table_name="tenant_propostas")
    op.drop_index(op.f("ix_tenant_propostas_empresa_id"), table_name="tenant_propostas")
    op.drop_table("tenant_propostas")

    op.drop_index(op.f("ix_tenant_commercial_leads_id"), table_name="tenant_commercial_leads")
    op.drop_index(op.f("ix_tenant_commercial_leads_empresa_id"), table_name="tenant_commercial_leads")
    op.drop_table("tenant_commercial_leads")

    op.drop_index(op.f("ix_tenant_pipeline_etapas_id"), table_name="tenant_pipeline_etapas")
    op.drop_index(op.f("ix_tenant_pipeline_etapas_empresa_id"), table_name="tenant_pipeline_etapas")
    op.drop_table("tenant_pipeline_etapas")

    sa.Enum(name="tipointeracao").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="canalinteracao").drop(op.get_bind(), checkfirst=True)
