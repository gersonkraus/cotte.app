---
title: Catalogo
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Técnico - Catálogo
tags:
  - tecnico
  - frontend
  - catalogo
  - mapa
prioridade: media
status: documentado
---

# Mapa Técnico: Funcionalidade Catálogo

> Rastreamento completo de ponta a ponta — gerado por análise estática do código.

---

## 1. Entrada do Fluxo

### HTTP
- **Router principal:** `app/main.py:145` — prefixo `/api/v1/catalogo`
- **Router:** `app/routers/catalogo.py` (436 linhas)

### Frontend
- **Página dedicada:** `cotte-frontend/catalogo.html` (1151 linhas)
- **Menu lateral:** `cotte-frontend/js/layout.js:67` — `<a data-page="catalogo" href="catalogo.html" id="nav-catalogo">`
- **Controle de visibilidade do menu:** `cotte-frontend/js/layout.js:289` — remove nav se `!p.pode('catalogo')`
- **Modais de catálogo em orçamentos:**
  - `cotte-frontend/index.html:584-594` — modal `#modal-catalogo`
  - `cotte-frontend/orcamentos.html:633-644` — modal `#modal-catalogo`
- **Catálogo como auxiliar na view de orçamento:** `cotte-frontend/orcamento-view.html:424-438`

### WhatsApp Bot (entrada indireta)
- `app/routers/whatsapp.py:631` — `_encontrar_servico_catalogo()` chamado em `_criar_orcamento_via_bot()`

### Chat Interno (entrada indireta)
- `app/routers/orcamentos.py:835` — `_encontrar_servico_catalogo_orc()` chamado no handler de chat

---

## 2. Caminho Completo dos Arquivos

### Backend

| Caminho | Função |
|---------|--------|
| `app/routers/catalogo.py` | Router HTTP — todas as rotas do catálogo |
| `app/services/catalogo_service.py` | Seeds de categorias e serviços de demonstração |
| `app/services/template_segmento_service.py` | Templates de catálogo por segmento (eletricista, pedreiro, etc.) |
| `app/services/ia_service.py:138` | `interpretar_tabela_catalogo()` — parse de tabela via LiteLLM (modelo configurável) |
| `app/services/r2_service.py` | Upload/remoção de imagens no R2 |
| `app/models/models.py:435-464` | Models `CategoriaCatalogo` e `Servico` |
| `app/models/models.py:729-752` | Model `ItemOrcamento` (vincula `servico_id`) |
| `app/schemas/schemas.py:613-656` | Schemas `CategoriaCatalogo*` e `Servico*` |
| `app/schemas/schemas.py:88-101` | Schema `ItemOrcamentoCreate/Out` (campo `servico_id`) |
| `app/core/auth.py:102` | `exigir_permissao("catalogo", ...)` |
| `app/routers/whatsapp.py:554-600` | `_encontrar_servico_catalogo()` — busca por similaridade |
| `app/routers/orcamentos.py:2491-2527` | `_encontrar_servico_catalogo_orc()` — busca duplicada |
| `alembic/versions/z009_catalogo_categoria_custo.py` | Migration: tabela `categorias_catalogo` + colunas `categoria_id`, `preco_custo` |

### Frontend

| Caminho | Função |
|---------|--------|
| `cotte-frontend/catalogo.html` | Página principal do catálogo (CRUD, importação, templates) |
| `cotte-frontend/index.html` | Modal de catálogo na criação de orçamento (dashboard) |
| `cotte-frontend/orcamentos.html` | Modal de catálogo na edição de orçamento |
| `cotte-frontend/orcamento-view.html` | Carrega catálogo para exibir imagem de itens |
| `cotte-frontend/js/api.js:165` | Navegação inclui `nav-catalogo` |
| `cotte-frontend/js/layout.js:67/289` | Menu e controle de permissão |
| `cotte-frontend/js/services/ApiService.js:165/169` | Métodos `getCatalogo()` e `buscarCatalogo(termo)` |
| `cotte-frontend/js/dashboard/Modals.js:91-92` | Modal de catálogo no dashboard refatorado |

