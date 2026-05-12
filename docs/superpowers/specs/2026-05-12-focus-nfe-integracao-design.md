# Design: Migração Notaas → Focus NFe

**Data:** 2026-05-12  
**Status:** Aprovado  
**Escopo:** Substituição completa da API Notaas pela API Focus NFe para emissão de NF-e, NFC-e e NFS-e

---

## Contexto

A API Notaas está inoperante e sem suporte técnico. A migração para a Focus NFe é necessária para restaurar a capacidade de emissão fiscal do COTTE. A Focus é uma API brasileira madura com documentação completa, suporte a todos os tipos de nota e modelo de preços baseado em consumo.

---

## Decisões de Design

| Decisão | Escolha | Justificativa |
|---|---|---|
| Modelo de credenciais | Token único COTTE no `.env` | Focus não requer onboarding por empresa; multitenancy via `ref` |
| Formato da `ref` | `{cnpj_emitente}-{nota_id}` | Legível, rastreável, único por empresa+nota |
| Estratégia de polling | Webhook principal + polling fallback | Eficiência com resiliência |
| Tipos de nota | NF-e, NFC-e e NFS-e | Todos em uso no sistema |
| Abordagem de migração | Substituição direta (Abordagem A) | Código limpo, sem peso legado |

---

## Arquitetura

### O que muda

| Componente | Ação |
|---|---|
| `app/services/nfe_service.py` | Reescrito — mesma interface pública, internals Focus |
| `app/services/nfe_org_service.py` | **Deletado** — onboarding programático não existe na Focus |
| `app/routers/notas_fiscais.py` | Rotas renomeadas, webhook atualizado |
| `app/core/config.py` | `NOTAAS_ORG_TOKEN` + `NOTAAS_CRYPTO_SECRET` → `FOCUS_TOKEN` + `FOCUS_AMBIENTE` |
| DB schema | Migração Alembic: remover colunas `notaas_*`, adicionar `focus_ref` e `denegada` |
| Testes | Mocks atualizados para Focus |

### O que não muda

- `_montar_payload_nfe()` e `_montar_payload_nfse()` — lógica fiscal interna intacta
- `coletar_bloqueios_avisos_preparacao_nfe()` — validações pré-emissão intactas
- `fiscal_ai_service.py` — sugestão de NCM/CFOP por IA intacta
- Frontend (`nfe.js`, `orcamentos.html`) — sem alteração necessária

---

## Autenticação Focus

A Focus usa HTTP Basic Auth com o token como username e senha vazia.

```python
FOCUS_TOKEN = settings.FOCUS_TOKEN
FOCUS_BASE_URL = (
    "https://api.focusnfe.com.br"
    if settings.FOCUS_AMBIENTE == "producao"
    else "https://homologacao.focusnfe.com.br"
)

def _get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=FOCUS_BASE_URL,
        auth=(FOCUS_TOKEN, ""),
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )
```

Token único — sem criptografia por empresa. A credencial fica exclusivamente no `.env` do COTTE.

---

## Sistema de Referência (`ref`)

Cada nota usa `ref = f"{cnpj_limpo}-{nota_id}"` onde `cnpj_limpo` são apenas dígitos do CNPJ do emitente.

```python
def _gerar_ref(empresa: Empresa, nota_id: int) -> str:
    cnpj = re.sub(r'\D', '', empresa.cnpj or "")
    if not cnpj:
        raise ValueError("Empresa sem CNPJ — impossível gerar ref Focus")
    return f"{cnpj}-{nota_id}"
```

A `ref` é salva no campo `focus_ref` da `NotaFiscal` após a emissão. É usada para polling, cancelamento e identificação via webhook.

**Regra:** Se a nota já tem `focus_ref`, o service reenvia para o mesmo endpoint (permite retry em `erro_autorizacao`).

---

## Fluxo de Emissão

```
Router
  → _montar_payload_*()
  → POST /v2/{tipo}?ref={ref}              [HTTP 202 — aceito assincronamente]
  → salva focus_ref, status="processando"
  → aguarda webhook  (principal)
  → fallback: polling GET /v2/{tipo}/{ref}  (3s × 20 tentativas = 60s)
  → atualiza NotaFiscal com resultado
```

### Endpoints por tipo

| Tipo | Emissão | Consulta | Cancelamento |
|---|---|---|---|
| NF-e | `POST /v2/nfe?ref=` | `GET /v2/nfe/{ref}` | `DELETE /v2/nfe/{ref}` |
| NFC-e | `POST /v2/nfce?ref=` | `GET /v2/nfce/{ref}` | `DELETE /v2/nfce/{ref}` |
| NFS-e | `POST /v2/nfse?ref=` | `GET /v2/nfse/{ref}` | `DELETE /v2/nfse/{ref}` |

---

## Mapeamento de Status

