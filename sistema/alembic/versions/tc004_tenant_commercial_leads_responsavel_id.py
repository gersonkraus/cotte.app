"""Adiciona responsavel_id em tenant_commercial_leads se ausente.

Cenário: tabela criada parcialmente ou antes da coluna; tc002 retorna cedo
quando tenant_pipeline_etapas já existia, deixando schema desalinhado do modelo.

Revision ID: tc004_tenant_commercial_leads_responsavel
Revises: tc003_add_modulo_comercial
Create Date: 2026-04-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tc004_tenant_commercial_leads_responsavel"
down_revision: Union[str, None] = "tc003_add_modulo_comercial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("tenant_commercial_leads"):
        return
    cols = {c["name"] for c in insp.get_columns("tenant_commercial_leads")}
    if "responsavel_id" in cols:
        return
    op.add_column(
        "tenant_commercial_leads",
        sa.Column("responsavel_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tenant_commercial_leads_responsavel_id_usuarios",
        "tenant_commercial_leads",
        "usuarios",
        ["responsavel_id"],
        ["id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("tenant_commercial_leads"):
        return
    cols = {c["name"] for c in insp.get_columns("tenant_commercial_leads")}
    if "responsavel_id" not in cols:
        return
    op.drop_constraint(
        "fk_tenant_commercial_leads_responsavel_id_usuarios",
        "tenant_commercial_leads",
        type_="foreignkey",
    )
    op.drop_column("tenant_commercial_leads", "responsavel_id")
