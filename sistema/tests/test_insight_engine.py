from datetime import datetime

from app.services.insight_engine import InsightEngine


def test_build_returns_canonical_fields():
    engine = InsightEngine()
    out = engine.build_for_empresa(
        empresa_id=1,
        contexto={"dominio": "orcamentos"},
        snapshot={"orcamentos": [{"id": 10, "dias_pendente": 8, "status": "ENVIADO"}]},
    )
    assert isinstance(out, list)
    assert out
    item = out[0]
    for k in (
        "id",
        "tipo",
        "prioridade",
        "dominio",
        "titulo",
        "descricao",
        "acao",
        "contexto",
        "score",
        "fonte",
        "expira_em",
    ):
        assert k in item


def test_high_priority_is_ranked_first():
    engine = InsightEngine()
    out = engine.build_for_empresa(
        empresa_id=1,
        contexto={"dominio": "financeiro"},
        snapshot={
            "financeiro": {"saldo_projetado": -100.0, "inadimplencia_pct": 25.0},
            "orcamentos": [{"id": 33, "dias_pendente": 6, "status": "ENVIADO"}],
        },
    )
    assert out[0]["prioridade"] in ("critica", "alta")


def test_generated_ids_are_deterministic_and_expiration_is_timezone_aware_iso():
    engine = InsightEngine()
    payload = {
        "empresa_id": 1,
        "contexto": {"dominio": "financeiro"},
        "snapshot": {"financeiro": {"saldo_projetado": -50.0}},
    }

    first = engine.build_for_empresa(**payload)
    second = engine.build_for_empresa(**payload)

    assert first[0]["id"] == second[0]["id"]
    expira_em = datetime.fromisoformat(first[0]["expira_em"])
    assert expira_em.tzinfo is not None
    assert expira_em.utcoffset() is not None


def test_returns_only_matching_rules_sorted_by_score_desc():
    engine = InsightEngine()

    out = engine.build_for_empresa(
        empresa_id=2,
        contexto={},
        snapshot={
            "financeiro": {"saldo_projetado": -1.0, "inadimplencia_pct": 20.0},
            "orcamentos": [
                {"id": 1, "dias_pendente": 5, "status": "ENVIADO"},
                {"id": 2, "dias_pendente": 9, "status": "APROVADO"},
                {"id": 3, "dias_pendente": 9, "status": "RASCUNHO"},
            ],
        },
    )

    assert [item["score"] for item in out] == sorted(
        (item["score"] for item in out), reverse=True
    )
    assert {item["tipo"] for item in out} == {
        "saldo_projetado_negativo",
        "inadimplencia_alta",
        "orcamento_pendente",
    }


def test_dedupe_by_id_keeps_highest_score_and_preserves_items_without_id():
    engine = InsightEngine()

    out = engine.dedupe(
        [
            {"id": "duplicado", "score": 10, "titulo": "menor"},
            {"id": "sem-score", "titulo": "score ausente"},
            {"id": "duplicado", "score": 90, "titulo": "maior"},
            {"score": 70, "titulo": "sem id preservado"},
            "entrada invalida",
        ]
    )

    assert [item.get("titulo") for item in out] == [
        "maior",
        "sem id preservado",
        "score ausente",
    ]


def test_limit_orders_by_score_desc_before_cutting():
    engine = InsightEngine()

    out = engine.limit(
        [
            {"id": "baixo", "score": 10},
            {"id": "alto", "score": 90},
            {"id": "medio", "score": 50},
        ],
        2,
    )

    assert [item["id"] for item in out] == ["alto", "medio"]


def test_build_for_empresa_applies_dedupe_and_limit_when_requested():
    engine = InsightEngine()

    out = engine.build_for_empresa(
        empresa_id=3,
        contexto={"dominio": "hibrido"},
        snapshot={
            "financeiro": {"saldo_projetado": -1.0, "inadimplencia_pct": 30.0},
            "orcamentos": [
                {"id": 7, "dias_pendente": 9, "status": "ENVIADO"},
                {"id": 7, "dias_pendente": 9, "status": "ENVIADO"},
            ],
        },
        limit=2,
    )

    assert len(out) == 2
    assert [item["score"] for item in out] == [100, 80]
    assert len({item["id"] for item in out}) == 2


def test_build_for_empresa_ignores_non_dict_orcamento_items():
    engine = InsightEngine()

    out = engine.build_for_empresa(
        empresa_id=4,
        contexto={},
        snapshot={
            "orcamentos": [
                "orcamento invalido",
                {"id": 9, "dias_pendente": 8, "status": "ENVIADO"},
            ]
        },
    )

    assert [item["contexto"].get("orcamento_id") for item in out] == [9]


def test_build_for_empresa_ignores_non_numeric_rule_values():
    engine = InsightEngine()

    out = engine.build_for_empresa(
        empresa_id=5,
        contexto={},
        snapshot={
            "financeiro": {
                "saldo_projetado": "-100",
                "inadimplencia_pct": "25",
            },
            "orcamentos": [
                {"id": 10, "dias_pendente": "8", "status": "ENVIADO"},
                {"id": 11, "dias_pendente": 8, "status": "ENVIADO"},
            ],
        },
    )

    assert [item["contexto"].get("orcamento_id") for item in out] == [11]
    assert {item["tipo"] for item in out} == {"orcamento_pendente"}


def test_build_snapshot_returns_canonical_structure():
    import asyncio

    class MockDb:
        pass

    class MockContextBuilder:
        @staticmethod
        async def _ctx_financeiro(db, empresa_id):
            return {"saldo": {"atual": -50.0}}

        @staticmethod
        async def _ctx_orcamentos(db, empresa_id):
            return {
                "pendentes_acao": [
                    {"id": 1, "dias_aguardando": 7, "status": "ENVIADO"},
                    {"id": 2, "dias_aguardando": 3, "status": "RASCUNHO"},
                ]
            }

    import app.services.cotte_context_builder as ctx_module
    original = ctx_module.ContextBuilder
    ctx_module.ContextBuilder = MockContextBuilder

    try:
        snapshot = asyncio.get_event_loop().run_until_complete(
            InsightEngine.build_snapshot(MockDb(), 1)
        )
        assert "financeiro" in snapshot
        assert "orcamentos" in snapshot
        assert snapshot["financeiro"]["saldo_projetado"] == -50.0
        assert len(snapshot["orcamentos"]) == 2
        assert snapshot["orcamentos"][0]["dias_pendente"] == 7
        assert snapshot["orcamentos"][0]["status"] == "ENVIADO"
    finally:
        ctx_module.ContextBuilder = original


def test_build_snapshot_returns_empty_on_exception():
    import asyncio

    class MockDb:
        pass

    class MockContextBuilder:
        @staticmethod
        async def _ctx_financeiro(db, empresa_id):
            raise RuntimeError("db error")

    import app.services.cotte_context_builder as ctx_module
    original = ctx_module.ContextBuilder
    ctx_module.ContextBuilder = MockContextBuilder

    try:
        snapshot = asyncio.get_event_loop().run_until_complete(
            InsightEngine.build_snapshot(MockDb(), 1)
        )
        assert snapshot == {"financeiro": {}, "orcamentos": []}
    finally:
        ctx_module.ContextBuilder = original
