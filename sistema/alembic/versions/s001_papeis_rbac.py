"""feat: sistema de papeis RBAC (acoes nos modulos + tabela papeis + papel_id em usuarios)

Revision ID: s001_papeis_rbac
Revises: e6ac99cf785c
Create Date: 2026-03-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "s001_papeis_rbac"
down_revision: Union[str, None] = "e6ac99cf785c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
    ), {"t": table})
    return result.fetchone() is not None


def _index_exists(conn, index: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :i"
    ), {"i": index})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Adicionar coluna 'acoes' em modulos_sistema (se não existir)
    if not _column_exists(conn, "modulos_sistema", "acoes"):
        op.add_column(
            "modulos_sistema",
            sa.Column(
                "acoes",
                sa.JSON(),
                nullable=True,
                server_default=sa.text("'[\"leitura\", \"escrita\", \"exclusao\", \"admin\"]'::json"),
            ),
        )

    # 2. Criar tabela 'papeis' (se não existir)
    if not _table_exists(conn, "papeis"):
        op.create_table(
            "papeis",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False, index=True),
            sa.Column("nome", sa.String(100), nullable=False),
            sa.Column("slug", sa.String(50), nullable=False),
            sa.Column("descricao", sa.String(500), nullable=True),
            sa.Column("permissoes", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_sistema", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("empresa_id", "slug", name="uq_papel_empresa_slug"),
        )

    if not _index_exists(conn, "ix_papeis_id"):
        op.create_index("ix_papeis_id", "papeis", ["id"], unique=True)

    if not _index_exists(conn, "ix_papeis_empresa_id"):
        op.create_index("ix_papeis_empresa_id", "papeis", ["empresa_id"], unique=False)

    # 3. Adicionar coluna 'papel_id' em usuarios (se não existir)
    if not _column_exists(conn, "usuarios", "papel_id"):
        op.add_column(
            "usuarios",
            sa.Column("papel_id", sa.Integer(), sa.ForeignKey("papeis.id"), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "usuarios", "papel_id"):
        op.drop_column("usuarios", "papel_id")

    if _index_exists(conn, "ix_papeis_empresa_id"):
        op.drop_index("ix_papeis_empresa_id", table_name="papeis")

    if _index_exists(conn, "ix_papeis_id"):
        op.drop_index("ix_papeis_id", table_name="papeis")

    if _table_exists(conn, "papeis"):
        op.drop_table("papeis")

    if _column_exists(conn, "modulos_sistema", "acoes"):
        op.drop_column("modulos_sistema", "acoes")
