"""Infraestrutura base para entidades tenant-scoped."""

from __future__ import annotations

TENANT_SCOPED_MODELS: list[type] = []


class TenantScopedMixin:
    """Marca models cujo escopo principal é `empresa_id`."""

    __tenant_scoped__ = True
    __tenant_scope_field__ = "empresa_id"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is not TenantScopedMixin and cls not in TENANT_SCOPED_MODELS:
            TENANT_SCOPED_MODELS.append(cls)
