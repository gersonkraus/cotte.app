from app.services.assistant_autonomy.intent_router import route_intent
from app.services.assistant_autonomy.semantic_model import detect_dimensions, detect_metrics
from app.services.assistant_autonomy.semantic_planner import build_semantic_plan


def test_route_intent_analytics():
    assert route_intent("compare as vendas deste mês com o passado") == "analytics"


def test_detect_metrics_and_dimensions():
    metrics = detect_metrics("quero relatório de clientes que mais compraram")
    dims = detect_dimensions("quero por vendedor e por mês")
    assert "top_customers" in metrics
    assert "seller" in dims
    assert "time_month" in dims


def test_build_semantic_plan_extracts_formats_period_and_capability():
    plan = build_semantic_plan("preciso de relatório financeiro com gráfico e pdf dos últimos 15 dias")
    assert plan.capability == "GeneratePrintableDocument"
    assert plan.request.period_days == 15
    assert "chart" in plan.request.output_formats
    assert "printable" in plan.request.output_formats


def test_build_semantic_plan_extracts_structured_filters():
    plan = build_semantic_plan(
        "Crie um relatório para imprimir com todas as vendas do vendedor João mostrando comissão de 8% com categorias X, Y e Z"
    )
    filters = plan.request.entity_filters
    assert plan.capability == "GeneratePrintableDocument"
    assert filters.get("seller_name")
    assert filters.get("commission_pct") == 8.0
    assert filters.get("categories") == ["X", "Y", "Z"]


def test_build_semantic_plan_routes_composite_flow():
    plan = build_semantic_plan("Crie um orçamento para cliente Maria e envie por WhatsApp e e-mail")
    assert plan.capability == "ExecuteCompositeWorkflow"
    channels = (plan.request.entity_filters or {}).get("channels") or {}
    assert channels.get("whatsapp") is True
    assert channels.get("email") is True
