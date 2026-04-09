"""merge heads

Revision ID: 20260323_merge_heads
Revises: 20260323_preco_custo, z_merge_p_and_e_heads
Create Date: 2026-03-23 14:51:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260323_merge_heads'
down_revision = ('20260323_preco_custo', 'z_merge_p_and_e_heads')
branch_labels = None
depends_on = None


def upgrade():
    """Merge das duas heads - não faz nada, apenas une as branches"""
    pass


def downgrade():
    pass