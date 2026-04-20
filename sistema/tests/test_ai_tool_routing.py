import pytest
from app.services.ai_intention_classifier import IntentionClassifier, IntencaoUsuario

# Casos de teste: (mensagem_do_usuario, intencao_esperada)
# Estes testes validam o roteamento determinístico baseado em regex.
TEST_CASES = [
    # --- Conflito 1: Relatórios vs. Listagem de Orçamentos ---
    ("listar orçamentos", IntencaoUsuario.LISTAR_ORCAMENTOS),
    ("me mostre os últimos orçamentos", IntencaoUsuario.LISTAR_ORCAMENTOS),
    ("todos os orçamentos", IntencaoUsuario.LISTAR_ORCAMENTOS),
    ("relatório de orçamentos aprovados este mês", IntencaoUsuario.GERAR_RELATORIO),
    ("gerar relatório de orçamentos", IntencaoUsuario.GERAR_RELATORIO),

    # --- Listagem de Clientes ---
    ("listar meus clientes", IntencaoUsuario.LISTAR_CLIENTES),
    ("quais são os meus clientes", IntencaoUsuario.LISTAR_CLIENTES),
    ("todos os clientes", IntencaoUsuario.LISTAR_CLIENTES),
    ("lista de clientes", IntencaoUsuario.LISTAR_CLIENTES),

    # --- Conflito 2: Faturamento (Relatório vs. Análise Simples) ---
    ("faturamento do mês", IntencaoUsuario.GERAR_RELATORIO),
    ("qual o faturamento dos últimos 90 dias", IntencaoUsuario.GERAR_RELATORIO),
    ("faturamento", IntencaoUsuario.FATURAMENTO), # Intenção mais genérica

    # --- Conflito 3: Ranking de Clientes ---
    ("ranking de clientes", IntencaoUsuario.GERAR_RELATORIO),
    ("top 10 clientes", IntencaoUsuario.GERAR_RELATORIO),
    ("melhores clientes por faturamento", IntencaoUsuario.GERAR_RELATORIO),

    # --- Conflito 4: Contas a Receber vs. Inadimplência ---
    ("contas a receber vencidas", IntencaoUsuario.INADIMPLENCIA),
    ("clientes devendo", IntencaoUsuario.INADIMPLENCIA),
    ("quem está inadimplente", IntencaoUsuario.INADIMPLENCIA),
    ("contas a receber", IntencaoUsuario.CONTAS_RECEBER),
    
    # --- Gatilhos Gerais ---
    ("saldo", IntencaoUsuario.SALDO_RAPIDO),
    ("quanto tenho em caixa?", IntencaoUsuario.SALDO_RAPIDO),
    ("criar orçamento para o cliente Gerson de 2 mil reais", IntencaoUsuario.CRIAR_ORCAMENTO),
    ("aprovar o orçamento 123", IntencaoUsuario.OPERADOR),
    ("ver o orc-456", IntencaoUsuario.OPERADOR),
    ("preciso de ajuda", IntencaoUsuario.ONBOARDING),
    ("como eu crio um cliente?", IntencaoUsuario.AJUDA_SISTEMA),
]

@pytest.mark.parametrize("message, expected_intent", TEST_CASES)
def test_intent_classification_routing(message, expected_intent):
    """
    Valida que gatilhos específicos são classificados para a intenção correta,
    garantindo que a rota determinística (regex) funcione como esperado e
    resolvendo ambiguidades entre ferramentas.
    """
    classifier = IntentionClassifier()
    
    # Testa diretamente o método de classificação por regex, que é síncrono
    # e o principal ponto de conflito.
    result_intent = classifier._classificar_regex(message)
    
    assert result_intent == expected_intent
