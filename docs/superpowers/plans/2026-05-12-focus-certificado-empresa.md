# Certificado Digital por Empresa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que cada empresa cliente do COTTE configure seu certificado digital A1 dentro do próprio painel, com registro automático e transparente na Focus NFe API.

**Architecture:** Nova função `registrar_empresa_focus()` em `nfe_service.py` chama `POST /v2/empresas` (ou `PUT` se já cadastrada) na Focus com o certificado em base64. Novo endpoint `POST /notas-fiscais/configurar-certificado` no router aceita o `.pfx` como upload. Campo `focus_certificado_configurado` na tabela `empresas` persiste o estado. Frontend restaura o formulário de upload de certificado removido na migração Notaas→Focus.

**Tech Stack:** FastAPI (UploadFile + Form), httpx (Basic Auth Focus), SQLAlchemy, Alembic, Vanilla JS

---

> ⚠️ **VERIFICAÇÃO OBRIGATÓRIA ANTES DE EXECUTAR:**
> Os campos da Focus NFe para o endpoint `/v2/empresas` precisam ser confirmados no painel da Focus (app.focusnfe.com.br → Documentação → Empresas) antes da Task 2. Os nomes usados neste plano são: `certificado_pfx` (base64), `senha_certificado`, `cnpj`, `nome`, `inscricao_estadual`, `regime_tributario`. Se diferir, ajuste na Task 2.

---

## Mapa de Arquivos

| Arquivo | Ação |
|---|---|
| `alembic/versions/z033_focus_certificado_empresa.py` | Criar: adiciona `focus_certificado_configurado` e `focus_certificado_validade` |
| `app/models/models.py` | Modificar: classe `Empresa` — 2 novos campos |
| `app/services/nfe_service.py` | Modificar: adicionar `registrar_empresa_focus()` |
| `app/routers/notas_fiscais.py` | Modificar: novo endpoint `POST /configurar-certificado`, atualizar `GET /status-focus` |
| `cotte-frontend/configuracoes.html` | Modificar: restaurar seção de certificado |
| `cotte-frontend/js/configuracoes.js` | Modificar: adicionar função `configurarCertificadoFocus()`, atualizar status bar |
| `tests/test_nfe_service.py` | Modificar: testes para `registrar_empresa_focus()` |

---

## Task 1: DB Migration + Model

**Files:**
- Create: `sistema/alembic/versions/z033_focus_certificado_empresa.py`
- Modify: `sistema/app/models/models.py`

- [ ] **Step 1: Criar a migration Alembic**

Crie `/home/gk/Projeto-izi/sistema/alembic/versions/z033_focus_certificado_empresa.py`:

```python
"""Adiciona focus_certificado_configurado e focus_certificado_validade a empresas

Revision ID: z033_focus_certificado_empresa
Revises: z032_focus_nfe_migration
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "z033_focus_certificado_empresa"
down_revision = "z032_focus_nfe_migration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("empresas", sa.Column(
        "focus_certificado_configurado",
        sa.Boolean(),
        nullable=True,
        server_default=sa.false(),
    ))
    op.add_column("empresas", sa.Column(
        "focus_certificado_validade",
        sa.DateTime(timezone=True),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column("empresas", "focus_certificado_validade")
    op.drop_column("empresas", "focus_certificado_configurado")
```

- [ ] **Step 2: Adicionar campos ao model Empresa**

Localize o bloco de configuração NF-e na classe `Empresa` em `app/models/models.py`:
```bash
grep -n "nfe_ambiente" /home/gk/Projeto-izi/sistema/app/models/models.py
```

Adicione após `nfe_ambiente`:
```python
    focus_certificado_configurado = Column(Boolean, default=False)
    focus_certificado_validade = Column(DateTime(timezone=True), nullable=True)
```

> `Boolean` e `DateTime` já importados no arquivo. Confirme: `grep "from sqlalchemy import\|Boolean\|DateTime" app/models/models.py | head -3`

- [ ] **Step 3: Rodar a migration**

```bash
cd /home/gk/Projeto-izi/sistema
alembic upgrade head 2>&1
```

Esperado: `Running upgrade z032_focus_nfe_migration -> z033_focus_certificado_empresa`

