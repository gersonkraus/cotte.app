"""Fase 1 e 2 - Melhorias Financeiro

Revision ID: j001
Revises: i002
Create Date: 2025-03-17 22:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'j001'
down_revision: Union[str, None] = 'i002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Adicionar campos de soft delete e cancelamento à ContaFinanceira ─────────
    op.add_column('contas_financeiras', sa.Column('excluido_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('contas_financeiras', sa.Column('excluido_por_id', sa.Integer(), nullable=True))
    op.add_column('contas_financeiras', sa.Column('motivo_exclusao', sa.String(length=500), nullable=True))
    op.add_column('contas_financeiras', sa.Column('cancelado_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('contas_financeiras', sa.Column('cancelado_por_id', sa.Integer(), nullable=True))
    op.add_column('contas_financeiras', sa.Column('motivo_cancelamento', sa.String(length=500), nullable=True))
    
    # Foreign keys para soft delete e cancelamento
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_conta_excluido_por'
            ) THEN
                ALTER TABLE contas_financeiras 
                ADD CONSTRAINT fk_conta_excluido_por 
                FOREIGN KEY (excluido_por_id) REFERENCES usuarios(id);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_conta_cancelado_por'
            ) THEN
                ALTER TABLE contas_financeiras 
                ADD CONSTRAINT fk_conta_cancelado_por 
                FOREIGN KEY (cancelado_por_id) REFERENCES usuarios(id);
            END IF;
        END $$;
    """)
    
    # Índices para otimizar queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_contas_financeiras_excluido_em ON contas_financeiras (excluido_em);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_contas_financeiras_cancelado_em ON contas_financeiras (cancelado_em);")
    
    # ── Criar tabela MovimentacaoCaixa (Sprint 2.1) ───────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_caixa (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            tipo VARCHAR(10) NOT NULL,
            valor NUMERIC(10, 2) NOT NULL,
            descricao VARCHAR(300) NOT NULL,
            categoria VARCHAR(100) DEFAULT 'geral',
            data DATE DEFAULT CURRENT_DATE NOT NULL,
            confirmado BOOLEAN DEFAULT true NOT NULL,
            comprovante_url VARCHAR(500),
            criado_por_id INTEGER REFERENCES usuarios(id),
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        );
    """)
    
    # Índices para MovimentacaoCaixa
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacoes_caixa_empresa_id ON movimentacoes_caixa (empresa_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacoes_caixa_data ON movimentacoes_caixa (data);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacoes_caixa_tipo ON movimentacoes_caixa (tipo);")
    
    # ── Criar tabela CategoriaFinanceira (Sprint 2.2) ─────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS categorias_financeiras (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            nome VARCHAR(100) NOT NULL,
            tipo VARCHAR(10) DEFAULT 'despesa' NOT NULL,
            cor VARCHAR(7) DEFAULT '#00e5a0',
            icone VARCHAR(10) DEFAULT '📁',
            ativo BOOLEAN DEFAULT true NOT NULL,
            ordem INTEGER DEFAULT 0 NOT NULL,
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        );
    """)
    
    # Índices para CategoriaFinanceira
    op.execute("CREATE INDEX IF NOT EXISTS ix_categorias_financeiras_empresa_id ON categorias_financeiras (empresa_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_categorias_financeiras_tipo ON categorias_financeiras (tipo);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_categorias_financeiras_ativo ON categorias_financeiras (ativo);")
    
    # ── Criar tabela SaldoCaixaConfig (Sprint 1.3) ────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS saldo_caixa_configs (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL UNIQUE REFERENCES empresas(id),
            saldo_inicial NUMERIC(10, 2) DEFAULT 0 NOT NULL,
            configurado_em TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            configurado_por_id INTEGER REFERENCES usuarios(id)
        );
    """)
    
    # Índice para SaldoCaixaConfig
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_saldo_caixa_configs_empresa_id ON saldo_caixa_configs (empresa_id);")


def downgrade() -> None:
    # ── Remover tabelas novas ───────────────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS saldo_caixa_configs;")
    op.execute("DROP TABLE IF EXISTS categorias_financeiras;")
    op.execute("DROP TABLE IF EXISTS movimentacoes_caixa;")
    
    # ── Remover colunas de soft delete da ContaFinanceira ───────────────────────
    op.drop_column('contas_financeiras', 'motivo_cancelamento')
    op.drop_column('contas_financeiras', 'cancelado_por_id')
    op.drop_column('contas_financeiras', 'cancelado_em')
    op.drop_column('contas_financeiras', 'motivo_exclusao')
    op.drop_column('contas_financeiras', 'excluido_por_id')
    op.drop_column('contas_financeiras', 'excluido_em')
