# Handoff: Renderizador Genérico de Listas Paginadas no Assistente IA

**Data:** 2026-05-17
**Status:** Em andamento — implementação frontend completa, aguardando validação em runtime e integração backend

---

## 1. Objetivo

Implementar um sistema de renderização genérico de listas paginadas no assistente IA do COTTE, capaz de exibir qualquer entidade (orçamentos, clientes, NFs, produtos, fornecedores etc.) sem necessidade de criar renderizadores específicos para cada tipo. O objetivo final é que o backend possa definir colunas, labels e formatação via payload, e o frontend renderize automaticamente sem deploy adicional.

---

## 2. Contexto essencial

### Stack
- **Frontend:** HTML/CSS/JavaScript vanilla (sem framework), arquivos em `sistema/cotte-frontend/`
- **Backend:** FastAPI, respostas via SSE streaming (`POST /ai/assistente/stream`)
- **Assistente IA:** Renderizadores em `assistente-ia-render-types.js`, facade em `assistente-ia-render.js`, shell/eventos em `assistente-ia-shell.js`
- **Testes e2e:** Playwright, fixture em `tests/e2e/assistente-ia-fixture.js`

### Decisões tomadas
1. **Renderer genérico como fallback** — Os renderizadores específicos (`renderListaOrcamentos`, `renderListaClientes`) mantêm prioridade no `resolveAssistenteRenderResult`. O genérico só atua quando `is_list: true` e nenhum renderer específico capturou.
2. **Config registry pattern** — `_GENERIC_LIST_ENTITY_CONFIGS` guarda configs por entity key, com registro dinâmico via `registerGenericEntityConfig()`.
3. **Auto-detecção de colunas** — Quando não há `columnSchema`, extrai colunas automaticamente dos objetos (heurística por chave/tipo).
4. **`entity_config` embutido no payload** — O backend pode enviar `entity_config` em `dados` ou `_meta_frontend_data`; o frontend auto-registra e renderiza.
5. **Formatadores** — `_formatValueBySchema` suporta: `currency`, `date`, `date_short`, `boolean`, `percent`, `cnpj`, `cpf`, `phone`.
6. **Paginação via cursor** — `has_more` + `next_cursor`, botão "Carregar mais" com `data-generic-load-more`.
7. **Preservação de contrato** — Nenhuma mudança no backend foi necessária; tudo é retrocompatível.

### Restrições
- Regras do AGENTS.md: menor alteração possível, não quebrar fluxo existente, não refatorar sem pedido.
- O fluxo de `orcamentos` e `clientes` com renderizadores específicos NÃO foi alterado — continuar funcionando igual.
- CSS existente reutilizado (`.ai-table`, `.orc-list-card`, `.orc-list-card__load-more`, `.orc-list-empty`, `.semantic-printable-card`).

---

## 3. O que já foi feito

### Etapa 1: Investigação
- Mapeou fluxo completo do stream: `assistente-ia.js` → POST `/ai/assistente/stream` → SSE chunks → `resolveAssistenteRenderResult` → render.
- Identificou que `is_list` chegava no `assistente-ia.js:1044` mas só fazia `console.log`.
- Mapeou backend: `is_list` gerado em `cotte_ai_hub.py:2489` (orcamentos), `:2507` (clientes), `:3536` (fastpath V2).
- Confirmou que backend NÃO envia `columns`/schema — só rows cruas + `next_cursor` + `has_more`.

### Etapa 2: Implementação do renderer genérico (`renderGenericDataList`)
- Criado em `assistente-ia-render-types.js` (~200 linhas).
- Detecta entidade automaticamente (procura array conhecido em `_GENERIC_LIST_ENTITY_CONFIGS`, depois qualquer array de objetos).
- Auto-detecção de colunas com heurística (pula `id`, `empresa_id`, etc.).
- Formatação automática: moeda (R$), datas (dd/mm/aaaa), booleanos, ISO dates.
- Tabela desktop + printable card (Imprimir/CSV/PDF) + pills de totais por status.
- Botão "Carregar mais" com cursor e filtros preservados em data-attrs.
- Fallback visual: `.orc-list-empty` com mensagem contextual quando lista vazia.

### Etapa 3: Integração no fluxo existente
- **`resolveAssistenteRenderResult`** — adicionado handler `is_list` ANTES de `renderTabelaRica`, DEPOIS dos renderizadores específicos.
- **`assistente-ia.js:1044`** — substituído `console.log` por verificação de existência do renderer.
- **`assistente-ia-render.js`** — `_appendGenericRowsToExistingTable()` para acrescentar rows sem re-renderizar card inteiro.
- **`assistente-ia-render.js`** — `processAIResponse` estendido com `_isSilentLoadMoreGeneric`.
- **`assistente-ia-shell.js`** — handler de clique no botão "Carregar mais" genérico (`data-generic-load-more`).

