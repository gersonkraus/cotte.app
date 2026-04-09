"""add_agendamentos_module

Revision ID: 407429405c03
Revises: s002_superadmin_empresa_nullable
Create Date: 2026-03-25 20:29:26.489516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '407429405c03'
down_revision: Union[str, None] = 's002_superadmin_empresa_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Tabelas independentes primeiro ──

    op.create_table('config_agendamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('horario_inicio', sa.String(length=5), nullable=True),
        sa.Column('horario_fim', sa.String(length=5), nullable=True),
        sa.Column('dias_trabalho', sa.JSON(), nullable=True),
        sa.Column('duracao_padrao_min', sa.Integer(), nullable=True),
        sa.Column('intervalo_minimo_min', sa.Integer(), nullable=True),
        sa.Column('antecedencia_minima_horas', sa.Integer(), nullable=True),
        sa.Column('permite_agendamento_cliente', sa.Boolean(), nullable=True),
        sa.Column('requer_confirmacao', sa.Boolean(), nullable=True),
        sa.Column('lembrete_antecedencia_horas', sa.JSON(), nullable=True),
        sa.Column('mensagem_confirmacao', sa.Text(), nullable=True),
        sa.Column('mensagem_lembrete', sa.Text(), nullable=True),
        sa.Column('mensagem_reagendamento', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_config_agendamento_empresa_id'), 'config_agendamento', ['empresa_id'], unique=True)
    op.create_index(op.f('ix_config_agendamento_id'), 'config_agendamento', ['id'], unique=False)

    op.create_table('config_agendamento_usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('horario_inicio', sa.String(length=5), nullable=True),
        sa.Column('horario_fim', sa.String(length=5), nullable=True),
        sa.Column('dias_trabalho', sa.JSON(), nullable=True),
        sa.Column('duracao_padrao_min', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'usuario_id', name='uq_config_agd_empresa_usuario'),
    )
    op.create_index(op.f('ix_config_agendamento_usuario_empresa_id'), 'config_agendamento_usuario', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_config_agendamento_usuario_id'), 'config_agendamento_usuario', ['id'], unique=False)
    op.create_index(op.f('ix_config_agendamento_usuario_usuario_id'), 'config_agendamento_usuario', ['usuario_id'], unique=True)

    op.create_table('slots_bloqueados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('data_inicio', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_fim', sa.DateTime(timezone=True), nullable=False),
        sa.Column('motivo', sa.String(length=300), nullable=True),
        sa.Column('recorrente', sa.Boolean(), nullable=True),
        sa.Column('recorrencia_tipo', sa.String(length=20), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_slots_bloqueados_empresa_id'), 'slots_bloqueados', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_slots_bloqueados_id'), 'slots_bloqueados', ['id'], unique=False)
    op.create_index(op.f('ix_slots_bloqueados_usuario_id'), 'slots_bloqueados', ['usuario_id'], unique=False)

    # ── 2. Tabela agendamentos — sem FK circular para orcamentos ainda ──

    op.create_table('agendamentos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('orcamento_id', sa.Integer(), nullable=True),  # FK adicionada depois
        sa.Column('criado_por_id', sa.Integer(), nullable=False),
        sa.Column('responsavel_id', sa.Integer(), nullable=True),
        sa.Column('numero', sa.String(length=20), nullable=True),
        sa.Column('status', sa.Enum('PENDENTE', 'CONFIRMADO', 'EM_ANDAMENTO', 'CONCLUIDO', 'REAGENDADO', 'CANCELADO', 'NAO_COMPARECEU', name='statusagendamento'), nullable=True),
        sa.Column('tipo', sa.Enum('ENTREGA', 'SERVICO', 'INSTALACAO', 'MANUTENCAO', 'VISITA_TECNICA', 'OUTRO', name='tipoagendamento'), nullable=True),
        sa.Column('origem', sa.Enum('MANUAL', 'WHATSAPP', 'ASSISTENTE_IA', 'AUTOMATICO', name='origemagendamento'), nullable=True),
        sa.Column('data_agendada', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_fim', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duracao_estimada_min', sa.Integer(), nullable=True),
        sa.Column('endereco', sa.Text(), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('motivo_cancelamento', sa.Text(), nullable=True),
        sa.Column('confirmado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('concluido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reagendamento_anterior_id', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.ForeignKeyConstraint(['criado_por_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['reagendamento_anterior_id'], ['agendamentos.id']),
        sa.ForeignKeyConstraint(['responsavel_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'numero', name='uq_agendamentos_empresa_numero'),
    )
    op.create_index(op.f('ix_agendamentos_cliente_id'), 'agendamentos', ['cliente_id'], unique=False)
    op.create_index(op.f('ix_agendamentos_empresa_id'), 'agendamentos', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_agendamentos_id'), 'agendamentos', ['id'], unique=False)
    op.create_index(op.f('ix_agendamentos_numero'), 'agendamentos', ['numero'], unique=False)
    op.create_index(op.f('ix_agendamentos_orcamento_id'), 'agendamentos', ['orcamento_id'], unique=False)
    op.create_index(op.f('ix_agendamentos_responsavel_id'), 'agendamentos', ['responsavel_id'], unique=False)

    # ── 3. FKs cruzadas (resolve ciclo) ──

    op.create_foreign_key('fk_agendamentos_orcamento_id', 'agendamentos', 'orcamentos', ['orcamento_id'], ['id'])

    op.add_column('orcamentos', sa.Column('agendamento_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_orcamentos_agendamento_id'), 'orcamentos', ['agendamento_id'], unique=False)
    op.create_foreign_key('fk_orcamentos_agendamento_id', 'orcamentos', 'agendamentos', ['agendamento_id'], ['id'])

    # ── 4. Histórico ──

    op.create_table('historico_agendamentos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agendamento_id', sa.Integer(), nullable=False),
        sa.Column('status_anterior', sa.String(length=30), nullable=True),
        sa.Column('status_novo', sa.String(length=30), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('editado_por_id', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agendamento_id'], ['agendamentos.id']),
        sa.ForeignKeyConstraint(['editado_por_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_historico_agendamentos_agendamento_id'), 'historico_agendamentos', ['agendamento_id'], unique=False)
    op.create_index(op.f('ix_historico_agendamentos_id'), 'historico_agendamentos', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('historico_agendamentos')
    op.drop_constraint('fk_orcamentos_agendamento_id', 'orcamentos', type_='foreignkey')
    op.drop_index(op.f('ix_orcamentos_agendamento_id'), table_name='orcamentos')
    op.drop_column('orcamentos', 'agendamento_id')
    op.drop_constraint('fk_agendamentos_orcamento_id', 'agendamentos', type_='foreignkey')
    op.drop_table('agendamentos')
    op.drop_table('slots_bloqueados')
    op.drop_table('config_agendamento_usuario')
    op.drop_table('config_agendamento')
