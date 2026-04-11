---
title: Tender Sauteeing Wave
tags:
  - tecnico
prioridade: media
status: documentado
---
# Plano: Redesign Chat Assistente IA v2 — Mobile-first + Cards Compactos

## Contexto
O assistente IA (`assistente-ia.html`) tem cards internos (orçamento, saldo, confirmações) que não são responsivos e ocupam espaço excessivo no mobile. O objetivo é modernizar o visual para se assemelhar a apps de mensagens IA (ChatGPT, Claude) mantendo **todas as funcionalidades** existentes. Dois mockups Stitch (`chatv2.md` e `chatv2-menu.md`) definem a direção visual.

---

## Arquivos a Modificar (6 arquivos)

| # | Arquivo | Tipo |
|---|---------|------|
| 1 | `sistema/cotte-frontend/css/assistente-ia.css` | CSS principal (~3300 linhas) |
| 2 | `sistema/cotte-frontend/css/assistente-ia-mobile.css` | CSS mobile (80 linhas) |
| 3 | `sistema/cotte-frontend/assistente-ia.html` | HTML layout |
| 4 | `sistema/cotte-frontend/js/assistente-ia-shell.js` | JS shell utilities |
| 5 | `sistema/cotte-frontend/js/assistente-ia-input.js` | JS input + addMessage() |
| 6 | `sistema/cotte-frontend/js/assistente-ia-render.js` | JS render pipeline |

---

## Fase 1: CSS — Tokens e Bolhas (sem risco de quebra)

### 1.1 Novos tokens CSS
**Arquivo:** `assistente-ia.css` (linhas 1-46, bloco `:root`)

Adicionar após os tokens existentes:
```css
--ai-bubble-user-radius: 1.25rem 1.25rem 0.25rem 1.25rem;
--ai-bubble-ai-radius: 1.25rem 1.25rem 1.25rem 0.25rem;
--ai-card-radius-v2: 14px;
--ai-input-radius: 999px;
--ai-header-glass: rgba(255,255,255,0.70);
--ai-header-blur: 40px;
--ai-chip-bg: color-mix(in srgb, var(--ai-accent) 10%, transparent);
--ai-chip-text: var(--ai-accent-dark);
```
Dark mode: `--ai-header-glass: rgba(17,24,39,0.75);`

### 1.2 Header glassmorphism (mobile)
**Arquivo:** `assistente-ia.css` (seção `.chat-header`, ~linhas 1224-1296)
- `backdrop-filter: blur(40px)` (subir de 20px)
- `background: var(--ai-header-glass)`
- Shadow sutil: `0 1px 24px rgba(0,0,0,0.04)`
- Avatar: 40px (reduzir de 44px)
- Safe area: `padding-top: calc(14px + env(safe-area-inset-top, 0px))`

### 1.3 Bolhas de mensagem mais limpas
**Arquivo:** `assistente-ia.css` (linhas ~696-812)
- `.message-bubble`: `max-width: 82%` (reduzir de 88%)
- `.message.ai .message-bubble::before` (barra teal lateral): `display: none` — mockup mostra bolhas limpas
- Shadow AI mais suave: `box-shadow: 0 1px 6px rgba(0,0,0,0.06)`

### 1.4 Feedback inline (junto ao timestamp)
**Arquivo:** `assistente-ia.css` (linhas ~2173-2198)
- `.feedback-bar`: `opacity: 0.65` (subir de 0.45), `gap: 6px`, `margin-top: 0`
- `.feedback-btn`: `border-radius: 6px`, `padding: 2px 6px`, hover com `background: var(--ai-accent-dim)`

---

## Fase 2: CSS — Cards Compactos

### 2.1 Todos os cards: max-width responsivo
**Arquivo:** `assistente-ia.css` (linhas ~1711-2037)

Aplicar a `.orc-preview-card`, `.orc-success-card`, `.opr-card`, `.saldo-rapido-resposta`, `.confirmation-card`:
- `max-width: min(380px, 100%)` (nunca excede a tela)
- `padding: 16px` (reduzir de 20px)
- Remover `transform: translateY(-2px)` no hover (inadequado em chat)

### 2.2 Campos mais compactos
- `.orc-field`, `.opr-field`: `padding: 8px 0` (reduzir de 10px)
- `.orc-confirm-btn`, `.orc-cancel-btn`: `border-radius: 10px`

### 2.3 Success card — grid mobile fix
**Arquivo:** `assistente-ia-mobile.css`
- `.orc-action-btns--success`: manter `grid-template-columns: repeat(2, 1fr)` no mobile padrão
- `.orc-action-btn`: `min-height: 52px` (reduzir de 68px), `padding: 10px 12px`
- Novo breakpoint `@media (max-width: 380px)`: `grid-template-columns: 1fr`

### 2.4 Saldo rápido mobile
- `.saldo-valor`: `font-size: 1.6rem` no mobile (reduzir de 2rem)

---

## Fase 3: CSS — Novos Componentes

### 3.1 Action status chips (novo)
Pill acima da bolha AI para ações completas ("Saldo consultado ✓"):
```css
.action-status-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 999px;
  font-size: 0.7rem; font-weight: 600;
  background: var(--ai-chip-bg); color: var(--ai-chip-text);
  margin-bottom: 6px;
}
```

