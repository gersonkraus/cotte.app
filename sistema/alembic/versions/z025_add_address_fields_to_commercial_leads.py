"""add address fields to commercial_leads

Adiciona campos de endereço completo ao modelo CommercialLead:
cep, logradouro, numero, complemento, bairro, uf

Revision ID: z025_add_address_fields
Revises: z023_agendamento_opcao_escolhida, z024_merge_823_alias, z_merge_p_and_e_heads
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "z025_add_address_fields"
down_revision: Union[str, None, tuple] = (
    "z023_agendamento_opcao_escolhida",
    "z024_merge_823_alias",
    "z_merge_p_and_e_heads",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if table_name not in set(inspector.get_table_names()):
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    cols = [
        ("cep", sa.String(9)),
        ("logradouro", sa.String(200)),
        ("numero", sa.String(20)),
        ("complemento", sa.String(100)),
        ("bairro", sa.String(100)),
        ("uf", sa.String(2)),
    ]
    for col_name, col_type in cols:
        if not _has_column(inspector, "commercial_leads", col_name):
            op.add_column(
                "commercial_leads",
                sa.Column(col_name, col_type, nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for col_name in ("uf", "bairro", "complemento", "numero", "logradouro", "cep"):
        if _has_column(inspector, "commercial_leads", col_name):
            op.drop_column("commercial_leads", col_name)