- [ ] **Step 4: Verificar**

```bash
cd /home/gk/Projeto-izi/sistema
python -c "
from app.models.models import Empresa
e = Empresa()
print('cert ok:', hasattr(e, 'focus_certificado_configurado'))
print('validade ok:', hasattr(e, 'focus_certificado_validade'))
"
```

Esperado: ambos `True`

- [ ] **Step 5: Commit**

```bash
cd /home/gk/Projeto-izi/sistema
git add alembic/versions/z033_focus_certificado_empresa.py app/models/models.py
git commit -m "feat(nfe): migration e model para certificado Focus por empresa"
```

---

## Task 2: Função registrar_empresa_focus() no nfe_service

**Files:**
- Modify: `sistema/app/services/nfe_service.py`
- Test: `sistema/tests/test_nfe_service.py`

> **ANTES DE IMPLEMENTAR:** Confirme os nomes dos campos da Focus NFe para `/v2/empresas` consultando https://focusnfe.com.br/doc/ ou o suporte Focus. Os campos usados aqui são os padrões conhecidos — ajuste se necessário.

- [ ] **Step 1: Escrever testes TDD que falham**

Adicione ao final de `tests/test_nfe_service.py`:

```python
@pytest.mark.asyncio
async def test_registrar_empresa_focus_sucesso(db):
    from app.models.models import Empresa
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp Cert", cnpj="12345678000195")
    cert_bytes = b"fake-pfx-content"
    senha = "senha123"

    resp_focus = httpx.Response(
        200,
        json={"id": "12345678000195", "status": "ativo"},
        request=httpx.Request("POST", "https://homologacao.focusnfe.com.br/v2/empresas"),
    )

    with patch("app.services.nfe_service._get_client") as mock_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=resp_focus)
        mock_ctx.return_value = mock_client

        resultado = await nfe_service.registrar_empresa_focus(emp, cert_bytes, senha)

    assert resultado["success"] is True
    assert emp.focus_certificado_configurado is True


@pytest.mark.asyncio
async def test_registrar_empresa_focus_atualiza_se_ja_existe(db):
    from app.models.models import Empresa
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp Cert Existe", cnpj="12345678000195")
    emp.focus_certificado_configurado = True
    cert_bytes = b"new-pfx-content"
    senha = "nova_senha"

    resp_focus = httpx.Response(
        200,
        json={"id": "12345678000195", "status": "ativo"},
        request=httpx.Request("PUT", "https://homologacao.focusnfe.com.br/v2/empresas/12345678000195"),
    )

    with patch("app.services.nfe_service._get_client") as mock_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.put = AsyncMock(return_value=resp_focus)
        mock_ctx.return_value = mock_client

        resultado = await nfe_service.registrar_empresa_focus(emp, cert_bytes, senha)

    assert resultado["success"] is True


@pytest.mark.asyncio
async def test_registrar_empresa_focus_cnpj_vazio_levanta_erro(db):
    from app.models.models import Empresa
    from tests.conftest import make_empresa

    emp = make_empresa(db, nome="Emp SemCNPJ", cnpj=None)

    with pytest.raises(ValueError, match="CNPJ"):
        await nfe_service.registrar_empresa_focus(emp, b"pfx", "senha")
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_registrar_empresa_focus_sucesso -v --tb=short 2>&1 | tail -5
```

Esperado: `FAILED` com `AttributeError: module ... has no attribute 'registrar_empresa_focus'`

- [ ] **Step 3: Implementar registrar_empresa_focus() em nfe_service.py**

Localize onde termina a função `emitir_nota_background` em `nfe_service.py`:
```bash
grep -n "def emitir_nota_background\|def cancelar_nota\|def registrar_empresa" /home/gk/Projeto-izi/sistema/app/services/nfe_service.py
```

Adicione a função ANTES de `cancelar_nota`:

