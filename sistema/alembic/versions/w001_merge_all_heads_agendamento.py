"""merge: unifica todos os heads antes do agendamento_modo

Revision ID: w001_merge_all_heads_agendamento
Revises: 1548e7057e6c, 9d6276e279b2, ag001_fix_antecedencia, m001_feedback_assistente, z003_add_missing_fk_indexes, z003_merge_z002_and_9d6276, z006_audit_security
Create Date: 2026-03-26
"""
from typing import Union, Sequence
from alembic import op

revision: str = "w001_merge_all_heads_agendamento"
down_revision: Union[str, Sequence[str], None] = (
    "1548e7057e6c",
    "9d6276e279b2",
    "ag001_fix_antecedencia",
    "m001_feedback_assistente",
    "z003_add_missing_fk_indexes",
    "z003_merge_z002_and_9d6276",
    "z006_audit_security",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
