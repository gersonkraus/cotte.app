from app.services.analytics_sql_guard import validate_analytics_sql


def test_sql_guard_bloqueia_dml_ddl():
    out = validate_analytics_sql("UPDATE orcamentos SET total=0")
    assert out.ok is False
    assert out.code in {"sql_not_read_only", "sql_blocked_keyword"}


def test_sql_guard_bloqueia_multi_statement():
    out = validate_analytics_sql("SELECT * FROM orcamentos; SELECT * FROM clientes")
    assert out.ok is False
    assert out.code == "sql_multi_statement_blocked"


def test_sql_guard_bloqueia_source_fora_whitelist():
    out = validate_analytics_sql("SELECT * FROM usuarios")
    assert out.ok is False
    assert out.code == "sql_not_allowed_source"


def test_sql_guard_aceita_select_simples():
    out = validate_analytics_sql("SELECT id, total FROM orcamentos")
    assert out.ok is True
