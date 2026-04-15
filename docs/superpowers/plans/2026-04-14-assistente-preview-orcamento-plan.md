---
title: 2026 04 14 Assistente Preview Orcamento Plan
tags:
  - tecnico
prioridade: media
status: documentado
---
# Preview Completo de Orçamento no Assistente Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrar o modal responsivo de detalhes de orçamento nativo do sistema dentro do chat do Assistente IA.

**Architecture:** O `assistente-ia.html` importará o script `orcamento-detalhes.js` e o HTML estrutural do modal. O `assistente-ia-actions.js` fornecerá funções de atalho globais que o `orcamento-detalhes` exige para interagir com recursos como aprovação, WhatsApp e PDF, redirecionando o fluxo ou chamando os endpoints do assistente.

**Tech Stack:** HTML, Vanilla JavaScript, CSS.

---

### Task 1: Inserir o HTML do Modal no Assistente

**Files:**
- Modify: `sistema/cotte-frontend/assistente-ia.html`

- [ ] **Step 1: Inserir o HTML do modal-detalhes e modal-orc-docs**
Adicionar o bloco de código exato no final do `<body>` do `assistente-ia.html`, antes das tags `<script>`:
```html
<!-- MODAL DETALHES ORÇAMENTO (Importado para o Assistente) -->
<div class="modal-overlay" id="modal-detalhes">
  <div class="modal" style="max-width:600px">
    <div class="modal-header">
      <div class="modal-title" id="detalhes-titulo">📋 Orçamento</div>
      <button class="modal-close" onclick="fecharDetalhes()">✕</button>
    </div>
    <div class="modal-body" id="detalhes-body" style="padding:0 28px 4px;max-height:72vh;overflow-y:auto">
      <!-- preenchido por JS -->
    </div>
    <div class="modal-footer" id="detalhes-footer" style="flex-wrap:wrap;gap:8px">
      <!-- botões preenchidos por JS -->
    </div>
  </div>
</div>

<!-- MODAL DOCUMENTOS DO ORÇAMENTO -->
<div class="modal-overlay" id="modal-orc-docs">
  <div class="modal modal-docs">
    <div class="modal-header">
      <div>
        <div class="modal-title">📎 Documentos da proposta</div>
        <div style="font-size:12px;color:var(--muted);margin-top:2px">Gerencie PDFs e anexos do orçamento</div>
      </div>
      <button class="modal-close" onclick="fecharModalDocsOrcamento()">✕</button>
    </div>
    <div class="modal-body" style="padding:20px 24px">
      <div id="orc-docs-list" style="display:flex;flex-direction:column;gap:12px"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Incluir o script orcamento-detalhes.js**
No mesmo arquivo `assistente-ia.html`, logo acima de `</body>`, adicione:
```html
<script src="js/orcamento-detalhes.js"></script>
```

- [ ] **Step 3: Commit**
```bash
git add sistema/cotte-frontend/assistente-ia.html
git commit -m "feat(ai): add budget details modal HTML and script to assistant"
```

---

### Task 2: Criar Aliases e Atalhos no Assistente

**Files:**
- Modify: `sistema/cotte-frontend/js/assistente-ia-actions.js`

- [ ] **Step 1: Declarar funções globais esperadas pelo modal**
No final de `assistente-ia-actions.js`, adicione as funções de atalho que fazem a ponte entre o `orcamento-detalhes.js` e a lógica do assistente/navegação do sistema:

```javascript
// --- Aliases para o modal de orcamento-detalhes.js ---
window.api = window.httpClient; // O modal usa api.get()

// Como o assistente não usa cache local persistente de orçamentos da mesma forma que a listagem,
// declaramos um array vazio global que o orcamento-detalhes pode tentar usar se quiser (evita crash).
window.orcamentosCache = []; 

window.enviarWhatsapp = async function(id) {
    // O modal chama fecharDetalhes() antes. Redirecionamos para a função nativa do assistente.
    await enviarPorWhatsapp(id, null, null);
};

window.enviarEmail = async function(id) {
    await enviarPorEmail(id, null, null);
};

window.abrirModalEditarOrcamento = function(id) {
    window.location.href = `orcamentos.html?editar=${id}`;
};

window.duplicarOrcamento = function(id) {
    window.location.href = `orcamentos.html?duplicar=${id}`;
};

window.abrirTimeline = function(id, num) {
    window.location.href = `orcamentos.html?timeline=${id}`;
};