```python
async def registrar_empresa_focus(
    empresa,
    cert_bytes: bytes,
    senha_certificado: str,
) -> dict:
    """Cadastra ou atualiza empresa (emissor) na Focus NFe com certificado A1.

    POST /v2/empresas quando for o primeiro cadastro.
    PUT  /v2/empresas/{cnpj} quando já estiver cadastrada (atualização de certificado).
    O certificado .pfx é enviado em base64.
    """
    import base64

    cnpj = re.sub(r"\D", "", empresa.cnpj or "")
    if not cnpj:
        raise ValueError("Empresa sem CNPJ — impossível registrar na Focus NFe")

    cert_b64 = base64.b64encode(cert_bytes).decode()

    # Monta payload com campos da empresa + certificado
    # ⚠️ Confirme os nomes de campo com a documentação Focus NFe /v2/empresas
    payload = {
        "cnpj": cnpj,
        "nome": empresa.nome or "",
        "email": getattr(empresa, "email", "") or "",
        "inscricao_estadual": empresa.inscricao_estadual or "",
        "regime_tributario": _regime_tributario_para_focus(empresa.regime_tributario),
        "certificado_pfx": cert_b64,
        "senha_certificado": senha_certificado,
    }

    ja_cadastrada = bool(empresa.focus_certificado_configurado)

    async with _get_client() as client:
        try:
            if ja_cadastrada:
                resp = await client.put(
                    f"/v2/empresas/{cnpj}",
                    json={"certificado_pfx": cert_b64, "senha_certificado": senha_certificado},
                )
            else:
                resp = await client.post("/v2/empresas", json=payload)

            if resp.status_code not in (200, 201):
                detalhe = resp.text[:300]
                return {"success": False, "erro": f"Focus retornou {resp.status_code}: {detalhe}"}

            data = resp.json()
        except httpx.RequestError as e:
            return {"success": False, "erro": f"Erro de conexão com a Focus NFe: {e}"}

    empresa.focus_certificado_configurado = True

    # Tenta extrair data de validade do certificado se a Focus retornar
    validade_raw = data.get("data_expiracao_certificado") or data.get("certificate_expires_at")
    if validade_raw:
        from datetime import datetime as _dt
        try:
            empresa.focus_certificado_validade = _dt.fromisoformat(validade_raw.replace("Z", "+00:00"))
        except Exception:
            pass

    return {"success": True, "data": data}


def _regime_tributario_para_focus(regime: str) -> int:
    """Converte regime tributário do COTTE para código numérico da Focus NFe.

    Focus NFe aceita:
      1 = Simples Nacional
      2 = Simples Nacional — excesso de receita
      3 = Regime Normal
    """
    if not regime:
        return 1
    r = regime.lower()
    if "simples" in r or "mei" in r:
        return 1
    return 3
```

- [ ] **Step 4: Rodar os testes**

```bash
cd /home/gk/Projeto-izi/sistema
python -m pytest tests/test_nfe_service.py::test_registrar_empresa_focus_sucesso tests/test_nfe_service.py::test_registrar_empresa_focus_atualiza_se_ja_existe tests/test_nfe_service.py::test_registrar_empresa_focus_cnpj_vazio_levanta_erro -v --tb=short 2>&1 | tail -10
```

