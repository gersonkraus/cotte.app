from app.services.internal_copilot_sql_guard import validate_sql_query


def test_validate_sql_query_blocks_drop_statement():
    decision = validate_sql_query(
        sql="DROP TABLE orcamentos",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )

    assert decision.allowed is False
    assert decision.reason == "blocked_statement"


def test_validate_sql_query_injects_empresa_filter_and_limit():
    decision = validate_sql_query(
        sql="SELECT id, cliente_nome FROM orcamentos",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )

    assert decision.allowed is True
    assert "empresa_id = 3" in (decision.rewritten_sql or "")
    assert "LIMIT 100" in (decision.rewritten_sql or "")


def test_validate_sql_query_blocks_union_select():
    decision = validate_sql_query(
        sql="SELECT id FROM orcamentos UNION SELECT id FROM usuarios",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )

    assert decision.allowed is False
    assert decision.reason == "unsupported_select_shape"


def test_validate_sql_query_blocks_select_with_alias():
    decision = validate_sql_query(
        sql="SELECT o.id FROM orcamentos o",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )

    assert decision.allowed is False
    assert decision.reason == "unsupported_select_shape"


def test_validate_sql_query_requires_confirmation_for_write_statement():
    decision = validate_sql_query(
        sql="UPDATE orcamentos SET cliente_nome = 'Maria'",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )

    assert decision.allowed is False
    assert decision.needs_confirmation is True
    assert decision.reason == "write_requires_confirmation"
    assert decision.mode == "confirmation_required"


def test_validate_sql_query_requires_confirmation_for_insert_statement():
    decision = validate_sql_query(
        sql="INSERT INTO orcamentos (cliente_nome) VALUES ('Maria')",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )

    assert decision.allowed is False
    assert decision.needs_confirmation is True
    assert decision.reason == "write_requires_confirmation"
    assert decision.mode == "confirmation_required"


def test_validate_sql_query_requires_confirmation_for_delete_statement():
    decision = validate_sql_query(
        sql="DELETE FROM orcamentos WHERE id = 10",
        empresa_id=3,
        allowed_tables={"orcamentos": {"empresa_column": "empresa_id"}},
    )

    assert decision.allowed is False
    assert decision.needs_confirmation is True
    assert decision.reason == "write_requires_confirmation"
    assert decision.mode == "confirmation_required"
