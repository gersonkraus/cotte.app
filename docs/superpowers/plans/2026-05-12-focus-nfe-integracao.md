# Focus NFe — Migração Notaas → Focus NFe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir completamente a integração com a API Notaas pela API Focus NFe para emissão de NF-e, NFC-e e NFS-e no COTTE.

**Architecture:** Token único `FOCUS_TOKEN` no `.env` do COTTE para todas as empresas; multitenancy via `ref = {cnpj}-{nota_id}` por nota. Emissão assíncrona via webhook (principal) + polling como fallback. Sem onboarding programático por empresa.

**Tech Stack:** FastAPI, SQLAlchemy, httpx, Alembic, pytest, Focus NFe API (Basic Auth)

---

## Mapa de Arquivos

| Arquivo | Ação |
|---|---|
| `app/core/config.py` | Modificar: trocar `NOTAAS_*` por `FOCUS_TOKEN` + `FOCUS_AMBIENTE` |
| `app/services/nfe_service.py` | Modificar: reescrever client, emitir_nota, cancelar_nota, webhook utils |
| `app/services/nfe_org_service.py` | **Deletar** |
| `app/models/models.py` | Modificar: remover campos `notaas_*`, adicionar `focus_ref`, `denegada` |
| `app/schemas/schemas.py` | Modificar: `ConfiguracaoFiscalEmpresa` e `NotaFiscalOut` |
| `app/routers/notas_fiscais.py` | Modificar: renomear rotas, reescrever webhook, remover nfe_org_service |
| `alembic/versions/z032_focus_nfe_migration.py` | Criar: migration Alembic |
| `tests/test_nfe_service.py` | Modificar: mocks e imports atualizados |
| `tests/test_nfe_webhook.py` | Modificar: handler Focus |
| `tests/test_nfe_router.py` | Modificar: rotas renomeadas |

---

## Task 1: Configuração e Client HTTP Focus

**Files:**
- Modify: `app/core/config.py:134-135`
- Modify: `app/services/nfe_service.py:1-42`
- Test: `tests/test_nfe_service.py`

- [ ] **Step 1: Escrever testes que falham para _gerar_ref() e nova config**

Adicione no início de `tests/test_nfe_service.py` (após os imports existentes):

```python
from app.services.nfe_service import _gerar_ref

def test_gerar_ref_formata_cnpj_sem_mascara():
    emp = SimpleNamespace(cnpj="12.345.678/0001-90")
    assert _gerar_ref(emp, 42) == "12345678000190-42"

def test_gerar_ref_cnpj_sem_mascara():
    emp = SimpleNamespace(cnpj="12345678000190")
    assert _gerar_ref(emp, 1) == "12345678000190-1"

def test_gerar_ref_cnpj_vazio_levanta_value_error():
    emp = SimpleNamespace(cnpj="")
    with pytest.raises(ValueError, match="CNPJ"):
        _gerar_ref(emp, 1)

def test_gerar_ref_cnpj_none_levanta_value_error():
    emp = SimpleNamespace(cnpj=None)
    with pytest.raises(ValueError, match="CNPJ"):
        _gerar_ref(emp, 1)
```

- [ ] **Step 2: Rodar testes para confirmar que falham**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_gerar_ref_formata_cnpj_sem_mascara -v
```

Esperado: `FAILED` com `ImportError: cannot import name '_gerar_ref'`

- [ ] **Step 3: Atualizar config.py — substituir NOTAAS por FOCUS**

Em `app/core/config.py`, substituir as linhas:
```python
    NOTAAS_ORG_TOKEN: str = ""
    NOTAAS_CRYPTO_SECRET: str = ""
```

Por:
```python
    FOCUS_TOKEN: str = ""
    FOCUS_AMBIENTE: str = "homologacao"  # "homologacao" | "producao"
