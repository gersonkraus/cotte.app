# Campanhas Aba Principal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mover `Campanhas` do hub `Config` para a barra principal do Comercial, posicionando a aba ao lado de `Funil` com a menor alteracao possivel.

**Architecture:** A mudanca fica concentrada em `tenant-comercial.html`, reaproveitando o painel `#tab-campanhas` e os containers existentes. O JavaScript atual ja suporta `switchTab('campanhas')`, entao a implementacao deve apenas alinhar a navegacao HTML com esse comportamento e validar o fluxo manualmente.

**Tech Stack:** HTML estatico, JavaScript vanilla (`tenant-comercial-core.js`, `tenant-comercial.js`), CSS existente do frontend tenant.

---

## Estrutura de arquivos

- Modificar: `sistema/cotte-frontend/tenant-comercial.html`
- Consultar para validacao de comportamento: `sistema/cotte-frontend/js/tenant-comercial-core.js`
- Consultar para carregamento de campanhas: `sistema/cotte-frontend/js/tenant-comercial.js`
- Documento de design de referencia: `docs/superpowers/specs/2026-05-05-campanhas-aba-principal-design.md`

### Task 1: Promover Campanhas para a barra principal

**Files:**
- Modify: `sistema/cotte-frontend/tenant-comercial.html:43-64`
- Modify: `sistema/cotte-frontend/tenant-comercial.html:408-413`
- Test: validacao manual em `sistema/cotte-frontend/tenant-comercial.html`

- [ ] **Step 1: Confirmar o markup atual da navegacao**

Run: `rg -n "data-tab=\"pipeline\"|data-tab=\"config\"|data-sub=\"campanhas\"" sistema/cotte-frontend/tenant-comercial.html`
Expected: linhas com `pipeline`, `config` e `campanhas` dentro da subnav de `Config`.

- [ ] **Step 2: Aplicar a mudanca minima no HTML principal**

Substitua o trecho da barra principal e da subnavegacao de `Config` por este markup:

```html
<div class="admin-tabs" role="tablist" aria-label="Menu Comercial">
  <button class="admin-tab active" data-tab="hoje" role="tab" aria-selected="true" aria-controls="tab-hoje" id="tab-hoje-btn" title="Análise diária da IA: quais contatos precisam de atenção agora">
    <span class="admin-tab-icon">🧠</span> Hoje <span class="badge" id="badge-briefing" style="display:none;background:#ef4444;color:#fff;border-radius:10px;padding:1px 7px;font-size:0.7rem;margin-left:2px"></span>
  </button>
  <button class="admin-tab" data-tab="leads" role="tab" aria-selected="false" aria-controls="tab-leads" id="tab-leads-btn" title="Lista completa de todos os seus contatos e clientes potenciais">
    <span class="admin-tab-icon">👥</span> Contatos
  </button>
  <button class="admin-tab" data-tab="pipeline" role="tab" aria-selected="false" aria-controls="tab-pipeline" id="tab-pipeline-btn" title="Funil de vendas: acompanhe em qual etapa cada contato está">
    <span class="admin-tab-icon">🔄</span> Funil
  </button>
  <button class="admin-tab" data-tab="campanhas" role="tab" aria-selected="false" aria-controls="tab-campanhas" id="tab-campanhas-btn" title="Envie campanhas em lote por WhatsApp ou e-mail para seus contatos">
    <span class="admin-tab-icon">📧</span> Campanhas
  </button>
  <button class="admin-tab" data-tab="lembretes" role="tab" aria-selected="false" aria-controls="tab-lembretes" id="tab-lembretes-btn" title="Compromissos e tarefas com data e hora agendados">
    <span class="admin-tab-icon">⏰</span> Lembretes
  </button>
  <button class="admin-tab" data-tab="dashboard" role="tab" aria-selected="false" aria-controls="tab-dashboard" id="tab-dashboard-btn" title="Visão geral com métricas e tarefas do dia">
    <span class="admin-tab-icon">📊</span> Painel
  </button>
  <button class="admin-tab" data-tab="importacao" role="tab" aria-selected="false" aria-controls="tab-importacao" id="tab-importacao-btn" title="Importe contatos de planilhas, listas de texto ou CSV">
    <span class="admin-tab-icon">📥</span> Importação
  </button>
  <button class="admin-tab" data-tab="config" role="tab" aria-selected="false" aria-controls="tab-config" id="tab-config-btn" title="Configurações, modelos, propostas e cadastros">
    <span class="admin-tab-icon">⚙️</span> Config
  </button>
</div>
```

