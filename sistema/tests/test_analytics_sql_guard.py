from app.services.analytics_sql_guard import validate_analytics_sql


# ── Deve BLOQUEAR ──────────────────────────────────────────────────────────

def test_guard_bloqueia_update():
    out = validate_analytics_sql("UPDATE orcamentos SET total=0 WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code in {"sql_not_read_only", "sql_blocked_keyword"}


def test_guard_bloqueia_insert():
    out = validate_analytics_sql("INSERT INTO orcamentos (id) VALUES (1)")
    assert out.ok is False


def test_guard_bloqueia_delete():
    out = validate_analytics_sql("DELETE FROM clientes WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code in {"sql_not_read_only", "sql_blocked_keyword"}


def test_guard_bloqueia_drop():
    out = validate_analytics_sql("DROP TABLE clientes")
    assert out.ok is False


def test_guard_bloqueia_multi_statement():
    out = validate_analytics_sql(
        "SELECT * FROM orcamentos WHERE empresa_id = :empresa_id; SELECT 1"
    )
    assert out.ok is False
    assert out.code == "sql_multi_statement_blocked"


def test_guard_bloqueia_sem_tenant_scope():
    out = validate_analytics_sql("SELECT id, total FROM orcamentos")
    assert out.ok is False
    assert out.code == "sql_missing_tenant_scope"


def test_guard_bloqueia_or_1_equals_1():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id OR 1=1"
    )
    assert out.ok is False
    assert out.code == "sql_tenant_bypass_pattern"


def test_guard_bloqueia_tabela_pg():
    out = validate_analytics_sql("SELECT * FROM pg_tables WHERE empresa_id = :empresa_id")
    assert out.ok is False
    assert out.code == "sql_system_table_blocked"


def test_guard_bloqueia_alembic():
    out = validate_analytics_sql("SELECT * FROM alembic_version WHERE schemaname = :empresa_id")
    assert out.ok is False
    assert out.code == "sql_system_table_blocked"


def test_guard_bloqueia_parenteses_desbalanceados():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id AND (id > 0"
    )
    assert out.ok is False
    assert out.code == "sql_unbalanced_parentheses"


# ── Deve PERMITIR ──────────────────────────────────────────────────────────

def test_guard_aceita_select_simples():
    out = validate_analytics_sql(
        "SELECT id, total FROM orcamentos WHERE empresa_id = :empresa_id"
    )
    assert out.ok is True
    assert out.sql is not None


def test_guard_aceita_join():
    out = validate_analytics_sql(
        "SELECT o.id, c.nome, SUM(o.valor_total) "
        "FROM orcamentos o JOIN clientes c ON o.cliente_id = c.id "
        "WHERE o.empresa_id = :empresa_id GROUP BY o.id, c.nome"
    )
    assert out.ok is True


def test_guard_aceita_union():
    out = validate_analytics_sql(
        "SELECT id, 'orcamento' as tipo FROM orcamentos WHERE empresa_id = :empresa_id "
        "UNION ALL "
        "SELECT id, 'cliente' as tipo FROM clientes WHERE empresa_id = :empresa_id"
    )
    assert out.ok is True


def test_guard_aceita_subquery_in():
    out = validate_analytics_sql(
        "SELECT * FROM clientes WHERE empresa_id = :empresa_id "
        "AND id IN (SELECT cliente_id FROM orcamentos WHERE empresa_id = :empresa_id AND status = 'aprovado')"
    )
    assert out.ok is True


def test_guard_aceita_cte():
    out = validate_analytics_sql(
        "WITH top_clientes AS ("
        "  SELECT cliente_id, SUM(valor_total) as total "
        "  FROM orcamentos WHERE empresa_id = :empresa_id GROUP BY cliente_id"
        ") SELECT c.nome, t.total FROM top_clientes t JOIN clientes c ON c.id = t.cliente_id"
    )
    assert out.ok is True


def test_guard_aceita_group_by_order_by():
    out = validate_analytics_sql(
        "SELECT status, COUNT(*) as qtd, SUM(valor_total) as total "
        "FROM orcamentos WHERE empresa_id = :empresa_id "
        "GROUP BY status ORDER BY total DESC LIMIT 10"
    )
    assert out.ok is True


def test_guard_aceita_cross_tenant_sem_empresa_id():
    out = validate_analytics_sql(
        "SELECT COUNT(*) FROM orcamentos",
        allow_cross_tenant=True,
    )
    assert out.ok is True


def test_guard_result_tem_campos_de_compatibilidade():
    out = validate_analytics_sql(
        "SELECT id FROM orcamentos WHERE empresa_id = :empresa_id"
    )
    assert out.ok is True
    assert hasattr(out, "risk_score")
    assert hasattr(out, "complexity")