```

- [ ] **Step 4: Reescrever o topo de nfe_service.py (linhas 1-42)**

Substituir as linhas 1–42 inteiras por:

```python
"""
nfe_service.py — Integração com API Focus NFe para emissão de NF-e/NFC-e/NFS-e.
URLs: https://api.focusnfe.com.br (prod) | https://homologacao.focusnfe.com.br (homolog)
Auth: HTTP Basic Auth — token como username, senha vazia (token único COTTE no .env)
Multitenancy: ref = "{cnpj_emitente}-{nota_id}" por nota
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Empresa, NotaFiscal, Orcamento, Cliente
from app.core.database import SessionLocal
from app.services.fiscal_ai_service import sugerir_dados_fiscais

logger = logging.getLogger(__name__)

POLLING_INTERVAL = 3
POLLING_MAX_ATTEMPTS = 20


def _focus_base_url() -> str:
    if settings.FOCUS_AMBIENTE == "producao":
        return "https://api.focusnfe.com.br"
    return "https://homologacao.focusnfe.com.br"


def _get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_focus_base_url(),
        auth=(settings.FOCUS_TOKEN, ""),
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )


def _gerar_ref(empresa: Empresa, nota_id: int) -> str:
    cnpj = re.sub(r"\D", "", empresa.cnpj or "")
    if not cnpj:
        raise ValueError("Empresa sem CNPJ — impossível gerar ref Focus")
    return f"{cnpj}-{nota_id}"


def _path_focus(tipo: str, ref: str) -> str:
    """Caminho relativo para consulta/cancelamento na Focus por tipo de nota."""
    t = (tipo or "").lower()
    if t == "nfce":
        return f"/v2/nfce/{ref}"
    if t == "nfse":
        return f"/v2/nfse/{ref}"
    return f"/v2/nfe/{ref}"


def _endpoint_emissao_focus(tipo: str) -> str:
    t = (tipo or "").lower()
    if t == "nfce":
        return "/v2/nfce"
    if t == "nfse":
        return "/v2/nfse"
    return "/v2/nfe"
```

- [ ] **Step 5: Rodar os testes para confirmar que passam**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_gerar_ref_formata_cnpj_sem_mascara tests/test_nfe_service.py::test_gerar_ref_cnpj_sem_mascara tests/test_nfe_service.py::test_gerar_ref_cnpj_vazio_levanta_value_error tests/test_nfe_service.py::test_gerar_ref_cnpj_none_levanta_value_error -v
```

Esperado: 4 × PASSED

- [ ] **Step 6: Commit**

```bash
git add app/core/config.py app/services/nfe_service.py tests/test_nfe_service.py
git commit -m "feat(nfe): config e client HTTP Focus NFe"
```

---

## Task 2: Migration Alembic + Atualizar Models

**Files:**
- Create: `alembic/versions/z032_focus_nfe_migration.py`
- Modify: `app/models/models.py:365-369` (Empresa) e `app/models/models.py:975-976` (NotaFiscal)

- [ ] **Step 1: Criar migration Alembic**

Crie o arquivo `alembic/versions/z032_focus_nfe_migration.py`:

```python
"""Migração Notaas → Focus NFe: remove colunas notaas_*, adiciona focus_ref e denegada

Revision ID: z032
Revises: z_merge_p_and_e_heads
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "z032"
down_revision = "z_merge_p_and_e_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remover colunas Notaas da tabela empresas
    op.drop_column("empresas", "notaas_project_id")
    op.drop_column("empresas", "notaas_api_key")
    op.drop_column("empresas", "notaas_ambiente")
    op.drop_column("empresas", "notaas_webhook_secret")

    # Remover colunas Notaas da tabela notas_fiscais
    op.drop_column("notas_fiscais", "notaas_invoice_id")
    op.drop_column("notas_fiscais", "notaas_delivery_id")

    # Adicionar novos campos Focus
    op.add_column("notas_fiscais", sa.Column("focus_ref", sa.String(120), nullable=True))
    op.add_column("notas_fiscais", sa.Column("denegada", sa.Boolean(), nullable=True, server_default=sa.false()))

    # Índice para busca por focus_ref
    op.create_index("ix_notas_fiscais_focus_ref", "notas_fiscais", ["focus_ref"])


def downgrade() -> None:
    op.drop_index("ix_notas_fiscais_focus_ref", "notas_fiscais")
    op.drop_column("notas_fiscais", "denegada")
    op.drop_column("notas_fiscais", "focus_ref")
    op.add_column("notas_fiscais", sa.Column("notaas_delivery_id", sa.String(100), nullable=True))
    op.add_column("notas_fiscais", sa.Column("notaas_invoice_id", sa.String(100), nullable=True))
    op.add_column("empresas", sa.Column("notaas_webhook_secret", sa.String(200), nullable=True))
    op.add_column("empresas", sa.Column("notaas_ambiente", sa.String(20), server_default="homologacao"))
    op.add_column("empresas", sa.Column("notaas_api_key", sa.String(200), nullable=True))
    op.add_column("empresas", sa.Column("notaas_project_id", sa.String(100), nullable=True))
```

> **Nota:** Verifique o `down_revision` consultando `alembic/versions/z_merge_p_and_e_heads.py` para confirmar o revision ID correto. Se diferir, ajuste o valor.

- [ ] **Step 2: Atualizar models.py — Empresa (linhas 365-369)**

Substituir o bloco `# Configuração Notaas por empresa` na classe `Empresa`:

```python
    # Configuração NF-e por empresa (ambiente preferido; token é global no .env)
    nfe_ambiente = Column(String(20), default="homologacao")  # "homologacao" | "producao"
```

- [ ] **Step 3: Atualizar models.py — NotaFiscal (linhas 975-976)**

Substituir:
```python
    notaas_invoice_id = Column(String(100), nullable=True)
    notaas_delivery_id = Column(String(100), nullable=True)
```

Por:
```python
    focus_ref = Column(String(120), nullable=True, index=True)
    denegada = Column(Boolean, default=False)
```

- [ ] **Step 4: Rodar a migration**

```bash
cd /home/gk/Projeto-izi/sistema
alembic upgrade head
```

Esperado: migration z032 executada sem erros.

- [ ] **Step 5: Verificar que as colunas foram aplicadas**