---

## 3. Sequência de Chamadas

### Fluxo A — CRUD de Itens do Catálogo (página dedicada)

```
Frontend (catalogo.html)
  ├─ api.get('/catalogo/?apenas_ativos=false')       → listar
  ├─ api.post('/catalogo/', payload)                  → criar
  ├─ api.put('/catalogo/${id}', payload)              → atualizar
  ├─ api.delete('/catalogo/${id}')                    → soft-delete (ativo=false)
  ├─ api.patch('/catalogo/${id}', { ativo: true })    → reativar (PATCH inexistente → usa PUT)
  ├─ fetch('/catalogo/${id}/imagem', POST)            → upload imagem
  └─ api.delete('/catalogo/${id}/imagem')             → remover imagem
      ↓
Router (app/routers/catalogo.py)
  ├─ exigir_permissao("catalogo", "leitura"|"escrita"|"admin")
  ├─ seed_catalogo_padrao() ← chamado em GET / e GET /categorias
  ├─ db.query(Servico).filter(empresa_id=...)
  └─ CRUD direto no model Servico
      ↓
Service (app/services/catalogo_service.py)
  └─ seed_catalogo_padrao()
      ├─ _seed_categorias_padrao()    → cria "Serviços", "Materiais", "Mão de obra", "Transporte"
      └─ _seed_servicos_demonstracao() → cria "Cliente Teste", "Material Teste"
```

### Fluxo B — CRUD de Categorias

```
Frontend (catalogo.html)
  ├─ api.get('/catalogo/categorias')
  ├─ api.post('/catalogo/categorias', { nome })
  └─ api.delete('/catalogo/categorias/${id}')
      ↓
Router (app/routers/catalogo.py)
  ├─ GET  → query CategoriaCatalogo por empresa_id, order_by nome
  ├─ POST → cria CategoriaCatalogo(empresa_id, nome.strip())
  └─ DELETE → verifica vínculos em Servico antes de deletar (HTTP 400 se vinculados)
```

### Fluxo C — Importação de Catálogo

#### C1 — Importação por texto colado

```
Frontend (catalogo.html:890)
  → api.post('/catalogo/analisar-importacao', { texto })
    ↓
Router (catalogo.py:244-255)
  → interpretar_tabela_catalogo(texto)        ← LiteLLM / modelo em config
  → _enriquecer_com_duplicatas(items, db, empresa_id)
  → retorna { items: [...], total: N }
```

#### C2 — Importação por arquivo (CSV/XLSX/PDF)

```
Frontend (catalogo.html:874)
  → fetch('/catalogo/analisar-arquivo', POST, FormData)
    ↓
Router (catalogo.py:273-342)
  ├─ Parse CSV (utf-8-sig → latin-1 fallback)
  ├─ Parse XLSX via openpyxl
  ├─ Parse PDF via pdfplumber
  └─ interpretar_tabela_catalogo(texto) + _enriquecer_com_duplicatas()
```

#### C3 — Confirmação de importação em lote

```
Frontend (catalogo.html:987)
  → api.post('/catalogo/importar-lote', { items: [...] })
    ↓
Router (catalogo.py:345-399)
  ├─ Query nomes existentes (case-insensitive)
  ├─ Para cada item: skip se vazio ou duplicado
  ├─ Parse de preço com try/except
  ├─ Cria Servico(...)
  └─ Retorna { criados: N, items: [...] }
```

#### C4 — Importação por template de segmento

