# Onboarding Checklist Comercial — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exibir um checklist de 5 passos na aba "Hoje" do módulo Comercial, guiando novos usuários pela configuração inicial com explicações e atalhos diretos para cada seção.

**Architecture:** Módulo JS singleton `OnboardingComercial` isolado no arquivo `tenant-comercial-onboarding.js`. Detecta estado via caches globais já carregados pelo core + 1 chamada leve à API para verificar leads. Usa CSS variables do projeto para suporte automático a tema claro/escuro.

**Tech Stack:** Vanilla JS (IIFE/singleton pattern), CSS custom properties, `localStorage` (persistência entre visitas), `sessionStorage` (ocultar por sessão).

---

## Mapa de arquivos

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| CRIAR | `sistema/cotte-frontend/js/tenant-comercial-onboarding.js` | Toda a lógica de onboarding: detecção de estado, render, navegação, ocultar |
| MODIFICAR | `sistema/cotte-frontend/css/tenant-comercial.css` | Classes `.ob-*` para o bloco de onboarding |
| MODIFICAR | `sistema/cotte-frontend/js/tenant-comercial-core.js` | Chamar `OnboardingComercial.init()` após `carregarCadastrosCache()` |
| MODIFICAR | `sistema/cotte-frontend/tenant-comercial.html` | Adicionar `<script src="js/tenant-comercial-onboarding.js?v=1">` |

---

## Task 1: Estilos CSS do bloco de onboarding

**Files:**
- Modify: `sistema/cotte-frontend/css/tenant-comercial.css` (adicionar ao final)

- [ ] **Step 1.1: Adicionar CSS ao final de `tenant-comercial.css`**

```css
/* ── Onboarding Checklist ─────────────────────────── */
.ob-bloco {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 20px;
}
.ob-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}
.ob-titulo-principal {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}
.ob-subtitulo {
  font-size: 12px;
  color: var(--muted);
  margin-top: 3px;
}
.ob-progresso-label {
  font-size: 10px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .05em;
  text-align: right;
}
.ob-progresso-valor {
  font-size: 20px;
  font-weight: 800;
  color: var(--accent);
  text-align: right;
}
.ob-progresso-total { font-size: 12px; color: var(--muted); }
.ob-barra-wrap {
  height: 4px;
  background: var(--border);
  border-radius: 4px;
  margin-bottom: 16px;
  overflow: hidden;
}
.ob-barra {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #6366f1);
  border-radius: 4px;
  transition: width .4s ease;
}
.ob-passos { display: flex; flex-direction: column; gap: 8px; }
.ob-passo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 9px;
}
.ob-passo--ok {
  background: rgba(16,185,129,.08);
  border: 1px solid rgba(16,185,129,.25);
}
.ob-passo--ativo {
  background: rgba(245,158,11,.08);
  border: 1px solid rgba(245,158,11,.3);
}
.ob-passo--pendente {
  background: var(--surface2, var(--surface));
  border: 1px solid var(--border);
  opacity: .65;
}
.ob-num {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.ob-num--ok  { background: #10b981; color: #fff; }
.ob-num--ativo { background: #f59e0b; color: #fff; }
.ob-num--pendente { background: var(--border); color: var(--muted); }
.ob-info { flex: 1; min-width: 0; }
.ob-titulo { font-size: 13px; font-weight: 600; color: var(--text); }
.ob-titulo--ok { text-decoration: line-through; opacity: .7; color: #10b981; }
.ob-desc { font-size: 11px; color: var(--muted); margin-top: 2px; }
.ob-desc--ok { color: #10b981; opacity: .8; }
.ob-dica {
  display: inline-block;
  margin-top: 5px;
  font-size: 10px;
  color: var(--accent);
  background: transparent;
  border: 1px solid var(--accent);
  border-radius: 4px;
  padding: 2px 7px;
  cursor: pointer;
  font-family: inherit;
  transition: background .15s;
}
.ob-dica:hover { background: var(--accent); color: #fff; }
.ob-btn {
  padding: 5px 11px;
  background: var(--border);
  border: none;
  border-radius: 6px;
  color: var(--muted);
  font-size: 11px;
  cursor: pointer;
  flex-shrink: 0;
  font-family: inherit;
  transition: background .15s;
}
.ob-btn--ativo { background: #f59e0b; color: #fff; font-weight: 600; }
.ob-btn--ativo:hover { background: #d97706; }
.ob-footer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ob-footer-hint { font-size: 11px; color: var(--muted); opacity: .7; }
.ob-ocultar {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 11px;
  cursor: pointer;
  text-decoration: underline;
  font-family: inherit;
}
```

