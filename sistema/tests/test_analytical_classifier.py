from app.ai.analytical_classifier import classify_analytical_intent


# ── Queries analíticas — devem retornar is_analytical=True ────────────────

def test_classifica_ranking():
    r = classify_analytical_intent("quais são os top 5 clientes que mais compraram?")
    assert r.is_analytical is True
    assert r.confidence > 0.4


def test_classifica_top_n():
    r = classify_analytical_intent("me mostra os 10 melhores clientes do mês")
    assert r.is_analytical is True


def test_classifica_agrupamento():
    r = classify_analytical_intent("faturamento por mês dos últimos 6 meses")
    assert r.is_analytical is True


def test_classifica_ticket_medio():
    r = classify_analytical_intent("qual é o ticket médio dos meus orçamentos aprovados?")
    assert r.is_analytical is True


def test_classifica_crescimento():
    r = classify_analytical_intent("qual foi o crescimento do faturamento comparando com o mês passado?")
    assert r.is_analytical is True


def test_classifica_inadimplencia():
    r = classify_analytical_intent("quais clientes estão inadimplentes?")
    assert r.is_analytical is True


def test_classifica_topicos_combinados():
    r = classify_analytical_intent("qual o faturamento por cliente nos últimos 90 dias?")
    assert r.is_analytical is True


def test_classifica_analise_historico():
    r = classify_analytical_intent("histórico de vendas por serviço")
    assert r.is_analytical is True


def test_classifica_top3():
    r = classify_analytical_intent("top 3 serviços mais vendidos")
    assert r.is_analytical is True


def test_classifica_quem_mais():
    r = classify_analytical_intent("quem mais comprou em abril?")
    assert r.is_analytical is True


# ── Queries operacionais — devem retornar is_analytical=False ─────────────

def test_nao_classifica_saldo():
    r = classify_analytical_intent("qual é meu saldo?")
    assert r.is_analytical is False


def test_nao_classifica_criar_orcamento():
    r = classify_analytical_intent("cria um orçamento para o João")
    assert r.is_analytical is False


def test_nao_classifica_aprovar():
    r = classify_analytical_intent("aprovar orçamento 5")
    assert r.is_analytical is False


def test_nao_classifica_listar_clientes():
    r = classify_analytical_intent("lista meus clientes")
    assert r.is_analytical is False


def test_nao_classifica_saudacao():
    r = classify_analytical_intent("olá, bom dia!")
    assert r.is_analytical is False


def test_nao_classifica_mensagem_vazia():
    r = classify_analytical_intent("")
    assert r.is_analytical is False


def test_retorna_triggers_quando_analitico():
    r = classify_analytical_intent("ranking dos melhores clientes")
    assert r.is_analytical is True
    assert len(r.triggers) > 0
