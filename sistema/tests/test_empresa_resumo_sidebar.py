"""
GET /empresa/resumo-sidebar — payload agregado para a sidebar (1 round-trip).
"""

from datetime import datetime, timedelta, timezone

from tests.conftest import make_empresa, make_usuario
from app.core.auth import criar_token

_API_V1 = "/api/v1"


def test_resumo_sidebar_200_e_chaves(http_client, db):
    emp = make_empresa(db, plano="pro", nome="Acme Sidebar")
    emp.ativo = True
    emp.trial_ate = datetime.now(timezone.utc) + timedelta(days=30)
    emp.assinatura_valida_ate = datetime.now(timezone.utc) + timedelta(days=30)
    db.commit()

    u = make_usuario(db, emp, email="sidebar-batch@teste.com")
    u.token_versao = 1
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    r = http_client.get(
        f"{_API_V1}/empresa/resumo-sidebar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "empresa" in data and "uso" in data
    assert "notificacoes_nao_lidas" in data
    assert data["empresa"]["nome"] == "Acme Sidebar"
    assert set(data["empresa"].keys()) == {"id", "nome", "logo_url", "plano"}
    assert data["uso"]["plano"] == "pro"
    assert isinstance(data["notificacoes_nao_lidas"], int)
