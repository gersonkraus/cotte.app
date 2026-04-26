"""tenant comercial: segmentos, templates, campanhas, import, propostas enviadas tenant, colunas lead/etapa

Revision ID: tc005_tenant_comercial_full_parity
Revises: tc004_tenant_commercial_leads_responsavel
Create Date: 2026-04-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tc005_tenant_comercial_full_parity"
down_revision: Union[str, None] = "tc004_tenant_commercial_leads_responsavel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cols_pipe = {c["name"] for c in insp.get_columns("tenant_pipeline_etapas")} if insp.has_table(
        "tenant_pipeline_etapas"
    ) else set()
    if "slug" not in cols_pipe and insp.has_table("tenant_pipeline_etapas"):
        op.add_column(
            "tenant_pipeline_etapas",
            sa.Column("slug", sa.String(length=50), nullable=True),
        )
        op.create_index(
            "ix_tenant_pipeline_etapas_slug",
            "tenant_pipeline_etapas",
            ["slug"],
            unique=False,
        )

    cols_lead = {c["name"] for c in insp.get_columns("tenant_commercial_leads")} if insp.has_table(
        "tenant_commercial_leads"
    ) else set()
    if "nome_empresa" not in cols_lead and insp.has_table("tenant_commercial_leads"):
        op.add_column(
            "tenant_commercial_leads",
            sa.Column("nome_empresa", sa.String(length=150), nullable=True),
        )
    if "status_pipeline" not in cols_lead and insp.has_table("tenant_commercial_leads"):
        op.add_column(
            "tenant_commercial_leads",
            sa.Column(
                "status_pipeline",
                sa.String(length=50),
                nullable=True,
                server_default="novo",
            ),
        )
        op.create_index(
            "ix_tenant_commercial_leads_status_pipeline",
            "tenant_commercial_leads",
            ["status_pipeline"],
            unique=False,
        )
    if "lead_score" not in cols_lead and insp.has_table("tenant_commercial_leads"):
        op.add_column(
            "tenant_commercial_leads",
            sa.Column(
                "lead_score",
                sa.Enum("quente", "morno", "frio", name="leadscore_tenant", native_enum=False),
                nullable=True,
                server_default="frio",
            ),
        )
    if "proximo_contato_em" not in cols_lead and insp.has_table("tenant_commercial_leads"):
        op.add_column(
            "tenant_commercial_leads",
            sa.Column("proximo_contato_em", sa.DateTime(timezone=True), nullable=True),
        )
    if "ultimo_contato_em" not in cols_lead and insp.has_table("tenant_commercial_leads"):
        op.add_column(
            "tenant_commercial_leads",
            sa.Column("ultimo_contato_em", sa.DateTime(timezone=True), nullable=True),
        )

    if insp.has_table("tenant_commercial_templates"):
        return

    op.create_table(
        "tenant_commercial_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "nome", name="uq_tenant_segment_empresa_nome"),
    )
    op.create_index(
        op.f("ix_tenant_commercial_segments_empresa_id"),
        "tenant_commercial_segments",
        ["empresa_id"],
        unique=False,
    )

    op.create_table(
        "tenant_commercial_lead_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "nome", name="uq_tenant_origem_empresa_nome"),
    )
    op.create_index(
        op.f("ix_tenant_commercial_lead_sources_empresa_id"),
        "tenant_commercial_lead_sources",
        ["empresa_id"],
        unique=False,
    )

    tipotemplate = sa.Enum(
        "mensagem_inicial",
        "followup",
        "proposta_comercial",
        "email_comercial",
        name="tipotemplate",
        create_type=False,
    )
    canaltemplate = sa.Enum("whatsapp", "email", "ambos", name="canaltemplate", create_type=False)

    op.create_table(
        "tenant_commercial_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("tipo", tipotemplate, nullable=False),
        sa.Column("canal", canaltemplate, nullable=False),
        sa.Column("assunto", sa.String(length=200), nullable=True),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_commercial_templates_empresa_id"),
        "tenant_commercial_templates",
        ["empresa_id"],
        unique=False,
    )

    statuslembrete = sa.Enum(
        "pendente", "concluido", "atrasado", name="statuslembrete", create_type=False
    )
    canalsugerido = sa.Enum(
        "whatsapp", "email", "ligacao", "reuniao", name="canalsugerido", create_type=False
    )

    op.create_table(
        "tenant_commercial_reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", statuslembrete, nullable=True),
        sa.Column("canal_sugerido", canalsugerido, nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["tenant_commercial_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_commercial_reminders_empresa_id"),
        "tenant_commercial_reminders",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_commercial_reminders_lead_id"),
        "tenant_commercial_reminders",
        ["lead_id"],
        unique=False,
    )

    op.create_table(
        "tenant_commercial_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("total_leads", sa.Integer(), nullable=True),
        sa.Column("enviados", sa.Integer(), nullable=True),
        sa.Column("entregues", sa.Integer(), nullable=True),
        sa.Column("respondidos", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["tenant_commercial_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_commercial_campaigns_empresa_id"),
        "tenant_commercial_campaigns",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_commercial_campaigns_template_id"),
        "tenant_commercial_campaigns",
        ["template_id"],
        unique=False,
    )

    op.create_table(
        "tenant_campaign_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("data_envio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_entrega", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_resposta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["tenant_commercial_campaigns.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["tenant_commercial_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_campaign_leads_campaign_id"),
        "tenant_campaign_leads",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_campaign_leads_lead_id"),
        "tenant_campaign_leads",
        ["lead_id"],
        unique=False,
    )

    op.create_table(
        "tenant_lead_importacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("metodo", sa.String(length=20), nullable=False),
        sa.Column("total_importados", sa.Integer(), nullable=True),
        sa.Column("total_validos", sa.Integer(), nullable=True),
        sa.Column("total_invalidos", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_lead_importacoes_empresa_id"),
        "tenant_lead_importacoes",
        ["empresa_id"],
        unique=False,
    )

    op.create_table(
        "tenant_lead_importacao_itens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("importacao_id", sa.Integer(), nullable=False),
        sa.Column("nome_responsavel", sa.String(length=100), nullable=False),
        sa.Column("nome_empresa", sa.String(length=150), nullable=False),
        sa.Column("whatsapp", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("cidade", sa.String(length=100), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["importacao_id"], ["tenant_lead_importacoes.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["tenant_commercial_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_lead_importacao_itens_importacao_id"),
        "tenant_lead_importacao_itens",
        ["importacao_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_lead_importacao_itens_lead_id"),
        "tenant_lead_importacao_itens",
        ["lead_id"],
        unique=False,
    )

    statusproposta = sa.Enum(
        "rascunho",
        "enviada",
        "visualizada",
        "aceita",
        "expirada",
        "substituida",
        name="statusproposta",
        create_type=False,
    )

    op.create_table(
        "tenant_propostas_publicas_enviadas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("proposta_publica_id", sa.Integer(), nullable=False),
        sa.Column("tenant_lead_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=36), nullable=False),
        sa.Column("dados_personalizados", sa.JSON(), nullable=True),
        sa.Column("validade_dias", sa.Integer(), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", statusproposta, nullable=True),
        sa.Column("aceita_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aceita_por_nome", sa.String(length=100), nullable=True),
        sa.Column("aceita_por_email", sa.String(length=100), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["proposta_publica_id"], ["propostas_publicas.id"]),
        sa.ForeignKeyConstraint(["tenant_lead_id"], ["tenant_commercial_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_tenant_propostas_publicas_enviadas_empresa_id"),
        "tenant_propostas_publicas_enviadas",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_propostas_publicas_enviadas_tenant_lead_id"),
        "tenant_propostas_publicas_enviadas",
        ["tenant_lead_id"],
        unique=False,
    )

    op.create_table(
        "tenant_propostas_visualizacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proposta_enviada_id", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("secao_mais_vista", sa.String(length=50), nullable=True),
        sa.Column("tempo_segundos", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(
            ["proposta_enviada_id"], ["tenant_propostas_publicas_enviadas.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_propostas_visualizacoes_proposta_enviada_id"),
        "tenant_propostas_visualizacoes",
        ["proposta_enviada_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("tenant_propostas_visualizacoes"):
        op.drop_index(
            op.f("ix_tenant_propostas_visualizacoes_proposta_enviada_id"),
            table_name="tenant_propostas_visualizacoes",
        )
        op.drop_table("tenant_propostas_visualizacoes")

    if insp.has_table("tenant_propostas_publicas_enviadas"):
        op.drop_index(
            op.f("ix_tenant_propostas_publicas_enviadas_tenant_lead_id"),
            table_name="tenant_propostas_publicas_enviadas",
        )
        op.drop_index(
            op.f("ix_tenant_propostas_publicas_enviadas_empresa_id"),
            table_name="tenant_propostas_publicas_enviadas",
        )
        op.drop_table("tenant_propostas_publicas_enviadas")

    if insp.has_table("tenant_lead_importacao_itens"):
        op.drop_index(
            op.f("ix_tenant_lead_importacao_itens_lead_id"),
            table_name="tenant_lead_importacao_itens",
        )
        op.drop_index(
            op.f("ix_tenant_lead_importacao_itens_importacao_id"),
            table_name="tenant_lead_importacao_itens",
        )
        op.drop_table("tenant_lead_importacao_itens")

    if insp.has_table("tenant_lead_importacoes"):
        op.drop_index(
            op.f("ix_tenant_lead_importacoes_empresa_id"),
            table_name="tenant_lead_importacoes",
        )
        op.drop_table("tenant_lead_importacoes")

    if insp.has_table("tenant_campaign_leads"):
        op.drop_index(op.f("ix_tenant_campaign_leads_lead_id"), table_name="tenant_campaign_leads")
        op.drop_index(
            op.f("ix_tenant_campaign_leads_campaign_id"), table_name="tenant_campaign_leads"
        )
        op.drop_table("tenant_campaign_leads")

    if insp.has_table("tenant_commercial_campaigns"):
        op.drop_index(
            op.f("ix_tenant_commercial_campaigns_template_id"),
            table_name="tenant_commercial_campaigns",
        )
        op.drop_index(
            op.f("ix_tenant_commercial_campaigns_empresa_id"),
            table_name="tenant_commercial_campaigns",
        )
        op.drop_table("tenant_commercial_campaigns")

    if insp.has_table("tenant_commercial_reminders"):
        op.drop_index(
            op.f("ix_tenant_commercial_reminders_lead_id"),
            table_name="tenant_commercial_reminders",
        )
        op.drop_index(
            op.f("ix_tenant_commercial_reminders_empresa_id"),
            table_name="tenant_commercial_reminders",
        )
        op.drop_table("tenant_commercial_reminders")

    if insp.has_table("tenant_commercial_templates"):
        op.drop_index(
            op.f("ix_tenant_commercial_templates_empresa_id"),
            table_name="tenant_commercial_templates",
        )
        op.drop_table("tenant_commercial_templates")

    if insp.has_table("tenant_commercial_lead_sources"):
        op.drop_index(
            op.f("ix_tenant_commercial_lead_sources_empresa_id"),
            table_name="tenant_commercial_lead_sources",
        )
        op.drop_table("tenant_commercial_lead_sources")

    if insp.has_table("tenant_commercial_segments"):
        op.drop_index(
            op.f("ix_tenant_commercial_segments_empresa_id"),
            table_name="tenant_commercial_segments",
        )
        op.drop_table("tenant_commercial_segments")

    if insp.has_table("tenant_commercial_leads"):
        cols = {c["name"] for c in insp.get_columns("tenant_commercial_leads")}
        if "ultimo_contato_em" in cols:
            op.drop_column("tenant_commercial_leads", "ultimo_contato_em")
        if "proximo_contato_em" in cols:
            op.drop_column("tenant_commercial_leads", "proximo_contato_em")
        if "lead_score" in cols:
            op.drop_column("tenant_commercial_leads", "lead_score")
        if "status_pipeline" in cols:
            op.drop_index("ix_tenant_commercial_leads_status_pipeline", table_name="tenant_commercial_leads")
            op.drop_column("tenant_commercial_leads", "status_pipeline")
        if "nome_empresa" in cols:
            op.drop_column("tenant_commercial_leads", "nome_empresa")

    if insp.has_table("tenant_pipeline_etapas"):
        pcols = {c["name"] for c in insp.get_columns("tenant_pipeline_etapas")}
        if "slug" in pcols:
            op.drop_index("ix_tenant_pipeline_etapas_slug", table_name="tenant_pipeline_etapas")
            op.drop_column("tenant_pipeline_etapas", "slug")
