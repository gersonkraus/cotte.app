"""
Throttle de presença (ultima_atividade_em) em get_usuario_atual.
"""

from datetime import datetime, timedelta, timezone

import app.core.config as app_config
from app.core.auth import criar_token, _normalizar_utc, _presenca_esta_desatualizada
from app.models.models import Usuario
from tests.conftest import make_empresa, make_usuario

_API_V1 = "/api/v1"


def test_presenca_esta_desatualizada_none_e_stale():
    agora = datetime.now(timezone.utc)
    intervalo = timedelta(minutes=2)
    assert _presenca_esta_desatualizada(None, agora, intervalo) is True
    assert (
        _presenca_esta_desatualizada(agora - timedelta(minutes=3), agora, intervalo)
        is True
    )
    assert (
        _presenca_esta_desatualizada(agora - timedelta(seconds=30), agora, intervalo)
        is False
    )


def test_segunda_requisicao_nao_atualiza_presenca_dentro_do_intervalo(
    http_client, db, monkeypatch
):
    monkeypatch.setattr(
        app_config.settings,
        "ULTIMA_ATIVIDADE_COMMIT_INTERVAL_SECONDS",
        3600,
    )
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    emp.trial_ate = datetime.now(timezone.utc) + timedelta(days=30)
    emp.assinatura_valida_ate = datetime.now(timezone.utc) + timedelta(days=30)
    marca = datetime.now(timezone.utc) - timedelta(minutes=5)
    emp.ultima_atividade_em = marca
    db.commit()

    u = make_usuario(db, emp, email="presenca-throttle@teste.com")
    u.token_versao = 1
    u.ultima_atividade_em = marca
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    headers = {"Authorization": f"Bearer {token}"}

    r1 = http_client.get(f"{_API_V1}/orcamentos/", headers=headers)
    r2 = http_client.get(f"{_API_V1}/orcamentos/", headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200

    db.expire_all()
    u_db = db.query(Usuario).filter(Usuario.id == u.id).first()
    assert u_db.ultima_atividade_em is not None
    diff = abs(
        (
            _normalizar_utc(u_db.ultima_atividade_em)
            - _normalizar_utc(marca)
        ).total_seconds()
    )
    assert diff < 2, "presença não deve ter sido regravada"


def test_presenca_atualiza_quando_intervalo_passou(http_client, db, monkeypatch):
    monkeypatch.setattr(
        app_config.settings,
        "ULTIMA_ATIVIDADE_COMMIT_INTERVAL_SECONDS",
        60,
    )
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    emp.trial_ate = datetime.now(timezone.utc) + timedelta(days=30)
    emp.assinatura_valida_ate = datetime.now(timezone.utc) + timedelta(days=30)
    velho = datetime.now(timezone.utc) - timedelta(hours=2)
    emp.ultima_atividade_em = velho
    db.commit()

    u = make_usuario(db, emp, email="presenca-stale@teste.com")
    u.token_versao = 1
    u.ultima_atividade_em = velho
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    antes = datetime.now(timezone.utc)
    r = http_client.get(
        f"{_API_V1}/orcamentos/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    db.expire_all()
    u_db = db.query(Usuario).filter(Usuario.id == u.id).first()
    assert u_db.ultima_atividade_em is not None
    ultima = _normalizar_utc(u_db.ultima_atividade_em)
    assert ultima > _normalizar_utc(velho)
    assert ultima >= antes - timedelta(seconds=5)
