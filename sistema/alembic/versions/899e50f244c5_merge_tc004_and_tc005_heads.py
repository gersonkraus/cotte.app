"""merge tc004 and tc005 heads

Revision ID: 899e50f244c5
Revises: tc004_tenant_commercial_leads_responsavel, tc005_tenant_comercial_full_parity
Create Date: 2026-04-26 16:53:51.639323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '899e50f244c5'
down_revision: Union[str, None] = ('tc004_tenant_commercial_leads_responsavel', 'tc005_tenant_comercial_full_parity')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