Esperado: 3 × PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/gk/Projeto-izi/sistema
git add app/services/nfe_service.py tests/test_nfe_service.py
git commit -m "feat(nfe): registrar_empresa_focus() — cadastro de certificado A1 na Focus"
```

---

## Task 3: Endpoint POST /configurar-certificado no Router

**Files:**
- Modify: `sistema/app/routers/notas_fiscais.py`

- [ ] **Step 1: Adicionar endpoint ao router**

Localize a rota `POST /configurar-focus` em `app/routers/notas_fiscais.py`:
```bash
grep -n "configurar-focus\|configurar-certificado" /home/gk/Projeto-izi/sistema/app/routers/notas_fiscais.py
```

Adicione o novo endpoint APÓS a rota `POST /configurar-focus`:

```python
@router.post("/configurar-certificado")
async def configurar_certificado_focus(
    certificado: UploadFile = File(..., description="Certificado A1 (.pfx ou .p12)"),
    senha_certificado: str = Form(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
    _=Depends(exigir_permissao("configuracoes", "escrita")),
):
    """Faz upload do certificado A1 e registra a empresa na Focus NFe."""
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")

    if not empresa.cnpj:
        raise HTTPException(422, "CNPJ da empresa é obrigatório. Preencha os dados fiscais primeiro.")

    if not settings.FOCUS_TOKEN:
        raise HTTPException(503, "FOCUS_TOKEN não configurado no servidor.")

    cert_bytes = await certificado.read()
    if len(cert_bytes) > 102400:  # 100KB
        raise HTTPException(413, "Certificado deve ter no máximo 100KB")

    if not cert_bytes:
        raise HTTPException(422, "Arquivo de certificado vazio")

    try:
        resultado = await nfe_service.registrar_empresa_focus(empresa, cert_bytes, senha_certificado)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error("Erro ao registrar empresa na Focus empresa_id=%s: %s", usuario.empresa_id, e)
        raise HTTPException(400, f"Erro ao registrar empresa na Focus NFe: {e}")

    if not resultado["success"]:
        raise HTTPException(400, resultado.get("erro", "Erro desconhecido na Focus NFe"))

    db.commit()

    return {
        "success": True,
        "message": "Certificado configurado com sucesso na Focus NFe",
        "certificado_configurado": empresa.focus_certificado_configurado,
        "validade": empresa.focus_certificado_validade.isoformat() if empresa.focus_certificado_validade else None,
    }
```

Adicione os imports necessários ao topo do router. Verifique o que já existe:
```bash
grep -n "UploadFile\|File\|Form" /home/gk/Projeto-izi/sistema/app/routers/notas_fiscais.py | head -5
```

Se `UploadFile`, `File` e `Form` não estiverem importados, adicione ao bloco de imports:
```python
from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks, UploadFile, File, Form
```

- [ ] **Step 2: Atualizar GET /status-focus para incluir status do certificado**

Localize a função `status_focus`:
```bash
grep -n "async def status_focus" /home/gk/Projeto-izi/sistema/app/routers/notas_fiscais.py
```

Adicione `certificado_configurado` e `certificado_validade` ao return da função:

```python
    return {
        "configurado": token_ok,
        "conectado": conectado,
        "ambiente": settings.FOCUS_AMBIENTE,
        "nfe_ambiente_empresa": empresa.nfe_ambiente or "homologacao",
        "certificado_configurado": bool(empresa.focus_certificado_configurado),
        "certificado_validade": empresa.focus_certificado_validade.isoformat() if empresa.focus_certificado_validade else None,
    }
```

- [ ] **Step 3: Verificar que o router importa sem erros**

```bash
cd /home/gk/Projeto-izi/sistema
python -c "from app.routers.notas_fiscais import router; print('router ok')"
```

- [ ] **Step 4: Commit**

```bash
cd /home/gk/Projeto-izi/sistema
git add app/routers/notas_fiscais.py
git commit -m "feat(nfe): endpoint POST /configurar-certificado para upload de cert A1 Focus"
```

---

## Task 4: Frontend — Formulário de Certificado

**Files:**
- Modify: `sistema/cotte-frontend/configuracoes.html`
- Modify: `sistema/cotte-frontend/js/configuracoes.js`

- [ ] **Step 1: Restaurar seção de certificado no HTML**

Localize o status bar Focus em `cotte-frontend/configuracoes.html`:
```bash
grep -n "focus-status-bar\|focus-status-icon" /home/gk/Projeto-izi/sistema/cotte-frontend/configuracoes.html
```

Adicione a seção de certificado APÓS o `focus-status-bar`:

```html
              <!-- Seção de certificado A1 para Focus NFe -->
              <div id="secao-certificado-focus" style="margin-top:1.25rem;padding-top:1.25rem;border-top:1px solid var(--border-color)">
                <div class="cfg-card-title" style="font-size:0.95rem;margin-bottom:0.5rem">Certificado Digital A1</div>
                <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:1rem">
                  Envie o arquivo .pfx ou .p12 do certificado A1 da empresa. O COTTE registrará automaticamente o emissor na Focus NFe.
                </p>
                <div id="cert-status-atual" style="display:none;margin-bottom:0.75rem;padding:0.5rem 0.75rem;border-radius:6px;font-size:0.8rem"></div>
                <div class="cfg-fields-grid">
                  <div class="cfg-form-group">
                    <label for="fiscal-certificado">Arquivo do Certificado (.pfx / .p12)</label>
                    <input type="file" id="fiscal-certificado" class="cfg-input" accept=".pfx,.p12" style="padding:0.4rem">
                  </div>
                  <div class="cfg-form-group">
                    <label for="fiscal-cert-senha">Senha do Certificado</label>
                    <input type="password" id="fiscal-cert-senha" class="cfg-input" placeholder="Senha do .pfx">
                  </div>
                </div>
                <button class="btn btn-primary" id="btn-configurar-cert" onclick="configurarCertificadoFocus(this)" style="margin-top:0.5rem">
                  Enviar certificado para a Focus NFe
                </button>
              </div>
```

- [ ] **Step 2: Atualizar carregarStatusFocus() para mostrar status do certificado**

Localize a função `carregarStatusFocus` em `cotte-frontend/js/configuracoes.js`:
```bash
grep -n "async function carregarStatusFocus" /home/gk/Projeto-izi/sistema/cotte-frontend/js/configuracoes.js
```

Substitua a função inteira por:

```javascript
async function carregarStatusFocus() {
  const bar = document.getElementById('focus-status-bar');
  const icon = document.getElementById('focus-status-icon');
  const text = document.getElementById('focus-status-text');
  const certStatus = document.getElementById('cert-status-atual');
  if (!bar) return;
  bar.style.display = 'block';

  try {
    const s = await api.get('/notas-fiscais/status-focus');
    if (!s) return;

    if (s.configurado && s.conectado) {
      bar.style.background = 'rgba(34,197,94,0.1)';
      icon.textContent = '✅';
      text.textContent = `Focus NFe conectada — Ambiente: ${s.ambiente === 'producao' ? 'Produção' : 'Homologação'}.`;
    } else if (s.configurado && !s.conectado) {
      bar.style.background = 'rgba(234,179,8,0.1)';
      icon.textContent = '⚠️';
      text.textContent = 'Token configurado mas sem conexão com a Focus NFe. Verifique a rede ou o token.';
    } else {
      bar.style.background = 'rgba(239,68,68,0.1)';
      icon.textContent = '❌';
      text.textContent = 'FOCUS_TOKEN não configurado no servidor. Contate o administrador.';
    }

    // Status do certificado
    if (certStatus) {
      if (s.certificado_configurado) {
        const validade = s.certificado_validade
          ? `Válido até ${new Date(s.certificado_validade).toLocaleDateString('pt-BR')}`
          : 'Válido';
        certStatus.style.display = 'block';
        certStatus.style.background = 'rgba(34,197,94,0.1)';
        certStatus.style.color = 'var(--text-primary)';
        certStatus.textContent = `✅ Certificado configurado na Focus NFe — ${validade}`;
      } else {
        certStatus.style.display = 'block';
        certStatus.style.background = 'rgba(234,179,8,0.1)';
        certStatus.style.color = 'var(--text-primary)';
        certStatus.textContent = '⚠️ Certificado não configurado — envie o .pfx abaixo para habilitar a emissão.';
      }
    }
  } catch (_) {
    bar.style.background = 'rgba(234,179,8,0.1)';
    icon.textContent = '⚠️';
    text.textContent = 'Não foi possível verificar status da Focus NFe.';
  }
}
```

- [ ] **Step 3: Adicionar função configurarCertificadoFocus()**

Localize o bloco de exports no final do arquivo:
```bash
grep -n "window.carregarStatusFocus\|window.salvarConfiguracao" /home/gk/Projeto-izi/sistema/cotte-frontend/js/configuracoes.js | tail -5
```

Adicione a função `configurarCertificadoFocus` ANTES do bloco de exports:

```javascript
async function configurarCertificadoFocus(btnEl) {
  const certInput = document.getElementById('fiscal-certificado');
  const senhaInput = document.getElementById('fiscal-cert-senha');

  if (!certInput || !certInput.files || !certInput.files[0]) {
    showNotif('⚠️', 'Certificado obrigatório', 'Selecione o arquivo .pfx ou .p12 do certificado A1.', 'warning');
    return;
  }
  if (!senhaInput || !senhaInput.value) {
    showNotif('⚠️', 'Senha obrigatória', 'Informe a senha do certificado digital.', 'warning');
    return;
  }

  if (btnEl) { btnEl.disabled = true; btnEl.textContent = 'Enviando...'; }

  try {
    const formData = new FormData();
    formData.append('certificado', certInput.files[0]);
    formData.append('senha_certificado', senhaInput.value);

    const token = localStorage.getItem('cotte_token');
    const url = buildApiRequestUrl('/notas-fiscais/configurar-certificado');
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.detail || data.error || `Erro ${resp.status}`);
    }

    senhaInput.value = '';
    certInput.value = '';

    const validade = data.validade
      ? ` (válido até ${new Date(data.validade).toLocaleDateString('pt-BR')})`
      : '';
    showNotif('✅', 'Certificado configurado!', `Emissor registrado na Focus NFe com sucesso${validade}.`);

    await carregarStatusFocus();
  } catch (err) {
    showNotif('❌', 'Erro ao configurar certificado', err.message || 'Verifique o arquivo e a senha.', 'error');
  } finally {
    if (btnEl) { btnEl.disabled = false; btnEl.textContent = 'Enviar certificado para a Focus NFe'; }
  }
}
```

Adicione ao bloco de exports:
```javascript
window.configurarCertificadoFocus = configurarCertificadoFocus;
```

- [ ] **Step 4: Verificar que não há erros de sintaxe no JS**

```bash
cd /home/gk/Projeto-izi/sistema
node --check cotte-frontend/js/configuracoes.js 2>&1
```

Esperado: sem output (sem erros)

- [ ] **Step 5: Commit**

```bash
cd /home/gk/Projeto-izi/sistema
git add cotte-frontend/configuracoes.html cotte-frontend/js/configuracoes.js
git commit -m "feat(frontend): formulário de certificado A1 para Focus NFe"
```

---

## Task 5: Teste End-to-End Manual

Esta task não tem automação — é verificação manual no sistema real.

- [ ] **Step 1: Garantir que FOCUS_TOKEN está no .env**

```bash
grep "FOCUS_TOKEN\|FOCUS_AMBIENTE" /home/gk/Projeto-izi/sistema/.env
```

Se não existir, adicione:
```
FOCUS_TOKEN=seu_token_de_homologacao
FOCUS_AMBIENTE=homologacao
```

- [ ] **Step 2: Subir o servidor**

```bash
cd /home/gk/Projeto-izi/sistema
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 3: Verificar status no painel**

