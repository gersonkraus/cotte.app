import pytest
from tests.conftest import make_empresa, make_usuario

@pytest.fixture
def empresa_com_fiscal(db):
    emp = make_empresa(db, nome="Empresa Fiscal Test")
    emp.cnpj = "12345678000100"
    emp.inscricao_estadual = "123456"
    emp.inscricao_municipal = "789012"
    emp.regime_tributario = "simples_nacional"
    emp.crt = "1"
    emp.notaas_api_key = "ntaas_test_key"
    emp.notaas_ambiente = "homologacao"
    db.commit()
    db.refresh(emp)
    return emp

def _auth_header(usuario):
    from app.core.auth import criar_token
    token = criar_token(data={"sub": str(usuario.id), "v": usuario.token_versao})
    return {"Authorization": "Bearer " + token}

def test_get_configuracao_fiscal(http_client, db, empresa_com_fiscal):
    usuario = make_usuario(db, empresa_com_fiscal)
    usuario.token_versao = 1
    db.commit()
    db.refresh(usuario)
    resp = http_client.get(
        "/api/v1/notas-fiscais/configuracao",
        headers=_auth_header(usuario),
    )
    print("GET RES:", resp.json())
    assert resp.status_code == 200

def test_salvar_configuracao_fiscal(http_client, db, empresa_com_fiscal):
    usuario = make_usuario(db, empresa_com_fiscal, is_superadmin=True)
    usuario.token_versao = 1
    db.commit()
    db.refresh(usuario)
    resp = http_client.put(
        "/api/v1/notas-fiscais/configuracao",
        json={"cnpj": "98765432000199", "regime_tributario": "lucro_presumido"},
        headers=_auth_header(usuario),
    )
    print("PUT RES:", resp.json())
    assert resp.status_code == 200

def test_listar_notas_fiscais(http_client, db, empresa_com_fiscal):
    usuario = make_usuario(db, empresa_com_fiscal)
    usuario.token_versao = 1
    db.commit()
    db.refresh(usuario)
    resp = http_client.get(
        "/api/v1/notas-fiscais",
        headers=_auth_header(usuario),
    )
    print("GET LIST RES:", resp.json())
    assert resp.status_code == 200
