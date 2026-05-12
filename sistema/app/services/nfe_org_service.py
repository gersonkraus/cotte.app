"""
nfe_org_service.py — Gerenciamento de projetos Notaas via Organization API.

Usa o token da organização (NOTAAS_ORG_TOKEN) para criar e gerenciar
projetos (empresas fiscais) de forma automatizada.

Fluxo completo de onboarding:
  1. criar_ou_obter_projeto(empresa) → cria o projeto se não existir
  2. upload_certificado(project_id, cert_bytes, password) → envia o A1
  3. criar_api_key(project_id) → gera ntaas_ key e salva em Empresa
"""

import logging
import os

import httpx
from sqlalchemy.orm import Session

from app.models.models import Empresa

logger = logging.getLogger(__name__)

NOTAAS_BASE_URL = "https://platform.notaas.com.br/api/v1"

# Mapeamento regime tributário interno → Notaas
_REGIME_MAP = {
    "simples_nacional": "3",
    "mei": "2",
    "lucro_presumido": "1",
    "lucro_real": "1",
}

# Mapeamento ambiente interno → Notaas
_AMBIENTE_MAP = {
    "producao": 1,
    "homologacao": 2,
}


def _get_org_token() -> str:
    token = os.environ.get("NOTAAS_ORG_TOKEN", "")
    if not token:
        raise ValueError("NOTAAS_ORG_TOKEN não configurado no ambiente")
    return token


def _get_org_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=NOTAAS_BASE_URL,
        headers={"x-api-key": _get_org_token(), "Content-Type": "application/json"},
        timeout=30.0,
    )


async def criar_ou_obter_projeto(db: Session, empresa: Empresa) -> str:
    """Cria (ou obtém existente) o projeto Notaas para esta empresa.

    Retorna o project_id UUID da Notaas e atualiza empresa.notaas_project_id.
    Lança ValueError se CNPJ inválido ou limite de plano atingido.
    """
    if empresa.notaas_project_id:
        return empresa.notaas_project_id

    if not empresa.cnpj:
        raise ValueError("CNPJ da empresa é obrigatório para criar projeto na Notaas")

    payload: dict = {
        "cnpj": "".join(filter(str.isdigit, empresa.cnpj)),
        "razaoSocial": empresa.nome,
        "name": empresa.nome,
    }

    if empresa.inscricao_municipal:
        payload["inscricaoMunicipal"] = empresa.inscricao_municipal
    if empresa.inscricao_estadual:
        payload["inscricaoEstadual"] = empresa.inscricao_estadual
    if empresa.regime_tributario:
        payload["regimeTributario"] = _REGIME_MAP.get(empresa.regime_tributario, "1")
    if empresa.endereco_codigo_municipio_ibge:
        payload["codigoMunicipio"] = empresa.endereco_codigo_municipio_ibge
    if empresa.notaas_ambiente:
        payload["ambiente"] = _AMBIENTE_MAP.get(empresa.notaas_ambiente, 2)

    if empresa.endereco_logradouro:
        payload["endereco"] = {
            "logradouro": empresa.endereco_logradouro or "",
            "numero": empresa.endereco_numero or "S/N",
            "complemento": empresa.endereco_complemento or "",
            "bairro": empresa.endereco_bairro or "",
            "cidade": empresa.endereco_cidade or "",
            "uf": empresa.endereco_uf or "",
            "cep": "".join(filter(str.isdigit, empresa.endereco_cep or "")),
        }

    async with _get_org_client() as client:
        resp = await client.post("/org/projects", json=payload)

        if resp.status_code == 409:
            # CNPJ já existe — pega o ID existente
            data = resp.json()
            project_id = data.get("existingProjectId")
            if not project_id:
                raise ValueError(f"CNPJ já cadastrado na Notaas mas sem existingProjectId: {resp.text}")
        elif resp.status_code == 201:
            data = resp.json()
            project_id = data.get("id")
        else:
            resp.raise_for_status()
            project_id = resp.json().get("id")

    if not project_id:
        raise ValueError("Notaas não retornou project_id")

    empresa.notaas_project_id = project_id
    db.flush()
    logger.info("Projeto Notaas criado/obtido: %s para empresa_id=%s", project_id, empresa.id)
    return project_id


async def upload_certificado(project_id: str, cert_bytes: bytes, password: str) -> dict:
    """Faz upload do certificado A1 (.pfx/.p12) para o projeto.

    Retorna o payload de resposta da Notaas com validUntil, daysUntilExpiration, etc.
    """
    org_token = _get_org_token()
    async with httpx.AsyncClient(
        base_url=NOTAAS_BASE_URL,
        headers={"x-api-key": org_token},
        timeout=30.0,
    ) as client:
        resp = await client.post(
            f"/org/projects/{project_id}/certificate",
            files={"file": ("certificado.pfx", cert_bytes, "application/x-pkcs12")},
            data={"password": password},
        )
        if resp.status_code not in (200, 201):
            raise ValueError(f"Erro ao enviar certificado: {resp.status_code} — {resp.text[:300]}")
        return resp.json()