```bash
cd /home/gk/Projeto-izi/sistema
python -c "
from app.core.database import SessionLocal
from app.models.models import NotaFiscal, Empresa
db = SessionLocal()
nf = db.query(NotaFiscal).first()
print('focus_ref ok:', hasattr(nf, 'focus_ref') if nf else 'sem registros — ok')
db.close()
"
```

Esperado: `focus_ref ok: True` ou `focus_ref ok: sem registros — ok`

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/z032_focus_nfe_migration.py app/models/models.py
git commit -m "feat(nfe): migration Alembic e models Focus NFe"
```

---

## Task 3: Reescrever emitir_nota() para Focus

**Files:**
- Modify: `app/services/nfe_service.py` (função `emitir_nota` e `emitir_nota_background`)
- Test: `tests/test_nfe_service.py`

- [ ] **Step 1: Escrever testes que falham para emitir_nota com Focus**

Adicione em `tests/test_nfe_service.py`:

```python
@pytest.mark.asyncio
async def test_emitir_nota_focus_sucesso(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Empresa Focus", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="pendente")
    db.add(nota)
    db.flush()

    payload_nfe = {"natureza_operacao": "Venda", "itens": []}

    resp_emissao = httpx.Response(202, json={})
    resp_status = httpx.Response(200, json={
        "status": "autorizado",
        "chave_nfe": "35240512345678000195550010000000011000000011",
        "numero": "1",
        "protocolo": "135240000000001",
        "caminho_xml_nota_fiscal": "/arquivos/nfe/xml/nota.xml",
        "caminho_danfe": "/arquivos/nfe/danfe/nota.pdf",
    })

    with patch("app.services.nfe_service._get_client") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_emissao)
        mock_client.get = AsyncMock(return_value=resp_status)
        mock_client_ctx.return_value = mock_client

        resultado = await nfe_service.emitir_nota(db, nota, emp, payload_nfe)

    assert resultado.status == "emitida"
    assert resultado.focus_ref == f"12345678000195-{nota.id}"
    assert resultado.chave_acesso == "35240512345678000195550010000000011000000011"
    assert resultado.numero == "1"
    assert resultado.protocolo == "135240000000001"
    assert resultado.xml_url == "/arquivos/nfe/xml/nota.xml"
    assert resultado.danfe_url == "/arquivos/nfe/danfe/nota.pdf"


@pytest.mark.asyncio
async def test_emitir_nota_focus_erro_autorizacao(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Empresa Erro", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="pendente")
    db.add(nota)
    db.flush()

    resp_emissao = httpx.Response(202, json={})
    resp_status = httpx.Response(200, json={
        "status": "erro_autorizacao",
        "erros": [{"codigo": "539", "mensagem": "Rejeicao: CNPJ do emitente invalido"}],
    })

    with patch("app.services.nfe_service._get_client") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_emissao)
        mock_client.get = AsyncMock(return_value=resp_status)
        mock_client_ctx.return_value = mock_client

        resultado = await nfe_service.emitir_nota(db, nota, emp, payload_nfe := {})

    assert resultado.status == "erro"
    assert resultado.denegada is False


@pytest.mark.asyncio
async def test_emitir_nota_focus_denegado(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Empresa Denegada", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="pendente")
    db.add(nota)
    db.flush()

    resp_emissao = httpx.Response(202, json={})
    resp_status = httpx.Response(200, json={
        "status": "denegado",
        "erros": [{"codigo": "301", "mensagem": "CNPJ emitente irregular na Receita"}],
    })

    with patch("app.services.nfe_service._get_client") as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_emissao)
        mock_client.get = AsyncMock(return_value=resp_status)
        mock_client_ctx.return_value = mock_client

        resultado = await nfe_service.emitir_nota(db, nota, emp, {})

    assert resultado.status == "erro"
    assert resultado.denegada is True
```

- [ ] **Step 2: Rodar testes para confirmar que falham**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_emitir_nota_focus_sucesso -v
```

Esperado: `FAILED` — `emitir_nota` ainda usa Notaas

- [ ] **Step 3: Adicionar helper _atualizar_nota_com_status_focus() em nfe_service.py**

Adicione esta função antes de `emitir_nota`:

```python
def _atualizar_nota_com_status_focus(nota_fiscal: NotaFiscal, status_data: dict) -> None:
    """Aplica campos da resposta Focus no objeto NotaFiscal conforme status."""
    status = status_data.get("status", "")

    if status == "autorizado":
        nota_fiscal.status = "emitida"
        nota_fiscal.chave_acesso = (
            status_data.get("chave_nfe")
            or status_data.get("chave_nfse")
            or status_data.get("chave_cte")
        )
        nota_fiscal.numero = str(status_data.get("numero") or "")
        nota_fiscal.protocolo = str(status_data.get("protocolo") or "")
        nota_fiscal.xml_url = status_data.get("caminho_xml_nota_fiscal")
        nota_fiscal.danfe_url = status_data.get("caminho_danfe")
        nota_fiscal.emitida_em = nota_fiscal.emitida_em or datetime.utcnow()

    elif status == "denegado":
        nota_fiscal.status = "erro"
        nota_fiscal.denegada = True
        erros = status_data.get("erros") or []
        primeiro = erros[0] if erros else {}
        nota_fiscal.erro_codigo = str(primeiro.get("codigo") or "DENEGADO")
        nota_fiscal.erro_mensagem = primeiro.get("mensagem") or "Nota denegada pela SEFAZ"

    elif status in ("erro_autorizacao", "erro"):
        nota_fiscal.status = "erro"
        nota_fiscal.denegada = False
        erros = status_data.get("erros") or []
        primeiro = erros[0] if erros else {}
        nota_fiscal.erro_codigo = str(primeiro.get("codigo") or "ERRO_AUTORIZACAO")
        nota_fiscal.erro_mensagem = primeiro.get("mensagem") or "Erro na autorização SEFAZ"

    elif status == "cancelado":
        nota_fiscal.status = "cancelada"
        nota_fiscal.cancelada_em = datetime.utcnow()
```

