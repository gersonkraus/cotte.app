# Design: Emissão Inteligente de NF-e (Simples Nacional)

**Data:** 2026-05-11  
**Status:** Aprovado  
**Escopo:** NF-e (modelo 55) para empresas do Simples Nacional / MEI  
**Abordagem:** Híbrida — campos fiscais no catálogo + IA completa o que estiver faltando na emissão

---

## Problema

O catálogo de produtos (`servicos`) não tem campos fiscais. O `nfe_service.py` usa valores hardcoded para NCM (`"00000000"`), CFOP (`"5102"`), CSOSN (`"102"`), unidade (`"UN"`) e tipo de pagamento (`"01"`). Há também um bug crítico que confunde `inscricao_municipal` com `codigo_municipio_ibge` no destinatário. Resultado: praticamente impossível emitir NF-e válida por um operador leigo.

---

## Solução: Abordagem C — Emissão Inteligente com Pré-verificação

### Princípio
- Operador nunca vê código fiscal. Sistema cuida de tudo.
- Catálogo armazena dados fiscais (configurados uma vez por produto).
- IA preenche automaticamente qualquer campo ausente na emissão.
- Antes de emitir: tela de confirmação simples com status legível.

---

## 1. Modelo de Dados

### Migration: campos fiscais em `servicos`

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `ncm` | String(8) | `None` | Código NCM (ex: "84714900") |
| `cfop` | String(4) | `None` | Código fiscal da operação (ex: "5102") |
| `csosn` | String(4) | `None` | Situação tributária Simples (ex: "400") |
| `origem` | Integer | `0` | 0=nacional, 1=importado direto, 2=importado adquirido |
| `unidade_fiscal` | String(6) | `None` | Unidade (UN, PC, KG, MT, CX…) |
| `dados_fiscais_ok` | Boolean | `False` | Flag: dados revisados por humano |

**Nenhuma alteração em `ItemOrcamento`** — item herda do produto via `servico_id`. A emissão usa `item.servico.ncm` etc.

---

## 2. Serviço de IA Fiscal

**Arquivo:** `sistema/app/services/fiscal_ai_service.py`  
**Usa:** `ia_service.py` existente (LiteLLM)

### Função principal
```python
async def sugerir_dados_fiscais(
    descricao: str,
    categoria: str | None = None,
    preco: float | None = None
) -> dict
```

**Retorno:**
```json
{
  "ncm": "84714900",
  "cfop": "5102",
  "csosn": "400",
  "origem": 0,
  "unidade": "UN",
  "confianca": "alta"
}
```

**Defaults para Simples Nacional** (quando IA tiver baixa confiança):
- `cfop` = `"5102"` — venda interna de mercadoria
- `csosn` = `"400"` — tributado pelo Simples sem retenção
- `origem` = `0` — nacional
- `unidade` = `"UN"`

### Onde é chamada
1. **Catálogo (admin):** botão "Sugerir com IA" ao editar produto
2. **Emissão (fallback):** produto sem NCM → IA sugere na hora, sem bloquear operador

---

## 3. Atualização do NF-e Service

**Arquivo:** `sistema/app/services/nfe_service.py`  
**Função:** `_montar_payload_nfe`

### Lógica de campos por item (substitui hardcodes)
```
ncm      = servico.ncm          || IA sugere  || "00000000"
cfop     = servico.cfop         || "5102"
csosn    = servico.csosn        || "400"
origem   = servico.origem       ?? 0
unidade  = servico.unidade_fiscal || servico.unidade || "UN"
```

### Bugs corrigidos
- **Bug crítico (linha ~102):** `codigoMunicipio` usava `inscricao_municipal` (número da prefeitura) em vez de `empresa.endereco_codigo_municipio_ibge` (código IBGE 7 dígitos)
- **Tipo pagamento (linha ~134):** mapeado de `orcamento.forma_pagamento`:
  - `"pix"` → `"17"` | `"cartao_credito"` → `"03"` | `"boleto"` → `"15"` | default → `"99"`
- **CRT (linha ~60):** lido de `empresa.crt` em vez de hardcoded `1`

### Carregamento com joinedload
O router (em `/preparar` e `/emitir`) deve buscar o orçamento com `selectinload(Orcamento.itens).joinedload(ItemOrcamento.servico)` antes de passar para `_montar_payload_nfe`, para evitar N+1 queries.