window.aprovarOrcamento = function(id, num) {
    // Envia o comando de aprovação direto no chat de forma silenciosa
    const aprovarCmd = `aprovar ${num}`;
    window._silentNextMessage = true;
    sendQuickMessage(aprovarCmd);
};

window.abrirModalDocsOrcamento = function(id) {
    window.location.href = `orcamentos.html?docs=${id}`;
};
```

- [ ] **Step 2: Commit**
```bash
git add sistema/cotte-frontend/js/assistente-ia-actions.js
git commit -m "feat(ai): map budget actions for details modal inside assistant"
```

---

### Task 3: Injetar o Botão "Ver Preview Completo" nos Cards de Resposta

**Files:**
- Modify: `sistema/cotte-frontend/js/assistente-ia-render-types.js`

- [ ] **Step 1: Atualizar `renderOrcamentoCriado`**
Procure a função `renderOrcamentoCriado`. No final, na tag `div.orc-card-v2__actions`, adicione um novo bloco `div` englobando os botões atuais e adicione o botão do preview acima deles.

**Substitua o trecho final de `renderOrcamentoCriado`:**
```javascript
            <div class="orc-card-v2__actions">
                <button type="button" class="btn btn-primary" onclick="abrirDetalhesOrcamento(${orcId})" style="width: 100%; margin-bottom: 12px; font-size: 14px; font-weight: 600; justify-content: center; padding: 10px;">
                    🔍 Ver Preview Completo
                </button>
                <div style="display: flex; gap: 8px; width: 100%;">
                    <div class="orc-card-v2__icon-btns" style="flex: 1;">
                        <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                        <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                        <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                    </div>
                    <button type="button" class="orc-card-v2__aprovar-btn btn-aprovar" data-quick-send="${aprovarEnc}" data-silent-send="true" style="flex: 1;">✓ Aprovar</button>
                </div>
            </div>
        </div>
    </div>`;
```

- [ ] **Step 2: Atualizar `renderOrcamentoAtualizado`**
Faça o mesmo para `renderOrcamentoAtualizado`.

**Substitua o trecho final de `renderOrcamentoAtualizado`:**
```javascript
            <div class="orc-card-v2__actions">
                <button type="button" class="btn btn-primary" onclick="abrirDetalhesOrcamento(${orcId})" style="width: 100%; margin-bottom: 12px; font-size: 14px; font-weight: 600; justify-content: center; padding: 10px;">
                    🔍 Ver Preview Completo
                </button>
                <div style="display: flex; gap: 8px; width: 100%;">
                    <div class="orc-card-v2__icon-btns" style="flex: 1;">
                        <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                        <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                        <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                    </div>
                    <button type="button" class="orc-card-v2__aprovar-btn btn-aprovar" data-quick-send="${aprovarEnc}" data-silent-send="true" style="flex: 1;">✓ Aprovar</button>
                </div>
            </div>
        </div>
    </div>`;
```

- [ ] **Step 3: Atualizar `renderOrcamentoAprovado`**
No caso do `renderOrcamentoAprovado`, o botão de aprovar não existe, mas os botões de ação sim. Adicione o botão "Ver Preview" em cima dos outros também.

**Substitua o trecho final de `renderOrcamentoAprovado`:**
```javascript
            <div class="orc-card-v2__actions">
                <button type="button" class="btn btn-primary" onclick="abrirDetalhesOrcamento(${orcId})" style="width: 100%; margin-bottom: 12px; font-size: 14px; font-weight: 600; justify-content: center; padding: 10px;">
                    🔍 Ver Preview Completo
                </button>
                <div class="orc-card-v2__icon-btns" style="justify-content: center; gap: 12px;">
                    <button type="button" class="orc-card-v2__icon-btn btn-calendar" onclick="abrirModalAgendamentoRapido(${orcId}, '${escapeHtml(orcNum)}', '${(clienteNome || '').replace(/'/g, "\\'")}')" title="Agendar">📅</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-whats" ${disWhats} data-enviar-wa="${orcId}" data-orc-numero="${numEnc}" title="Enviar WhatsApp">💬</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-link" ${linkTokenAttr} title="Copiar link">🔗</button>
                    <button type="button" class="orc-card-v2__icon-btn btn-email" ${disEmail} data-enviar-email="${orcId}" data-orc-numero="${numEnc}" title="Enviar E-mail">✉️</button>
                </div>
            </div>
        </div>
    </div>`;
```

- [ ] **Step 4: Commit**
```bash
git add sistema/cotte-frontend/js/assistente-ia-render-types.js
git commit -m "feat(ai): add 'Ver Preview Completo' button to budget cards in assistant"
```
