from app.models.models import ToolCallLog
from app.services.ai_observability_service import build_ai_health_summary
from tests.conftest import make_empresa


def test_build_ai_health_summary_agrega_todas_empresas_quando_empresa_id_none(db):
    empresa_a = make_empresa(db, nome="Obs Service A", telefone_operador="5511999911101")
    empresa_b = make_empresa(db, nome="Obs Service B", telefone_operador="5511999911102")

    db.add_all(
        [
            ToolCallLog(
                empresa_id=empresa_a.id,
                usuario_id=None,
                sessao_id="sess-obs-svc-1",
                tool="listar_orcamentos",
                args_json={"_meta": {"engine": "operational"}},
                resultado_json={"ok": True},
                status="ok",
                latencia_ms=90,
            ),
            ToolCallLog(
                empresa_id=empresa_b.id,
                usuario_id=None,
                sessao_id="sess-obs-svc-2",
                tool="analisar_tool_logs",
                args_json={"_meta": {"engine": "internal_copilot"}},
                resultado_json={"ok": True},
                status="ok",
                latencia_ms=140,
            ),
        ]
    )
    db.commit()

    out = build_ai_health_summary(db=db, empresa_id=None, hours=24)

    assert out["overview"]["total_tool_calls"] == 2
    assert "operational" in out["engines"]
    assert "internal_copilot" in out["engines"]


def test_build_ai_health_summary_mantem_filtro_por_empresa(db):
    empresa_a = make_empresa(db, nome="Obs Service C", telefone_operador="5511999911103")
    empresa_b = make_empresa(db, nome="Obs Service D", telefone_operador="5511999911104")

    db.add_all(
        [
            ToolCallLog(
                empresa_id=empresa_a.id,
                usuario_id=None,
                sessao_id="sess-obs-svc-3",
                tool="listar_orcamentos",
                args_json={"_meta": {"engine": "operational"}},
                resultado_json={"ok": True},
                status="ok",
                latencia_ms=90,
            ),
            ToolCallLog(
                empresa_id=empresa_b.id,
                usuario_id=None,
                sessao_id="sess-obs-svc-4",
                tool="analisar_tool_logs",
                args_json={"_meta": {"engine": "internal_copilot"}},
                resultado_json={"ok": True},
                status="ok",
                latencia_ms=140,
            ),
        ]
    )
    db.commit()

    out = build_ai_health_summary(db=db, empresa_id=empresa_a.id, hours=24)

    assert out["overview"]["total_tool_calls"] == 1
    assert "operational" in out["engines"]
    assert "internal_copilot" not in out["engines"]
