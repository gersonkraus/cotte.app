"""merge 1548e7057e6c (monetary refactor) with m001 (feedback_assistente)

Revision ID: n001_merge_1548_and_m001
Revises: 1548e7057e6c, m001_feedback_assistente
Create Date: 2026-03-21

Fecha o grafo: ambas as branches partem de z005_status_pipeline_missing.
Sem alteração de schema.
"""
from typing import Sequence, Union

revision: str = "n001_merge_1548_and_m001"
down_revision: Union[str, Sequence[str], None] = (
    "1548e7057e6c",
    "m001_feedback_assistente",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
