import sys
import os
import pytest

# Ajusta path para importar app
sys.path.append(os.getcwd())

from app.services.ai_intention_classifier import IntencaoUsuario, detectar_intencao_assistente
from app.services.cotte_ai_hub import FallbackManual

@pytest.mark.parametrize("mensagem, expected_id", [
    ("ver 142", 142),
    ("ver orçamento 142", 142),
    ("orçamento o-142", 142),
    ("o-142", 142),
    ("orçamento 142", 142),
    ("ver PED-142", 142),
    ("abrir o-142", 142),
    ("detalhes 142", 142),
])
def test_orcamento_visualization_routing(mensagem, expected_id):
    """Testa se comandos de visualização de orçamento são roteados corretamente para OPERADOR."""
    intent = detectar_intencao_assistente(mensagem)
    assert intent == "OPERADOR"
    
    cmd = FallbackManual.extrair_comando(mensagem)
    assert cmd["acao"] == "VER"
    assert cmd["orcamento_id"] == expected_id