- [ ] **Step 4: Reescrever emitir_nota() em nfe_service.py**

Substitua a função `emitir_nota` inteira (era linhas 601-699):

```python
async def emitir_nota(
    db: Session,
    nota_fiscal: NotaFiscal,
    empresa: Empresa,
    payload: dict,
) -> NotaFiscal:
    """Envia payload para API Focus NFe e aguarda resultado via polling."""
    ref = nota_fiscal.focus_ref or _gerar_ref(empresa, nota_fiscal.id)
    endpoint = _endpoint_emissao_focus(nota_fiscal.tipo)

    nota_fiscal.status = "processando"
    nota_fiscal.focus_ref = ref
    nota_fiscal.payload_enviado = payload
    db.commit()

    async with _get_client() as client:
        try:
            resp = await client.post(f"{endpoint}?ref={ref}", json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = "AUTH_ERROR"
                nota_fiscal.erro_mensagem = "Token Focus inválido — verifique FOCUS_TOKEN no ambiente"
                logger.critical("FOCUS_TOKEN inválido — revisar configuração (empresa_id=%s)", empresa.id)
                db.commit()
                return nota_fiscal
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = str(e.response.status_code)
            nota_fiscal.erro_mensagem = e.response.text[:500]
            db.commit()
            return nota_fiscal
        except httpx.RequestError as e:
            nota_fiscal.status = "erro"
            nota_fiscal.erro_codigo = "REQUEST_ERROR"
            nota_fiscal.erro_mensagem = str(e)[:500]
            db.commit()
            return nota_fiscal

        path = _path_focus(nota_fiscal.tipo, ref)
        for _ in range(POLLING_MAX_ATTEMPTS):
            await asyncio.sleep(POLLING_INTERVAL)
            try:
                status_resp = await client.get(path)
            except httpx.RequestError:
                continue

            if status_resp.status_code == 404:
                continue  # Focus pode retornar 404 enquanto processa
            if status_resp.status_code >= 400:
                nota_fiscal.status = "erro"
                nota_fiscal.erro_codigo = str(status_resp.status_code)
                nota_fiscal.erro_mensagem = status_resp.text[:200]
                db.commit()
                return nota_fiscal

            status_data = status_resp.json()
            current = status_data.get("status", "")

            if current == "processando_autorizacao":
                continue

            _atualizar_nota_com_status_focus(nota_fiscal, status_data)
            db.commit()
            return nota_fiscal

    nota_fiscal.status = "erro"
    nota_fiscal.erro_mensagem = "Timeout aguardando processamento da SEFAZ"
    db.commit()
    return nota_fiscal
```

