from app.services.assistant_autonomy.contracts import ExecutionResult, ExecutionStepResult
from app.services.assistant_autonomy.response_composer import compose_response_contract, to_ai_response_payload
from app.services.assistant_autonomy.semantic_planner import build_semantic_plan


def _execution_ok() -> ExecutionResult:
    return ExecutionResult(
        success=True,
        capability="GenerateAnalyticsReport",
        trace=[
            ExecutionStepResult(step="resolve_intent", stage="resolve", status="ok", latency_ms=2),
            ExecutionStepResult(step="tool:executar_sql_analitico", stage="fetch", status="ok", latency_ms=18),
        ],
        outputs={
            "tools": [
                {
                    "name": "executar_sql_analitico",
                    "status": "ok",
                    "data": {
                        "rows": [
                            {"vendedor": "João", "total_vendas": 1500.0},
                            {"vendedor": "Ana", "total_vendas": 1200.0},
                        ]
                    },
                }
            ]
        },
        metrics={"total_steps": 2, "total_duration_ms": 33, "generated_at": "2026-04-14T00:00:00+00:00"},
    )


def test_response_contract_contains_standard_metadata_and_printable():
    plan = build_semantic_plan("relatório imprimível de ranking de vendedores com gráfico")
    execution = _execution_ok()
    contract = compose_response_contract(plan, execution)
    assert contract.metadata.get("capability")
    assert "filters" in contract.metadata
    assert "data_sources" in contract.metadata
    assert contract.printable_payload is not None
    assert isinstance(contract.insights, list)
    assert isinstance(contract.suggested_actions, list)


def test_to_ai_response_payload_embeds_semantic_contract():
    plan = build_semantic_plan("relatório financeiro com tabela")
    execution = _execution_ok()
    contract = compose_response_contract(plan, execution)
    payload = to_ai_response_payload(contract=contract, execution=execution)
    semantic_contract = payload["dados"]["semantic_contract"]
    assert semantic_contract["summary"]
    assert isinstance(semantic_contract["table"], list)
    assert isinstance(semantic_contract["insights"], list)
    assert isinstance(semantic_contract["suggested_actions"], list)
    assert "metadata" in semantic_contract
