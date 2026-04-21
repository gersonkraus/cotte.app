# Análise do Módulo de Catálogo — COTTE
**Data:** 21/04/2026  
**Objetivo:** Identificar bugs, falhas de processo, falhas de lógica, falta de funcionalidades e problemas de integração antes da comercialização.

---

## 1. Inventário de Arquivos Analisados

### Backend
| Arquivo | Linhas | Papel |
|---|---|---|
| `app/routers/catalogo.py` | 461 | Router principal — CRUD, upload, importação |
| `app/services/catalogo_service.py` | 63 | Seeding de catálogo padrão |
| `app/services/template_segmento_service.py` | 462 | Templates por segmento de negócio |
| `app/services/ai_catalog_suggester.py` | 86 | Sugestões de catálogo via IA |
| `app/services/ai_tools/catalogo_tools.py` | 106 | Tools do assistente (MCP-style) |
| `app/repositories/servico_repository.py` | 244 | Repository async (órfão — nunca chamado pelo router) |
| `app/models/models.py` L548–577 | — | Modelos `Servico` e `CategoriaCatalogo` |
| `app/schemas/schemas.py` L691–734 | — | Schemas Pydantic |
| `app/services/ia_service.py` L540–560 | — | `interpretar_tabela_catalogo` |
| `app/services/r2_service.py` | — | Upload e deleção de imagens |

### Frontend
| Arquivo | Linhas |
|---|---|
| `cotte-frontend/catalogo.html` | 1181 |

### Migrations Alembic
- `z009_catalogo_categoria_custo.py` — cria tabela `categorias_catalogo` e colunas `preco_custo`, `categoria_id`
- `20260323_add_categoria_id_servicos.py` — idempotente (redundante com z009)
- `20260323_add_preco_custo_servicos.py` — idempotente (redundante com z009)

### Integrações verificadas
- `app/services/whatsapp_bot_service.py` L519–561
- `app/services/orcamento_bot_service.py` L65–83
- `app/services/cotte_ai_hub.py` L1306–1421
- `app/services/orcamento_core_service.py` L141–163
- `app/routers/orcamentos.py` L310–348, L2163–2199

---

## 2. Bugs Críticos

### 2.1. ✅ CORRIGIDO — `criar_servico` descarta `preco_custo` e `categoria_id`
**Arquivo:** `app/routers/catalogo.py` L129–132  
**Severidade:** CRÍTICO

O schema `ServicoCreate` aceita `preco_custo` e `categoria_id` e o frontend envia ambos no payload (catalogo.html L753–760), mas o construtor `Servico(...)` ignora os dois campos:

```python
# BUGADO — campos enviados são silenciosamente descartados
servico = Servico(
    empresa_id=usuario.empresa_id,
    nome=dados.nome,
    descricao=dados.descricao,
    preco_padrao=dados.preco_padrao,
    unidade=dados.unidade,
    ativo=True,
)
```

**Impacto:** Usuário cria item com custo e categoria, a UI mostra sucesso, mas ao reabrir o modal os campos chegam vazios. Toda análise financeira baseada em `preco_custo` fica inoperante.

---

### 2.2. ✅ CORRIGIDO — `ai_catalog_suggester` usa `AsyncSession` com sessão síncrona
**Arquivo:** `app/services/ai_catalog_suggester.py` (reescrito); `cotte_ai_hub.py` L1421  
**Severidade:** CRÍTICO

`buscar_sugestoes_catalogo` recebe `db: AsyncSession` e usa `await db.execute(...)`, mas `cotte_ai_hub.py` injeta a sessão síncrona retornada por `get_db()`. O `try/except` captura o erro silenciosamente e retorna `[]`, fazendo a funcionalidade de "sugestão de catálogo pelo assistente" estar **100% quebrada na prática**.

---

### 2.3. ✅ CORRIGIDO — Frontend usa `PATCH` mas backend só expõe `PUT`
**Arquivo:** `app/routers/catalogo.py` — adicionado `PATCH /{servico_id}`  
**Severidade:** CRÍTICO

```js
// catalogo.html L537 — o método PATCH não existe no backend
await api.patch(`/catalogo/${editandoId}`, { ativo: true });
```

O backend expõe apenas `PUT /{servico_id}`. FastAPI devolve **405 Method Not Allowed**. O botão "✅ Ativar" nunca funciona — itens inativados não podem ser reativados.

---

### 2.4. ✅ CORRIGIDO — Modal "Templates de Segmento" existe mas não tem botão de acesso
**Arquivo:** `cotte-frontend/catalogo.html` — botão "📐 Modelos" adicionado na topbar  
**Severidade:** CRÍTICO

