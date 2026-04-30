from __future__ import annotations

from app.services.cotte_context_builder import SessionStore, _sessions
from app.services.internal_copilot_memory import (
    INTERNAL_COPILOT_WORKING_MEMORY_KEY,
    InternalCopilotMemoryStore,
    SessionWorkingMemory,
)
from tests.conftest import make_empresa, make_usuario


def test_session_working_memory_default_shape():
    memory = SessionWorkingMemory()

    assert memory.model_dump() == {
        "objetivo_ativo": None,
        "tipo_fluxo_ativo": None,
        "escopo_ativo": None,
        "entidades_ativas": {},
        "subagente_primario": None,
        "subagentes_secundarios": [],
        "ultimo_resultado_relevante": None,
        "artefato_em_andamento": None,
        "tipo_resposta_esperada": None,
        "pendencia_confirmacao": None,
        "proximos_passos_sugeridos": [],
        "confianca_contextual": None,
    }


def test_internal_copilot_memory_store_applies_partial_patch():
    memory = InternalCopilotMemoryStore.apply_patch(
        SessionWorkingMemory(
            objetivo_ativo="Investigar erro no total",
            subagentes_secundarios=["sql_agent"],
        ),
        {
            "tipo_fluxo_ativo": "debug",
            "subagentes_secundarios": ["sql_agent", "code_rag"],
            "proximos_passos_sugeridos": ["Reproduzir erro", "Comparar query"],
        },
    )

    assert memory.model_dump() == {
        "objetivo_ativo": "Investigar erro no total",
        "tipo_fluxo_ativo": "debug",
        "escopo_ativo": None,
        "entidades_ativas": {},
        "subagente_primario": None,
        "subagentes_secundarios": ["sql_agent", "code_rag"],
        "ultimo_resultado_relevante": None,
        "artefato_em_andamento": None,
        "tipo_resposta_esperada": None,
        "pendencia_confirmacao": None,
        "proximos_passos_sugeridos": ["Reproduzir erro", "Comparar query"],
        "confianca_contextual": None,
    }


def test_internal_copilot_memory_store_ignores_empty_patch_without_persisting(db):
    emp = make_empresa(db, nome="Memoria Noop")
    user = make_usuario(db, emp, email="memoria-noop@teste.com")
    sessao_id = "sess-int-mem-noop"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    unchanged = InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        None,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert unchanged.model_dump() == SessionWorkingMemory().model_dump()
    persisted_context = SessionStore.get_operational_context(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    assert INTERNAL_COPILOT_WORKING_MEMORY_KEY not in persisted_context


def test_internal_copilot_memory_store_persists_and_reload_from_sessionstore(db):
    emp = make_empresa(db, nome="Memoria Copiloto")
    user = make_usuario(db, emp, email="memoria-copiloto@teste.com")
    sessao_id = "sess-int-mem-persist"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    SessionStore.set_operational_context(
        sessao_id,
        {"cliente_nome_ativo": "Maria"},
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    updated = InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Diagnosticar falha no PATCH",
            "subagente_primario": "code_rag",
            "confianca_contextual": 0.82,
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert updated.objetivo_ativo == "Diagnosticar falha no PATCH"

    persisted_context = SessionStore.get_operational_context(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    assert persisted_context["cliente_nome_ativo"] == "Maria"
    assert persisted_context[INTERNAL_COPILOT_WORKING_MEMORY_KEY] == updated.model_dump()

    _sessions.pop(SessionStore._cache_key(sessao_id, emp.id, user.id), None)

    reloaded = InternalCopilotMemoryStore.get_memory(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    assert reloaded.model_dump() == updated.model_dump()


def test_internal_copilot_memory_store_tolerates_invalid_payload(db):
    emp = make_empresa(db, nome="Memoria Invalida")
    user = make_usuario(db, emp, email="memoria-invalida@teste.com")
    sessao_id = "sess-int-mem-invalid"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)
    SessionStore.set_operational_context(
        sessao_id,
        {
            INTERNAL_COPILOT_WORKING_MEMORY_KEY: {
                "objetivo_ativo": "Investigar falha",
                "subagentes_secundarios": "sql_agent",
            }
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    memory = InternalCopilotMemoryStore.get_memory(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert memory.model_dump() == SessionWorkingMemory().model_dump()


def test_internal_copilot_memory_store_clear_memory(db):
    emp = make_empresa(db, nome="Memoria Limpeza")
    user = make_usuario(db, emp, email="memoria-limpeza@teste.com")
    sessao_id = "sess-int-mem-clear"
    SessionStore.ensure_sessao_db(sessao_id, emp.id, user.id, db)

    InternalCopilotMemoryStore.patch_memory(
        sessao_id,
        {
            "objetivo_ativo": "Corrigir regressao",
            "tipo_fluxo_ativo": "fix",
        },
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    SessionStore.set_operational_context(
        sessao_id,
        {"cliente_nome_ativo": "Joao"},
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    cleared = InternalCopilotMemoryStore.clear_memory(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )

    assert cleared.model_dump() == SessionWorkingMemory().model_dump()

    persisted_context = SessionStore.get_operational_context(
        sessao_id,
        db=db,
        empresa_id=emp.id,
        usuario_id=user.id,
    )
    assert INTERNAL_COPILOT_WORKING_MEMORY_KEY not in persisted_context
    assert persisted_context["cliente_nome_ativo"] == "Joao"
