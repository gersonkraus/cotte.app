"""
Testes: webhook Kiwify → bloqueio/ativação de empresa + check 402 em auth.

Cenários:
  1. subscription_payment_failed desativa a empresa (lookup por e-mail do usuário)
  2. subscription_canceled desativa via fallback por Empresa.email
  3. Login bloqueado (402) quando assinatura expirou há > 3 dias
  4. Login OK quando assinatura expirou há < 3 dias (dentro da graça)
  5. Trial sem trial_ate nem assinatura_valida_ate não bloqueia (200; legado)
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from tests.conftest import make_empresa, make_usuario
from app.core.auth import criar_token

# Alinhado a include_routers em main.py (prefixo /api/v1)
_API_V1 = "/api/v1"
_KIWIFY_WEBHOOK = f"{_API_V1}/webhooks/kiwify"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: desabilita validação de token Kiwify nos testes
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def sem_kiwify_token():
    """Desenvolvimento: token vazio não bloqueia; ENVIRONMENT fora de produção."""
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.KIWIFY_TOKEN = ""
        mock_settings.ENVIRONMENT = "development"
        yield


# ─────────────────────────────────────────────────────────────────────────────
# Produção sem KIWIFY_TOKEN: rejeita antes de idempotência / alteração de assinatura
# ─────────────────────────────────────────────────────────────────────────────

def test_producao_sem_kiwify_token_retorna_401(http_client, db):
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    db.commit()
    make_usuario(db, emp, email="prod@teste.com")
    db.commit()

    payload = {
        "event": "subscription_payment_failed",
        "data": {"customer": {"email": "prod@teste.com"}},
    }
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.KIWIFY_TOKEN = ""
        mock_settings.ENVIRONMENT = "production"
        r = http_client.post(_KIWIFY_WEBHOOK, json=payload)

    assert r.status_code == 401
    assert "KIWIFY_TOKEN" in r.json()["detail"]
    db.refresh(emp)
    assert emp.ativo is True


# ─────────────────────────────────────────────────────────────────────────────
# Cenário 1: payment_failed desativa a empresa
# ─────────────────────────────────────────────────────────────────────────────

def test_payment_failed_desativa(http_client, db):
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    db.commit()
    make_usuario(db, emp, email="pagador@teste.com")
    db.commit()

    payload = {
        "event": "subscription_payment_failed",
        "data": {"customer": {"email": "pagador@teste.com"}},
    }
    r = http_client.post(_KIWIFY_WEBHOOK, json=payload)
    assert r.status_code == 200
    assert r.json()["acao"] == "desativada"

    db.refresh(emp)
    assert emp.ativo == False


# ─────────────────────────────────────────────────────────────────────────────
# Cenário 1b: subscription_suspended também desativa
# ─────────────────────────────────────────────────────────────────────────────

def test_subscription_suspended_desativa(http_client, db):
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    db.commit()
    make_usuario(db, emp, email="suspenso@teste.com")
    db.commit()

    payload = {
        "event": "subscription_suspended",
        "data": {"customer": {"email": "suspenso@teste.com"}},
    }
    r = http_client.post(_KIWIFY_WEBHOOK, json=payload)
    assert r.status_code == 200
    assert r.json()["acao"] == "desativada"

    db.refresh(emp)
    assert emp.ativo == False


# ─────────────────────────────────────────────────────────────────────────────
# Cenário 2: lookup por Empresa.email (fallback)
# ─────────────────────────────────────────────────────────────────────────────

def test_lookup_por_empresa_email(http_client, db):
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    emp.email = "empresa@dominio.com"
    db.commit()
    # Usuário tem e-mail diferente do e-mail da empresa
    make_usuario(db, emp, email="usuario@outro.com", is_gestor=True)
    db.commit()

    payload = {
        "event": "subscription_canceled",
        "data": {"customer": {"email": "empresa@dominio.com"}},
    }
    r = http_client.post(_KIWIFY_WEBHOOK, json=payload)
    assert r.status_code == 200
    assert r.json()["acao"] == "desativada"

    db.refresh(emp)
    assert emp.ativo == False


# ─────────────────────────────────────────────────────────────────────────────
# Cenário 3: login bloqueado quando assinatura expirou há > 3 dias (402)
# ─────────────────────────────────────────────────────────────────────────────

def test_login_bloqueado_apos_graca(http_client, db):
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    emp.assinatura_valida_ate = datetime.now(timezone.utc) - timedelta(days=4)
    db.commit()

    u = make_usuario(db, emp)
    u.token_versao = 1
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    r = http_client.get(f"{_API_V1}/orcamentos/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 402
    assert "expirada" in r.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Cenário 4: dentro do período de graça (2 dias expirado) → 200
# ─────────────────────────────────────────────────────────────────────────────

def test_login_ok_dentro_da_graca(http_client, db):
    emp = make_empresa(db, plano="pro")
    emp.ativo = True
    emp.assinatura_valida_ate = datetime.now(timezone.utc) - timedelta(days=2)
    db.commit()

    u = make_usuario(db, emp)
    u.token_versao = 1
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    r = http_client.get(f"{_API_V1}/orcamentos/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Cenário 5: trial sem data de validade não bloqueia
# ─────────────────────────────────────────────────────────────────────────────

def test_trial_sem_data_nao_bloqueia(http_client, db):
    emp = make_empresa(db, plano="trial")
    emp.ativo = True
    emp.assinatura_valida_ate = None
    db.commit()

    u = make_usuario(db, emp)
    u.token_versao = 1
    db.commit()

    token = criar_token({"sub": str(u.id), "v": 1})
    r = http_client.get(f"{_API_V1}/orcamentos/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