A função `abrirModalTemplates()` está definida (L1040) e o modal HTML existe (L276), mas **nenhum botão na UI** chama essa função. Os endpoints `GET /catalogo/templates/segmentos` e `POST /catalogo/templates/{slug}/importar` estão prontos no backend. A feature de onboarding (importar catálogo pré-pronto por segmento: eletricista, pedreiro, pintor, etc.) está **completamente inacessível ao usuário final**.

---

### 2.5. ✅ CORRIGIDO — `seed_catalogo_padrao` nunca comita — seed não persiste
**Arquivo:** `services/catalogo_service.py` — adicionado `db.commit()`; `routers/catalogo.py` — chamadas removidas das rotas GET  
**Severidade:** ALTO

O service chama `db.flush()` mas nunca `db.commit()`. Em rotas GET o FastAPI não comita automaticamente, então as categorias e serviços de demonstração são criados em memória e revertidos ao final de cada request. Isso faz o seed rodar em **toda chamada GET** gerando latência extra, e ainda assim os dados nunca são gravados.

---

### 2.6. Itens inativados: integração orçamento quebra ao re-editar
**Arquivo:** `app/routers/orcamentos.py` L2163  
**Severidade:** ALTO

`_encontrar_servico_catalogo_orc` filtra `ativo==True`. Se o item do catálogo for inativado após o orçamento ser criado, ao re-editar o orçamento o link `servico_id` fica sem correspondência ativa — o item aparece sem nome ou sem preço referenciado.

---

### 2.7. `importar_lote` conta itens errado
**Arquivo:** `app/routers/catalogo.py` L411–424  
**Severidade:** ALTO

Após importar, o endpoint recarrega todos os serviços cujos nomes constam no payload — inclusive os que já existiam antes. O campo `criados` na resposta reflete o total encontrado, não o total realmente criado, inflando o número reportado ao usuário.

---

### 2.8. `analisar_arquivo` não valida retorno da IA (crash em KeyError)
**Arquivo:** `app/routers/catalogo.py` L280–292  
**Severidade:** ALTO

`_enriquecer_com_duplicatas` chama `item["nome"].lower()` sem verificar a chave. Se o LLM retornar um item sem `nome` ou com estrutura diferente, `KeyError` derruba todo o endpoint de importação.

---

### 2.9. ✅ CORRIGIDO — Sem unique constraint em `servicos(empresa_id, nome)`
**Arquivo:** `models/models.py` — `UniqueConstraint` adicionado; migration `z022_unique_servico_empresa_nome.py` criada  
**Severidade:** ALTO

Não há `UniqueConstraint("empresa_id", "nome")` no modelo. Chamadas concorrentes ou chamadas diretas à API permitem duplicatas. A validação de duplicata existe apenas no frontend e em partes do fluxo de importação.

---

### 2.10. `buscar_servico_similar` usa substring — muitos falsos positivos
**Arquivo:** `app/repositories/servico_repository.py` L219–240  
**Severidade:** ALTO

```python
if nome_lower in servico_nome_lower or servico_nome_lower in nome_lower:
    return servico
```

"Porta" casa com "Porta de madeira", "Porta janela", "Porta-retrato". O sistema bloqueia cadastros legítimos por falsa duplicata.

---

### 2.11. Template de segmento não passa `descricao` e `preco_custo` ao importar
**Arquivo:** `app/services/template_segmento_service.py` L443–451  
**Severidade:** ALTO

```python
servico = Servico(
    empresa_id=empresa_id,
    nome=item["nome"],
    preco_padrao=item["preco_padrao"],
    unidade=item["unidade"],
    categoria_id=mapa_categorias.get(item.get("categoria")),
    ativo=True,
    # preco_custo e descricao ausentes
)
```

---

### 2.12. `atualizar_servico` aceita `preco_padrao` negativo (sem validação)
**Arquivo:** `app/routers/catalogo.py` L162–163; `app/schemas/schemas.py`  
**Severidade:** ALTO

`ServicoBase.preco_padrao: Decimal = Decimal("0.0")` não tem `ge=0`. Qualquer cliente com acesso direto à API pode persistir preço negativo.

---

### 2.13. Upload sem verificação de magic bytes
**Arquivo:** `app/routers/catalogo.py` L212  
**Severidade:** ALTO

Apenas a extensão do arquivo é verificada. Um `.jpg` com conteúdo malicioso (SVG com XSS, etc.) passa pelo upload.

---

