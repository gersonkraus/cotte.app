"""merge tc006 endereco tenant and z025 address fields

Revision ID: z026_merge_tc006_z025
Revises: tc006_add_endereco_tenant, z025_add_address_fields
Create Date: 2026-04-30

"""
from typing import Sequence, Union

revision: str = 'z026_merge_tc006_z025'
down_revision: Union[str, Sequence[str]] = ('tc006_add_endereco_tenant', 'z025_add_address_fields')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
