---
title: Plano Novo Frontend
tags:
  - roadmap
  - frontend
prioridade: media
status: documentado
---
---
title: Plano Novo Frontend
tags:
  - roadmap
  - frontend
prioridade: alta
status: documentado
---
# Plano: Modernização do Frontend (Jinja2 + Alpine.js)

## Contexto

O frontend tem 34 arquivos HTML estáticos, cada um com ~30 linhas de boilerplate idêntico:
- script de tema (localStorage)
- Google Fonts (preconnect + link)
- CSS links com versões (`style.css?v=3`)
- script tags em ordem específica (`utils.js`, `api.js`, `layout.js`)

**Problema**: mudar um número de versão (ex: `api.js?v=9` → `v=10`) exige editar 34 arquivos.

A sidebar já é dinâmica via `layout.js` (faz chamada à API) e não muda — permanece JavaScript.

**Objetivo**: Usar Jinja2 para eliminar boilerplate duplicado. Risco baixo por ser migração incremental com fallback automático.

---

## Abordagem: Hybrid Server-Side

- FastAPI continua servindo `/app/` via `StaticFiles` como fallback
- Rotas Jinja2 registradas **antes** do mount de StaticFiles têm prioridade automática
- Páginas migradas usam template; não-migradas continuam via arquivo estático
- Zero downtime, zero breaking changes

---

## Arquivos Críticos

| Arquivo | Papel |
|---|---|
| `sistema/app/main.py` | Adicionar `Jinja2Templates` + rotas de páginas |
| `sistema/app/templates/` | Já existe (tem `orcamento.html` de PDF — não mexer) |
| `sistema/cotte-frontend/js/layout.js` | Não muda — sidebar continua JS |
| `sistema/cotte-frontend/clientes.html` | Primeira página a migrar (teste piloto) |

---

## Implementação

### Fase 1 — Setup Jinja2 em main.py

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(_BASE_DIR / "app/templates"))

# Rota de página migrada (ANTES do app.mount — tem prioridade)
@app.get("/app/clientes.html", include_in_schema=False)
async def page_clientes(request: Request):
    return templates.TemplateResponse("pages/clientes.html", {"request": request})

# Mount estático permanece como fallback (não muda)
app.mount("/app", StaticFiles(directory=str(_BASE_DIR / "cotte-frontend"), html=True), name="frontend")
```

### Fase 2 — Criar `base.html`

**Caminho**: `sistema/app/templates/base.html`

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script>(function(){
    var t=localStorage.getItem("cotte_tema");
    document.documentElement.setAttribute("data-theme", t || "light");
  })()</script>
  <title>COTTE — {% block title %}{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap">
  <link rel="stylesheet" href="/app/css/style.css?v=3">
  {% block extra_css %}{% endblock %}
</head>
<body>

<aside class="sidebar" id="sidebar"></aside>

<main class="main">
  {% block content %}{% endblock %}
</main>

<div class="notif" id="notif"></div>
{% block modals %}{% endblock %}

<script src="/app/js/utils.js?v=1"></script>
<script src="/app/js/api.js?v=9"></script>
<script src="/app/js/layout.js?v=5"></script>
{% block page_scripts %}{% endblock %}
<script>
  inicializarLayout('{% block page_key %}{% endblock %}');
  {% block init %}{% endblock %}
</script>
</body>
</html>
```

### Fase 3 — Criar página migrada (clientes como piloto)

**Caminho**: `sistema/app/templates/pages/clientes.html`

Conteúdo: apenas o que é único da página (topbar + tabela + modais), usando `{% extends "base.html" %}` e blocks.

### Fase 4 — Migração incremental

Ordem sugerida (do mais simples ao mais complexo):
1. `clientes.html` ← piloto
2. `catalogo.html`
3. `relatorios.html`
4. `orcamentos.html`
5. Demais páginas autenticadas

**Páginas que NÃO migrar** (sem sidebar, layout diferente):
- `login.html`, `cadastro.html`, `landing.html`, `orcamento-publico.html`

---

## Estrutura de arquivos a criar/editar

```
sistema/
├── app/
│   ├── main.py                          ← EDITAR: adicionar templates + rotas
│   └── templates/
│       ├── base.html                    ← CRIAR
│       ├── orcamento.html               ← NÃO MEXER (PDF)
│       └── pages/
│           └── clientes.html            ← CRIAR (piloto)
```

O arquivo original `sistema/cotte-frontend/clientes.html` **permanece intacto** como fallback até a migração ser validada.

---

## Verificação

1. Subir o servidor: `uvicorn sistema.app.main:app --reload`
2. Acessar `/app/clientes.html` → deve renderizar via Jinja2
3. Sidebar carrega normalmente (JS injeta como sempre)
4. Autenticação funciona (api.js + layout.js não mudaram)
5. Acessar página NÃO migrada (ex: `/app/orcamentos.html`) → continua via StaticFiles
6. Mudar versão de CSS em `base.html` → reflete em todas as páginas migradas

---

## Fase 5 — Alpine.js (após Jinja2 validado)

Alpine.js resolve um problema diferente do Jinja2: **reatividade no browser** sem precisar de arquivos JS separados.

### O que resolve

Hoje para um modal simples:
```js
// clientes.js
document.getElementById('modal-cliente').classList.add('open');
document.getElementById('btn-salvar').addEventListener('click', salvarCliente);
```

Com Alpine.js, vira direto no HTML:
```html
<div x-data="{ modalAberto: false }">
  <button @click="modalAberto = true">Novo cliente</button>
  <div x-show="modalAberto" x-transition><!-- modal --></div>
</div>
```

### Estratégia de adoção

- **NÃO refatorar** páginas existentes em massa (alto risco)
- Usar Alpine.js em **páginas novas** ou ao refatorar uma existente
- Lógica de negócio (chamadas API, manipulação de dados) permanece em JS
- Alpine.js cuida apenas de: show/hide, toggle, form state, transições

### Como adicionar ao `base.html`

```html
<!-- Adicionar no <head> do base.html -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

### Casos de uso prioritários no COTTE

| Situação | Hoje | Com Alpine.js |
|---|---|---|
| Abrir/fechar modal | `classList.add('open')` em JS | `x-show="modalAberto"` no HTML |
| Toggle de seção | `element.style.display` | `x-show` + `x-transition` |
| Estado de botão loading | `btn.disabled = true` | `x-bind:disabled="salvando"` |
| Tab ativa | Classe manual via JS | `x-data="{ aba: 'geral' }"` |

### Páginas candidatas para piloto Alpine.js

1. Nova página que ainda não existe (risco zero)
2. `configuracoes.html` (muitas abas e toggles, muito JS de UI)
3. `catalogo.html` (filtros e modal simples)

---

## Próximos passos futuros (opcional)

Após validar Jinja2 + Alpine.js:
- HTMX para features novas de formulário/CRUD server-driven
