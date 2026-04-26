"""Garante módulo comercial (tenant) e vínculo em planos pagos.

Revision ID: tc003_add_modulo_comercial
Revises: tc002_add_tenant_comercial_tables
Create Date: 2026-04-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tc003_add_modulo_comercial"
down_revision: Union[str, None] = "tc002_add_tenant_comercial_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    r = bind.execute(
        sa.text("SELECT id FROM modulos_sistema WHERE slug = :s"),
        {"s": "comercial"},
    ).first()
    if r is None:
        bind.execute(
            sa.text(
                """
            INSERT INTO modulos_sistema (nome, slug, descricao, acoes, ativo)
            VALUES (
                'Comercial',
                'comercial',
                'CRM de leads, pipeline e propostas (tenant)',
                '["leitura", "escrita", "exclusao", "admin"]'::json,
                true
            )
            """
            )
        )
        r = bind.execute(
            sa.text("SELECT id FROM modulos_sistema WHERE slug = :s"),
            {"s": "comercial"},
        ).first()
    mod_id = r[0]

    for plano in ("starter", "pro", "business"):
        pr = bind.execute(
            sa.text("SELECT id FROM planos WHERE lower(nome) = lower(:n)"),
            {"n": plano},
        ).first()
        if pr is None:
            continue
        pid = pr[0]
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM plano_modulos WHERE plano_id = :p AND modulo_id = :m"
            ),
            {"p": pid, "m": mod_id},
        ).first()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO plano_modulos (plano_id, modulo_id) VALUES (:p, :m)"
                ),
                {"p": pid, "m": mod_id},
            )


def downgrade() -> None:
    bind = op.get_bind()
    r = bind.execute(
        sa.text("SELECT id FROM modulos_sistema WHERE slug = :s"),
        {"s": "comercial"},
    ).first()
    if r is None:
        return
    mod_id = r[0]
    bind.execute(
        sa.text("DELETE FROM plano_modulos WHERE modulo_id = :m"),
        {"m": mod_id},
    )
    # Não remove a linha em modulos_sistema (pode ser referenciada em código)
