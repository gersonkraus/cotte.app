"""fix_missing_commercial_leads_columns_again

Corrige problemas de integridade no banco de dados do módulo comercial.
Esta migration garante que todas as tabelas e colunas necessárias existam
corretamente para o funcionamento do CRM comercial.

Revision ID: f123456789ab
Revises: 5f2d3c4b1a9e
Create Date: 2026-03-20 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = 'f123456789ab'
down_revision: Union[str, None] = '5f2d3c4b1a9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Corrige tabelas e colunas do módulo comercial."""
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Verificar se as tabelas existem
    existing_tables = inspector.get_table_names()
    
    # ── Garantir que commercial_segments existe ──────────────────────────────
    if 'commercial_segments' not in existing_tables:
        op.create_table(
            'commercial_segments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(100), nullable=False),
            sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nome', name='uq_commercial_segments_nome')
        )
        op.create_index(op.f('ix_commercial_segments_id'), 'commercial_segments', ['id'], unique=False)
    
    # ── Garantir que commercial_lead_sources existe ───────────────────────────
    if 'commercial_lead_sources' not in existing_tables:
        op.create_table(
            'commercial_lead_sources',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(100), nullable=False),
            sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nome', name='uq_commercial_lead_sources_nome')
        )
        op.create_index(op.f('ix_commercial_lead_sources_id'), 'commercial_lead_sources', ['id'], unique=False)
    
    # ── Garantir que commercial_leads existe ─────────────────────────────────
    if 'commercial_leads' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('commercial_leads')]
        fks = [fk['name'] for fk in inspector.get_foreign_keys('commercial_leads')]
        
        # Adicionar coluna ativo se não existir
        if 'ativo' not in columns:
            op.add_column('commercial_leads', sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False))
        
        # Adicionar coluna segmento_id se não existir
        if 'segmento_id' not in columns:
            op.add_column('commercial_leads', sa.Column('segmento_id', sa.Integer(), nullable=True))
        
        # Adicionar coluna origem_lead_id se não existir
        if 'origem_lead_id' not in columns:
            op.add_column('commercial_leads', sa.Column('origem_lead_id', sa.Integer(), nullable=True))
        
        # Adicionar coluna lead_score se não existir
        if 'lead_score' not in columns:
            op.add_column('commercial_leads', sa.Column('lead_score', sa.String(20), server_default='FRIO', nullable=True))
        
        # Adicionar FK para segmento se não existir
        if 'fk_commercial_leads_segmento_id' not in fks:
            try:
                op.create_foreign_key(
                    'fk_commercial_leads_segmento_id',
                    'commercial_leads', 'commercial_segments',
                    ['segmento_id'], ['id']
                )
            except Exception:
                pass  # FK pode já existir com nome diferente
        
        # Adicionar FK para origem se não existir
        if 'fk_commercial_leads_origem_lead_id' not in fks:
            try:
                op.create_foreign_key(
                    'fk_commercial_leads_origem_lead_id',
                    'commercial_leads', 'commercial_lead_sources',
                    ['origem_lead_id'], ['id']
                )
            except Exception:
                pass  # FK pode já existir com nome diferente
    
    # ── Garantir que commercial_templates existe ─────────────────────────────
    if 'commercial_templates' not in existing_tables:
        op.create_table(
            'commercial_templates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(150), nullable=False),
            sa.Column('tipo', sa.String(50), nullable=False),
            sa.Column('canal', sa.String(20), nullable=False),
            sa.Column('assunto', sa.String(200), nullable=True),
            sa.Column('conteudo', sa.Text(), nullable=False),
            sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_commercial_templates_id'), 'commercial_templates', ['id'], unique=False)
    
    # ── Garantir que commercial_reminders existe ────────────────────────────
    if 'commercial_reminders' not in existing_tables:
        op.create_table(
            'commercial_reminders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('lead_id', sa.Integer(), nullable=False),
            sa.Column('titulo', sa.String(200), nullable=False),
            sa.Column('descricao', sa.Text(), nullable=True),
            sa.Column('data_hora', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.String(20), server_default='PENDENTE', nullable=False),
            sa.Column('canal_sugerido', sa.String(20), nullable=True),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('concluido_em', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['lead_id'], ['commercial_leads.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_commercial_reminders_id'), 'commercial_reminders', ['id'], unique=False)
        op.create_index(op.f('ix_commercial_reminders_lead_id'), 'commercial_reminders', ['lead_id'], unique=False)
    
    # ── Garantir que commercial_config existe ──────────────────────────────
    if 'commercial_config' not in existing_tables:
        op.create_table(
            'commercial_config',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('link_demo', sa.String(300), nullable=True),
            sa.Column('link_proposta', sa.String(300), nullable=True),
            sa.Column('assinatura_comercial', sa.Text(), nullable=True),
            sa.Column('canal_preferencial', sa.String(20), server_default='whatsapp', nullable=False),
            sa.Column('textos_auxiliares', sa.Text(), nullable=True),
            sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_commercial_config_id'), 'commercial_config', ['id'], unique=False)
        
        # Criar registro padrão
        op.execute("INSERT INTO commercial_config (id, canal_preferencial) VALUES (1, 'whatsapp') ON CONFLICT DO NOTHING")
    
    # ── Garantir que commercial_interactions existe ─────────────────────────
    if 'commercial_interactions' not in existing_tables:
        op.create_table(
            'commercial_interactions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('lead_id', sa.Integer(), nullable=False),
            sa.Column('tipo', sa.String(30), nullable=False),
            sa.Column('canal', sa.String(20), nullable=True),
            sa.Column('conteudo', sa.Text(), nullable=True),
            sa.Column('status_envio', sa.String(20), server_default='enviado', nullable=False),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('enviado_em', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['lead_id'], ['commercial_leads.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_commercial_interactions_id'), 'commercial_interactions', ['id'], unique=False)
        op.create_index(op.f('ix_commercial_interactions_lead_id'), 'commercial_interactions', ['lead_id'], unique=False)


def downgrade() -> None:
    """Remove correções (não recomendado em produção)."""
    pass