### Etapa 4: Registro dinâmico (`registerGenericEntityConfig`)
- `registerGenericEntityConfig(key, config)` — registra entidade em runtime.
- `unregisterGenericEntityConfig(key)` — remove.
- `getRegisteredEntityConfigs()` — retorna todas.

### Etapa 5: `columnSchema` com labels e formatos customizados
- Config pode ter `columnSchema: [{ key, label, format, align }]`.
- Quando presente, substitui auto-detecção completamente.
- `_formatValueBySchema()` com formatadores: currency, date, date_short, boolean, percent, cnpj, cpf, phone.
- Headers usam labels do schema; alinhamento respeitado.

### Etapa 6: `entity_config` do backend (auto-registro)
- `_entityConfigToGenericConfig()` converte schema do backend para config interna.
- `renderGenericDataList` detecta `dados.entity_config` e `_meta_frontend_data.entity_config`.
- Auto-registra via `registerGenericEntityConfig` antes de renderizar.
- Permite que o backend defina tudo (título, colunas, formatos) sem mudança no JS.

### Etapa 7: Testes e2e
- **Novo arquivo:** `tests/e2e/assistente-ia-generic-list.spec.js` (12 testes).
- **Fixture atualizada:** `tests/e2e/assistente-ia-fixture.js` com mocks para entidades genéricas, lista vazia, register entity, entity config auto.
- Testes cobrem: renderização, "Carregar mais", pills, printable card, fallback vazio, registro/desregistro, columnSchema, entity_config auto, formatação.

### O que foi descartado
- Nada foi descartado. Toda implementação foi incremental sobre o existente.

---

## 4. Estado atual

### Funciona (implementado, validado sintaticamente)
- `renderGenericDataList()` com auto-detecção e columnSchema
- `_formatValueBySchema()` com 8 formatadores
- `_entityConfigToGenericConfig()` conversão de schema do backend
- Auto-registro de `entity_config` do payload
- `registerGenericEntityConfig()` / `unregisterGenericEntityConfig()` / `getRegisteredEntityConfigs()`
- Fallback visual para lista vazia
- Integração no `resolveAssistenteRenderResult` (prioridade correta)
- Handler "Carregar mais" genérico no shell
- `_appendGenericRowsToExistingTable` no render
- Testes e2e (12 specs) com fixture atualizada

### Ainda não validado
- **Runtime real** — não foi testado com o servidor local rodando (só validação de sintaxe `node -c`)
- **Playwright** — testes e2e não foram executados (dependem de ambiente Playwright configurado)
- **Backend enviando `entity_config`** — o backend ainda não foi alterado para enviar `entity_config` no payload

### Não quebra nada existente
- `renderListaOrcamentos` e `renderListaClientes` continuam com prioridade no resolver
- Fluxo de stream, tool_running, langgraph_step, cache badge — tudo intocado
- Todos os 4 arquivos JS passaram em `node -c`

---

## 5. Próximos passos

1. **Validar em runtime local** — subir servidor, pedir ao assistente "listar orçamentos" (deve usar renderer específico, sem mudança) e confirmar que nada quebrou
2. **Testar fallback genérico** — simular resposta do backend com `is_list: true` para uma entidade sem renderer específico (ex.: produtos) e verificar renderização
3. **Executar testes Playwright** — `npx playwright test tests/e2e/assistente-ia-generic-list.spec.js`
4. **(Opcional) Implementar `entity_config` no backend** — modificar `cotte_ai_hub.py` para incluir `entity_config` no `_meta_frontend_data` de respostas de lista, começando por uma entidade piloto (ex.: fornecedores)
5. **Adicionar `format: 'badge'` no `_formatValueBySchema`** — renderizar badges automáticos com cor por status
6. **Adicionar `entity_config.actions`** — botões de ação definidos no schema do backend (ex.: `{ icon: "💬", href_template: "https://wa.me/55{{telefone}}" }`)

---

## 6. Perguntas em aberto

1. O backend deve começar a enviar `entity_config` imediatamente, ou primeiro validamos o genérico com auto-detecção em produção?
2. Quais entidades adicionais (além de orcamentos e clientes) devem ser priorizadas para renderização genérica?
3. O `.orc-list-card` com `width: max-content` no CSS pode causar overflow em tabelas largas com muitas colunas — precisa de ajuste?
4. Deve haver um limite de colunas no schema do backend (ex.: max 8)?

---

## 7. Artefatos relevantes