```
Frontend (catalogo.html)
  ├─ api.get('/catalogo/templates/segmentos')
  ├─ api.get('/catalogo/templates/${slug}')
  └─ api.post('/catalogo/templates/${slug}/importar')
    ↓
Router (catalogo.py:405-436)
  → importar_template_para_empresa(segmento, empresa_id, db)
    ↓
Service (template_segmento_service.py:315-369)
  ├─ Lookup em TEMPLATES_SEGMENTOS (dict estático)
  ├─ Cria/busca CategoriaCatalogo por nome
  ├─ Cria Servico com categoria_id mapeado
  └─ Retorna { segmento, categorias_criadas, servicos_criados }
```

### Fluxo D — Catálogo como Fonte de Preços (consumidores)

#### D1 — WhatsApp Bot

```
app/routers/whatsapp.py:603 → _criar_orcamento_via_bot()
  ├─ interpretar_mensagem(mensagem) → InterpretacaoIA { servico, valor, desconto, ... }
  ├─ _encontrar_servico_catalogo(empresa, descricao, db) → Servico | None
  ├─ Se preco_padrao > 0 → subtotal = preco_padrao
  ├─ Se ia_valor > 0 → subtotal = ia_valor (sobrescreve)
  ├─ Cria Orcamento + ItemOrcamento(servico_id=match.id if match)
  └─ Vincula imagem_url via ItemOrcamento.imagem_url property
```

#### D2 — Chat Interno de Orçamentos

```
app/routers/orcamentos.py:829 → handler de chat
  ├─ interpretar_mensagem(mensagem)
  ├─ _encontrar_servico_catalogo_orc(empresa, descricao, db) → Servico | None
  ├─ Mesma lógica de preço: catálogo primeiro, IA sobrescreve se explícito
  └─ Cria Orcamento + ItemOrcamento(servico_id=match.id if match)
```

#### D3 — View de Orçamento (frontend)

```
orcamento-view.html:424
  → api.get('/catalogo/?apenas_ativos=false')
  → Mapeia imagem_url dos serviços para exibição nos itens
```

---

## 4. Estruturas de Dados Envolvidas

### Tabelas do Banco

#### `categorias_catalogo`
| Coluna | Tipo | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| empresa_id | Integer | FK → empresas.id, NOT NULL, INDEX |
| nome | String(100) | NOT NULL |

#### `servicos`
| Coluna | Tipo | Constraints |
|--------|------|-------------|
| id | Integer | PK, INDEX |
| empresa_id | Integer | FK → empresas.id, NOT NULL, INDEX |
| nome | String(200) | NOT NULL |
| descricao | Text | nullable |
| preco_padrao | Numeric(10,2) | default 0.0 |
| preco_custo | Numeric(10,2) | nullable |
| unidade | String(30) | default "un" |
| ativo | Boolean | default True |
| imagem_url | String(300) | nullable |
| categoria_id | Integer | FK → categorias_catalogo.id, nullable |

#### `itens_orcamento` (campos relevantes)
| Coluna | Tipo | Constraints |
|--------|------|-------------|
| servico_id | Integer | FK → servicos.id, nullable (vínculo opcional com catálogo) |

### Schemas Pydantic

#### CategoriaCatalogoCreate
```python
nome: str = Field(..., min_length=1, max_length=100)
```

#### CategoriaCatalogoOut
```python
id: int
nome: str
```

#### ServicoCreate (herda ServicoBase)
```python
nome: str
descricao: Optional[str] = None
preco_padrao: Decimal = Decimal("0.0")
preco_custo: Optional[Decimal] = None
unidade: str = "un"
categoria_id: Optional[int] = None
```

#### ServicoUpdate
```python
nome: Optional[str] = None
descricao: Optional[str] = None
preco_padrao: Optional[Decimal] = None
preco_custo: Optional[Decimal] = None
unidade: Optional[str] = None
ativo: Optional[bool] = None
categoria_id: Optional[int] = None
```

#### ServicoOut (herda ServicoBase)
```python
id: int
empresa_id: int
ativo: bool
imagem_url: Optional[str] = None
categoria: Optional[CategoriaCatalogoOut] = None
```

