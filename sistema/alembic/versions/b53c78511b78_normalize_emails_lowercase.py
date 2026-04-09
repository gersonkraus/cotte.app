"""normalize_emails_lowercase

Revision ID: b53c78511b78
Revises: o001_add_campos_fiscais_cliente
Create Date: 2026-03-22 21:27:52.471503

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b53c78511b78"
down_revision: Union[str, None] = "o001_add_campos_fiscais_cliente"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Para usuários com email misto onde já existe versão minúscula (duplicata),
    # marca com sufixo _dup_ID para evitar conflito de FK — não podemos deletar
    # pois podem ter registros vinculados (orçamentos, etc.)
    op.execute("""
        UPDATE usuarios
        SET email = lower(email) || '_dup_' || id::text
        WHERE email != lower(email)
          AND lower(email) IN (
              SELECT email FROM usuarios WHERE email = lower(email)
          )
    """)
    # Normaliza os emails restantes que ainda têm maiúsculas (sem duplicata)
    op.execute("UPDATE usuarios SET email = lower(email) WHERE email != lower(email)")


def downgrade() -> None:
    pass
