import pytest
from app.services.internal_copilot_memory import SessionWorkingMemory
from app.services.internal_copilot_artifacts import LiveArtifact
from app.services.internal_copilot_response import ResponseComposer

def test_response_composer_empty_states():
    memory = SessionWorkingMemory()
    artifact = LiveArtifact()
    
    payload = ResponseComposer.compose(memory, artifact)
    
    assert "Operação concluída." in payload["resposta"]
    assert "Operação concluída." in payload["mensagem"]
    assert payload.get("table") is None
    assert payload.get("chart") is None

def test_response_composer_with_artifact_data():
    memory = SessionWorkingMemory(
        objetivo_ativo="Analisar vendas"
    )
    artifact = LiveArtifact(
        summary="Análise de vendas concluída com sucesso.",
        insights=["Vendas subiram 10%", "Foco no produto A"],
        table=[{"id": 1, "total": 100}],
        chart={"type": "bar", "data": [1, 2, 3]},
        suggested_actions=["Gerar PDF"]
    )
    
    payload = ResponseComposer.compose(memory, artifact)
    
    assert "Análise de vendas concluída com sucesso." in payload["resposta"]
    assert "**Insights:**" in payload["resposta"]
    assert "- Vendas subiram 10%" in payload["resposta"]
    
    assert payload["table"] == [{"id": 1, "total": 100}]
    assert payload["sql_result"] == [{"id": 1, "total": 100}]
    assert payload["chart"] == {"type": "bar", "data": [1, 2, 3]}
    assert payload["actions"] == ["Gerar PDF"]

def test_response_composer_with_dicts():
    memory_dict = {
        "objetivo_ativo": "Aprovar orcamento",
        "pendencia_confirmacao": {"fields": ["justificativa"]}
    }
    artifact_dict = {
        "summary": "Confirme a aprovação do orçamento 123",
    }
    
    payload = ResponseComposer.compose(memory_dict, artifact_dict)
    
    assert payload["resposta"] == "Confirme a aprovação do orçamento 123"
    assert payload["form"] == {"fields": ["justificativa"]}

def test_response_composer_actions_fallback():
    # If artifact has no actions but memory has suggested actions
    memory = SessionWorkingMemory(
        proximos_passos_sugeridos=["Cancelar", "Confirmar"]
    )
    artifact = LiveArtifact(
        summary="Aguardando ação"
    )
    
    payload = ResponseComposer.compose(memory, artifact)
    assert payload["actions"] == ["Cancelar", "Confirmar"]