#### ItemOrcamentoCreate
```python
descricao: str
quantidade: Decimal = Decimal("1.0")
valor_unit: Decimal
servico_id: Optional[int] = None  # vínculo opcional com catálogo
```

#### ItemOrcamentoOut
```python
id: int
descricao: str
quantidade: Decimal
valor_unit: Decimal
total: Decimal
servico_id: Optional[int] = None
imagem_url: Optional[str] = None  # property delegada ao Servico vinculado
```

### Payload de Importação (IA)

```json
[
  {
    "nome": "Serviço extraído",
    "preco_padrao": 100.0,
    "unidade": "un",
    "descricao": "Descrição opcional"
  }
]
```

### Payload de Confirmação de Lote

```json
{
  "items": [
    {
      "nome": "...",
      "preco_padrao": 100.0,
      "unidade": "un",
      "descricao": "...",
      "duplicado": false,
      "selecionado": true
    }
  ]
}
```

---

## 5. Regras de Negócio Encontradas

| # | Regra | Localização |
|---|-------|------------|
| 1 | Soft-delete de serviço: `ativo=False` preserva vínculos com orçamentos existentes | `catalogo.py:169-171` |
| 2 | Categorias padrão criadas automaticamente (Serviços, Materiais, Mão de obra, Transporte) | `catalogo_service.py:10-15` |
| 3 | Seed idempotente: não duplica se já existirem itens | `catalogo_service.py:18-63` |
| 4 | Categorias só podem ser excluídas se não tiverem serviços vinculados | `catalogo.py:80-85` |
| 5 | Importação ignora nomes duplicados (comparação case-insensitive) | `catalogo.py:356-366`, `template_segmento_service.py:342-350` |
| 6 | Preço do catálogo tem prioridade sobre valor da IA quando disponível | `whatsapp.py:660-674`, `orcamentos.py:859-667` |
| 7 | Valor explícito da IA sobrescreve preço do catálogo | `whatsapp.py:672-674`, `orcamentos.py:866-867` |
| 8 | Match de catálogo: primeiro exato por nome normalizado, depois similaridade por interseção de palavras (limiar ≥50%) | `whatsapp.py:574-600`, `orcamentos.py:2509-2527` |
| 9 | Permissões granulares: leitura / escrita / admin no recurso "catalogo" | `catalogo.py` (todas rotas), `auth.py:102` |
| 10 | Upload de imagem: extensões .png/.jpg/.jpeg/.webp; remove imagem anterior do R2 | `catalogo.py:192-216` |
| 11 | ItemOrcamento.imagem_url delega ao Servico vinculado (catálogo) para exibição | `models.py:747-752` |
| 12 | Templates de segmento: dados estáticos embutidos no código (não no banco) | `template_segmento_service.py:10-299` |

---

## 6. Problemas de Arquitetura

### CRÍTICO — Código Duplicado: Busca por Similaridade

`_encontrar_servico_catalogo` (`app/routers/whatsapp.py:554`) e `_encontrar_servico_catalogo_orc` (`app/routers/orcamentos.py:2491`) são **virtualmente idênticas**.

Ambas:
- Normalizam texto (diferem apenas no nome da função auxiliar)
- Fazem query de **todos** os serviços ativos da empresa
- Aplicam match exato → fallback por interseção de palavras com limiar 0.5

**Impacto:** Corrigir o algoritmo de similaridade exige alterar dois arquivos. Se um for esquecido, comportamento divergente.

**Funções auxiliares também duplicadas:**
- `_normalizar_texto()` em `whatsapp.py:544`
- `_normalizar_texto_orc()` em `orcamentos.py:2481`
- Mesma implementação: lowercase → NFKD → remove acentos → regex `[^a-z0-9]+` → trim

### MÉDIO — Lógica de Preço no Router

A regra "preço catálogo primeiro, IA sobrescreve se explícito" está duplicada em:
- `catalogo.py:862-867` (handler de orçamento via chat)
- `whatsapp.py:665-674` (handler de WhatsApp)