- [ ] **Step 5: Rodar os testes para confirmar que passam**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_emitir_nota_focus_sucesso tests/test_nfe_service.py::test_emitir_nota_focus_erro_autorizacao tests/test_nfe_service.py::test_emitir_nota_focus_denegado -v
```

Esperado: 3 × PASSED

- [ ] **Step 6: Commit**

```bash
git add app/services/nfe_service.py tests/test_nfe_service.py
git commit -m "feat(nfe): emitir_nota() reescrito para Focus NFe"
```

---

## Task 4: Reescrever cancelar_nota() para Focus

**Files:**
- Modify: `app/services/nfe_service.py` (funções `cancelar_nota` e `verificar_assinatura_webhook`)
- Test: `tests/test_nfe_service.py`

- [ ] **Step 1: Escrever testes que falham**

Adicione em `tests/test_nfe_service.py`:

```python
@pytest.mark.asyncio
async def test_cancelar_nota_focus_sucesso(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp Cancel", cnpj="12345678000195")
    nota = NotaFiscal(
        empresa_id=emp.id, tipo="nfe", status="emitida",
        focus_ref="12345678000195-99",
    )
    db.add(nota)
    db.flush()

    resp_cancel = httpx.Response(200, json={"status": "cancelado"})

    with patch("app.services.nfe_service._get_client") as mock_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.delete = AsyncMock(return_value=resp_cancel)
        mock_ctx.return_value = mock_client

        resultado = await nfe_service.cancelar_nota(db, nota, emp, "Erro no preço informado")

    assert resultado.status == "cancelada"
    assert resultado.cancelamento_motivo == "Erro no preço informado"


@pytest.mark.asyncio
async def test_cancelar_nota_focus_sem_ref_levanta_erro(db):
    from app.models.models import NotaFiscal
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp SemRef", cnpj="12345678000195")
    nota = NotaFiscal(empresa_id=emp.id, tipo="nfe", status="emitida", focus_ref=None)
    db.add(nota)
    db.flush()

    with pytest.raises(ValueError, match="focus_ref"):
        await nfe_service.cancelar_nota(db, nota, emp, "motivo qualquer")


def test_verificar_token_webhook_focus_valido():
    import base64
    from app.services.nfe_service import verificar_token_webhook_focus
    token = "meu_token_focus"
    encoded = base64.b64encode(f"{token}:".encode()).decode()
    assert verificar_token_webhook_focus(f"Basic {encoded}", token) is True


def test_verificar_token_webhook_focus_invalido():
    import base64
    from app.services.nfe_service import verificar_token_webhook_focus
    encoded = base64.b64encode(b"token_errado:").decode()
    assert verificar_token_webhook_focus(f"Basic {encoded}", "token_correto") is False


def test_verificar_token_webhook_focus_header_ausente():
    from app.services.nfe_service import verificar_token_webhook_focus
    assert verificar_token_webhook_focus("", "qualquer") is False
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_cancelar_nota_focus_sucesso -v
```

Esperado: `FAILED`

- [ ] **Step 3: Reescrever cancelar_nota() em nfe_service.py**

Substituir a função `cancelar_nota` inteira (era linhas 702-733):

```python
async def cancelar_nota(
    db: Session,
    nota_fiscal: NotaFiscal,
    empresa: Empresa,
    motivo: str,
) -> NotaFiscal:
    """Cancela NF emitida via Focus: DELETE /v2/{tipo}/{ref}."""
    ref = nota_fiscal.focus_ref
    if not ref:
        raise ValueError("Nota sem focus_ref para cancelar")

    path = _path_focus(nota_fiscal.tipo, ref)

    async with _get_client() as client:
        try:
            resp = await client.delete(path, json={"justificativa": motivo})
            if resp.status_code not in (200, 201, 204):
                raise httpx.HTTPStatusError(
                    f"Cancelamento falhou: {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
        except httpx.RequestError as e:
            raise ValueError(f"Erro de conexão ao cancelar nota: {e}") from e

    nota_fiscal.status = "cancelada"
    nota_fiscal.cancelada_em = datetime.utcnow()
    nota_fiscal.cancelamento_motivo = motivo
    db.commit()
    return nota_fiscal
```

- [ ] **Step 4: Substituir verificar_assinatura_webhook por verificar_token_webhook_focus()**

Remover a função `verificar_assinatura_webhook` (era linhas 736-744) e adicionar:

```python
def verificar_token_webhook_focus(authorization_header: str, expected_token: str) -> bool:
    """Valida o header Authorization: Basic {base64(token:)} enviado pela Focus."""
    import base64
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(authorization_header[6:]).decode()
        token = decoded.split(":")[0]
        return hmac.compare_digest(token, expected_token)
    except Exception:
        return False
```

> **Nota:** `import hmac` e `import base64` já estão no topo do arquivo após a Task 1.

- [ ] **Step 5: Rodar os testes**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_cancelar_nota_focus_sucesso tests/test_nfe_service.py::test_cancelar_nota_focus_sem_ref_levanta_erro tests/test_nfe_service.py::test_verificar_token_webhook_focus_valido tests/test_nfe_service.py::test_verificar_token_webhook_focus_invalido tests/test_nfe_service.py::test_verificar_token_webhook_focus_header_ausente -v
```

Esperado: 5 × PASSED

- [ ] **Step 6: Commit**

```bash
git add app/services/nfe_service.py tests/test_nfe_service.py
git commit -m "feat(nfe): cancelar_nota() e webhook auth reescritos para Focus"
```

---

## Task 5: Atualizar Schemas

**Files:**
- Modify: `app/schemas/schemas.py:2069-2146`

- [ ] **Step 1: Atualizar NotaFiscalOut — substituir notaas_invoice_id por focus_ref e adicionar denegada**

Substituir o campo `notaas_invoice_id: Optional[str] = None` na classe `NotaFiscalOut`:

```python
class NotaFiscalOut(BaseModel):
    id: int
    tipo: str
    modelo: Optional[int] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    status: str
    natureza_operacao: Optional[str] = None
    chave_acesso: Optional[str] = None
    protocolo: Optional[str] = None
    xml_url: Optional[str] = None
    danfe_url: Optional[str] = None
    qr_code: Optional[str] = None
    erro_codigo: Optional[str] = None
    erro_mensagem: Optional[str] = None
    criado_em: datetime
    emitida_em: Optional[datetime] = None
    cancelada_em: Optional[datetime] = None
    orcamento_id: Optional[int] = None
    focus_ref: Optional[str] = None
    denegada: Optional[bool] = False

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Atualizar ConfiguracaoFiscalEmpresa — remover campos notaas_*, adicionar nfe_ambiente**

Substituir a classe `ConfiguracaoFiscalEmpresa` inteira:

```python
class ConfiguracaoFiscalEmpresa(BaseModel):
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    regime_tributario: Optional[str] = None
    crt: Optional[int] = None
    endereco_logradouro: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_uf: Optional[str] = None
    endereco_cep: Optional[str] = None
    endereco_codigo_municipio_ibge: Optional[str] = None
    nfe_ambiente: Optional[str] = "homologacao"  # "homologacao" | "producao"

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Verificar que o servidor sobe sem erros de importação**

```bash
cd /home/gk/Projeto-izi/sistema
python -c "from app.schemas.schemas import ConfiguracaoFiscalEmpresa, NotaFiscalOut; print('schemas ok')"
```

Esperado: `schemas ok`

- [ ] **Step 4: Commit**

```bash
git add app/schemas/schemas.py
git commit -m "feat(nfe): schemas atualizados para Focus NFe"
```

---

## Task 6: Reescrever Webhook Handler Focus

**Files:**
- Modify: `app/routers/notas_fiscais.py`
- Test: `tests/test_nfe_webhook.py`

- [ ] **Step 1: Escrever testes que falham para o novo webhook**

Substitua o conteúdo de `tests/test_nfe_webhook.py` por:

```python
import base64
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

FOCUS_TOKEN = "token_de_teste"
WEBHOOK_URL = "/notas-fiscais/webhook/focus"


def _auth_header(token: str = FOCUS_TOKEN) -> dict:
    encoded = base64.b64encode(f"{token}:".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def test_webhook_focus_autorizado_atualiza_nota(db_session):
    """Webhook 'autorizado' da Focus atualiza NotaFiscal no DB."""
    from app.models.models import NotaFiscal, Empresa
    nota = db_session.query(NotaFiscal).filter(
        NotaFiscal.focus_ref != None
    ).first()
    if not nota:
        pytest.skip("Sem nota com focus_ref para testar")

    payload = {
        "ref": nota.focus_ref,
        "status": "autorizado",
        "chave_nfe": "35240512345678000195550010000000011000000011",
        "numero": "100",
        "protocolo": "135240000000100",
        "caminho_xml_nota_fiscal": "/xml/nota.xml",
        "caminho_danfe": "/danfe/nota.pdf",
    }

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.FOCUS_TOKEN = FOCUS_TOKEN
        response = client.post(WEBHOOK_URL, json=payload, headers=_auth_header())

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_webhook_focus_token_invalido_retorna_401():
    payload = {"ref": "qualquer", "status": "autorizado"}
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.FOCUS_TOKEN = "token_correto"
        response = client.post(WEBHOOK_URL, json=payload, headers=_auth_header("token_errado"))
    assert response.status_code == 401


def test_webhook_focus_sem_auth_retorna_401():
    payload = {"ref": "qualquer", "status": "autorizado"}
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.FOCUS_TOKEN = "qualquer_token"
        response = client.post(WEBHOOK_URL, json=payload)
    assert response.status_code == 401


def test_webhook_focus_ref_desconhecida_retorna_ok():
    """Ref inexistente: retorna 200 silenciosamente (idempotência)."""
    payload = {"ref": "00000000000000-99999", "status": "autorizado"}
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.FOCUS_TOKEN = FOCUS_TOKEN
        response = client.post(WEBHOOK_URL, json=payload, headers=_auth_header())
    assert response.status_code == 200
    assert response.json()["ok"] is True
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_webhook.py::test_webhook_focus_token_invalido_retorna_401 -v
```

Esperado: `FAILED` — rota `/webhook/focus` não existe

- [ ] **Step 3: Substituir o handler do webhook em notas_fiscais.py**

Localizar a rota `@router.post("/webhook/notaas")` (em torno da linha 371) e substituir toda a função até o fim do handler por:

```python
@router.post("/webhook/focus")
async def receber_webhook_focus(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str = Header(None),
):
    """Recebe notificações de status de NF-e, NFC-e e NFS-e da Focus NFe."""
    if not nfe_service.verificar_token_webhook_focus(authorization or "", settings.FOCUS_TOKEN):
        raise HTTPException(401, "Autenticação do webhook Focus inválida")

    payload = await request.json()
    ref = payload.get("ref", "")
    if not ref:
        return {"ok": True}

    nota = db.query(NotaFiscal).filter(NotaFiscal.focus_ref == ref).first()
    if not nota:
        return {"ok": True}

    nfe_service._atualizar_nota_com_status_focus(nota, payload)

    if nota.orcamento_id and nota.status in ("emitida", "cancelada", "erro"):
        descricao = {
            "emitida": f"Nota Fiscal {nota.tipo.upper()} {nota.numero or ''} emitida (via webhook Focus)",
            "cancelada": f"Nota Fiscal {nota.tipo.upper()} {nota.numero or ''} cancelada",
            "erro": f"Erro na emissão da Nota Fiscal: {nota.erro_mensagem or 'desconhecido'}",
        }.get(nota.status, "")
        if descricao:
            historico = HistoricoEdicao(
                orcamento_id=nota.orcamento_id,
                editado_por_id=None,
                descricao=descricao,
                tipo="nota_fiscal",
            )
            db.add(historico)

    db.commit()
    return {"ok": True}
```

> **Nota:** Certifique-se de que `settings` está importado no router. Se não estiver, adicione `from app.core.config import settings` no bloco de imports.

- [ ] **Step 4: Rodar os testes de webhook**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_webhook.py -v
```

Esperado: todos os testes passam ou são skipados por ausência de dados

- [ ] **Step 5: Commit**

```bash
git add app/routers/notas_fiscais.py tests/test_nfe_webhook.py
git commit -m "feat(nfe): webhook /webhook/focus com autenticação Focus Basic Auth"
```

---

## Task 7: Renomear Rotas e Remover nfe_org_service

**Files:**
- Modify: `app/routers/notas_fiscais.py`

- [ ] **Step 1: Remover import de nfe_org_service do router**

Localizar a linha:
```python
from app.services import nfe_org_service
```
e removê-la (junto com qualquer `import httpx` que só era usado pelo org_service, se aplicável).

- [ ] **Step 2: Substituir /configurar-notaas por /configurar-focus**

Localizar a rota `@router.post("/configurar-notaas")` (~linha 291) e substituir toda a função por:

```python
@router.post("/configurar-focus")
def configurar_focus(
    dados: ConfiguracaoFiscalEmpresa,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
    _=Depends(exigir_permissao("configuracoes", "escrita")),
):
    """Salva o ambiente NF-e preferido da empresa (homologacao/producao)."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    empresa.nfe_ambiente = dados.nfe_ambiente or "homologacao"
    db.commit()

    return {
        "success": True,
        "message": "Configuração fiscal salva",
        "ambiente": empresa.nfe_ambiente,
        "token_configurado": bool(settings.FOCUS_TOKEN),
    }
```

- [ ] **Step 3: Substituir /status-notaas por /status-focus**

Localizar a rota `@router.get("/status-notaas")` (~linha 331) e substituir toda a função por:

```python
@router.get("/status-focus")
async def status_focus(
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Verifica conectividade com a API Focus NFe e retorna status de configuração."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    token_ok = bool(settings.FOCUS_TOKEN)
    conectado = False

    if token_ok:
        try:
            async with nfe_service._get_client() as client:
                r = await client.get("/v2/nfe/ref-ping-teste-cotte")
                conectado = r.status_code in (200, 404, 422)
        except Exception:
            conectado = False

    return {
        "configurado": token_ok,
        "conectado": conectado,
        "ambiente": settings.FOCUS_AMBIENTE,
        "nfe_ambiente_empresa": empresa.nfe_ambiente or "homologacao",
    }
```

- [ ] **Step 4: Atualizar salvar_configuracao_fiscal para usar nfe_ambiente**

Localizar a linha:
```python
    empresa.notaas_ambiente = dados.notaas_ambiente or "homologacao"
```
e substituir por:
```python
    empresa.nfe_ambiente = dados.nfe_ambiente or "homologacao"
```

Também remover as linhas que salvam `notaas_api_key` e `notaas_webhook_secret`:
```python
    if dados.notaas_api_key and dados.notaas_api_key != "***":
        empresa.notaas_api_key = dados.notaas_api_key
    if dados.notaas_webhook_secret:
        empresa.notaas_webhook_secret = dados.notaas_webhook_secret
```

E atualizar o bloco que expõe campos da empresa no `GET /configuracao` (função `obter_configuracao_fiscal`, ~linha 55):
- Remover campos: `notaas_project_id`, `notaas_api_key`, `notaas_ambiente`
- Adicionar: `nfe_ambiente=empresa.nfe_ambiente`

- [ ] **Step 5: Verificar que a aplicação sobe sem erros**

```bash
cd /home/gk/Projeto-izi/sistema
python -c "from app.routers.notas_fiscais import router; print('router ok')"
```

Esperado: `router ok`

- [ ] **Step 6: Commit**

```bash
git add app/routers/notas_fiscais.py
git commit -m "feat(nfe): rotas /configurar-focus e /status-focus, remove org_service"
```

---

## Task 8: Deletar nfe_org_service.py

**Files:**
- Delete: `app/services/nfe_org_service.py`

- [ ] **Step 1: Confirmar que nenhum outro arquivo importa nfe_org_service**

```bash
cd /home/gk/Projeto-izi/sistema
grep -r "nfe_org_service" --include="*.py" .
```

Esperado: nenhum resultado (se houver resultados além do próprio arquivo, corrija antes de deletar).

- [ ] **Step 2: Deletar o arquivo**

```bash
rm /home/gk/Projeto-izi/sistema/app/services/nfe_org_service.py
```

- [ ] **Step 3: Confirmar que os testes ainda passam**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py tests/test_nfe_webhook.py -v
```

Esperado: todos passam

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(nfe): remove nfe_org_service.py (Notaas)"
```

---

## Task 9: Limpar Testes Legados Notaas

**Files:**
- Modify: `tests/test_nfe_service.py`
- Modify: `tests/test_nfe_router.py`

- [ ] **Step 1: Atualizar imports em test_nfe_service.py**

Localizar o bloco de imports no topo e substituir:

```python
from app.services.nfe_service import (
    _limpar_doc,
    _limpar_cep,
    verificar_assinatura_webhook,       # <- remover
    _normalizar_cfop_para_string,
    _cfop_formato_notaas_valido,        # <- renomear para _cfop_formato_valido se necessário
    _cfop_padrao_por_uf_empresa_cliente,
    _quantidade_valores_item_nfe,
    sugerir_acao_campo_erro_notaas,     # <- remover ou manter (funções permanecem internas)
)
```

Por:

```python
from app.services.nfe_service import (
    _limpar_doc,
    _limpar_cep,
    verificar_token_webhook_focus,
    _normalizar_cfop_para_string,
    _cfop_formato_notaas_valido,
    _cfop_padrao_por_uf_empresa_cliente,
    _quantidade_valores_item_nfe,
    _gerar_ref,
)
```

- [ ] **Step 2: Remover/atualizar testes que referenciam Notaas**

Remover ou atualizar os testes:
- `test_verificar_assinatura_webhook_valid` → substituir por `test_verificar_token_webhook_focus_valido` (já adicionado no Task 4)
- `test_verificar_assinatura_webhook_invalid` → substituir
- `test_verificar_assinatura_webhook_with_prefix` → remover
- `test_path_polling_status_notaas_nfe_usa_prefixo_nfe` → substituir por teste de `_path_focus`
- `test_sugerir_acao_mensagem_erro_cstat_972_responsavel_tecnico` → o texto pode mencionar "Focus" ao invés de "Notaas" — ajustar a asserção se necessário

Adicione:

```python
def test_path_focus_nfe():
    from app.services.nfe_service import _path_focus
    assert _path_focus("nfe", "12345678000195-1") == "/v2/nfe/12345678000195-1"
    assert _path_focus("nfce", "12345678000195-2") == "/v2/nfce/12345678000195-2"
    assert _path_focus("nfse", "12345678000195-3") == "/v2/nfse/12345678000195-3"
```

- [ ] **Step 3: Atualizar test_nfe_router.py**

Localizar referências a `/configurar-notaas` e `/status-notaas` e substituir por `/configurar-focus` e `/status-focus`.

Localizar referências a campos `notaas_*` nas asserções e atualizar para `nfe_ambiente`, `focus_ref`.

- [ ] **Step 4: Rodar toda a suite de testes NF-e**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py tests/test_nfe_router.py tests/test_nfe_webhook.py -v
```

Esperado: todos os testes passam (sem `FAILED`)

- [ ] **Step 5: Commit**

```bash
git add tests/test_nfe_service.py tests/test_nfe_router.py tests/test_nfe_webhook.py
git commit -m "test(nfe): testes atualizados para Focus NFe"
```

---

## Task 10: Deploy — Configurar Railway

**Files:** nenhum arquivo local

- [ ] **Step 1: Acessar o painel Railway e adicionar variáveis de ambiente**

No painel do Railway (projeto COTTE), adicionar:

```
FOCUS_TOKEN=<token_fornecido_pela_focus>
FOCUS_AMBIENTE=homologacao
```

Remover as variáveis:
```
NOTAAS_ORG_TOKEN
NOTAAS_CRYPTO_SECRET
```

- [ ] **Step 2: Fazer redeploy e verificar startup**

Após configurar as variáveis, fazer redeploy e verificar no log que a aplicação sobe sem erros relacionados a NF-e.

- [ ] **Step 3: Testar conectividade via GET /status-focus**

Fazer um GET autenticado em `/notas-fiscais/status-focus` e verificar resposta:

```json
{
  "configurado": true,
  "conectado": true,
  "ambiente": "homologacao",
  "nfe_ambiente_empresa": "homologacao"
}
```

- [ ] **Step 4: Emitir uma NF-e de teste em homologação**

Usar o frontend do COTTE para emitir uma NF-e de teste em homologação e confirmar:
- Status muda para `processando` após clicar em emitir
- Status muda para `emitida` (via polling ou webhook) com `focus_ref` preenchido
- DANFE URL acessível

- [ ] **Step 5: Quando validado em homologação, alterar para produção**

No Railway, alterar:
```
FOCUS_AMBIENTE=producao
```
E redesployar.

---

## Resumo das Mudanças

| Componente | Antes | Depois |
|---|---|---|
| Auth | `x-api-key` por empresa | Basic Auth token único |
| Identificador nota | `notaas_invoice_id` | `focus_ref = {cnpj}-{nota_id}` |
| Onboarding | `nfe_org_service.onboarding_completo()` | Não existe — token no `.env` |
| Webhook rota | `POST /webhook/notaas` | `POST /webhook/focus` |
| Config rota | `POST /configurar-notaas` | `POST /configurar-focus` |
| Status rota | `GET /status-notaas` | `GET /status-focus` |
| Nota denegada | Não distinguia | `denegada=True` bloqueia reemissão |
| Arquivo removido | — | `nfe_org_service.py` deletado |