async def criar_api_key(db: Session, empresa: Empresa, project_id: str) -> str:
    """Cria uma API key de projeto e salva em empresa.notaas_api_key.

    Retorna a chave gerada (ntaas_...).
    A chave é retornada pela Notaas apenas nesta chamada — armazenada aqui.
    """
    async with _get_org_client() as client:
        resp = await client.post(
            f"/org/projects/{project_id}/api-keys",
            json={"name": f"COTTE-empresa-{empresa.id}"},
        )
        resp.raise_for_status()
        data = resp.json()

    api_key = data.get("key")
    if not api_key:
        raise ValueError("Notaas não retornou api key")

    from app.core.crypto import encrypt_secret
    from app.core.config import settings
    empresa.notaas_api_key = encrypt_secret(api_key, crypto_secret=settings.NOTAAS_CRYPTO_SECRET) or api_key
    db.flush()
    logger.info("API key Notaas criada para empresa_id=%s (prefix=%s)", empresa.id, data.get("keyPrefix"))
    return api_key


async def registrar_webhook(db: Session, empresa: Empresa, api_key: str) -> dict:
    """Registra o webhook do COTTE na Notaas para este projeto.

    Usa a ntaas_ API key do projeto.
    Gera um secret único por empresa para validação HMAC-SHA256.
    Se o endpoint já existir, apenas renova o secret local.
    """
    import secrets as _secrets

    app_url = os.environ.get("APP_URL", "").rstrip("/")
    if not app_url:
        logger.warning("APP_URL não configurado — webhook não registrado na Notaas")
        return {"registered": False, "error": "APP_URL ausente"}

    webhook_url = f"{app_url}/api/v1/notas-fiscais/webhook/notaas"
    webhook_secret = _secrets.token_hex(32)

    _events = [
        "nfe.issued", "nfe.error", "nfe.cancelled",
        "nfce.issued", "nfce.error", "nfce.cancelled",
        "nfse.issued", "nfse.error", "nfse.cancelled",
    ]

    async with httpx.AsyncClient(
        base_url=NOTAAS_BASE_URL,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        timeout=30.0,
    ) as client:
        # Verifica se já existe um endpoint com esta URL para evitar duplicata
        # BUG2-FIX: se já existe, mantém o secret do banco (não gera um novo que
        # ficaria divergente do secret registrado na Notaas).
        list_resp = await client.get("/webhooks/endpoints")
        if list_resp.status_code == 200:
            body = list_resp.json()
            endpoints = body.get("data", body) if isinstance(body, dict) else body
            for ep in (endpoints if isinstance(endpoints, list) else []):
                if ep.get("url") == webhook_url:
                    logger.info("Webhook já registrado para empresa_id=%s, mantendo secret atual", empresa.id)
                    return {"webhook_url": webhook_url, "registered": True, "already_existed": True}

        resp = await client.post(
            "/webhooks/endpoints",
            json={"url": webhook_url, "events": _events, "secret": webhook_secret},
        )
        if resp.status_code not in (200, 201):
            # Não-crítico: onboarding continua mesmo sem webhook registrado
            logger.warning(
                "Falha ao registrar webhook Notaas empresa_id=%s: %s — %s",
                empresa.id, resp.status_code, resp.text[:200],
            )
            return {"registered": False, "error": f"{resp.status_code}: {resp.text[:100]}"}

    empresa.notaas_webhook_secret = webhook_secret
    db.flush()
    logger.info("Webhook Notaas registrado empresa_id=%s → %s", empresa.id, webhook_url)
    return {"webhook_url": webhook_url, "registered": True}


async def onboarding_completo(
    db: Session,
    empresa: Empresa,
    cert_bytes: bytes,
    cert_password: str,
) -> dict:
    """Executa o onboarding completo em um único passo:
    1. Cria/obtém projeto
    2. Faz upload do certificado
    3. Cria API key
    4. Registra webhook com secret único

    Retorna dict com project_id, cert_info, api_key_prefix e webhook_url.
    """
    project_id = await criar_ou_obter_projeto(db, empresa)
    cert_info = await upload_certificado(project_id, cert_bytes, cert_password)

    # Sempre cria nova API key no onboarding (a anterior pode ter sido perdida)
    api_key = await criar_api_key(db, empresa, project_id)

    webhook_info = await registrar_webhook(db, empresa, api_key)

    db.commit()
    return {
        "project_id": project_id,
        "cert_valido_ate": cert_info.get("validUntil"),
        "cert_dias_restantes": cert_info.get("daysUntilExpiration"),
        "api_key_prefix": api_key[:12] + "...",  # nunca retornar chave completa ao frontend
        "webhook_url": webhook_info.get("webhook_url"),
        "webhook_registrado": webhook_info.get("registered", False),
    }


async def verificar_status_projeto(project_id: str) -> dict:
    """Retorna dados do projeto incluindo hasCertificate e hasApiKey."""
    async with _get_org_client() as client:
        resp = await client.get(f"/org/projects/{project_id}")
        if resp.status_code == 404:
            return {"found": False}
        resp.raise_for_status()
        data = resp.json()
        return {
            "found": True,
            "active": data.get("active", False),
            "hasCertificate": data.get("hasCertificate", False),
            "hasApiKey": data.get("hasApiKey", False),
            "razaoSocial": data.get("razaoSocial"),
            "ambiente": data.get("ambiente"),
        }
