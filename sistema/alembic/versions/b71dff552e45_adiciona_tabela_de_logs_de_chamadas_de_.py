"""Adiciona tabela de logs de chamadas de tools para telemetria

Revision ID: b71dff552e45
Revises: z023_agendamento_opcao_escolhida
Create Date: 2026-04-20 15:42:55.246248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'b71dff552e45'
down_revision: Union[str, None] = 'z023_agendamento_opcao_escolhida'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_table(table_name: str) -> bool:
        return table_name in set(inspector.get_table_names())

    def has_index(table_name: str, index_name: str) -> bool:
        if not has_table(table_name):
            return False
        return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table_name)}

    def has_column(table_name: str, column_name: str) -> bool:
        if not has_table(table_name):
            return False
        return column_name in {col["name"] for col in inspect(bind).get_columns(table_name)}

    def has_fk(table_name: str, constraint_name: str) -> bool:
        if not has_table(table_name):
            return False
        return constraint_name in {fk["name"] for fk in inspect(bind).get_foreign_keys(table_name) if fk.get("name")}

    def has_fk_columns(table_name: str, constrained_cols: list[str], referred_table: str) -> bool:
        if not has_table(table_name):
            return False
        for fk in inspect(bind).get_foreign_keys(table_name):
            if fk.get("constrained_columns") == constrained_cols and fk.get("referred_table") == referred_table:
                return True
        return False

    if not has_table('tool_call_logs'):
        op.create_table('tool_call_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('sessao_id', sa.String(), nullable=True),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('tool_args', sa.JSON(), nullable=True),
        sa.Column('user_input', sa.String(), nullable=True),
        sa.Column('execution_status', sa.String(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    if has_column('tool_call_logs', 'empresa_id') and not has_index('tool_call_logs', op.f('ix_tool_call_logs_empresa_id')):
        op.create_index(op.f('ix_tool_call_logs_empresa_id'), 'tool_call_logs', ['empresa_id'], unique=False)
    if has_column('tool_call_logs', 'id') and not has_index('tool_call_logs', op.f('ix_tool_call_logs_id')):
        op.create_index(op.f('ix_tool_call_logs_id'), 'tool_call_logs', ['id'], unique=False)
    if has_column('tool_call_logs', 'sessao_id') and not has_index('tool_call_logs', op.f('ix_tool_call_logs_sessao_id')):
        op.create_index(op.f('ix_tool_call_logs_sessao_id'), 'tool_call_logs', ['sessao_id'], unique=False)
    if has_column('tool_call_logs', 'tool_name') and not has_index('tool_call_logs', op.f('ix_tool_call_logs_tool_name')):
        op.create_index(op.f('ix_tool_call_logs_tool_name'), 'tool_call_logs', ['tool_name'], unique=False)
    if has_column('tool_call_logs', 'user_id') and not has_index('tool_call_logs', op.f('ix_tool_call_logs_user_id')):
        op.create_index(op.f('ix_tool_call_logs_user_id'), 'tool_call_logs', ['user_id'], unique=False)
    op.alter_column('assistente_preferencias_usuario', 'modulos_ativos',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=sa.JSON(),
               existing_nullable=False,
               existing_server_default=sa.text('\'{"catalogo": true, "clientes": true, "financeiro": true, "orcamentos": true}\'::jsonb'))
    op.alter_column('assistente_prompts_empresa', 'criado_em',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    if has_table('assistente_prompts_empresa') and has_index('assistente_prompts_empresa', 'ix_assistente_prompts_empresa_categoria_only'):
        op.drop_index('ix_assistente_prompts_empresa_categoria_only', table_name='assistente_prompts_empresa')
    if has_table('assistente_prompts_empresa') and not has_index('assistente_prompts_empresa', op.f('ix_assistente_prompts_empresa_id')):
        op.create_index(op.f('ix_assistente_prompts_empresa_id'), 'assistente_prompts_empresa', ['id'], unique=False)
    if has_fk('assistente_prompts_empresa', 'assistente_prompts_empresa_atualizado_por_id_fkey'):
        op.drop_constraint('assistente_prompts_empresa_atualizado_por_id_fkey', 'assistente_prompts_empresa', type_='foreignkey')
    if has_fk('assistente_prompts_empresa', 'assistente_prompts_empresa_empresa_id_fkey'):
        op.drop_constraint('assistente_prompts_empresa_empresa_id_fkey', 'assistente_prompts_empresa', type_='foreignkey')
    if has_fk('assistente_prompts_empresa', 'assistente_prompts_empresa_criado_por_id_fkey'):
        op.drop_constraint('assistente_prompts_empresa_criado_por_id_fkey', 'assistente_prompts_empresa', type_='foreignkey')
    if has_table('assistente_prompts_empresa') and not has_fk_columns('assistente_prompts_empresa', ['criado_por_id'], 'usuarios'):
        op.create_foreign_key(None, 'assistente_prompts_empresa', 'usuarios', ['criado_por_id'], ['id'])
    if has_table('assistente_prompts_empresa') and not has_fk_columns('assistente_prompts_empresa', ['atualizado_por_id'], 'usuarios'):
        op.create_foreign_key(None, 'assistente_prompts_empresa', 'usuarios', ['atualizado_por_id'], ['id'])
    if has_table('assistente_prompts_empresa') and not has_fk_columns('assistente_prompts_empresa', ['empresa_id'], 'empresas'):
        op.create_foreign_key(None, 'assistente_prompts_empresa', 'empresas', ['empresa_id'], ['id'])
    if has_table('schema_drift_snapshots') and not has_index('schema_drift_snapshots', op.f('ix_schema_drift_snapshots_id')):
        op.create_index(op.f('ix_schema_drift_snapshots_id'), 'schema_drift_snapshots', ['id'], unique=False)
    if has_table('tool_call_log') and not has_index('tool_call_log', op.f('ix_tool_call_log_id')):
        op.create_index(op.f('ix_tool_call_log_id'), 'tool_call_log', ['id'], unique=False)
    if has_table('usuarios') and has_index('usuarios', 'ix_usuario_telefone_operador'):
        op.drop_index('ix_usuario_telefone_operador', table_name='usuarios')
    if has_table('usuarios') and not has_index('usuarios', op.f('ix_usuarios_telefone_operador')):
        op.create_index(op.f('ix_usuarios_telefone_operador'), 'usuarios', ['telefone_operador'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_usuarios_telefone_operador'), table_name='usuarios')
    op.create_index('ix_usuario_telefone_operador', 'usuarios', ['telefone_operador'], unique=False)
    op.drop_index(op.f('ix_tool_call_log_id'), table_name='tool_call_log')
    op.drop_index(op.f('ix_schema_drift_snapshots_id'), table_name='schema_drift_snapshots')
    op.drop_constraint(None, 'assistente_prompts_empresa', type_='foreignkey')
    op.drop_constraint(None, 'assistente_prompts_empresa', type_='foreignkey')
    op.drop_constraint(None, 'assistente_prompts_empresa', type_='foreignkey')
    op.create_foreign_key('assistente_prompts_empresa_criado_por_id_fkey', 'assistente_prompts_empresa', 'usuarios', ['criado_por_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('assistente_prompts_empresa_empresa_id_fkey', 'assistente_prompts_empresa', 'empresas', ['empresa_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('assistente_prompts_empresa_atualizado_por_id_fkey', 'assistente_prompts_empresa', 'usuarios', ['atualizado_por_id'], ['id'], ondelete='SET NULL')
    op.drop_index(op.f('ix_assistente_prompts_empresa_id'), table_name='assistente_prompts_empresa')
    op.create_index('ix_assistente_prompts_empresa_categoria_only', 'assistente_prompts_empresa', ['categoria'], unique=False)
    op.alter_column('assistente_prompts_empresa', 'criado_em',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('assistente_preferencias_usuario', 'modulos_ativos',
               existing_type=sa.JSON(),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=False,
               existing_server_default=sa.text('\'{"catalogo": true, "clientes": true, "financeiro": true, "orcamentos": true}\'::jsonb'))
    op.drop_index(op.f('ix_tool_call_logs_user_id'), table_name='tool_call_logs')
    op.drop_index(op.f('ix_tool_call_logs_tool_name'), table_name='tool_call_logs')
    op.drop_index(op.f('ix_tool_call_logs_sessao_id'), table_name='tool_call_logs')
    op.drop_index(op.f('ix_tool_call_logs_id'), table_name='tool_call_logs')
    op.drop_index(op.f('ix_tool_call_logs_empresa_id'), table_name='tool_call_logs')
    op.drop_table('tool_call_logs')
    # ### end Alembic commands ###