### Arquivos alterados
| Arquivo | Linhas aprox. alteradas |
|---------|------------------------|
| `sistema/cotte-frontend/js/assistente-ia-render-types.js` | +320 linhas (renderer genérico, columnSchema, entity_config, formatters, registro) |
| `sistema/cotte-frontend/js/assistente-ia-render.js` | +100 linhas (`_appendGenericRowsToExistingTable`, suporte `_isSilentLoadMoreGeneric`) |
| `sistema/cotte-frontend/js/assistente-ia-shell.js` | +40 linhas (handler "Carregar mais" genérico) |
| `sistema/cotte-frontend/js/assistente-ia.js` | ~3 linhas (substituído console.log) |
| `tests/e2e/assistente-ia-fixture.js` | +80 linhas (mocks) |
| `tests/e2e/assistente-ia-generic-list.spec.js` | **Novo** — 12 testes |

### Arquivos NÃO alterados (referência)
- `sistema/cotte-frontend/css/assistente-ia.css` — reutilizado CSS existente
- `sistema/app/routers/ai_hub.py` — endpoint stream não modificado
- `sistema/app/services/cotte_ai_hub.py` — backend não modificado

### Funções expostas globalmente (window.*)
- `renderGenericDataList(dados)` — renderer principal
- `registerGenericEntityConfig(key, config)` — registro dinâmico
- `unregisterGenericEntityConfig(key)` — desregistro
- `getRegisteredEntityConfigs()` — listar configs
- `_entityConfigToGenericConfig(entityConfig, entityKey)` — conversão de schema do backend
- `_formatValueBySchema(raw, col)` — formatador por tipo
- `_appendGenericRowsToExistingTable(dados)` — append de rows

### Formato de `entity_config` esperado pelo frontend
```json
{
  "title": "Fornecedores",
  "title_key": "razao_social",
  "badge_field": "status",
  "badge_map": { "ativo": "badge-aprovado", "inativo": "badge-recusado" },
  "load_more_label": "Carregar mais fornecedores",
  "load_more_command": "Liste mais fornecedores com cursor \"{{cursor}}\", limite {{limit}}.",
  "columns": [
    { "key": "razao_social", "label": "Razão Social", "align": "left" },
    { "key": "cnpj", "label": "CNPJ", "format": "cnpj" },
    { "key": "total_compras", "label": "Total", "format": "currency", "align": "right" },
    { "key": "status", "label": "Situação", "format": "badge" }
  ]
}
```

### Formato de dados do backend (payload com `is_list`)
```json
{
  "is_list": true,
  "total": 47,
  "has_more": true,
  "next_cursor": "cursor-abc-123",
  "limit": 10,
  "filtros": { "status": "ativo" },
  "totais_por_status": { "ativo": 30, "inativo": 17 },
  "entity_config": { "...como acima..." },
  "fornecedores": [
    { "razao_social": "Empresa Alpha", "cnpj": "12345678000190", "total_compras": 15000.50, "status": "ativo" }
  ]
}
```

### Comandos úteis
```bash
# Validar sintaxe JS
node -c sistema/cotte-frontend/js/assistente-ia-render-types.js
node -c sistema/cotte-frontend/js/assistente-ia-render.js
node -c sistema/cotte-frontend/js/assistente-ia-shell.js
node -c sistema/cotte-frontend/js/assistente-ia.js

# Rodar testes e2e (requer Playwright)
npx playwright test tests/e2e/assistente-ia-generic-list.spec.js

# Rodar servidor local
cd sistema && python -m uvicorn app.main:app --reload --port 8000
```

---

## 8. Instruções pra próxima sessão

- **Tom:** Direto, pragmático, em português do Brasil (seguir AGENTS.md).
- **Prioridade:** Validar em runtime antes de adicionar features. Não assumir que funciona sem testar.
- **Armadilhas:**
  - NÃO alterar `renderListaOrcamentos` ou `renderListaClientes` — eles têm prioridade no resolver e não devem ser afetados.
  - O CSS `.orc-list-card` tem `width: max-content` — tabelas largas podem transbordar. Se isso acontecer, ajustar no CSS, não no JS.
  - O `_GENERIC_LIST_ENTITY_CONFIGS` já tem configs para `orcamentos` e `clientes` com actions específicas — não remover.
  - O handler de "Carregar mais" genérico no shell.js verifica `!loadMoreGenericBtn.closest('[data-orcamentos-load-more]') && !loadMoreGenericBtn.closest('[data-clientes-load-more]')` para não conflitar com os handlers específicos — manter essa guarda.
  - Os testes e2e dependem do fixture interceptando `/ai/assistente/stream` — se adicionar novos casos, adicionar no fixture também.
- **Regra do AGENTS.md:** Regra crítica de IA — se mexer em `ai_intention_classifier.py` ou tools, rodar `cd sistema && pytest tests/test_ai_tool_routing.py`. Nesta sessão não mexemos nesses arquivos.
