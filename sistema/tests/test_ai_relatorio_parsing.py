import pytest
from app.services.cotte_ai_hub import _v2_parse_relatorio_params

def test_parse_relatorio_params_inadimplencia():
    # Deve retornar o domínio "inadimplencia" quando o intent_str for INADIMPLENCIA
    dominio, periodo_dias, agrupamento, metrica = _v2_parse_relatorio_params("lista de clientes devedores", intent_str="INADIMPLENCIA")
    assert dominio == "inadimplencia"
    
def test_parse_relatorio_params_without_intent():
    dominio, periodo_dias, agrupamento, metrica = _v2_parse_relatorio_params("faturamento")
    assert dominio == "orcamentos"
