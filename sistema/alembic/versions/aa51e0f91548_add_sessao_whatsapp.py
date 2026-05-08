"""add_sessao_whatsapp

Revision ID: aa51e0f91548
Revises: tc008_add_anexo_to_tenant_templates
Create Date: 2026-05-07 19:41:20.106396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa51e0f91548'
down_revision: Union[str, None] = 'tc008_add_anexo_to_tenant_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cria o tipo enum se ainda não existir
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leadscore') THEN
                CREATE TYPE leadscore AS ENUM ('QUENTE', 'MORNO', 'FRIO');
            END IF;
        END $$
    """)

    # Normaliza valores existentes para maiúsculas antes do cast
    op.execute("""
        UPDATE tenant_commercial_leads
        SET lead_score = UPPER(lead_score)
        WHERE lead_score IS NOT NULL
    """)

    op.create_table('sessao_whatsapp',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('telefone', sa.String(length=20), nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=True),
    sa.Column('etapa', sa.String(length=50), nullable=False),
    sa.Column('contexto', sa.JSON(), nullable=False),
    sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessao_whatsapp_empresa_id'), 'sessao_whatsapp', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_sessao_whatsapp_id'), 'sessao_whatsapp', ['id'], unique=False)
    op.create_index(op.f('ix_sessao_whatsapp_telefone'), 'sessao_whatsapp', ['telefone'], unique=True)

    # Remove o default antes de alterar o tipo (PostgreSQL não converte default automaticamente)
    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score DROP DEFAULT")

    # USING necessário para PostgreSQL converter VARCHAR → enum
    op.execute("""
        ALTER TABLE tenant_commercial_leads
        ALTER COLUMN lead_score TYPE leadscore
        USING lead_score::leadscore
    """)

    # Restaura o default com o valor correto do enum
    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score SET DEFAULT 'FRIO'::leadscore")


def downgrade() -> None:
    op.execute("""
        ALTER TABLE tenant_commercial_leads
        ALTER COLUMN lead_score TYPE VARCHAR(6)
        USING lead_score::VARCHAR
    """)
    op.drop_index(op.f('ix_sessao_whatsapp_telefone'), table_name='sessao_whatsapp')
    op.drop_index(op.f('ix_sessao_whatsapp_id'), table_name='sessao_whatsapp')
    op.drop_index(op.f('ix_sessao_whatsapp_empresa_id'), table_name='sessao_whatsapp')
    op.drop_table('sessao_whatsapp')
    op.execute("DROP TYPE IF EXISTS leadscore")
