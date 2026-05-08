"""add_mercadolivre_domain_tables

Revision ID: ml002_add_mercadolivre_domain_tables
Revises: ml001_add_mercadolivre_integration_tables
Create Date: 2026-05-08 19:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ml002_add_mercadolivre_domain_tables"
down_revision: Union[str, None] = "ml001_add_mercadolivre_integration_tables"
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

    if not _table_exists(inspector, "mercadolivre_pedido_vinculos"):
        op.create_table(
            "mercadolivre_pedido_vinculos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("ml_order_id", sa.String(length=80), nullable=False),
            sa.Column("orcamento_id", sa.Integer(), nullable=False),
            sa.Column("status_ml", sa.String(length=40), nullable=True),
            sa.Column("status_sync", sa.String(length=30), nullable=False, server_default="ok"),
            sa.Column("erro", sa.Text(), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.ForeignKeyConstraint(["orcamento_id"], ["orcamentos.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("empresa_id", "ml_order_id", name="uq_mercadolivre_pedido_vinculos_empresa_order"),
            sa.UniqueConstraint("empresa_id", "orcamento_id", name="uq_mercadolivre_pedido_vinculos_empresa_orcamento"),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "mercadolivre_pedido_vinculos", op.f("ix_mercadolivre_pedido_vinculos_id")):
        op.create_index(op.f("ix_mercadolivre_pedido_vinculos_id"), "mercadolivre_pedido_vinculos", ["id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_pedido_vinculos", op.f("ix_mercadolivre_pedido_vinculos_empresa_id")):
        op.create_index(op.f("ix_mercadolivre_pedido_vinculos_empresa_id"), "mercadolivre_pedido_vinculos", ["empresa_id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_pedido_vinculos", op.f("ix_mercadolivre_pedido_vinculos_ml_order_id")):
        op.create_index(op.f("ix_mercadolivre_pedido_vinculos_ml_order_id"), "mercadolivre_pedido_vinculos", ["ml_order_id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_pedido_vinculos", op.f("ix_mercadolivre_pedido_vinculos_orcamento_id")):
        op.create_index(op.f("ix_mercadolivre_pedido_vinculos_orcamento_id"), "mercadolivre_pedido_vinculos", ["orcamento_id"], unique=False)

    if not _table_exists(inspector, "mercadolivre_item_vinculos"):
        op.create_table(
            "mercadolivre_item_vinculos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("ml_item_id", sa.String(length=80), nullable=False),
            sa.Column("servico_id", sa.Integer(), nullable=False),
            sa.Column("sync_mode", sa.String(length=20), nullable=False, server_default="ml_only_pull"),
            sa.Column("allow_push_price", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("allow_push_stock", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("allow_push_title", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("allow_push_description", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_pull_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_push_hash", sa.String(length=64), nullable=True),
            sa.Column("source_of_truth", sa.String(length=20), nullable=False, server_default="ml"),
            sa.Column("ultimo_erro", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.ForeignKeyConstraint(["servico_id"], ["servicos.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("empresa_id", "ml_item_id", name="uq_mercadolivre_item_vinculos_empresa_item"),
            sa.UniqueConstraint("empresa_id", "servico_id", name="uq_mercadolivre_item_vinculos_empresa_servico"),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "mercadolivre_item_vinculos", op.f("ix_mercadolivre_item_vinculos_id")):
        op.create_index(op.f("ix_mercadolivre_item_vinculos_id"), "mercadolivre_item_vinculos", ["id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_item_vinculos", op.f("ix_mercadolivre_item_vinculos_empresa_id")):
        op.create_index(op.f("ix_mercadolivre_item_vinculos_empresa_id"), "mercadolivre_item_vinculos", ["empresa_id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_item_vinculos", op.f("ix_mercadolivre_item_vinculos_ml_item_id")):
        op.create_index(op.f("ix_mercadolivre_item_vinculos_ml_item_id"), "mercadolivre_item_vinculos", ["ml_item_id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_item_vinculos", op.f("ix_mercadolivre_item_vinculos_servico_id")):
        op.create_index(op.f("ix_mercadolivre_item_vinculos_servico_id"), "mercadolivre_item_vinculos", ["servico_id"], unique=False)

    if not _table_exists(inspector, "mercadolivre_sync_jobs"):
        op.create_table(
            "mercadolivre_sync_jobs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("counters_json", sa.JSON(), nullable=True),
            sa.Column("erro", sa.Text(), nullable=True),
            sa.Column("trigger_source", sa.String(length=20), nullable=True),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "mercadolivre_sync_jobs", op.f("ix_mercadolivre_sync_jobs_id")):
        op.create_index(op.f("ix_mercadolivre_sync_jobs_id"), "mercadolivre_sync_jobs", ["id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_sync_jobs", op.f("ix_mercadolivre_sync_jobs_empresa_id")):
        op.create_index(op.f("ix_mercadolivre_sync_jobs_empresa_id"), "mercadolivre_sync_jobs", ["empresa_id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_sync_jobs", op.f("ix_mercadolivre_sync_jobs_tipo")):
        op.create_index(op.f("ix_mercadolivre_sync_jobs_tipo"), "mercadolivre_sync_jobs", ["tipo"], unique=False)
    if not _index_exists(inspector, "mercadolivre_sync_jobs", op.f("ix_mercadolivre_sync_jobs_status")):
        op.create_index(op.f("ix_mercadolivre_sync_jobs_status"), "mercadolivre_sync_jobs", ["status"], unique=False)

    if not _table_exists(inspector, "mercadolivre_sync_lock"):
        op.create_table(
            "mercadolivre_sync_lock",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(length=40), nullable=False),
            sa.Column("lock_token", sa.String(length=80), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("empresa_id", "tipo", name="uq_mercadolivre_sync_lock_empresa_tipo"),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "mercadolivre_sync_lock", op.f("ix_mercadolivre_sync_lock_id")):
        op.create_index(op.f("ix_mercadolivre_sync_lock_id"), "mercadolivre_sync_lock", ["id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_sync_lock", op.f("ix_mercadolivre_sync_lock_empresa_id")):
        op.create_index(op.f("ix_mercadolivre_sync_lock_empresa_id"), "mercadolivre_sync_lock", ["empresa_id"], unique=False)
    if not _index_exists(inspector, "mercadolivre_sync_lock", op.f("ix_mercadolivre_sync_lock_tipo")):
        op.create_index(op.f("ix_mercadolivre_sync_lock_tipo"), "mercadolivre_sync_lock", ["tipo"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "mercadolivre_sync_lock"):
        for idx in (
            op.f("ix_mercadolivre_sync_lock_tipo"),
            op.f("ix_mercadolivre_sync_lock_empresa_id"),
            op.f("ix_mercadolivre_sync_lock_id"),
        ):
            if _index_exists(inspector, "mercadolivre_sync_lock", idx):
                op.drop_index(idx, table_name="mercadolivre_sync_lock")
        op.drop_table("mercadolivre_sync_lock")
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "mercadolivre_sync_jobs"):
        for idx in (
            op.f("ix_mercadolivre_sync_jobs_status"),
            op.f("ix_mercadolivre_sync_jobs_tipo"),
            op.f("ix_mercadolivre_sync_jobs_empresa_id"),
            op.f("ix_mercadolivre_sync_jobs_id"),
        ):
            if _index_exists(inspector, "mercadolivre_sync_jobs", idx):
                op.drop_index(idx, table_name="mercadolivre_sync_jobs")
        op.drop_table("mercadolivre_sync_jobs")
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "mercadolivre_item_vinculos"):
        for idx in (
            op.f("ix_mercadolivre_item_vinculos_servico_id"),
            op.f("ix_mercadolivre_item_vinculos_ml_item_id"),
            op.f("ix_mercadolivre_item_vinculos_empresa_id"),
            op.f("ix_mercadolivre_item_vinculos_id"),
        ):
            if _index_exists(inspector, "mercadolivre_item_vinculos", idx):
                op.drop_index(idx, table_name="mercadolivre_item_vinculos")
        op.drop_table("mercadolivre_item_vinculos")
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "mercadolivre_pedido_vinculos"):
        for idx in (
            op.f("ix_mercadolivre_pedido_vinculos_orcamento_id"),
            op.f("ix_mercadolivre_pedido_vinculos_ml_order_id"),
            op.f("ix_mercadolivre_pedido_vinculos_empresa_id"),
            op.f("ix_mercadolivre_pedido_vinculos_id"),
        ):
            if _index_exists(inspector, "mercadolivre_pedido_vinculos", idx):
                op.drop_index(idx, table_name="mercadolivre_pedido_vinculos")
        op.drop_table("mercadolivre_pedido_vinculos")