- [ ] **Step 1.2: Commit**

```bash
git add sistema/cotte-frontend/css/tenant-comercial.css
git commit -m "style(onboarding): adiciona classes .ob-* para checklist de configuração"
```

---

## Task 2: Módulo JS `tenant-comercial-onboarding.js`

**Files:**
- Create: `sistema/cotte-frontend/js/tenant-comercial-onboarding.js`

- [ ] **Step 2.1: Criar o arquivo com o módulo completo**

```js
(function() {
  'use strict';

  var STORAGE_KEY = 'cotte_comercial_onboarding_seen';
  var SESSION_KEY  = 'cotte_comercial_onboarding_hidden';

  var PASSOS = [
    {
      id: 'segmento',
      titulo: 'Criar um Segmento',
      descricao: 'Classifica seus leads por área de atuação (ex: Tecnologia, Varejo, Saúde)',
      tab: 'cadastros',
      check: function() { return segmentosCache.length > 0; }
    },
    {
      id: 'origem',
      titulo: 'Criar uma Origem',
      descricao: 'Indica de onde o lead veio (ex: Instagram, Indicação, Google)',
      tab: 'cadastros',
      check: function() { return origensCache.length > 0; }
    },
    {
      id: 'pipeline',
      titulo: 'Criar Etapas do Pipeline',
      descricao: 'As fases do seu processo de vendas: ex. Contato → Proposta → Fechado. Necessário para o Kanban.',
      tab: 'cadastros',
      check: function() { return pipelineStages.length > 0; }
    },
    {
      id: 'template',
      titulo: 'Criar um Template de Mensagem',
      descricao: 'Mensagens pré-escritas com variáveis como {nome} e {empresa}, para WhatsApp ou e-mail',
      tab: 'templates',
      check: function() { return templatesCache.length > 0; }
    },
    {
      id: 'lead',
      titulo: 'Adicionar seu primeiro Lead',
      descricao: 'Contatos que você quer converter em clientes',
      dica: '💡 Tem uma lista? Use a Importação em lote',
      tabDica: 'importacao',
      tab: 'leads',
      check: function() { return OnboardingComercial._temLead; }
    }
  ];

  var OnboardingComercial = {
    _temLead: false,

    init: async function() {
      if (sessionStorage.getItem(SESSION_KEY)) return;

      try {
        var res = await api.get('/tenant/comercial/leads?limit=1&per_page=1');
        this._temLead = (res && typeof res.total === 'number')
          ? res.total > 0
          : (Array.isArray(res) && res.length > 0);
      } catch(e) {
        this._temLead = false;
      }

      var status = this._getStatus();
      var todosCompletos = status.every(function(s) { return s.completo; });

      if (todosCompletos) {
        localStorage.removeItem(STORAGE_KEY);
        return;
      }

      localStorage.setItem(STORAGE_KEY, '1');
      this._render(status);
    },

    _getStatus: function() {
      return PASSOS.map(function(p) {
        return { passo: p, completo: p.check() };
      });
    },

    _render: function(status) {
      var container = document.getElementById('briefing-container');
      if (!container) return;

      var total      = status.length;
      var concluidos = status.filter(function(s) { return s.completo; }).length;
      var pct        = Math.round((concluidos / total) * 100);
      var proximoIdx = status.findIndex(function(s) { return !s.completo; });

      var passosHTML = status.map(function(s, i) {
        var p = s.passo;

        if (s.completo) {
          return '<div class="ob-passo ob-passo--ok">' +
            '<div class="ob-num ob-num--ok">✓</div>' +
            '<div class="ob-info">' +
              '<div class="ob-titulo ob-titulo--ok">' + p.titulo + '</div>' +
              '<div class="ob-desc ob-desc--ok">Concluído · ' + p.descricao + '</div>' +
            '</div>' +
          '</div>';
        }

        var isProximo = (i === proximoIdx);
        var dicaHTML  = '';
        if (p.dica) {
          dicaHTML = '<button type="button" class="ob-dica"' +
            ' onclick="OnboardingComercial._irPara(\'' + p.tabDica + '\')">' +
            p.dica + '</button>';
        }

        return '<div class="ob-passo ' + (isProximo ? 'ob-passo--ativo' : 'ob-passo--pendente') + '">' +
          '<div class="ob-num ' + (isProximo ? 'ob-num--ativo' : 'ob-num--pendente') + '">' + (i + 1) + '</div>' +
          '<div class="ob-info">' +
            '<div class="ob-titulo">' + p.titulo + '</div>' +
            '<div class="ob-desc">' + p.descricao + '</div>' +
            dicaHTML +
          '</div>' +
          '<button type="button" class="ob-btn' + (isProximo ? ' ob-btn--ativo' : '') + '"' +
            ' onclick="OnboardingComercial._irPara(\'' + p.tab + '\')">' +
            (isProximo ? 'Ir →' : 'Ir') +
          '</button>' +
        '</div>';
      }).join('');

      var html =
        '<div class="ob-bloco" id="ob-bloco">' +
          '<div class="ob-header">' +
            '<div>' +
              '<div class="ob-titulo-principal">🚀 Configure o Comercial</div>' +
              '<div class="ob-subtitulo">Complete os passos abaixo para começar a usar o CRM</div>' +
            '</div>' +
            '<div>' +
              '<div class="ob-progresso-label">Progresso</div>' +
              '<div class="ob-progresso-valor">' + concluidos +
                '<span class="ob-progresso-total">/' + total + '</span>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="ob-barra-wrap"><div class="ob-barra" style="width:' + pct + '%"></div></div>' +
          '<div class="ob-passos">' + passosHTML + '</div>' +
          '<div class="ob-footer">' +
            '<span class="ob-footer-hint">Este guia some automaticamente quando tudo estiver pronto</span>' +
            '<button type="button" class="ob-ocultar" onclick="OnboardingComercial._ocultar()">Ocultar por agora</button>' +
          '</div>' +
        '</div>';

      container.insertAdjacentHTML('afterbegin', html);
    },

    _irPara: function(tab) {
      switchTab(tab);
    },

    _ocultar: function() {
      sessionStorage.setItem(SESSION_KEY, '1');
      var bloco = document.getElementById('ob-bloco');
      if (bloco) bloco.remove();
    }
  };

  window.OnboardingComercial = OnboardingComercial;
})();
```

