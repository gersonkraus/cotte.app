"""feat: documentos da empresa

Revision ID: b8c1d2e3f4a5
Revises: a07fa98d3427
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c1d2e3f4a5"
down_revision: Union[str, None] = "a07fa98d3427"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tipo_enum = sa.Enum(
        "certificado_garantia",
        "contrato",
        "termo",
        "documento_tecnico",
        "anexo",
        "outro",
        name="tipo_documento_empresa",
    )
    status_enum = sa.Enum(
        "ativo",
        "inativo",
        "arquivado",
        name="status_documento_empresa",
    )

    op.create_table(
        "documentos_empresa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=True),
        sa.Column("tipo", tipo_enum, server_default="outro", nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("arquivo_path", sa.String(length=500), nullable=False),
        sa.Column("arquivo_nome_original", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=True),
        sa.Column("versao", sa.String(length=50), nullable=True),
        sa.Column("status", status_enum, server_default="ativo", nullable=False),
        sa.Column("permite_download", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("visivel_no_portal", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "slug", name="uq_documentos_empresa_empresa_slug"),
    )
    op.create_index(op.f("ix_documentos_empresa_empresa_id"), "documentos_empresa", ["empresa_id"], unique=False)
    op.create_index(op.f("ix_documentos_empresa_id"), "documentos_empresa", ["id"], unique=False)

    op.create_table(
        "orcamento_documentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("orcamento_id", sa.Integer(), nullable=False),
        sa.Column("documento_id", sa.Integer(), nullable=True),
        sa.Column("ordem", sa.Integer(), server_default="0", nullable=False),
        sa.Column("exibir_no_portal", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("enviar_por_email", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("enviar_por_whatsapp", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("documento_nome", sa.String(length=200), nullable=False),
        sa.Column("documento_tipo", sa.String(length=50), nullable=True),
        sa.Column("documento_versao", sa.String(length=50), nullable=True),
        sa.Column("arquivo_path", sa.String(length=500), nullable=False),
        sa.Column("arquivo_nome_original", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=True),
        sa.Column("permite_download", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos_empresa.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["orcamento_id"], ["orcamentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("orcamento_id", "documento_id", name="uq_orcamento_documentos_orcamento_documento"),
    )
    op.create_index(op.f("ix_orcamento_documentos_documento_id"), "orcamento_documentos", ["documento_id"], unique=False)
    op.create_index(op.f("ix_orcamento_documentos_id"), "orcamento_documentos", ["id"], unique=False)
    op.create_index(op.f("ix_orcamento_documentos_orcamento_id"), "orcamento_documentos", ["orcamento_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orcamento_documentos_orcamento_id"), table_name="orcamento_documentos")
    op.drop_index(op.f("ix_orcamento_documentos_id"), table_name="orcamento_documentos")
    op.drop_index(op.f("ix_orcamento_documentos_documento_id"), table_name="orcamento_documentos")
    op.drop_table("orcamento_documentos")

    op.drop_index(op.f("ix_documentos_empresa_id"), table_name="documentos_empresa")
    op.drop_index(op.f("ix_documentos_empresa_empresa_id"), table_name="documentos_empresa")
    op.drop_table("documentos_empresa")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS status_documento_empresa")
        op.execute("DROP TYPE IF EXISTS tipo_documento_empresa")
