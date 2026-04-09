"""Amplia alembic_version.version_num para VARCHAR(255).

O PostgreSQL padrão do Alembic usa version_num VARCHAR(32). Revisões com ID
longo (ex.: z013_template_publico_default_classico) estouram ao gravar a versão.

Revision ID: z012a_widen_alembic_ver
Revises: z012_template_publico
Create Date: 2026-03-29
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "z012a_widen_alembic_ver"
down_revision: Union[str, None] = "z012_template_publico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)"
            )
        )
