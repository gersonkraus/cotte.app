"""Merge z006_audit_logs_remove_perm_catalogo e p003_add_missing_empresa_columns.

Revision ID: z007_merge_z006_and_p003
Revises: z006_audit_logs_remove_perm_catalogo, p003_add_missing_empresa_columns
Create Date: 2026-03-23
"""
from typing import Sequence, Union

revision: str = "z007_merge_z006_and_p003"
down_revision: Union[str, Sequence[str], None] = (
    "z006_audit_security",
    "p003_add_missing_empresa_columns",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
