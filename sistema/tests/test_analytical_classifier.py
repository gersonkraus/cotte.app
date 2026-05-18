from app.ai.analytical_classifier import (
    classify_analytical_intent,
    build_history_context,
    HistoryContext,
)


# ── Queries analíticas explícitas — devem retornar is_analytical=True ─────────

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
    r = classify_analytical_intent(
        "qual foi o crescimento do faturamento comparando com o mês passado?"
    )
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


# ── Novas keywords: tabela, contas, extrato ────────────────────────────────────

def test_classifica_tabela_contas():
    r = classify_analytical_intent("crie uma tabela com todas as contas da Ana Julia")
    assert r.is_analytical is True
    assert any("tabela" in t or "todas as contas" in t for t in r.triggers)


def test_classifica_tabela_cliente_id():
    r = classify_analytical_intent("crie uma tabela com todas as contas da Ana julia id 1")
    assert r.is_analytical is True


def test_classifica_contas_de():
    r = classify_analytical_intent("mostra as contas de João")
    assert r.is_analytical is True


def test_classifica_extrato():
    r = classify_analytical_intent("extrato da conta do mês")
    assert r.is_analytical is True


def test_classifica_vencidas():
    r = classify_analytical_intent("quais contas estão vencidas?")
    assert r.is_analytical is True


def test_classifica_em_aberto():
    r = classify_analytical_intent("listar contas em aberto")
    assert r.is_analytical is True


def test_classifica_detalhar():
    r = classify_analytical_intent("quero detalhar as movimentações")
    assert r.is_analytical is True


def test_classifica_todas_as_despesas():
    r = classify_analytical_intent("mostrar todas as despesas do cliente")
    assert r.is_analytical is True


def test_classifica_gerar_relatorio():
    r = classify_analytical_intent("gerar relatório de vendas")
    assert r.is_analytical is True


# ── Follow-up com contexto de dados (HistoryContext) ──────────────────────────

def _data_history():
    return [
        {"role": "user", "content": "lista de clientes que estão devendo"},
        {
            "role": "assistant",
            "content": (
                "Contas a Receber por Cliente — foram encontrados 103 registros. "
                "Exibindo 10 itens. Ana Julia: R$ 8.384,59 (70 contas). "
                "Qual delas você gostaria de detalhar?"
            ),
        },
    ]


def test_followup_tabela_com_contexto():
    hist = build_history_context(_data_history())
    assert hist.is_data_context is True
    r = classify_analytical_intent(
        "crie uma tabela com todas as contas da Ana julia", history_context=hist
    )
    assert r.is_analytical is True
    assert any("data_followup" in t for t in r.triggers)


def test_followup_id_curto_com_contexto():
    hist = build_history_context(_data_history())
    r = classify_analytical_intent("id 1", history_context=hist)
    assert r.is_analytical is True
    assert any("short_reply_in_data_context" in t for t in r.triggers)


def test_followup_esse_cliente_com_contexto():
    hist = build_history_context(_data_history())
    r = classify_analytical_intent("detalhes desse cliente", history_context=hist)
    assert r.is_analytical is True


def test_followup_sem_contexto_nao_dispara():
    # "id 1" sem contexto de dados NÃO deve ser analítico
    r = classify_analytical_intent("id 1")
    assert r.is_analytical is False


def test_build_history_context_detecta_dados():
    hist = build_history_context(_data_history())
    assert hist.is_data_context is True
    assert hist.last_ai_asked_question is True


def test_build_history_context_sem_dados():
    msgs = [
        {"role": "user", "content": "olá"},
        {"role": "assistant", "content": "Olá! Como posso ajudar?"},
    ]
    hist = build_history_context(msgs)
    assert hist.is_data_context is False


def test_build_history_context_lista_vazia():
    hist = build_history_context([])
    assert hist.is_data_context is False
    assert hist.last_ai_asked_question is False


# ── Queries operacionais — NÃO devem ser analíticas ──────────────────────────

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
