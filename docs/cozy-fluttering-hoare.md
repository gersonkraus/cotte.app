---
title: Cozy Fluttering Hoare
tags:
  - tecnico
prioridade: media
status: documentado
---
# Plano: Introduzir Jinja2 para Layout Base

## Contexto

O frontend tem 34 arquivos HTML estáticos, cada um com ~30 linhas de boilerplate idêntico:
- script de tema (localStorage)
- Google Fonts (preconnect + link)
- CSS links com versões (`style.css?v=3`)
- script tags em ordem específica (`utils.js`, `api.js`, `layout.js`)

Problema: mudar um número de versão (ex: `api.js?v=9` → `v=10`) exige editar 34 arquivos. A sidebar já é dinâmica via `layout.js` (faz chamada à API) e não muda — permanece JavaScript.

**Objetivo**: Usar Jinja2 para eliminar boilerplate duplicado. A sidebar continua JS. Risco baixo por ser migração incremental com fallback automático.

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
| `sistema/app/templates/` | Já existe (tem `orcamento.html` de PDF) |
| `sistema/cotte-frontend/js/layout.js` | Não muda — sidebar continua JS |
| `sistema/cotte-frontend/clientes.html` | Primeira página a migrar (teste) |

---

## Implementação

### Fase 1 — Setup Jinja2 em main.py

```python
# main.py
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(_BASE_DIR / "app/templates"))

# Rota de página migrada (ANTES do app.mount)
@app.get("/app/clientes.html", include_in_schema=False)
async def page_clientes(request: Request):
    return templates.TemplateResponse("pages/clientes.html", {"request": request})

# Mount estático permanece como fallback (não muda)
app.mount("/app", StaticFiles(directory=str(_BASE_DIR / "cotte-frontend"), html=True), name="frontend")
```

### Fase 2 — Criar `base.html`

**Caminho**: `sistema/app/templates/base.html`

Conteúdo do template base (extrai o boilerplate comum):

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

## Caminho dos arquivos a criar/editar

```
sistema/
├── app/
│   ├── main.py                          ← EDITAR: adicionar templates + rotas
│   └── templates/
│       ├── base.html                    ← CRIAR
│       └── pages/
│           └── clientes.html            ← CRIAR (piloto)
```

O arquivo original `sistema/cotte-frontend/clientes.html` **permanece intacto** como fallback até a migração ser validada.

---

## Verificação

1. Subir o servidor: `uvicorn sistema.app.main:app --reload`
2. Acessar `/app/clientes.html` → deve renderizar via Jinja2 (checar no Network tab: response é HTML server-side)
3. Sidebar carrega normalmente (JS injeta como sempre)
4. Autenticação funciona (api.js + layout.js não mudaram)
5. Acessar uma página NÃO migrada (ex: `/app/orcamentos.html`) → continua funcionando via StaticFiles
6. Mudar versão de CSS em `base.html` → reflete em todas as páginas migradas automaticamente
