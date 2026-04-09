"""fix_commercial_leads_fk_columns

Revision ID: d60f6d62a957
Revises: 9e5c2d29991b
Create Date: 2026-03-14 13:01:42.600641

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'd60f6d62a957'
down_revision: Union[str, None] = '9e5c2d29991b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to commercial_leads only
    inspector = inspect(op.get_bind())
    
    if 'commercial_leads' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('commercial_leads')]
        fks = [fk['name'] for fk in inspector.get_foreign_keys('commercial_leads')]
        
        if 'ativo' not in columns:
            op.add_column('commercial_leads', sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False))

        if 'segmento_id' not in columns:
            op.add_column('commercial_leads', sa.Column('segmento_id', sa.Integer(), nullable=True))
            if 'fk_commercial_leads_segmento_id' not in fks:
                op.execute("""
                    ALTER TABLE commercial_leads 
                    ADD CONSTRAINT fk_commercial_leads_segmento_id 
                    FOREIGN KEY (segmento_id) REFERENCES commercial_segments(id)
                """)

        if 'origem_lead_id' not in columns:
            op.add_column('commercial_leads', sa.Column('origem_lead_id', sa.Integer(), nullable=True))
            if 'fk_commercial_leads_origem_lead_id' not in fks:
                op.execute("""
                    ALTER TABLE commercial_leads 
                    ADD CONSTRAINT fk_commercial_leads_origem_lead_id 
                    FOREIGN KEY (origem_lead_id) REFERENCES commercial_lead_sources(id)
                """)


def downgrade() -> None:
    pass
