"""add_mercadolivre_integration_tables

Revision ID: ml001_add_mercadolivre_integration_tables
Revises: 0659a14bdfbe
Create Date: 2026-05-08 18:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ml001_add_mercadolivre_integration_tables"
down_revision: Union[str, None] = "0659a14bdfbe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "integracoes_mercadolivre"):
        op.create_table(
            "integracoes_mercadolivre",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("ml_user_id", sa.String(length=30), nullable=True),
            sa.Column("ml_nickname", sa.String(length=120), nullable=True),
            sa.Column("access_token", sa.Text(), nullable=True),
            sa.Column("refresh_token", sa.Text(), nullable=True),
            sa.Column("token_type", sa.String(length=20), nullable=True),
            sa.Column("token_scope", sa.String(length=200), nullable=True),
            sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("conectado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("oauth_state", sa.String(length=255), nullable=True),
            sa.Column("oauth_state_expira_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ultimo_sync_pedidos_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ultimo_sync_anuncios_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ultimo_erro", sa.Text(), nullable=True),
            sa.Column(
                "criado_em",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "atualizado_em",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("empresa_id"),
            sa.UniqueConstraint("ml_user_id"),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "integracoes_mercadolivre", op.f("ix_integracoes_mercadolivre_id")):
        op.create_index(
            op.f("ix_integracoes_mercadolivre_id"),
            "integracoes_mercadolivre",
            ["id"],
            unique=False,
        )
    if not _index_exists(inspector, "integracoes_mercadolivre", op.f("ix_integracoes_mercadolivre_empresa_id")):
        op.create_index(
            op.f("ix_integracoes_mercadolivre_empresa_id"),
            "integracoes_mercadolivre",
            ["empresa_id"],
            unique=False,
        )
    if not _index_exists(inspector, "integracoes_mercadolivre", op.f("ix_integracoes_mercadolivre_ml_user_id")):
        op.create_index(
            op.f("ix_integracoes_mercadolivre_ml_user_id"),
            "integracoes_mercadolivre",
            ["ml_user_id"],
            unique=False,
        )

    if not _table_exists(inspector, "mercadolivre_pedidos_snapshot"):
        op.create_table(
            "mercadolivre_pedidos_snapshot",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("resource_id", sa.String(length=80), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=True),
            sa.Column("atualizado_em_remoto", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column(
                "sincronizado_em",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "empresa_id",
                "resource_id",
                name="uq_mercadolivre_pedido_empresa_resource",
            ),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_id")):
        op.create_index(
            op.f("ix_mercadolivre_pedidos_snapshot_id"),
            "mercadolivre_pedidos_snapshot",
            ["id"],
            unique=False,
        )
    if not _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_empresa_id")):
        op.create_index(
            op.f("ix_mercadolivre_pedidos_snapshot_empresa_id"),
            "mercadolivre_pedidos_snapshot",
            ["empresa_id"],
            unique=False,
        )
    if not _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_resource_id")):
        op.create_index(
            op.f("ix_mercadolivre_pedidos_snapshot_resource_id"),
            "mercadolivre_pedidos_snapshot",
            ["resource_id"],
            unique=False,
        )
    if not _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_payload_hash")):
        op.create_index(
            op.f("ix_mercadolivre_pedidos_snapshot_payload_hash"),
            "mercadolivre_pedidos_snapshot",
            ["payload_hash"],
            unique=False,
        )

    if not _table_exists(inspector, "mercadolivre_anuncios_snapshot"):
        op.create_table(
            "mercadolivre_anuncios_snapshot",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("resource_id", sa.String(length=80), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=True),
            sa.Column("atualizado_em_remoto", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column(
                "sincronizado_em",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "empresa_id",
                "resource_id",
                name="uq_mercadolivre_anuncio_empresa_resource",
            ),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_id")):
        op.create_index(
            op.f("ix_mercadolivre_anuncios_snapshot_id"),
            "mercadolivre_anuncios_snapshot",
            ["id"],
            unique=False,
        )
    if not _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_empresa_id")):
        op.create_index(
            op.f("ix_mercadolivre_anuncios_snapshot_empresa_id"),
            "mercadolivre_anuncios_snapshot",
            ["empresa_id"],
            unique=False,
        )
    if not _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_resource_id")):
        op.create_index(
            op.f("ix_mercadolivre_anuncios_snapshot_resource_id"),
            "mercadolivre_anuncios_snapshot",
            ["resource_id"],
            unique=False,
        )
    if not _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_payload_hash")):
        op.create_index(
            op.f("ix_mercadolivre_anuncios_snapshot_payload_hash"),
            "mercadolivre_anuncios_snapshot",
            ["payload_hash"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "mercadolivre_anuncios_snapshot"):
        if _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_payload_hash")):
            op.drop_index(
                op.f("ix_mercadolivre_anuncios_snapshot_payload_hash"),
                table_name="mercadolivre_anuncios_snapshot",
            )
        if _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_resource_id")):
            op.drop_index(
                op.f("ix_mercadolivre_anuncios_snapshot_resource_id"),
                table_name="mercadolivre_anuncios_snapshot",
            )
        if _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_empresa_id")):
            op.drop_index(
                op.f("ix_mercadolivre_anuncios_snapshot_empresa_id"),
                table_name="mercadolivre_anuncios_snapshot",
            )
        if _index_exists(inspector, "mercadolivre_anuncios_snapshot", op.f("ix_mercadolivre_anuncios_snapshot_id")):
            op.drop_index(
                op.f("ix_mercadolivre_anuncios_snapshot_id"),
                table_name="mercadolivre_anuncios_snapshot",
            )
        op.drop_table("mercadolivre_anuncios_snapshot")
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "mercadolivre_pedidos_snapshot"):
        if _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_payload_hash")):
            op.drop_index(
                op.f("ix_mercadolivre_pedidos_snapshot_payload_hash"),
                table_name="mercadolivre_pedidos_snapshot",
            )
        if _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_resource_id")):
            op.drop_index(
                op.f("ix_mercadolivre_pedidos_snapshot_resource_id"),
                table_name="mercadolivre_pedidos_snapshot",
            )
        if _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_empresa_id")):
            op.drop_index(
                op.f("ix_mercadolivre_pedidos_snapshot_empresa_id"),
                table_name="mercadolivre_pedidos_snapshot",
            )
        if _index_exists(inspector, "mercadolivre_pedidos_snapshot", op.f("ix_mercadolivre_pedidos_snapshot_id")):
            op.drop_index(
                op.f("ix_mercadolivre_pedidos_snapshot_id"),
                table_name="mercadolivre_pedidos_snapshot",
            )
        op.drop_table("mercadolivre_pedidos_snapshot")
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "integracoes_mercadolivre"):
        if _index_exists(inspector, "integracoes_mercadolivre", op.f("ix_integracoes_mercadolivre_ml_user_id")):
            op.drop_index(
                op.f("ix_integracoes_mercadolivre_ml_user_id"),
                table_name="integracoes_mercadolivre",
            )
        if _index_exists(inspector, "integracoes_mercadolivre", op.f("ix_integracoes_mercadolivre_empresa_id")):
            op.drop_index(
                op.f("ix_integracoes_mercadolivre_empresa_id"),
                table_name="integracoes_mercadolivre",
            )
        if _index_exists(inspector, "integracoes_mercadolivre", op.f("ix_integracoes_mercadolivre_id")):
            op.drop_index(
                op.f("ix_integracoes_mercadolivre_id"),
                table_name="integracoes_mercadolivre",
            )
        op.drop_table("integracoes_mercadolivre")
