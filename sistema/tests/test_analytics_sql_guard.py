from app.services.analytics_sql_guard import validate_analytics_sql


def test_sql_guard_bloqueia_dml_ddl():
    out = validate_analytics_sql("UPDATE orcamentos SET total=0 WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code in {"sql_not_read_only", "sql_blocked_keyword"}


def test_sql_guard_bloqueia_multi_statement():
    out = validate_analytics_sql(
        "SELECT * FROM orcamentos WHERE empresa_id = :empresa_id; SELECT * FROM clientes"
    )
    assert out.ok is False
    assert out.code == "sql_multi_statement_blocked"


def test_sql_guard_bloqueia_source_fora_whitelist():
    out = validate_analytics_sql("SELECT * FROM usuarios WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code == "sql_not_allowed_source"


def test_sql_guard_aceita_select_simples():
    out = validate_analytics_sql("SELECT id, total FROM orcamentos WHERE empresa_id = :empresa_id")
    assert out.ok is True
    assert isinstance(out.risk_score, int)


def test_sql_guard_exige_tenant_scope():
    out = validate_analytics_sql("SELECT id, total FROM orcamentos")
    assert out.ok is False
    assert out.code == "sql_missing_tenant_scope"


def test_sql_guard_bloqueia_bypass_or_true():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id OR 1=1"
    )
    assert out.ok is False
    assert out.code == "sql_tenant_bypass_pattern"


def test_sql_guard_bloqueia_union():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id UNION SELECT id FROM clientes WHERE empresa_id = :empresa_id"
    )
    assert out.ok is False
    assert out.code == "sql_union_blocked"