### 2.14. ✅ CORRIGIDO — `analisar_arquivo` não limita tamanho no servidor
**Arquivo:** `routers/catalogo.py` — verificação de 5MB adicionada após `file.read()`  
**Severidade:** ALTO

O frontend valida 5MB, mas o backend lê `await file.read()` sem limite. Request direto pode enviar 500MB e exaurir memória.

---

### 2.15. ✅ CORRIGIDO — Sem rate limit nas rotas que chamam LLM
**Arquivo:** `routers/catalogo.py` — throttle `_checar_rate_limit_ia()` aplicado (10 chamadas/min por empresa)  
**Severidade:** CRÍTICO (segurança/custo)

Usuário autenticado mal-intencionado pode gastar todos os créditos de IA do sistema sem limitação.

---

## 3. Falhas de Processo / Fluxos Quebrados

| # | Problema | Arquivo | Severidade |
|---|---|---|---|
| 3.1 | Fluxo "Reativar item" não funciona (PATCH inexistente — item 2.3) | catalogo.html, catalogo.py | CRÍTICO |
| 3.2 | Fluxo "Importar template de segmento" sem UI de entrada (item 2.4) | catalogo.html | CRÍTICO |
| 3.3 | `toggleAtivo` definida no JS mas nunca chamada (código morto — usa `toggleAtivoItem`) | catalogo.html L794–802 | ALTO |
| 3.4 | Deleção de imagem falha com 503 se R2 não configurado, mesmo para imagens locais antigas | catalogo.py L220–221 | ALTO |
| 3.5 | CSV exportado pelo Excel (BR) usa `;` como separador — importação falha silenciosamente | catalogo.py L316 | MÉDIO |
| 3.6 | Seed de catálogo padrão roda em toda chamada GET listagem (latência + nunca persiste) | catalogo.py L111 | ALTO |
| 3.7 | `importar_lote` sem limite de itens no payload (100.000 itens trava o worker) | catalogo.py | ALTO |
| 3.8 | Modal de categorias não valida duplicata ao criar nova categoria | catalogo.html + catalogo.py L54–64 | MÉDIO |
| 3.9 | Filtros (status, categoria, busca) não são persistidos ao navegar e voltar | catalogo.html | MÉDIO |

---

## 4. Falhas de Lógica

### 4.1. Cálculo de margem silencioso para margem ≥ 100%
**Arquivo:** `cotte-frontend/catalogo.html` L716–734  
Se o usuário digitar margem 100 ou mais, a função `_calcularPreco` não atualiza o campo preço sem nenhuma mensagem de erro. Fórmula usa "margem sobre preço de venda" (markup-down), enquanto vendedores brasileiros tipicamente pensam em "markup sobre custo" — falta oferecer as duas opções.

### 4.2. Match de catálogo por WhatsApp sem tie-breaker
**Arquivo:** `app/services/whatsapp_bot_service.py` L538–561  
Dois serviços com score igual: o sistema escolhe o primeiro encontrado (ordem de inserção). Resultado: item errado pode virar orçamento.

### 4.3. Busca de catálogo IA sem normalização de acentos
**Arquivo:** `app/services/cotte_ai_hub.py` L1374  
`ilike('%pintura%')` não encontra "Pintura Acrílica" quando o usuário digita "pintura acrilica". PostgreSQL precisa de `unaccent` para isso.

### 4.4. `preco_custo` existe no banco mas nunca é usado pelo módulo financeiro
**Arquivo:** `app/models/models.py` L571; financeiro (ausente)  
O campo foi criado na migration mas não há cálculo de margem, DRE por item ou análise de rentabilidade em lugar algum. A coluna é uma ilha de dados.

### 4.5. Margem `NaN` quando preço e custo são ambos zero
**Arquivo:** `cotte-frontend/catalogo.html` — `_calcularMargem`  
`(0-0)/0` resulta em `NaN` exibido no campo de margem.

### 4.6. `ServicoOut.from_orm()` — API deprecada do Pydantic v2
**Arquivo:** `app/routers/catalogo.py` L423  
Em Pydantic v2 o correto é `ServicoOut.model_validate(s)`. Emite `DeprecationWarning` que polui os logs.

---

## 5. Falta de Funcionalidades Essenciais

### 5.1. ✅ CORRIGIDO — Sem paginação e busca server-side
`GET /catalogo/` agora aceita `skip`, `limit` (padrão 500). Frontend pode paginar conforme necessário.

### 5.2. ✅ CORRIGIDO — Sem endpoint `GET /catalogo/{id}`
Endpoint `GET /catalogo/{servico_id}` adicionado.

