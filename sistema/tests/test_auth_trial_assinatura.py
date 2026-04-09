"""
Gate unificado trial_ate + assinatura_valida_ate (get_usuario_atual e login).
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import func

from tests.conftest import make_empresa, make_usuario
from app.core.auth import criar_token, hash_senha, limite_acesso_empresa

_API_V1 = "/api/v1"


def test_trial_com_data_expirada_bloqueia_apos_graca(http_client, db):
    emp = make_empresa(db, plano="trial")
    emp.ativo = True
    emp.assinatura_valida_ate = None
    emp.trial_ate = datetime.now(timezone.utc) - timedelta(days=4)
    db.commit()

    u = make_usuario(db, emp)
    u.token_versao = 1
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    r = http_client.get(
        f"{_API_V1}/orcamentos/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 402


def test_trial_expirado_mas_assinatura_ativa_permite(http_client, db):
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    emp.trial_ate = datetime.now(timezone.utc) - timedelta(days=30)
    emp.assinatura_valida_ate = datetime.now(timezone.utc) + timedelta(days=30)
    db.commit()

    u = make_usuario(db, emp)
    u.token_versao = 1
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    r = http_client.get(
        f"{_API_V1}/orcamentos/", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


def test_login_bloqueado_trial_expirado(http_client, db):
    emp = make_empresa(db, plano="trial")
    emp.ativo = True
    emp.trial_ate = datetime.now(timezone.utc) - timedelta(days=4)
    db.commit()

    u = make_usuario(db, emp, email="trial-exp@teste.com")
    u.senha_hash = hash_senha("senha123")
    db.commit()

    r = http_client.post(
        f"{_API_V1}/auth/login",
        json={"email": "trial-exp@teste.com", "senha": "senha123"},
    )
    assert r.status_code == 402


def test_registrar_define_trial_igual_config(http_client, db, monkeypatch):
    """POST /auth/registrar deve gravar plano trial e trial_ate como /registro-publico."""

    monkeypatch.setattr(
        "app.services.admin_config.get_admin_config",
        lambda session: {"dias_trial_padrao": 21},
    )

    r = http_client.post(
        f"{_API_V1}/auth/registrar",
        json={
            "nome": "Novo Gestor",
            "email": "novo-registro-trial@teste.com",
            "senha": "SenhaSegura1!",
            "empresa_nome": "Empresa Registro API",
        },
    )
    assert r.status_code == 201

    from app.models.models import Empresa, Usuario

    u = (
        db.query(Usuario)
        .filter(func.lower(Usuario.email) == "novo-registro-trial@teste.com")
        .first()
    )
    assert u is not None
    emp = db.query(Empresa).filter(Empresa.id == u.empresa_id).first()
    assert emp.plano == "trial"
    lim = limite_acesso_empresa(emp)
    assert lim is not None
    agora = datetime.now(timezone.utc)
    assert (lim - agora).total_seconds() > 20 * 86400