Deveria estar em um service compartilhado.

### MÉDIO — Importação Fora do Service

`importar_lote` (`catalogo.py:345-399`) faz query de duplicatas e criação de serviços diretamente no router. `_enriquecer_com_duplicatas` (`catalogo.py:258-270`) também. Ambas deveriam estar em `catalogo_service.py`.

### BAIXO — Serviços de Demonstração com Nomes Confusos

`catalogo_service.py:34-47` define "Cliente Teste" e "Material Teste" como serviços de demonstração. "Cliente Teste" como nome de serviço é semanticamente incorreto.

### BAIXO — Import Morto

`app/routers/comercial.py:42` importa `interpretar_tabela_catalogo` mas não o utiliza neste arquivo.

### BAIXO — Campo categoria_id Ignorado na Criação

O schema `ServicoCreate` aceita `categoria_id` mas o router `criar_servico` (`catalogo.py:112-119`) não o inclui no construtor `Servico(...)`. O campo é silenciosamente ignorado ao criar via POST.

### BAIXO — PATCH Inexistente para Reativação

O frontend (`catalogo.html:513`) chama `api.patch('/catalogo/${id}', { ativo: true })` mas o router não tem endpoint PATCH. O comportamento depende da implementação do helper `api.patch` no frontend — pode estar fazendo PUT, mas é inconsistente.

### BAIXO — Query Completa de Serviços em Match

Tanto `whatsapp.py:567-570` quanto `orcamentos.py:2499-2506` carregam **todos** os serviços ativos da empresa em memória para fazer o match. Para empresas com muitos serviços, isso pode ser custoso. Uma query com filtro SQL seria mais eficiente.

---

## 7. Melhor Ponto para Alterar com Segurança

### Para alterações no CRUD do catálogo:
- `app/routers/catalogo.py` — rotas HTTP
- `app/services/catalogo_service.py` — regras de negócio
- `app/models/models.py` — estrutura do banco
- `app/schemas/schemas.py` — contratos de API
- `cotte-frontend/catalogo.html` — página principal

### Para corrigir a duplicação de busca por similaridade:
1. Criar `app/services/catalogo_busca_service.py` com a função centralizada
2. Remover `_encontrar_servico_catalogo` de `whatsapp.py`
3. Remover `_encontrar_servico_catalogo_orc` de `orcamentos.py`
4. Remover `_normalizar_texto` de `whatsapp.py` e `_normalizar_texto_orc` de `orcamentos.py`
5. Importar a função centralizada nos dois routers

### Para mover regras de preço para o service:
- Extrair lógica de `catalogo.py:862-867` e `whatsapp.py:665-674` para `catalogo_service.py`
- Criar função `resolver_preco_item(servico_match, ia_valor)` que encapsula a regra

### Para mover importação para o service:
- Mover `_enriquecer_com_duplicatas` e lógica de `importar_lote` para `catalogo_service.py`
- O router chamaria o service com validação de payload

---

## Mapa de Impacto por Alteração

| Alteração | Impacto |
|-----------|---------|
| Modelo `Servico` (nova coluna) | catálogo + orçamentos + WhatsApp + templates + importação + seed |
| Schema `ServicoOut` (campo novo) | todos os endpoints que retornam serviços + 3+ frontends |
| Lógica de similaridade | WhatsApp bot + chat interno de orçamentos (2 pontos) |
| Lógica de preço | WhatsApp bot + chat interno + página de catálogo |
| Permissões "catalogo" | `auth.py` + todas rotas do router + frontend `Permissoes.pode()` |
| Template de segmento | apenas `template_segmento_service.py` (isolado) |
| Seed de categorias | apenas `catalogo_service.py` (isolado) |

---

*Documento gerado em 2026-03-23. Baseado em análise estática do código-fonte do projeto COTTE.*
