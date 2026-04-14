import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_db as get_api_db
from app.core.auth import criar_token
from app.core.database import Base, get_db as get_core_db
from app.models.models import Cliente
from app.routers.clientes import router as clientes_router
from tests.conftest import (
    TestingSessionLocal,
    sync_engine_test,
    make_cliente,
    make_empresa,
    make_usuario,
)


API_V1 = "/api/v1"


def _auth_headers(usuario) -> dict[str, str]:
    token = criar_token({"sub": str(usuario.id), "v": int(usuario.token_versao or 1)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant_http_client():
    Base.metadata.create_all(bind=sync_engine_test)

    seed_db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        seed_db.execute(table.delete())
    seed_db.commit()
    seed_db.close()

    app = FastAPI()
    app.include_router(clientes_router, prefix=API_V1)

    def _override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_core_db] = _override_db
    app.dependency_overrides[get_api_db] = _override_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()


def test_clientes_lista_nao_vaza_registros_de_outra_empresa(tenant_http_client):
    db = TestingSessionLocal()
    empresa_a = make_empresa(db, nome="Empresa Lista A", telefone_operador="5511999910001")
    empresa_b = make_empresa(db, nome="Empresa Lista B", telefone_operador="5511999910002")

    usuario_a = make_usuario(db, empresa_a, email="tenant-list-a@teste.com")
    usuario_a.token_versao = 1
    make_usuario(db, empresa_b, email="tenant-list-b@teste.com").token_versao = 1

    make_cliente(db, empresa_a, nome="Cliente Empresa A", telefone="5511980010001")
    make_cliente(db, empresa_b, nome="Cliente Empresa B", telefone="5511980010002")
    db.commit()
    db.close()

    r = tenant_http_client.get(f"{API_V1}/clientes/", headers=_auth_headers(usuario_a))

    assert r.status_code == 200
    data = r.json()
    nomes = [item["nome"] for item in data]
    assert nomes == ["Cliente Empresa A"]


def test_cliente_por_id_de_outra_empresa_retorna_404(tenant_http_client):
    db = TestingSessionLocal()
    empresa_a = make_empresa(db, nome="Empresa Detalhe A", telefone_operador="5511999920001")
    empresa_b = make_empresa(db, nome="Empresa Detalhe B", telefone_operador="5511999920002")

    usuario_a = make_usuario(db, empresa_a, email="tenant-detail-a@teste.com")
    usuario_a.token_versao = 1
    cliente_b = make_cliente(
        db,
        empresa_b,
        nome="Cliente Privado B",
        telefone="5511980020002",
    )
    db.commit()
    cliente_b_id = cliente_b.id
    db.close()

    r = tenant_http_client.get(
        f"{API_V1}/clientes/{cliente_b_id}",
        headers=_auth_headers(usuario_a),
    )

    assert r.status_code == 404


def test_criar_cliente_permanece_na_empresa_do_usuario_autenticado(tenant_http_client):
    db = TestingSessionLocal()
    empresa_a = make_empresa(db, nome="Empresa Create A", telefone_operador="5511999930001")
    empresa_b = make_empresa(db, nome="Empresa Create B", telefone_operador="5511999930002")

    usuario_a = make_usuario(db, empresa_a, email="tenant-create-route@teste.com")
    usuario_a.token_versao = 1
    db.commit()
    empresa_a_id = empresa_a.id
    empresa_b_id = empresa_b.id
    db.close()

    payload = {
        "nome": "Cliente Criado Via Rota",
        "telefone": "5511980030001",
        "email": "cliente-rota@teste.com",
    }

    r = tenant_http_client.post(
        f"{API_V1}/clientes/",
        json=payload,
        headers=_auth_headers(usuario_a),
    )

    assert r.status_code == 201
    body = r.json()
    assert body["empresa_id"] == empresa_a_id

    verify_db = TestingSessionLocal()
    criado = verify_db.query(Cliente).filter(Cliente.id == body["id"]).first()
    assert criado is not None
    assert criado.empresa_id == empresa_a_id
    assert criado.empresa_id != empresa_b_id
    verify_db.close()
