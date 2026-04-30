from __future__ import annotations

from app.services.cotte_context_builder import SessionStore
from app.services.internal_copilot_artifacts import ArtifactManager, LiveArtifact
from app.services.internal_copilot_memory import (
    INTERNAL_COPILOT_WORKING_MEMORY_KEY,
    InternalCopilotMemoryStore,
)
from tests.conftest import make_empresa, make_usuario


def test_get_active_artifact_returns_default_shape_for_missing_artifact(db):
    emp = make_empresa(db, nome="Artefato Default")
    user = make_usuario(db, emp, email="artifact-default@teste.com")
    sessao_id = "sess-art-default"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    artifact = ArtifactManager.get_active_artifact(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert artifact.model_dump() == {
        "artifact_id": None,
        "artifact_type": None,
        "title": None,
        "summary": None,
        "table": [],
        "chart": None,
        "insights": [],
        "suggested_actions": [],
        "metadata": {},
        "status": "idle",
        "updated_at": None,
    }


def test_upsert_artifact_creates_new_artifact_and_persists_in_working_memory(db):
    emp = make_empresa(db, nome="Artefato Novo")
    user = make_usuario(db, emp, email="artifact-new@teste.com")
    sessao_id = "sess-art-create"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    artifact = ArtifactManager.upsert_artifact(
        sessao_id,
        {
            "artifact_id": "rel-1",
            "artifact_type": "report",
            "title": "Diagnostico inicial",
            "summary": "Resumo incremental.",
            "table": [{"coluna": "valor"}],
            "insights": ["Primeiro insight"],
            "suggested_actions": ["Aprofundar consulta"],
            "metadata": {"source": "sql_agent"},
            "status": "in_progress",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert artifact.artifact_id == "rel-1"
    assert artifact.artifact_type == "report"
    assert artifact.title == "Diagnostico inicial"
    assert artifact.status == "in_progress"
    assert artifact.updated_at is not None

    memory = InternalCopilotMemoryStore.get_memory(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    assert memory.artefato_em_andamento == artifact.model_dump(exclude_none=True)


def test_upsert_artifact_ignores_empty_patch_without_persisting(db):
    emp = make_empresa(db, nome="Artefato Noop")
    user = make_usuario(db, emp, email="artifact-noop@teste.com")
    sessao_id = "sess-art-noop"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    artifact = ArtifactManager.upsert_artifact(
        sessao_id,
        None,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert artifact.model_dump() == LiveArtifact().model_dump()
    memory = InternalCopilotMemoryStore.get_memory(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    assert memory.artefato_em_andamento is None


def test_upsert_artifact_preserves_existing_fields_on_incremental_update(db):
    emp = make_empresa(db, nome="Artefato Incremental")
    user = make_usuario(db, emp, email="artifact-incremental@teste.com")
    sessao_id = "sess-art-incremental"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    created = ArtifactManager.upsert_artifact(
        sessao_id,
        {
            "artifact_id": "rel-2",
            "artifact_type": "report",
            "title": "Receita por vendedor",
            "summary": "Base inicial.",
            "table": [{"vendedor": "Ana", "total": 1200}],
            "chart": {"type": "bar"},
            "insights": ["Ana lidera"],
            "suggested_actions": ["Ver detalhamento"],
            "metadata": {"origin": "semantic_contract"},
            "status": "in_progress",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    updated = ArtifactManager.upsert_artifact(
        sessao_id,
        {
            "summary": "Base inicial com complemento.",
            "insights": ["Ana lidera", "Carlos cresceu 12%"],
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert updated.artifact_id == created.artifact_id
    assert updated.artifact_type == created.artifact_type
    assert updated.title == created.title
    assert updated.table == created.table
    assert updated.chart == created.chart
    assert updated.metadata == created.metadata
    assert updated.summary == "Base inicial com complemento."
    assert updated.insights == ["Ana lidera", "Carlos cresceu 12%"]
    assert updated.updated_at is not None
    assert updated.updated_at != created.updated_at


def test_upsert_artifact_tolerates_invalid_patch(db):
    emp = make_empresa(db, nome="Artefato Patch Invalido")
    user = make_usuario(db, emp, email="artifact-invalid-patch@teste.com")
    sessao_id = "sess-art-invalid-patch"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    created = ArtifactManager.upsert_artifact(
        sessao_id,
        {
            "artifact_id": "rel-4",
            "artifact_type": "report",
            "summary": "Base inicial.",
            "status": "in_progress",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    updated = ArtifactManager.upsert_artifact(
        sessao_id,
        {"insights": "texto invalido"},
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert updated.model_dump() == created.model_dump()


def test_clear_artifact_removes_only_artifact_from_working_memory(db):
    emp = make_empresa(db, nome="Artefato Clear")
    user = make_usuario(db, emp, email="artifact-clear@teste.com")
    sessao_id = "sess-art-clear"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Montar relatorio vivo",
            "proximos_passos_sugeridos": ["Coletar mais contexto"],
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    ArtifactManager.upsert_artifact(
        sessao_id,
        {
            "artifact_id": "rel-3",
            "artifact_type": "report",
            "summary": "Parcial",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    cleared = ArtifactManager.clear_artifact(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert cleared.model_dump() == LiveArtifact().model_dump()

    persisted_context = SessionStore.get_operational_context(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    memory_payload = persisted_context[INTERNAL_COPILOT_WORKING_MEMORY_KEY]
    assert memory_payload["artefato_em_andamento"] is None
    assert memory_payload["objetivo_ativo"] == "Montar relatorio vivo"
    assert memory_payload["proximos_passos_sugeridos"] == ["Coletar mais contexto"]
