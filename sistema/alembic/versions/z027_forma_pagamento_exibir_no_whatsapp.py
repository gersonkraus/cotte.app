"""forma_pagamento: adiciona campo exibir_no_whatsapp

Revision ID: z027_forma_pagamento_exibir_no_whatsapp
Revises: aa51e0f91548
Create Date: 2026-05-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "z027_forma_pagamento_exibir_no_whatsapp"
down_revision: Union[str, Sequence[str]] = "aa51e0f91548"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "formas_pagamento_config",
        sa.Column(
            "exibir_no_whatsapp",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("formas_pagamento_config", "exibir_no_whatsapp")