Acesse **Configurações → Fiscal**. O status bar deve mostrar:
- ✅ Focus NFe conectada (se FOCUS_TOKEN correto)
- ⚠️ Certificado não configurado (ainda sem certificado)

- [ ] **Step 4: Enviar um certificado de teste**

No painel, na seção "Certificado Digital A1":
1. Selecione o arquivo `.pfx` da empresa
2. Informe a senha
3. Clique em "Enviar certificado para a Focus NFe"

Esperado:
- Notificação ✅ "Certificado configurado!"
- Status bar atualiza para mostrar a validade do certificado

- [ ] **Step 5: Verificar no painel da Focus**

Acesse [app.focusnfe.com.br](https://app.focusnfe.com.br) → **Emissores** e confirme que a empresa aparece cadastrada com o certificado.

- [ ] **Step 6: Commit final e push**

```bash
cd /home/gk/Projeto-izi/sistema
git push origin main
```

---

## Resumo

| O que muda | Por quê |
|---|---|
| Campo `focus_certificado_configurado` na tabela empresas | Persiste se o certificado já foi enviado (para decidir POST vs PUT na Focus) |
| Campo `focus_certificado_validade` | Permite exibir validade ao usuário e alertar antes do vencimento |
| `registrar_empresa_focus()` em nfe_service | Encapsula a chamada à Focus API de emissores, reutilizável |
| `POST /configurar-certificado` no router | Endpoint que o frontend chama com multipart/form-data |
| Seção de certificado no painel Configurações | UX transparente — cliente do COTTE nunca precisa acessar a Focus diretamente |
