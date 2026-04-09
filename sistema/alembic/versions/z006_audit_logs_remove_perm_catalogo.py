"""Cria tabela audit_logs e remove coluna perm_catalogo de usuarios.

Antes de remover perm_catalogo, migra todos os usuários com perm_catalogo=True
que ainda não tenham 'catalogo' no JSON de permissoes, populando com 'escrita'.

Revision ID: z006_audit_security
Revises: z005_status_pipeline_missing
Create Date: 2026-03-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "z006_audit_security"
down_revision: Union[str, Sequence[str], None] = "z005_status_pipeline_missing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tabelas = inspector.get_table_names()

    # ── 1. Criar tabela audit_logs ──────────────────────────────────────────
    if "audit_logs" not in tabelas:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=True),
            sa.Column("usuario_id", sa.Integer(), nullable=True),
            sa.Column("usuario_nome", sa.String(100), nullable=True),
            sa.Column("acao", sa.String(100), nullable=False),
            sa.Column("recurso", sa.String(100), nullable=True),
            sa.Column("recurso_id", sa.String(50), nullable=True),
            sa.Column("detalhes", sa.Text(), nullable=True),
            sa.Column("ip", sa.String(50), nullable=True),
            sa.Column(
                "criado_em",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_logs_empresa_id", "audit_logs", ["empresa_id"])
        op.create_index("ix_audit_logs_usuario_id", "audit_logs", ["usuario_id"])
        op.create_index("ix_audit_logs_criado_em", "audit_logs", ["criado_em"])

    # ── 2. Migrar perm_catalogo → permissoes["catalogo"] = "escrita" ────────
    cols_usuarios = {c["name"] for c in inspector.get_columns("usuarios")}
    if "perm_catalogo" in cols_usuarios:
        # Atualiza apenas quem tem perm_catalogo=True E não tem 'catalogo' no JSON
        conn.execute(
            sa.text(
                """
                UPDATE usuarios
                SET permissoes = COALESCE(permissoes, '{}'::jsonb) || '{"catalogo": "escrita"}'::jsonb
                WHERE perm_catalogo = TRUE
                  AND (permissoes IS NULL OR NOT (permissoes ? 'catalogo'))
                """
            )
        )

        # ── 3. Remover coluna perm_catalogo ─────────────────────────────────
        op.drop_column("usuarios", "perm_catalogo")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols_usuarios = {c["name"] for c in inspector.get_columns("usuarios")}

    # Restaura coluna perm_catalogo se não existir
    if "perm_catalogo" not in cols_usuarios:
        op.add_column(
            "usuarios",
            sa.Column("perm_catalogo", sa.Boolean(), nullable=True, server_default="false"),
        )
        # Restaura flag para quem tem 'catalogo' no JSON
        conn.execute(
            sa.text(
                """
                UPDATE usuarios
                SET perm_catalogo = TRUE
                WHERE permissoes ? 'catalogo'
                """
            )
        )

    # Remove tabela audit_logs
    tabelas = inspector.get_table_names()
    if "audit_logs" in tabelas:
        op.drop_index("ix_audit_logs_criado_em", table_name="audit_logs")
        op.drop_index("ix_audit_logs_usuario_id", table_name="audit_logs")
        op.drop_index("ix_audit_logs_empresa_id", table_name="audit_logs")
        op.drop_table("audit_logs")