---

## 4. Endpoint de Pré-emissão

**Rota:** `POST /notas-fiscais/preparar`  
**Arquivo:** `sistema/app/routers/notas_fiscais.py`

### Fluxo
1. Carrega orçamento com itens e dados fiscais do produto
2. Para cada item sem NCM → chama IA, preenche temporariamente (não salva no catálogo)
3. Valida: destinatário tem CPF ou CNPJ
4. Valida: empresa tem CNPJ, CRT, endereço completo, API key Notaas

### Resposta
```json
{
  "pronto": true,
  "resumo": "3 itens prontos, 1 NCM sugerido por IA",
  "avisos": ["NCM do item 'Cabo USB' sugerido por IA — verifique se necessário"],
  "bloqueios": [],
  "payload_preview": { "...": "payload completo pronto para emitir" }
}
```

- `bloqueios` (ex: cliente sem CPF/CNPJ) → botão "Emitir" desabilitado
- `avisos` → informativos, não bloqueiam emissão

---

## 5. Frontend

### A) Botão no orçamento aprovado

Local: página de detalhes do orçamento  
Trigger: botão `"Emitir NF-e"`  
Fluxo:
1. Chama `POST /notas-fiscais/preparar`
2. Abre modal com resumo: lista de itens + status + total + cliente
3. Exibe avisos não-bloqueantes (amarelo) e bloqueios (vermelho)
4. Botão `"Confirmar e Emitir"` → `POST /notas-fiscais/emitir`
5. Feedback: spinner → `"Nota emitida! Nº 000123"` com link para DANFE/XML

### B) Catálogo de produtos (admin/gestor)

Local: formulário de edição de produto  
Nova seção: "Dados Fiscais" (colapsável)  
Campos: NCM, CFOP, CSOSN, unidade fiscal  
Botão: `"Sugerir com IA"` → chama `GET /catalogo/{id}/sugerir-fiscal` → preenche campos  
Indicador: `🟢 NCM configurado` / `🟡 Usando sugestão IA` / `⚪ Sem dados fiscais`

---

## 6. Novos Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/notas-fiscais/preparar` | Pré-validação + payload completo |
| `GET` | `/catalogo/{id}/sugerir-fiscal` | IA sugere dados fiscais de um produto |
| `PATCH` | `/catalogo/{id}/fiscal` | Salva dados fiscais no produto |

---

## 7. Arquivos Modificados

| Arquivo | Mudança |
|---|---|
| `sistema/alembic/versions/XXXX_add_fiscal_fields_servicos.py` | Nova migration |
| `sistema/app/models/models.py` | Campos fiscais em `Servico` |
| `sistema/app/services/nfe_service.py` | Remove hardcodes, usa catálogo + IA |
| `sistema/app/services/fiscal_ai_service.py` | **Novo** — sugestão fiscal por IA |
| `sistema/app/routers/notas_fiscais.py` | Endpoint `/preparar` |
| `sistema/app/routers/catalogo.py` | Endpoints `/sugerir-fiscal` e `/fiscal` |
| `sistema/app/schemas/schemas.py` | Schemas novos: `FiscalSugestaoOut`, `FiscalUpdateRequest` |
| Frontend: página de orçamento | Botão "Emitir NF-e" + modal |
| Frontend: catálogo de produtos | Seção "Dados Fiscais" + botão IA |

---

## 8. Verificação / Testes

1. Criar produto sem NCM → acionar "Sugerir com IA" → verificar resposta
2. Criar orçamento com esse produto → `POST /preparar` → verificar `avisos` e `payload_preview`
3. Emitir NF-e em homologação → verificar status `"issued"` na Notaas
4. Criar produto com NCM manual → emissão usa NCM do catálogo (não chama IA)
5. Orçamento com cliente sem CPF/CNPJ → `preparar` retorna `bloqueios` (não emite)
6. Verificar `codigoMunicipio` correto no payload (código IBGE, não inscrição municipal)

---

## Restrições

- Stack: FastAPI + SQLAlchemy + Vanilla JS (sem frameworks novos)
- Não alterar contratos existentes do `POST /notas-fiscais/emitir`
- Não misturar com problemas pendentes de NFS-e, SQL enum ou certificado Notaas
- Deploy via push + hook automatizado (não manual)