- [ ] **Step 2.2: Commit**

```bash
git add sistema/cotte-frontend/js/tenant-comercial-onboarding.js
git commit -m "feat(onboarding): cria módulo tenant-comercial-onboarding.js"
```

---

## Task 3: Wiring no core.js

**Files:**
- Modify: `sistema/cotte-frontend/js/tenant-comercial-core.js`

O bloco `DOMContentLoaded` está nas linhas 121-126. A função `carregarCadastrosCache` está nas linhas 128-142. É necessário chamar `OnboardingComercial.init()` logo após `carregarCadastrosCache()` terminar, pois os caches precisam estar prontos.

- [ ] **Step 3.1: Adicionar chamada ao `OnboardingComercial.init()` no DOMContentLoaded**

Localizar o bloco:
```js
document.addEventListener('DOMContentLoaded', async function() {
  inicializarLayout('comercial');
  bindTabEvents();
  await carregarCadastrosCache();
  carregarDashboard();
});
```

Substituir por:
```js
document.addEventListener('DOMContentLoaded', async function() {
  inicializarLayout('comercial');
  bindTabEvents();
  await carregarCadastrosCache();
  if (typeof OnboardingComercial !== 'undefined') OnboardingComercial.init();
  carregarDashboard();
});
```

- [ ] **Step 3.2: Commit**

