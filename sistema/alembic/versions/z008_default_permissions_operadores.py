"""Popula permissoes padrão para operadores que não têm as chaves básicas.

Garante que todo usuário não-gestor e não-superadmin tenha ao menos:
  orcamentos, clientes, catalogo, relatorios, documentos, ia

Não sobrescreve permissões que já existem — apenas adiciona as faltantes.

Revision ID: z008_default_perms
Revises: z007_merge_z006_and_p003
Create Date: 2026-03-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "z008_default_perms"
down_revision: Union[str, Sequence[str], None] = "z007_merge_z006_and_p003"
branch_labels = None
depends_on = None

# Permissões padrão para operadores
_DEFAULTS = {
    "orcamentos": "escrita",
    "clientes":   "escrita",
    "catalogo":   "leitura",
    "relatorios": "leitura",
    "documentos": "leitura",
    "ia":         "leitura",
}


def upgrade() -> None:
    conn = op.get_bind()
    # Para cada chave padrão, adiciona ao JSON apenas se a chave não existir
    for recurso, nivel in _DEFAULTS.items():
        conn.execute(
            sa.text(
                f"""
                UPDATE usuarios
                SET permissoes = COALESCE(permissoes, '{{}}'::jsonb)
                              || jsonb_build_object('{recurso}', '{nivel}')
                WHERE is_gestor = FALSE
                  AND is_superadmin = FALSE
                  AND NOT (COALESCE(permissoes, '{{}}'::jsonb) ? '{recurso}')
                """
            )
        )


def downgrade() -> None:
    # Não há rollback seguro para remoção de chaves em JSON sem saber quais eram novas
    pass
