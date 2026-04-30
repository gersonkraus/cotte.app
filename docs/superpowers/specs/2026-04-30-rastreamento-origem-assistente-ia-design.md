# Design: Rastreamento de Origem — Assistente IA

**Data:** 2026-04-30  
**Status:** Aprovado  
**Objetivo:** Identificar visualmente (UI) e no banco registros criados pelo Assistente IA

---

## Contexto

Registros criados pelo Assistente IA (orçamentos, clientes, itens de catálogo, agendamentos) não são diferenciados dos criados manualmente. O usuário precisa saber visualmente quais registros vieram da IA — tanto nas listas quanto nos detalhes.

---

## Solução

Reutilizar o enum `OrigemRegistro` já existente (`MANUAL | WHATSAPP | ASSISTENTE_IA | WEBHOOK | SISTEMA`) — já usado em `ContaFinanceira` e `PagamentoFinanceiro` — estendendo-o para os modelos que ainda não o possuem.

---

## Seção 1: Banco de Dados e Models

### Models alterados

| Model | Mudança |
|-------|---------|
| `Orcamento` | Adicionar `origem: OrigemRegistro = "manual"` |
| `Cliente` | Adicionar `origem: OrigemRegistro = "manual"` |
| `Servico` | Adicionar `origem: OrigemRegistro = "manual"` |
| `Agendamento` | Já tem campo `origem: OrigemAgendamento` — apenas corrigir valor passado |

### Migration Alembic

Uma migration única:
- `ALTER TABLE orcamentos ADD COLUMN origem VARCHAR(20) NOT NULL DEFAULT 'manual'`
- `ALTER TABLE clientes ADD COLUMN origem VARCHAR(20) NOT NULL DEFAULT 'manual'`
- `ALTER TABLE servicos ADD COLUMN origem VARCHAR(20) NOT NULL DEFAULT 'manual'`

Registros existentes recebem `"manual"` automaticamente — sem dados retroativos de IA.

---

## Seção 2: Backend — Handlers dos AI Tools

### Arquivos a alterar

**`sistema/app/services/ai_tools/orcamento_tools.py`**
- Na chamada `criar_orcamento_core(...)`: adicionar `origem=OrigemRegistro.ASSISTENTE_IA`

**`sistema/app/services/orcamento_core_service.py`**  
- Aceitar parâmetro `origem: OrigemRegistro = OrigemRegistro.MANUAL`
- Setar `orcamento.origem = origem` na criação

**`sistema/app/services/ai_tools/cliente_tools.py`**  
- Na chamada `ClienteService.criar_cliente(...)`: passar `origem=OrigemRegistro.ASSISTENTE_IA`

**`sistema/app/services/cliente_service.py`** (ou similar)  
- Aceitar `origem` e setar no model `Cliente`

**`sistema/app/services/ai_tools/catalogo_tools.py`**  
- No bloco `Servico(...)`: setar `origem=OrigemRegistro.ASSISTENTE_IA`

**`sistema/app/services/ai_tools/agendamento_tools.py`**  
- Corrigir valor: `origem="assistente_tool"` → `origem=OrigemAgendamento.ASSISTENTE_IA`

### Retorno das APIs

Os routers de listagem e detalhe de `Orcamento`, `Cliente`, `Agendamento` e `Servico` já serializam o model completo — o campo `origem` será incluído automaticamente. Confirmar que os schemas Pydantic expõem o campo.

---

## Seção 3: Frontend — Indicador Visual

### Badge padrão

```html
<span class="badge-ia" title="Criado pelo Assistente IA">IA</span>
```

```css
.badge-ia {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  background: #ede9fe;
  color: #7c3aed;
  border: 1px solid #c4b5fd;
}
```

### Páginas com badge na lista

| Página | Coluna/Posição |
|--------|---------------|
| `orcamentos.html` | Coluna "Número" ou nova coluna "Origem" |
| `clientes.html` | Ao lado do nome do cliente |
| `agendamentos.html` | Coluna "Tipo" ou ao lado do número |
| Catálogo (serviços) | Ao lado do nome do serviço |

### Badge no detalhe

- **Orçamento**: cabeçalho do modal/página de detalhe
- **Cliente**: cabeçalho do card de informações
- **Agendamento**: cabeçalho do modal
- **Serviço**: card do item no catálogo

### Lógica JS

```javascript
// Exibir badge se origem === 'assistente_ia'
function renderOrigemBadge(origem) {
  if (origem === 'assistente_ia') {
    return '<span class="badge-ia">✦ IA</span>';
  }
  return '';
}
```

---

## Verificação

1. Criar registro manual → sem badge
2. Criar via Assistente IA → badge aparece na lista e no detalhe
3. Verificar migração: `SELECT origem, count(*) FROM orcamentos GROUP BY origem`
4. Verificar Agendamento: criar via IA e checar `origem = 'assistente_ia'` no banco

---

## Arquivos Críticos

- `sistema/app/models/models.py` — classes `Orcamento`, `Cliente`, `Servico`, `Agendamento`
- `sistema/app/services/ai_tools/orcamento_tools.py` — função `_criar_orcamento`
- `sistema/app/services/ai_tools/cliente_tools.py` — função `_criar_cliente`
- `sistema/app/services/ai_tools/catalogo_tools.py` — função `_cadastrar_material`
- `sistema/app/services/ai_tools/agendamento_tools.py` — função `_criar_agendamento`
- `sistema/app/services/orcamento_core_service.py` — função `criar_orcamento_core`
- Routers de listagem/detalhe: orcamentos, clientes, agendamentos, catálogo
- Frontends: `orcamentos.html`, `clientes.html`, `agendamentos.html`, e catálogo
