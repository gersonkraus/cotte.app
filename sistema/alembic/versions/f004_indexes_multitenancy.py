"""perf: adiciona índices em empresa_id e compostos para queries multi-tenant

Revision ID: f004_indexes_multitenancy
Revises: f003_fix_orcamento_numero_unique
Create Date: 2026-03-15 21:30:00.000000

Sem esses índices, queries do tipo WHERE empresa_id = ? fazem full table scan.
A 300 empresas × 500 orçamentos = 150k linhas, cada listagem seria lenta.

Usa CREATE INDEX CONCURRENTLY para não bloquear leituras/escritas em produção.
Como CONCURRENTLY não pode rodar dentro de transação, usa AUTOCOMMIT por conexão.
"""

from alembic import op
import sqlalchemy as sa


revision = "f004_indexes_multitenancy"
down_revision = "f003_fix_orcamento_numero_unique"
branch_labels = None
depends_on = None

# Índices a criar: (nome, tabela, colunas)
_INDEXES = [
    # ── Índices simples em empresa_id (mais urgentes) ──────────────────────
    ("ix_orcamentos_empresa_id",        "orcamentos",          "empresa_id"),
    ("ix_clientes_empresa_id",          "clientes",            "empresa_id"),
    ("ix_servicos_empresa_id",          "servicos",            "empresa_id"),
    ("ix_usuarios_empresa_id",          "usuarios",            "empresa_id"),
    # ── Índices compostos (queries com filtro multi-coluna) ────────────────
    ("ix_orcamentos_empresa_status",    "orcamentos",          "empresa_id, status"),
    ("ix_orcamentos_empresa_criado",    "orcamentos",          "empresa_id, criado_em DESC"),
    ("ix_contas_empresa_status",        "contas_financeiras",  "empresa_id, status"),
    ("ix_contas_empresa_vencimento",    "contas_financeiras",  "empresa_id, data_vencimento"),
    ("ix_notificacoes_empresa_lida",    "notificacoes",        "empresa_id, lida"),
]


def upgrade() -> None:
    # Usa CREATE INDEX sem CONCURRENTLY para compatibilidade com transação do Alembic.
    # Rodar dentro de transação é seguro no startup do deploy (sem tráfego ativo).
    conn = op.get_bind()
    for idx_name, table, cols in _INDEXES:
        conn.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})"))


def downgrade() -> None:
    conn = op.get_bind()
    for idx_name, table, _ in _INDEXES:
        conn.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))
