"""add tipo to historico_edicoes

Revision ID: 8aa701096665
Revises: 4f007c9fa25f
Create Date: 2026-04-21 19:32:39.403175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '8aa701096665'
down_revision: Union[str, None] = '4f007c9fa25f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("historico_edicoes")}

    if "tipo" not in columns:
        op.add_column('historico_edicoes', sa.Column('tipo', sa.String(length=64), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("historico_edicoes")}

    if "tipo" in columns:
        op.drop_column('historico_edicoes', 'tipo')