### 3.2 Date separator pills (novo)
Pill central entre grupos de mensagens:
```css
.chat-date-separator { display: flex; justify-content: center; padding: 8px 0; }
.chat-date-pill {
  padding: 4px 14px; border-radius: 999px;
  font-size: 0.68rem; font-weight: 600;
  color: var(--ai-muted);
  background: color-mix(in srgb, var(--ai-bg) 80%, var(--ai-card) 20%);
}
```

### 3.3 Quick Actions bottom sheet (novo)
Bottom sheet com backdrop blur + lista de ações rápidas:
- `.quick-actions-backdrop`: `position: fixed; inset: 0; backdrop-filter: blur(4px); z-index: 199`
- `.quick-actions-sheet`: `position: fixed; bottom: 0; border-radius: 1.5rem 1.5rem 0 0; z-index: 200; max-height: 70vh`
- `.quick-action-item`: `display: flex; gap: 14px; padding: 14px 12px; border-radius: 12px`
- Ícone 44x44 + label + desc + chevron
- Animação `slideUpSheet` (já existe no CSS)
- Dark mode override incluído

### 3.4 Botão attach (+) no input
- `.btn-attach`: `display: none` por padrão, `display: flex` em `@media (max-width: 768px)`
- Posicionado antes do textarea no `.input-group`

### 3.5 Embed mode: esconder novos elementos
```css
body.embed-mode .btn-attach,
body.embed-mode .quick-actions-sheet,
body.embed-mode .quick-actions-backdrop,
body.embed-mode .chat-date-separator { display: none !important; }
body.embed-mode .action-status-chip { font-size: 0.6rem; padding: 2px 6px; }
```

### 3.6 Reduced motion
Estender o bloco `prefers-reduced-motion` existente (~linha 2239):
```css
.quick-actions-sheet.is-open { animation: none; }
.action-status-chip, .chat-date-pill { animation: none; }
```

---

## Fase 4: HTML — Estrutura

### 4.1 Quick Actions bottom sheet
**Arquivo:** `assistente-ia.html` (após `<div class="quick-reply-area">`, ~linha 192)

Inserir:
- `<div class="quick-actions-backdrop" id="quickActionsBackdrop"></div>`
- `<div class="quick-actions-sheet" id="quickActionsSheet">` com 4 itens:
  - 💰 Consultar Saldo → `data-quick-action="Qual meu saldo atual?"`
  - 📝 Novo Orçamento → `data-quick-action="Gerar orcamento para cliente"`
  - 👥 Listar Clientes → `data-quick-action="Listar meus clientes"`
  - 📊 Resumo Financeiro → `data-quick-action="Resumo financeiro do mes"`
- ARIA: `role="dialog" aria-modal="true"`

### 4.2 Botão attach (+) no input
**Arquivo:** `assistente-ia.html` (dentro de `.input-group`, antes do `<textarea>`)

Inserir: `<button type="button" id="quickActionsBtn" class="chat-input-btn btn-attach">` com SVG de "+"

### 4.3 Cache busters
- `assistente-ia.css?v=13` → `?v=14`
- `assistente-ia-mobile.css?v=2` → `?v=3`

---

## Fase 5: JavaScript — Lógica Aditiva

### 5.1 Quick Actions sheet events
**Arquivo:** `assistente-ia-shell.js` (append no final)

- `_toggleQuickActions(open)`: toggle classes `is-open` no sheet e backdrop
- Click listener: `#quickActionsBtn` abre, backdrop fecha, `[data-quick-action]` envia mensagem via `sendQuickMessage()`
- Escape fecha o sheet

### 5.2 Date separator em addMessage()
**Arquivo:** `assistente-ia-input.js` (~linha 300, antes de `messagesContainer.appendChild`)

- Verificar se já existe `.chat-date-separator` com a data de hoje
- Se não existir, inserir pill com `toLocaleDateString('pt-BR', {day:'numeric', month:'long'})`

### 5.3 Action status chips
**Arquivo:** `assistente-ia-render.js` (~linha 42, dentro de `processAIResponse`)

- Map de `tipo_resposta` → label: `saldo_caixa` → "Saldo consultado", `orcamento_criado` → "Orçamento criado", etc.
- Prepend `<div class="action-status-chip">✓ {label}</div>` ao `responseContent`

---

## Verificação / Testes

1. **Visual**: Abrir `assistente-ia.html` no mobile (Chrome DevTools, 375px) e verificar:
   - Cards não excedem a largura da tela
   - Botões de ação do success card ficam em 2 colunas
   - Header com glassmorphism visível
   - Bolhas limpas sem barra teal lateral

2. **Quick Actions**: Clicar no "+" → sheet abre → clicar ação → mensagem enviada → sheet fecha

3. **Funcionalidade preservada**: Testar fluxo completo:
   - Digitar "qual meu saldo" → card saldo aparece com chip "Saldo consultado"
   - Criar orçamento → preview card → confirmar → success card com botões WhatsApp/Email
   - Feedback thumbs up/down funciona
   - Slash commands (/caixa, /faturamento) funcionam
   - Modo embed (via dashboard) continua compacto

4. **Dark mode**: Toggle tema e verificar todos os novos componentes

5. **Reduced motion**: Ativar em OS/browser e confirmar ausência de animações

---

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Remover barra teal lateral da bolha AI | Se necessário manter, usar `opacity: 0.4; width: 2px` em vez de `display: none` |
| Date separator duplicar ao restaurar histórico | Lógica checa `lastSep.dataset.date` — não duplica |
| z-index conflito Quick Actions | z-index 199/200, abaixo do modal preferências (300) |
| Cards dentro de embed mode | Todos novos elementos hidden com `!important` em embed |