### 5.3. ✅ CORRIGIDO — Sem filtro por categoria no backend
`GET /catalogo/` agora aceita parâmetro `categoria_id` para filtro server-side.

### 5.4. [CRÍTICO] Sem campos de estoque / SKU / NCM
Para qualquer empresa que vende produtos (não só serviços), faltam:
- `sku`, `codigo_barras`, `ncm`, `cest`
- `estoque_atual`, `estoque_minimo`
- `unidade_tributavel`

### 5.5. [ALTO] Sem histórico de preço
Empresas com orçamentos recorrentes precisam rastrear quando o preço mudou.

### 5.6. [ALTO] Sem exportação (CSV/Excel) do catálogo
Impossível fazer backup ou migrar entre empresas.

### 5.7. [ALTO] Sem suporte a múltiplas imagens / galeria
`Servico.imagem_url` é um único `String(300)`.

### 5.8. [ALTO] Categoria sem flag `ativa` (soft-delete)
Só é possível excluir (bloqueado se tem itens vinculados). Não há como arquivar/desativar uma categoria.

### 5.9. [ALTO] Sem campos comerciais: preço promocional, desconto máximo, validade do preço
Orçamentos não conseguem aplicar regras de preço automáticas.

### 5.10. [MÉDIO] Sem tags / etiquetas multi-valor por item

### 5.11. [MÉDIO] Sem hierarquia de categorias (subcategorias)

### 5.12. [MÉDIO] Sem validação de unidade contra lista padrão no backend
Frontend tem `<select>` com unidades, mas backend aceita qualquer string. Importação gera "unid", "pç", "peça" — inconsistência de exibição.

### 5.13. [MÉDIO] Sem estatísticas expostas via API
`ServicoRepository.get_estatisticas` existe mas não há rota. Dashboard do catálogo não pode ser construído.

### 5.14. [MÉDIO] Sem ordenação manual de categorias
Só ordena por nome. Impossível priorizar "Serviços Principais" acima de "Outros".

### 5.15. [MÉDIO] Imagem do item não aparece no PDF do orçamento
O schema `ItemOrcamentoOut` tem campo `imagem_url` opcional mas nunca é populado na geração do PDF.

---

## 6. Integração com o Resto do Sistema

### 6.1. Orçamentos
| Status | Detalhe |
|---|---|
| ✅ OK | `ItemOrcamento.servico_id` FK para `Servico` (opcional) corretamente configurada |
| ✅ OK | `_encontrar_servico_catalogo_orc` faz match razoável para casos simples |
| ⚠️ ALTO | Inativar item após orçamento: ao re-editar, `servico_id` fica sem match ativo |
| ⚠️ ALTO | Imagem do item nunca aparece no orçamento gerado (campo sem população) |
| ⚠️ MÉDIO | `ItemOrcamento` não espelha `preco_custo` — margem histórica fica errada se custo mudar |

### 6.2. WhatsApp / Bot IA
| Status | Detalhe |
|---|---|
| ✅ OK | Match por palavras-chave funciona em casos simples |
| ⚠️ MÉDIO | False positives em mensagens longas (score por interseção de palavras) |
| ⚠️ ALTO | Quando serviço não encontrado no catálogo, bot cria item avulso sem sugerir cadastro. O catálogo nunca "aprende" via bot |

### 6.3. Assistente IA / Hub
| Status | Detalhe |
|---|---|
| ❌ CRÍTICO | `ai_catalog_suggester` quebrado (sessão async vs sync — item 2.2) |
| ⚠️ ALTO | `ilike` sem `unaccent` — serviços com acento não encontrados |
| ⚠️ ALTO | `catalogo_tools.py` não tem tools para atualizar/deletar item ou gerenciar categorias — assistente não consegue administrar catálogo conversacionalmente |
| ⚠️ MÉDIO | `cadastrar_material` (tool) não aceita `categoria_id` nem `preco_custo` — mesmo bug do endpoint REST |

### 6.4. Módulo Financeiro
| Status | Detalhe |
|---|---|
| ❌ CRÍTICO | `preco_custo` existe no banco mas nunca é usado pelo financeiro. Não há cálculo de margem, DRE por item ou análise de rentabilidade |
| ⚠️ MÉDIO | Sem espelhamento de `preco_custo` em `ItemOrcamento` |

### 6.5. Onboarding
| Status | Detalhe |
|---|---|
| ✅ OK | `onboarding_service.py` conta serviços ativos para progresso |
| ⚠️ ALTO | `seed_catalogo_padrao` não comita → contador sempre zero → passo de onboarding nunca fecha |

---

## 7. O que está Funcionando Corretamente