| Status Focus | Status COTTE (DB) | Observação |
|---|---|---|
| `processando_autorizacao` | `processando` | — |
| `autorizado` | `emitida` | Salva chave, número, protocolo, URLs |
| `erro_autorizacao` | `erro` | Permite reemissão com mesmo `ref` |
| `denegado` | `erro` | `denegada=True` — bloqueia reemissão |
| `cancelado` | `cancelada` | — |

### Campos retornados em `autorizado`

| Campo Focus | Campo DB |
|---|---|
| `chave_nfe` | `chave_acesso` |
| `numero` | `numero` |
| `protocolo` | `protocolo` |
| `caminho_xml_nota_fiscal` | `xml_url` |
| `caminho_danfe` | `danfe_url` |

---

## Webhook

**Endpoint:** `POST /notas-fiscais/webhook/focus`

**Autenticação:** Verificar header `Authorization: Basic {token_base64}` — compara com `FOCUS_TOKEN` local.

**Payload recebido:**
```json
{
  "ref": "12345678000195-1337",
  "status": "autorizado",
  "chave_nfe": "...",
  "numero": "42",
  "protocolo": "...",
  "caminho_xml_nota_fiscal": "...",
  "caminho_danfe": "..."
}
```

**Extração da nota:** `nota_id = int(ref.split("-")[-1])` — busca `NotaFiscal` por ID + valida que `focus_ref` bate.

---

## Tratamento de Erros

| Situação | Comportamento |
|---|---|
| HTTP 422 (payload inválido) | `status=erro`, `erro_mensagem` com detalhe da Focus |
| HTTP 401 (token inválido) | `status=erro`, `erro_codigo="AUTH_ERROR"`, log crítico |
| HTTP 409 (ref já usada com status final) | Detecta e retorna nota existente sem reemitir |
| Timeout polling (60s) | `status=erro`, `erro_mensagem="Timeout SEFAZ"` — webhook pode ainda chegar |
| `denegado` | `status=erro`, `denegada=True` — frontend bloqueia reemissão |
| `erro_autorizacao` | `status=erro` — reemissão permitida via mesmo `ref` |

---

## Mudanças no Banco de Dados

### Migration Alembic

**Tabela `empresas` — remover:**
- `notaas_project_id`
- `notaas_api_key`
- `notaas_ambiente`
- `notaas_webhook_secret`

**Tabela `notas_fiscais` — remover:**
- `notaas_invoice_id`
- `notaas_delivery_id`

**Tabela `notas_fiscais` — adicionar:**
- `focus_ref VARCHAR(100)` — referência usada na Focus
- `denegada BOOLEAN DEFAULT FALSE` — nota denegada não pode ser reemitida

---

## Configurações no `.env`

```env
# Remover
NOTAAS_ORG_TOKEN=
NOTAAS_CRYPTO_SECRET=

# Adicionar
FOCUS_TOKEN=seu_token_aqui
FOCUS_AMBIENTE=homologacao   # ou producao
```

---

## Router — Rotas Renomeadas

| Rota antiga | Rota nova |
|---|---|
| `POST /configurar-notaas` | `POST /configurar-focus` |
| `GET /status-notaas` | `GET /status-focus` |
| `POST /webhook/notaas` | `POST /webhook/focus` |

**`POST /configurar-focus`:** Sem onboarding programático na Focus, esta rota passa a salvar apenas o `nfe_ambiente` preferido da empresa (`homologacao` / `producao`) e retorna o status atual (token configurado ou não, ambiente ativo). O token em si é global no `.env` e não exposto via API.

**`GET /status-focus`:** Faz um `GET /v2/nfe/{ref_inexistente}` para testar conectividade com a Focus e retorna `{"conectado": true/false, "ambiente": "..."}` sem expor credenciais.

---

## Testes

Arquivos existentes atualizados com mocks da Focus:
- `tests/test_nfe_service.py`
- `tests/test_nfe_router.py`
- `tests/test_nfe_webhook.py`

**Casos de teste:**
1. Emissão com sucesso → `status=emitida`, campos preenchidos
2. Emissão com `erro_autorizacao` → `status=erro`, retry com mesmo `ref`
3. Emissão `denegado` → `status=erro`, `denegada=True`
4. Cancelamento → `status=cancelada`
5. Webhook `autorizado` → DB atualizado sem polling
6. Webhook com token inválido → 401
7. Ref já usada → retorna nota existente
8. Timeout polling → `status=erro` com mensagem

---

## Fases de Implementação (sumário)

1. **Config e client** — variáveis `.env`, `config.py`, `_get_client()` Focus
2. **DB migration** — Alembic: remove `notaas_*`, adiciona `focus_ref` + `denegada`
3. **Models** — atualizar `Empresa` e `NotaFiscal`
4. **nfe_service.py** — reescrever `emitir_nota`, `cancelar_nota`, polling/webhook
5. **Router** — renomear rotas, atualizar webhook handler, remover org_service
6. **Deletar** `nfe_org_service.py`
7. **Testes** — atualizar mocks e casos de teste
8. **Deploy** — configurar `FOCUS_TOKEN` e `FOCUS_AMBIENTE` no Railway