E atualize a subnav de `Config` para remover `Campanhas`, deixando apenas:

```html
<div class="config-subnav" role="tablist" aria-label="Seções de configuração">
  <button class="config-subnav-btn active" data-sub="config-settings" role="tab" aria-selected="true">⚙️ Configurações</button>
  <button class="config-subnav-btn" data-sub="templates" role="tab" aria-selected="false">📝 Modelos</button>
  <button class="config-subnav-btn" data-sub="propostas-publicas" role="tab" aria-selected="false">📄 Propostas</button>
  <button class="config-subnav-btn" data-sub="cadastros" role="tab" aria-selected="false">📋 Cadastros</button>
</div>
```

- [ ] **Step 3: Verificar que o HTML resultante contem a nova hierarquia**

Run: `rg -n "data-tab=\"campanhas\"|data-sub=\"campanhas\"|Configurações, modelos, propostas e cadastros" sistema/cotte-frontend/tenant-comercial.html`
Expected: uma ocorrencia de `data-tab="campanhas"`, nenhuma ocorrencia de `data-sub="campanhas"` e `title` de `Config` sem citar campanhas.

- [ ] **Step 4: Commit**

```bash
git add sistema/cotte-frontend/tenant-comercial.html
git commit -m "fix(comercial): move campanhas para aba principal"
```

### Task 2: Validar o fluxo de navegacao reutilizando o JavaScript existente

**Files:**
- Consult: `sistema/cotte-frontend/js/tenant-comercial-core.js:148-176`
- Consult: `sistema/cotte-frontend/js/tenant-comercial.js:2744-2792`
- Test: validacao manual da tela renderizada

- [ ] **Step 1: Confirmar que o switch principal ja suporta campanhas**

Run: `rg -n "tab === 'campanhas'|carregarCampanhas\(" sistema/cotte-frontend/js/tenant-comercial-core.js sistema/cotte-frontend/js/tenant-comercial.js`
Expected: `switchTab` chamando `carregarCampanhas()` e funcoes de renderizacao de campanhas presentes.

- [ ] **Step 2: Validar manualmente a tela no navegador**

Checklist manual:

```text
1. Abrir tenant-comercial.html no fluxo normal da aplicacao.
2. Confirmar que a aba Campanhas aparece ao lado de Funil.
3. Clicar em Campanhas e verificar carregamento da tabela/cards existentes.
4. Abrir Config e confirmar que restaram 4 sub-abas: Configuracoes, Modelos, Propostas e Cadastros.
5. Verificar o seletor mobile, se aplicavel, para garantir que Campanhas entra como aba principal.
```

- [ ] **Step 3: Registrar se houve necessidade de ajuste extra em JavaScript**

Se a validacao manual falhar por algum acoplamento inesperado, aplicar apenas o menor ajuste necessario em `tenant-comercial-core.js` ou `tenant-comercial.js` mantendo este comportamento-alvo:

```js
else if (tab === 'campanhas') carregarCampanhas();
```

Se a validacao passar sem ajuste, nao modificar JavaScript.

- [ ] **Step 4: Commit**

```bash
git add sistema/cotte-frontend/tenant-comercial.html sistema/cotte-frontend/js/tenant-comercial-core.js sistema/cotte-frontend/js/tenant-comercial.js
git commit -m "test(comercial): validate campanhas top-level navigation"
```
