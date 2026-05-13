"""tenant_commercial_leads: whatsapp_conversa_vista_em + backfill

Revision ID: tc011_whatsapp_conversa_vista_tenant_leads
Revises: tc010_add_direcao_message_id_to_interactions, z035_backfill_notas_fiscais_criado_em
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tc011_whatsapp_conversa_vista_tenant_leads"
down_revision: Union[str, Sequence[str], None] = (
    "tc010_add_direcao_message_id_to_interactions",
    "z035_backfill_notas_fiscais_criado_em",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("tenant_commercial_leads"):
        return

    cols = {c["name"] for c in insp.get_columns("tenant_commercial_leads")}
    if "whatsapp_conversa_vista_em" not in cols:
        op.add_column(
            "tenant_commercial_leads",
            sa.Column("whatsapp_conversa_vista_em", sa.DateTime(timezone=True), nullable=True),
        )

    # Backfill: marca como "visto" até a última resposta WhatsApp já existente (sem badge retroativo)
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE tenant_commercial_leads AS l
                SET whatsapp_conversa_vista_em = sub.mx
                FROM (
                    SELECT lead_id, MAX(criado_em) AS mx
                    FROM tenant_commercial_interactions
                    WHERE direcao = 'recebido'
                      AND tipo::text IN ('WHATSAPP', 'whatsapp')
                    GROUP BY lead_id
                ) AS sub
                WHERE l.id = sub.lead_id
                """
            )
        )
    else:
        op.execute(
            sa.text(
                """
                UPDATE tenant_commercial_leads
                SET whatsapp_conversa_vista_em = (
                    SELECT MAX(i.criado_em)
                    FROM tenant_commercial_interactions AS i
                    WHERE i.lead_id = tenant_commercial_leads.id
                      AND i.direcao = 'recebido'
                      AND CAST(i.tipo AS TEXT) IN ('WHATSAPP', 'whatsapp')
                )
                WHERE EXISTS (
                    SELECT 1
                    FROM tenant_commercial_interactions AS i2
                    WHERE i2.lead_id = tenant_commercial_leads.id
                      AND i2.direcao = 'recebido'
                      AND CAST(i2.tipo AS TEXT) IN ('WHATSAPP', 'whatsapp')
                )
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("tenant_commercial_leads"):
        return
    cols = {c["name"] for c in insp.get_columns("tenant_commercial_leads")}
    if "whatsapp_conversa_vista_em" in cols:
        op.drop_column("tenant_commercial_leads", "whatsapp_conversa_vista_em")
