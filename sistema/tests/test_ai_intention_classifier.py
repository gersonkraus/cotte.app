import pytest
import os
from unittest.mock import patch, MagicMock

from app.services.ai_intention_classifier import (
    IntentionClassifier,
    IntencaoUsuario,
    ClassificacaoResult
)

@pytest.fixture
def classifier():
    return IntentionClassifier()

# ── TESTES ESTÁTICOS (REGRESSÃO DO REGEX) ─────────────────────────────
# Garante que as expressões regulares continuam funcionando perfeitamente (0ms e Custo 0)

@pytest.mark.parametrize("mensagem, intent_esperada", [
    # SALDO
    ("qual o saldo?", IntencaoUsuario.SALDO_RAPIDO),
    ("quanto tenho em caixa", IntencaoUsuario.SALDO_RAPIDO),
    ("caixa de hoje", IntencaoUsuario.SALDO_RAPIDO),
    
    # FATURAMENTO
    ("quanto fatura", IntencaoUsuario.FATURAMENTO),
    ("faturamento total", IntencaoUsuario.GERAR_RELATORIO),
    
    # RELATORIOS / ANALISE
    ("crie um ranking", IntencaoUsuario.GERAR_RELATORIO),
    ("quem mais comprou", IntencaoUsuario.GERAR_RELATORIO),
    ("relatório de vendas", IntencaoUsuario.GERAR_RELATORIO),
    ("ticket médio", IntencaoUsuario.GERAR_RELATORIO),
    
    # CRIAR ORÇAMENTO
    ("criar orçamento", IntencaoUsuario.CRIAR_ORCAMENTO),
    ("novo orçamento", IntencaoUsuario.CRIAR_ORCAMENTO),
    ("orçamento para ana julia", IntencaoUsuario.CRIAR_ORCAMENTO),
    ("orçamento da maria", IntencaoUsuario.CRIAR_ORCAMENTO),
    
    # LISTAR ORÇAMENTOS
    ("orçamentos da maria", IntencaoUsuario.LISTAR_ORCAMENTOS),
    
    # ONBOARDING
    ("como começo", IntencaoUsuario.ONBOARDING),
    ("por onde começo", IntencaoUsuario.ONBOARDING),
    
    # BATE PAPO
    ("bom dia", IntencaoUsuario.CONVERSACAO),
    ("olá, tudo bem?", IntencaoUsuario.CONVERSACAO),
])
@pytest.mark.asyncio
async def test_regex_classifier_base(classifier, mensagem, intent_esperada):
    """Testa o motor estático de Regex para garantir não regressão."""
    # Usando o método síncrono para garantir que o regex cobre esses casos básicos
    resultado = classifier.classificar_sync(mensagem)
    assert resultado == intent_esperada


# ── TESTES DE ESTRESSE E AUTO-HEALING (MUTAÇÃO COM LLM) ───────────────
# Só roda no CI se a flag estiver ativada, economiza tempo e $.

@pytest.mark.skipif(
    os.environ.get("RUN_AI_MUTATION_TESTS") != "true", 
    reason="Ative RUN_AI_MUTATION_TESTS=true para rodar o Auto-Healing com LLM"
)
@pytest.mark.asyncio
async def test_llm_auto_healing_mutation(classifier):
    """
    Uera mutações do prompt para testar se o classificador híbrido
    (Regex + Semântica) consegue entender intenções mal formatadas.
    """
    from litellm import acompletion
    
    # Gera variações coloquiais/erradas para "relatório de ranking de clientes"
    resp = await acompletion(
        model="openrouter/google/gemini-2.5-flash",
        api_key=os.getenv("AI_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
        messages=[{
            "role": "user", 
            "content": "Gere 3 frases coloquiais curtas, com possíveis erros de português "
                       "que signifiquem 'mostrar o ranking dos melhores clientes'. (use palavras como lista, quem mais, comprar, clientes) "
                       "Retorne APENAS as frases, uma por linha."
        }]
    )
    
    frases = resp.choices[0].message.content.strip().split("\n")
    frases = [f.strip("- *") for f in frases if f.strip()]
    
    for frase in frases:
        resultado = await classifier.classificar(frase)
        assert resultado.intencao in [IntencaoUsuario.GERAR_RELATORIO, IntencaoUsuario.ANALISE], f"Falhou com: {frase}"

