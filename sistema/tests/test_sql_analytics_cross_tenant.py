"""Testes para validação cross-tenant do SQL analítico."""

import pytest
from app.services.analytics_sql_guard import validate_analytics_sql


def test_validate_analytics_sql_requires_tenant_scope_by_default():
    """SQL sem :empresa_id deve falhar por padrão."""
    result = validate_analytics_sql("SELECT * FROM clientes")
    assert result.ok is False
    assert result.code == "sql_missing_tenant_scope"


def test_validate_analytics_sql_allows_no_tenant_scope_when_cross_tenant():
    """SQL sem :empresa_id é permitido quando allow_cross_tenant=True."""
    result = validate_analytics_sql("SELECT * FROM clientes", allow_cross_tenant=True)
    assert result.ok is True


def test_validate_analytics_sql_still_blocks_dangerous_when_cross_tenant():
    """SQL perigoso é bloqueado mesmo com allow_cross_tenant=True."""
    result = validate_analytics_sql("DELETE FROM clientes", allow_cross_tenant=True)
    assert result.ok is False
    assert result.code == "sql_not_read_only"


def test_validate_analytics_sql_still_requires_allowed_sources():
    """Fontes não permitidas são bloqueadas mesmo com allow_cross_tenant."""
    result = validate_analytics_sql(
        "SELECT * FROM tabela_nao_permitida", allow_cross_tenant=True
    )
    assert result.ok is False
    assert result.code == "sql_not_allowed_source"


def test_validate_analytics_sql_with_tenant_scope_passes_by_default():
    """SQL com :empresa_id passa na validação padrão."""
    result = validate_analytics_sql(
        "SELECT * FROM clientes WHERE empresa_id = :empresa_id"
    )
    assert result.ok is True


def test_validate_analytics_sql_blocks_union():
    """UNION é bloqueado independentemente de cross_tenant."""
    result = validate_analytics_sql(
        "SELECT id FROM clientes WHERE empresa_id = :empresa_id UNION SELECT id FROM orcamentos",
        allow_cross_tenant=True,
    )
    assert result.ok is False
    assert result.code == "sql_union_blocked"
