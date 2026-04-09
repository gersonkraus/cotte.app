"""add aceite_pendente_em to orcamentos

Revision ID: g001
Revises: 9f0c_add_bancos_pix_empresa
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'g001'
down_revision = '9f0c_add_bancos_pix_empresa'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orcamentos', sa.Column('aceite_pendente_em', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('orcamentos', 'aceite_pendente_em')
