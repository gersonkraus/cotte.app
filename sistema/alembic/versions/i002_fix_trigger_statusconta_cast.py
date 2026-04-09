"""fix trigger: adiciona cast ::statusconta nas strings do CASE

Revision ID: i002
Revises: 25a618cb66f6
Create Date: 2026-03-17
"""
from alembic import op
from sqlalchemy import text

revision = 'i002'
down_revision = '25a618cb66f6'
branch_labels = None
depends_on = None


_CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION tg_fn_recalcular_valor_pago()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE contas_financeiras cf
    SET
        valor_pago = COALESCE((
            SELECT SUM(pf.valor)
            FROM pagamentos_financeiros pf
            WHERE pf.conta_id = cf.id
              AND pf.status = 'confirmado'
        ), 0),
        status = CASE
            WHEN COALESCE((
                SELECT SUM(pf.valor)
                FROM pagamentos_financeiros pf
                WHERE pf.conta_id = cf.id
                  AND pf.status = 'confirmado'
            ), 0) >= cf.valor THEN 'pago'::statusconta
            WHEN COALESCE((
                SELECT SUM(pf.valor)
                FROM pagamentos_financeiros pf
                WHERE pf.conta_id = cf.id
                  AND pf.status = 'confirmado'
            ), 0) > 0 THEN 'parcial'::statusconta
            WHEN cf.data_vencimento IS NOT NULL AND cf.data_vencimento < CURRENT_DATE THEN 'vencido'::statusconta
            ELSE 'pendente'::statusconta
        END
    WHERE cf.id = COALESCE(NEW.conta_id, OLD.conta_id);
    RETURN NULL;
END;
$$;
"""

_DROP_TRIGGER = "DROP TRIGGER IF EXISTS tg_recalcular_valor_pago ON pagamentos_financeiros;"
_DROP_FUNCTION = "DROP FUNCTION IF EXISTS tg_fn_recalcular_valor_pago();"

_CREATE_TRIGGER = """
CREATE TRIGGER tg_recalcular_valor_pago
AFTER INSERT OR UPDATE OR DELETE ON pagamentos_financeiros
FOR EACH ROW EXECUTE FUNCTION tg_fn_recalcular_valor_pago();
"""


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(text(_DROP_TRIGGER))
        bind.execute(text(_DROP_FUNCTION))
        bind.execute(text(_CREATE_FUNCTION))
        bind.execute(text(_CREATE_TRIGGER))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(text(_DROP_TRIGGER))
        bind.execute(text(_DROP_FUNCTION))
