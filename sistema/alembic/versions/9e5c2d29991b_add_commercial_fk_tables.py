"""add_commercial_fk_tables

Revision ID: 9e5c2d29991b
Revises: 5f2d3c4b1a9e
Create Date: 2026-03-14 12:55:14.513071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e5c2d29991b'
down_revision: Union[str, None] = '5f2d3c4b1a9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona colunas ativo, segmento_id e origem_lead_id ao commercial_leads.
    Tabelas commercial_segments e commercial_lead_sources já são criadas
    pela migration 003_add_comercial_extended_tables.
    
    Esta migration foi corrigida para não recriar tabelas já existentes.
    """
    from sqlalchemy import inspect
    
    # Verificar e adicionar coluna 'ativo' se não existir
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('commercial_leads')]
    
    if 'ativo' not in columns:
        op.add_column('commercial_leads', sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False))
    
    if 'segmento_id' not in columns:
        op.add_column('commercial_leads', sa.Column('segmento_id', sa.Integer(), nullable=True))
    
    if 'origem_lead_id' not in columns:
        op.add_column('commercial_leads', sa.Column('origem_lead_id', sa.Integer(), nullable=True))
    
    # Criar foreign keys apenas se não existirem
    fks = inspector.get_foreign_keys('commercial_leads')
    existing_fk_names = [fk['name'] for fk in fks]
    
    if 'fk_commercial_leads_segmento_id' not in existing_fk_names:
        op.create_foreign_key(
            'fk_commercial_leads_segmento_id',
            'commercial_leads', 'commercial_segments',
            ['segmento_id'], ['id']
        )
    
    if 'fk_commercial_leads_origem_lead_id' not in existing_fk_names:
        op.create_foreign_key(
            'fk_commercial_leads_origem_lead_id',
            'commercial_leads', 'commercial_lead_sources',
            ['origem_lead_id'], ['id']
        )


def downgrade() -> None:
    """Remove as colunas adicionadas (tabelas não são dropadas pois pertencem a outra migration)."""
    # Drop foreign keys
    op.drop_constraint('fk_commercial_leads_origem_lead_id', 'commercial_leads', type_='foreignkey')
    op.drop_constraint('fk_commercial_leads_segmento_id', 'commercial_leads', type_='foreignkey')

    # Drop columns
    op.drop_column('commercial_leads', 'origem_lead_id')
    op.drop_column('commercial_leads', 'segmento_id')
    op.drop_column('commercial_leads', 'ativo')
