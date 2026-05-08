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
from decimal import Decimal

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

    empresa.notaas_api_key = api_key
    db.flush()
    logger.info("API key Notaas criada para empresa_id=%s (prefix=%s)", empresa.id, data.get("keyPrefix"))
    return api_key


async def onboarding_completo(
    db: Session,
    empresa: Empresa,
    cert_bytes: bytes,
    cert_password: str,
) -> dict:
    """Executa o onboarding completo em um único passo:
    1. Cria/obtém projeto
    2. Faz upload do certificado
    3. Cria API key e salva na empresa

    Retorna dict com project_id, cert_info e api_key_prefix.
    """
    project_id = await criar_ou_obter_projeto(db, empresa)
    cert_info = await upload_certificado(project_id, cert_bytes, cert_password)

    # Sempre cria nova API key no onboarding (a anterior pode ter sido perdida)
    api_key = await criar_api_key(db, empresa, project_id)

    db.commit()
    return {
        "project_id": project_id,
        "cert_valido_ate": cert_info.get("validUntil"),
        "cert_dias_restantes": cert_info.get("daysUntilExpiration"),
        "api_key_prefix": api_key[:12] + "...",  # nunca retornar chave completa ao frontend
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
