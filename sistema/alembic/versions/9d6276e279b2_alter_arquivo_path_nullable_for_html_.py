"""alter_arquivo_path_nullable_for_html_documents

Revision ID: 9d6276e279b2
Revises: k001_pipeline_stages
Create Date: 2026-03-20 20:38:00.021675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d6276e279b2'
down_revision: Union[str, None] = 'k001_pipeline_stages'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alterar coluna arquivo_path para nullable (permitir NULL para documentos HTML)
    op.alter_column('documentos_empresa', 'arquivo_path',
                    existing_type=sa.String(length=500),
                    nullable=True)


def downgrade() -> None:
    # Reverter para NOT NULL (mas primeiro precisamos garantir que não há NULLs)
    # Para documentos HTML, definir um valor padrão
    op.execute("""
        UPDATE documentos_empresa 
        SET arquivo_path = 'html-content-' || id::text || '.html'
        WHERE arquivo_path IS NULL AND tipo_conteudo = 'html'
    """)
    
    # Para qualquer outro NULL, definir um valor padrão
    op.execute("""
        UPDATE documentos_empresa 
        SET arquivo_path = 'placeholder-' || id::text || '.pdf'
        WHERE arquivo_path IS NULL
    """)
    
    # Agora podemos alterar para NOT NULL
    op.alter_column('documentos_empresa', 'arquivo_path',
                    existing_type=sa.String(length=500),
                    nullable=False)
