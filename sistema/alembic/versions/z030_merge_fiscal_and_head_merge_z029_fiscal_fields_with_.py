"""merge z029_fiscal_fields with 661b24753e61

Revision ID: z030_merge_fiscal_and_head
Revises: 661b24753e61, z029_add_fiscal_fields_servicos
Create Date: 2026-05-12 01:03:49.855445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'z030_merge_fiscal_and_head'
down_revision: Union[str, None] = ('661b24753e61', 'z029_add_fiscal_fields_servicos')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