```bash
git add sistema/cotte-frontend/js/tenant-comercial-core.js
git commit -m "feat(onboarding): ativa OnboardingComercial.init() após caches carregados"
```

---

## Task 4: Registrar o script no HTML

**Files:**
- Modify: `sistema/cotte-frontend/tenant-comercial.html`

O bloco de scripts começa na linha 906. O novo script deve ser carregado **após** `tenant-comercial-core.js` (linha 912) e **antes** dos outros módulos, pois o core define os caches globais que o onboarding precisa ler.

- [ ] **Step 4.1: Inserir tag `<script>` no `tenant-comercial.html`**

Localizar:
```html
  <script src="js/tenant-comercial-core.js?v=1"></script>
  <script src="js/tenant-comercial-dashboard.js?v=1"></script>
```

Substituir por:
```html
  <script src="js/tenant-comercial-core.js?v=1"></script>
  <script src="js/tenant-comercial-onboarding.js?v=1"></script>
  <script src="js/tenant-comercial-dashboard.js?v=1"></script>
```

- [ ] **Step 4.2: Commit**

```bash
git add sistema/cotte-frontend/tenant-comercial.html
git commit -m "feat(onboarding): registra script tenant-comercial-onboarding.js no HTML"
```

---

## Task 5: Verificação manual no navegador

Sem framework de testes automatizados para frontend vanilla, verificar manualmente:

- [ ] **Step 5.1: Teste — primeira visita com cadastros vazios**

1. Apagar as chaves do localStorage/sessionStorage no DevTools:
   - `cotte_comercial_onboarding_seen`
   - `cotte_comercial_onboarding_hidden`
2. Garantir que não há segmentos, origens, templates, pipelineStages cadastrados (ou usar uma empresa de teste vazia)
3. Abrir `/comercial` → bloco "🚀 Configure o Comercial" deve aparecer no topo da aba Hoje
4. Verificar: todos os 5 passos aparecem como pendentes, barra em 0%

- [ ] **Step 5.2: Teste — botão "Ir →" navega para a aba correta**

1. Clicar no botão "Ir →" do passo 1 (Segmento) → deve mudar para a aba Cadastros
2. Clicar no botão "Ir →" do passo 4 (Template) → deve mudar para a aba Templates
3. Clicar no botão "Ir →" do passo 5 (Lead) → deve mudar para a aba Leads
4. Clicar na dica "💡 Tem uma lista? Use a Importação em lote" → deve mudar para a aba Importação

- [ ] **Step 5.3: Teste — ocultar por agora**

1. Clicar em "Ocultar por agora" → bloco some
2. Recarregar a página → bloco aparece novamente (sessionStorage foi limpo pelo reload, localStorage ainda tem a flag de visto)

- [ ] **Step 5.4: Teste — passos concluídos mudam de estado**

1. Cadastrar 1 Segmento na aba Cadastros
2. Voltar para a aba Hoje (recarregar página) → passo 1 deve aparecer com ✓ verde e texto riscado
3. Barra de progresso deve mostrar 1/5 (20%)

- [ ] **Step 5.5: Teste — temas claro e escuro**

1. Trocar o tema pela UI do COTTE (ou `localStorage.setItem('cotte_tema','dark')` + reload)
2. Verificar que o bloco adapta as cores corretamente em ambos os modos

- [ ] **Step 5.6: Teste — desaparecimento completo**

1. Completar todos os 5 passos
2. Recarregar → bloco NÃO deve aparecer
3. Verificar no DevTools: `cotte_comercial_onboarding_seen` removido do localStorage

- [ ] **Step 5.7: Commit final**

```bash
git add -A
git commit -m "test(onboarding): verificação manual concluída — onboarding funcional"
```
