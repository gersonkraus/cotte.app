"""Criar tabelas ai_chat_sessoes e ai_chat_mensagens para persistência de sessões de IA.

Revision ID: z021_ai_chat_sessoes
Revises: z020_merge_all_heads
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "z021_ai_chat_sessoes"
down_revision = "z020_merge_all_heads"
branch_labels = None
depends_on = None


def upgrade():
    # Tabelas podem já existir (criadas via SQLAlchemy antes das migrations).
    # Usamos EXECUTE para criar apenas se não existirem.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_chat_sessoes (
            id VARCHAR(64) PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            criado_em TIMESTAMPTZ DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS ix_ai_chat_sessoes_empresa_id ON ai_chat_sessoes(empresa_id);
        CREATE INDEX IF NOT EXISTS ix_ai_chat_sessoes_usuario_id ON ai_chat_sessoes(usuario_id);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_chat_mensagens (
            id SERIAL PRIMARY KEY,
            sessao_id VARCHAR(64) NOT NULL REFERENCES ai_chat_sessoes(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            criado_em TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_ai_chat_mensagens_sessao_id ON ai_chat_mensagens(sessao_id);
        CREATE INDEX IF NOT EXISTS ix_ai_chat_mensagens_criado_em ON ai_chat_mensagens(criado_em);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS ai_chat_mensagens")
    op.execute("DROP TABLE IF EXISTS ai_chat_sessoes")
