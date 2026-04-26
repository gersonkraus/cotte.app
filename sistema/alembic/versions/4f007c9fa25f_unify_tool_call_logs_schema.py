"""unify_tool_call_logs_schema

Revision ID: 4f007c9fa25f
Revises: b71dff552e45
Create Date: 2026-04-20 16:58:36.625061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '4f007c9fa25f'
down_revision: Union[str, None] = 'b71dff552e45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_table(table_name: str) -> bool:
        return table_name in set(inspector.get_table_names())

    def has_column(table_name: str, column_name: str) -> bool:
        if not has_table(table_name):
            return False
        return column_name in {col["name"] for col in inspect(bind).get_columns(table_name)}

    def has_index(table_name: str, index_name: str) -> bool:
        if not has_table(table_name):
            return False
        return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table_name)}

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

    for index_name in (
        "ix_tool_call_log_criado_em",
        "ix_tool_call_log_empresa_id",
        "ix_tool_call_log_id",
        "ix_tool_call_log_sessao_id",
        "ix_tool_call_log_status",
        "ix_tool_call_log_tool",
        "ix_tool_call_log_usuario_id",
    ):
        if has_index("tool_call_log", index_name):
            op.drop_index(index_name, table_name="tool_call_log")
    if has_table("tool_call_log"):
        op.drop_table("tool_call_log")

    if not has_column("tool_call_logs", "usuario_id"):
        op.add_column("tool_call_logs", sa.Column("usuario_id", sa.Integer(), nullable=True))
    if not has_column("tool_call_logs", "tool"):
        op.add_column("tool_call_logs", sa.Column("tool", sa.String(length=100), nullable=True))
        if has_column("tool_call_logs", "tool_name"):
            op.execute(sa.text("UPDATE tool_call_logs SET tool = tool_name WHERE tool IS NULL"))
        op.execute(sa.text("UPDATE tool_call_logs SET tool = 'unknown' WHERE tool IS NULL"))
        op.alter_column("tool_call_logs", "tool", nullable=False)
    if not has_column("tool_call_logs", "args_json"):
        op.add_column("tool_call_logs", sa.Column("args_json", sa.JSON(), nullable=True))
        if has_column("tool_call_logs", "tool_args"):
            op.execute(sa.text("UPDATE tool_call_logs SET args_json = tool_args WHERE args_json IS NULL"))
    if not has_column("tool_call_logs", "resultado_json"):
        op.add_column("tool_call_logs", sa.Column("resultado_json", sa.JSON(), nullable=True))
    if not has_column("tool_call_logs", "status"):
        op.add_column("tool_call_logs", sa.Column("status", sa.String(length=20), nullable=True))
        if has_column("tool_call_logs", "execution_status"):
            op.execute(sa.text("UPDATE tool_call_logs SET status = execution_status WHERE status IS NULL"))
        op.execute(sa.text("UPDATE tool_call_logs SET status = 'ok' WHERE status IS NULL"))
        op.alter_column("tool_call_logs", "status", nullable=False)
    if not has_column("tool_call_logs", "latencia_ms"):
        op.add_column("tool_call_logs", sa.Column("latencia_ms", sa.Integer(), nullable=True))
    if not has_column("tool_call_logs", "input_tokens"):
        op.add_column("tool_call_logs", sa.Column("input_tokens", sa.Integer(), nullable=True))
    if not has_column("tool_call_logs", "output_tokens"):
        op.add_column("tool_call_logs", sa.Column("output_tokens", sa.Integer(), nullable=True))
    if not has_column("tool_call_logs", "criado_em"):
        op.add_column("tool_call_logs", sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))
        if has_column("tool_call_logs", "created_at"):
            op.execute(sa.text("UPDATE tool_call_logs SET criado_em = created_at WHERE criado_em IS NULL"))
        op.alter_column("tool_call_logs", "criado_em", nullable=False)

    if has_index("tool_call_logs", "ix_tool_call_logs_tool_name"):
        op.drop_index("ix_tool_call_logs_tool_name", table_name="tool_call_logs")
    if has_index("tool_call_logs", "ix_tool_call_logs_user_id"):
        op.drop_index("ix_tool_call_logs_user_id", table_name="tool_call_logs")
    if has_column("tool_call_logs", "criado_em") and not has_index("tool_call_logs", op.f("ix_tool_call_logs_criado_em")):
        op.create_index(op.f("ix_tool_call_logs_criado_em"), "tool_call_logs", ["criado_em"], unique=False)
    if has_column("tool_call_logs", "status") and not has_index("tool_call_logs", op.f("ix_tool_call_logs_status")):
        op.create_index(op.f("ix_tool_call_logs_status"), "tool_call_logs", ["status"], unique=False)
    if has_column("tool_call_logs", "tool") and not has_index("tool_call_logs", op.f("ix_tool_call_logs_tool")):
        op.create_index(op.f("ix_tool_call_logs_tool"), "tool_call_logs", ["tool"], unique=False)
    if has_column("tool_call_logs", "usuario_id") and not has_index("tool_call_logs", op.f("ix_tool_call_logs_usuario_id")):
        op.create_index(op.f("ix_tool_call_logs_usuario_id"), "tool_call_logs", ["usuario_id"], unique=False)
    if has_fk("tool_call_logs", "tool_call_logs_user_id_fkey"):
        op.drop_constraint("tool_call_logs_user_id_fkey", "tool_call_logs", type_="foreignkey")
    if has_table("usuarios") and has_column("tool_call_logs", "usuario_id") and not has_fk_columns("tool_call_logs", ["usuario_id"], "usuarios"):
        op.create_foreign_key(None, "tool_call_logs", "usuarios", ["usuario_id"], ["id"])

    for column_name in ("execution_status", "tool_name", "tool_args", "user_id", "created_at", "error_message"):
        if has_column("tool_call_logs", column_name):
            op.drop_column("tool_call_logs", column_name)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tool_call_logs', sa.Column('error_message', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('tool_call_logs', sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('tool_call_logs', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('tool_call_logs', sa.Column('tool_args', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('tool_call_logs', sa.Column('tool_name', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('tool_call_logs', sa.Column('execution_status', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'tool_call_logs', type_='foreignkey')
    op.create_foreign_key('tool_call_logs_user_id_fkey', 'tool_call_logs', 'usuarios', ['user_id'], ['id'])
    op.drop_index(op.f('ix_tool_call_logs_usuario_id'), table_name='tool_call_logs')
    op.drop_index(op.f('ix_tool_call_logs_tool'), table_name='tool_call_logs')
    op.drop_index(op.f('ix_tool_call_logs_status'), table_name='tool_call_logs')
    op.drop_index(op.f('ix_tool_call_logs_criado_em'), table_name='tool_call_logs')
    op.create_index('ix_tool_call_logs_user_id', 'tool_call_logs', ['user_id'], unique=False)
    op.create_index('ix_tool_call_logs_tool_name', 'tool_call_logs', ['tool_name'], unique=False)
    op.drop_column('tool_call_logs', 'criado_em')
    op.drop_column('tool_call_logs', 'output_tokens')
    op.drop_column('tool_call_logs', 'input_tokens')
    op.drop_column('tool_call_logs', 'latencia_ms')
    op.drop_column('tool_call_logs', 'status')
    op.drop_column('tool_call_logs', 'resultado_json')
    op.drop_column('tool_call_logs', 'args_json')
    op.drop_column('tool_call_logs', 'tool')
    op.drop_column('tool_call_logs', 'usuario_id')
    op.create_table('tool_call_log',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('usuario_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('sessao_id', sa.VARCHAR(length=64), autoincrement=False, nullable=True),
    sa.Column('tool', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('args_json', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('resultado_json', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('latencia_ms', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('input_tokens', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('output_tokens', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('criado_em', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name='tool_call_log_empresa_id_fkey'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name='tool_call_log_usuario_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='tool_call_log_pkey')
    )
    op.create_index('ix_tool_call_log_usuario_id', 'tool_call_log', ['usuario_id'], unique=False)
    op.create_index('ix_tool_call_log_tool', 'tool_call_log', ['tool'], unique=False)
    op.create_index('ix_tool_call_log_status', 'tool_call_log', ['status'], unique=False)
    op.create_index('ix_tool_call_log_sessao_id', 'tool_call_log', ['sessao_id'], unique=False)
    op.create_index('ix_tool_call_log_id', 'tool_call_log', ['id'], unique=False)
    op.create_index('ix_tool_call_log_empresa_id', 'tool_call_log', ['empresa_id'], unique=False)
    op.create_index('ix_tool_call_log_criado_em', 'tool_call_log', ['criado_em'], unique=False)
    # ### end Alembic commands ###