1. **Autenticação e multi-tenancy:** `exigir_permissao` e filtros `Servico.empresa_id` aplicados em todas as rotas.
2. **CRUD básico de categorias:** criar, listar, excluir funcionam.
3. **Upload de imagem no R2:** fluxo com limpeza de imagem anterior está correto (quando R2 configurado).
4. **Soft-delete de serviço:** `ativo=False` preserva FK em orçamentos antigos.
5. **Templates de segmento — backend:** `listar_segmentos`, `obter_template`, `importar_template_para_empresa` bem codificados.
6. **Schema Pydantic de retorno:** `ServicoOut` com `from_attributes=True` retorna categoria aninhada corretamente.
7. **Integração básica orçamento → catálogo:** `_encontrar_servico_catalogo_orc` funciona para casos simples.
8. **Migrations idempotentes:** as migrations `20260323_*` verificam existência antes de alterar.
9. **UI de listagem:** layout de cards responsivo e esteticamente correto.
10. **Importação via IA (arquitetura):** fluxo geral de importação CSV/XLSX/PDF com análise por LLM é bem estruturado.
11. **Tenant context:** `set_tenant_context` chamado corretamente em `catalogo.py` L105.
12. **Relacionamentos ORM:** `Servico.categoria` e `Categoria.servicos` com `back_populates` corretos.

---

## 8. Resumo de Severidades

| Severidade | Quantidade |
|---|---|
| **CRÍTICO** | 8 itens |
| **ALTO** | 22 itens |
| **MÉDIO** | 16 itens |
| **BAIXO** | 1 item |

---

## 9. Plano de Ação Mínimo para Comercialização

> **Status:** ✅ Todos os 10 itens concluídos em 21/04/2026.

| # | Fix | Arquivo(s) alterado(s) | Status |
|---|---|---|---|
| 1 | `criar_servico` — persistir `preco_custo` e `categoria_id` | `routers/catalogo.py` L131–132 | ✅ Concluído |
| 2 | Endpoint `PATCH /{servico_id}` para reativar item | `routers/catalogo.py` L194–220 | ✅ Concluído |
| 3 | Botão "📐 Modelos" na topbar chamando `abrirModalTemplates()` | `cotte-frontend/catalogo.html` L26–29, L383–385 | ✅ Concluído |
| 4 | Remover `seed_catalogo_padrao` das rotas GET + adicionar `db.commit()` no service | `routers/catalogo.py` L41–48; `services/catalogo_service.py` L63 | ✅ Concluído |
| 5 | `ai_catalog_suggester` — query síncrona direta em vez de async | `services/ai_catalog_suggester.py` (reescrito); `cotte_ai_hub.py` L1421 | ✅ Concluído |
| 6 | `UniqueConstraint("empresa_id", "nome")` em `Servico` + migration | `models/models.py` L563–565; `alembic/versions/z022_unique_servico_empresa_nome.py` | ✅ Concluído |
| 7 | Paginação (`skip`, `limit`) e filtro `categoria_id` no `GET /catalogo/` | `routers/catalogo.py` L98–121 | ✅ Concluído |
| 8 | Endpoint `GET /catalogo/{servico_id}` | `routers/catalogo.py` L123–142 | ✅ Concluído |
| 9 | Limite de 5MB no servidor em `analisar_arquivo` | `routers/catalogo.py` L374–376 | ✅ Concluído |
| 10 | Rate limit (10 chamadas/min por empresa) nas rotas LLM | `routers/catalogo.py` L34–52 (throttle) + L338, L376 | ✅ Concluído |

---

## 10. Pendências Pós-Lançamento (próximas sprints)

Itens que não bloqueiam o lançamento mas devem ser endereçados nas primeiras semanas:

| Severidade | Item |
|---|---|
| ALTO | `preco_custo` integrado ao módulo financeiro (margem, DRE por item) |
| ALTO | Imagem do item populada no PDF do orçamento |
| ALTO | Exportação CSV/Excel do catálogo |
| ALTO | Flag `ativa` em `CategoriaCatalogo` (soft-delete de categoria) |
| ALTO | `catalogo_tools.py` — tools faltando: atualizar, deletar, listar categorias |
| MÉDIO | Normalização de acentos na busca IA (`unaccent` PostgreSQL) |
| MÉDIO | Campos comerciais: preço promocional, desconto máximo, validade |
| MÉDIO | Validação de unidade contra lista padrão no backend |
| MÉDIO | Histórico de preço por item |
| MÉDIO | Paginação no frontend (carregar mais) integrada com `skip`/`limit` do backend |
