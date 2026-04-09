"""add_conteudo_html_tipo_conteudo_to_documentos_empresa

Revision ID: b0bac86d4955
Revises: a001_add_status_envio
Create Date: 2026-03-20 19:59:31.827335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0bac86d4955'
down_revision: Union[str, None] = 'a001_add_status_envio'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar coluna tipo_conteudo (enum: 'pdf', 'html')
    op.execute("CREATE TYPE tipo_conteudo_documento AS ENUM ('pdf', 'html')")
    op.add_column('documentos_empresa',
        sa.Column('tipo_conteudo', sa.Enum('pdf', 'html', name='tipo_conteudo_documento'), nullable=False, server_default='pdf')
    )
    # Adicionar coluna conteudo_html (TEXT, nullable)
    op.add_column('documentos_empresa',
        sa.Column('conteudo_html', sa.Text(), nullable=True)
    )
    # Adicionar coluna variaveis_suportadas (JSONB, nullable)
    op.add_column('documentos_empresa',
        sa.Column('variaveis_suportadas', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('documentos_empresa', 'variaveis_suportadas')
    op.drop_column('documentos_empresa', 'conteudo_html')
    op.drop_column('documentos_empresa', 'tipo_conteudo')
    op.execute("DROP TYPE tipo_conteudo_documento")
