---
title: Design Referencia
tags:
  - documentacao
  - frontend
prioridade: media
status: documentado
---
---
title: Design Referencia
tags:
  - documentacao
  - frontend
prioridade: media
status: documentado
---
# Design System — Precision Atelier
**Versão 2.0 | SaaS de Gestão Empresarial**

---

## Índice

1. [Visão Geral & North Star](#1-visão-geral--north-star)
2. [Tokens de Cor](#2-tokens-de-cor)
3. [Tipografia](#3-tipografia)
4. [Espaçamento & Grid](#4-espaçamento--grid)
5. [Elevação & Profundidade](#5-elevação--profundidade)
6. [Motion & Animação](#6-motion--animação)
7. [Componentes](#7-componentes)
8. [Padrões de Layout](#8-padrões-de-layout)
9. [Acessibilidade](#9-acessibilidade)
10. [Do's and Don'ts](#10-dos-and-donts)

---

## 1. Visão Geral & North Star

### O Conceito: "The Precision Atelier"

Este sistema transforma gestão empresarial complexa em uma experiência editorial serena. Rejeitamos o visual "SaaS-em-caixa" em favor de uma estética que equilibra **precisão industrial** com **materiais de luxo** — como um atelier físico de alta qualidade.

A assimetria intencional e a profundidade tonal substituem bordas rígidas. Em vez de confinar dados em caixas duras, deixamos as informações respirarem sobre "folhas" elevadas de papel digital, usando luz e sombra para guiar o olhar — não linhas estruturais.

### Princípios de Design

| Princípio | Descrição |
|-----------|-----------|
| **Tonal sobre Linear** | Hierarquia criada por camadas de cor, nunca por bordas de 1px |
| **Editorial sobre Funcional** | Tipografia contrastante cria ritmo, não apenas legibilidade |
| **Ambient sobre Explicit** | Sombras sentidas, não vistas; limites sugeridos, não declarados |
| **Sistemático sobre Ad-hoc** | Toda decisão visual deriva de um token — nunca valores soltos |

---

## 2. Tokens de Cor

### 2.1 Paleta Completa (Valores Hex Definitivos)

Todos os tokens abaixo devem ser declarados como CSS Custom Properties (variáveis).

```css
:root {
  /* === CORES DE MARCA === */
  --color-primary:           #00687a;
  --color-primary-hover:     #005566;
  --color-primary-container: #06b6d4;
  --color-primary-light:     #cff4fc;
  --color-on-primary:        #ffffff;

  /* === SUPERFÍCIES (do mais escuro ao mais claro) === */
  --color-surface-lowest:    #ffffff;   /* Folha ativa — mais elevada */
  --color-surface-low:       #f0f5f9;   /* Pasta — nível intermediário */
  --color-surface:           #f7fafe;   /* Base padrão da página */
  --color-surface-high:      #e8edf2;   /* Containers com profundidade */
  --color-surface-highest:   #dde3e9;   /* Elementos de maior contraste */

  /* === TEXTO === */
  --color-on-surface:        #181c1f;   /* Texto principal — NUNCA preto puro */
  --color-on-surface-variant:#42484e;   /* Texto secundário / labels */
  --color-on-surface-muted:  #6b737b;   /* Metadados, placeholders */
  --color-on-surface-faint:  #9aa3ab;   /* Texto desabilitado */

  /* === BORDAS (uso restrito — apenas fallback de acessibilidade) === */
  --color-outline:           rgba(24, 28, 31, 0.40); /* Ghost border forte */
  --color-outline-variant:   rgba(24, 28, 31, 0.15); /* Ghost border padrão */
  --color-outline-subtle:    rgba(24, 28, 31, 0.08); /* Ghost border mínimo */

  /* === SEMÂNTICOS === */
  --color-error:             #ba1a1a;
  --color-error-container:   #ffdad6;
  --color-on-error:          #ffffff;
  --color-on-error-container:#410002;

  --color-success:           #1a6e3c;
  --color-success-container: #b7f0cb;
  --color-on-success:        #ffffff;
  --color-on-success-container:#002110;

  --color-warning:           #7a5200;
  --color-warning-container: #ffdfa0;
  --color-on-warning:        #ffffff;
  --color-on-warning-container:#261900;

  --color-info:              #00527a;
  --color-info-container:    #c5e8ff;
  --color-on-info:           #ffffff;
  --color-on-info-container: #001e30;

  /* === CONTAINERS SECUNDÁRIOS === */
  --color-secondary:           #4a6268;
  --color-secondary-container: #cde7ed;
  --color-on-secondary:        #ffffff;
  --color-on-secondary-container: #051f24;

  /* === CONTAINERS TERCIÁRIOS === */
  --color-tertiary:            #545d7e;
  --color-tertiary-container:  #dbe2ff;
  --color-on-tertiary:         #ffffff;
  --color-on-tertiary-container:#111437;
}
```

### 2.2 Modo Escuro

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-primary:           #4fd8eb;
    --color-primary-hover:     #6fe2f2;
    --color-primary-container: #004f5d;
    --color-primary-light:     #001f26;
    --color-on-primary:        #003640;

    --color-surface-lowest:    #1a1f22;
    --color-surface-low:       #1f2428;
    --color-surface:           #111518;
    --color-surface-high:      #262b2f;
    --color-surface-highest:   #2e3438;

    --color-on-surface:        #e1e3e5;
    --color-on-surface-variant:#bdc4ca;
    --color-on-surface-muted:  #8d9499;
    --color-on-surface-faint:  #5a6166;

    --color-outline:           rgba(225, 227, 229, 0.38);
    --color-outline-variant:   rgba(225, 227, 229, 0.15);
    --color-outline-subtle:    rgba(225, 227, 229, 0.08);

    --color-error:             #ffb4ab;
    --color-error-container:   #93000a;
    --color-on-error:          #690005;
    --color-on-error-container:#ffdad6;

    --color-success:           #6dd99a;
    --color-success-container: #004d23;
    --color-on-success:        #003919;
    --color-on-success-container:#b7f0cb;

    --color-warning:           #ffba34;
    --color-warning-container: #5a3b00;
    --color-on-warning:        #3e2a00;
    --color-on-warning-container:#ffdfa0;

    --color-secondary:           #b1cbd0;
    --color-secondary-container: #334a50;
    --color-on-secondary:        #1b3439;
    --color-on-secondary-container:#cde7ed;
  }
}
```

### 2.3 A Regra "No-Line" (inegociável)

**Nunca use bordas sólidas de 1px para seccionar a UI.**

Limites devem ser criados exclusivamente por:

1. **Mudança de cor de fundo** — colocar um componente `surface-low` sobre um fundo `surface`
2. **Transições tonais** — usar a hierarquia `surface-lowest` → `surface-highest` para criar profundidade
3. **Ghost Border (apenas como fallback de acessibilidade)** — `1px solid var(--color-outline-variant)` quando contraste insuficiente

```css
/* ✅ CORRETO — separação por tonal layering */
.card {
  background: var(--color-surface-lowest);
}
.page-background {
  background: var(--color-surface);
}

/* ❌ ERRADO — borda explícita como separador visual */
.card {
  border: 1px solid #e0e0e0;
}
```

### 2.4 Estratégia de Glassmorphism

Para elementos flutuantes (toasts, dropdowns, tooltips, modais):

```css
.floating-element {
  background: rgba(247, 250, 254, 0.80);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--color-outline-variant); /* permitido aqui */
}

/* Fallback para ambientes sem suporte a backdrop-filter */
@supports not (backdrop-filter: blur(12px)) {
  .floating-element {
    background: var(--color-surface-lowest);
    box-shadow: 0 8px 32px rgba(24, 28, 31, 0.12);
  }
}
```

### 2.5 Gradientes Permitidos

Gradientes são permitidos **apenas** nas situações abaixo:

```css
/* CTAs primários — injeção de tátilidade */
.btn-primary {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-container));
}

/* Navegação lateral com glassmorphism */
.sidenav {
  background: linear-gradient(
    180deg,
    rgba(247, 250, 254, 0.90) 0%,
    rgba(240, 245, 249, 0.85) 100%
  );
  backdrop-filter: blur(16px);
}
```

---

## 3. Tipografia

### 3.1 Fontes

```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {
  --font-display: 'Plus Jakarta Sans', sans-serif; /* Títulos, valores financeiros */
  --font-body:    'Inter', sans-serif;             /* Dados, tabelas, interface */
  --font-mono:    'JetBrains Mono', 'Fira Code', monospace; /* Código, IDs */
}
```

### 3.2 Escala Tipográfica Completa

| Token | Font | Size | Weight | Line Height | Uso |
|-------|------|------|--------|-------------|-----|
| `--text-display-lg` | Plus Jakarta Sans | 3.5rem (56px) | 700 | 1.1 | Totais financeiros hero |
| `--text-display-md` | Plus Jakarta Sans | 2.5rem (40px) | 700 | 1.15 | KPIs de dashboard |
| `--text-display-sm` | Plus Jakarta Sans | 2rem (32px) | 600 | 1.2 | Subtotais importantes |
| `--text-headline-lg` | Plus Jakarta Sans | 1.75rem (28px) | 600 | 1.25 | Títulos de página |
| `--text-headline-md` | Plus Jakarta Sans | 1.5rem (24px) | 600 | 1.3 | Títulos de seção |
| `--text-headline-sm` | Plus Jakarta Sans | 1.25rem (20px) | 600 | 1.35 | Títulos de card |
| `--text-title-lg` | Inter | 1.125rem (18px) | 600 | 1.4 | Subtítulos de seção |
| `--text-title-md` | Inter | 1rem (16px) | 500 | 1.5 | Labels de grupo |
| `--text-title-sm` | Inter | 0.875rem (14px) | 500 | 1.5 | Labels de campo |
| `--text-body-lg` | Inter | 1rem (16px) | 400 | 1.6 | Corpo de texto |
| `--text-body-md` | Inter | 0.875rem (14px) | 400 | 1.6 | Dados, listas |
| `--text-body-sm` | Inter | 0.75rem (12px) | 400 | 1.5 | Dados densos, tabelas |
| `--text-label-lg` | Inter | 0.875rem (14px) | 500 | 1.4 | Botões, chips |
| `--text-label-md` | Inter | 0.75rem (12px) | 500 | 1.4 | Labels de input |
| `--text-label-sm` | Inter | 0.6875rem (11px) | 500 | 1.3 | Metadados, timestamps |

```css
:root {
  --text-display-lg:  700 3.5rem/1.1   var(--font-display);
  --text-display-md:  700 2.5rem/1.15  var(--font-display);
  --text-display-sm:  600 2rem/1.2     var(--font-display);
  --text-headline-lg: 600 1.75rem/1.25 var(--font-display);
  --text-headline-md: 600 1.5rem/1.3   var(--font-display);
  --text-headline-sm: 600 1.25rem/1.35 var(--font-display);
  --text-title-lg:    600 1.125rem/1.4 var(--font-body);
  --text-title-md:    500 1rem/1.5     var(--font-body);
  --text-title-sm:    500 0.875rem/1.5 var(--font-body);
  --text-body-lg:     400 1rem/1.6     var(--font-body);
  --text-body-md:     400 0.875rem/1.6 var(--font-body);
  --text-body-sm:     400 0.75rem/1.5  var(--font-body);
  --text-label-lg:    500 0.875rem/1.4 var(--font-body);
  --text-label-md:    500 0.75rem/1.4  var(--font-body);
  --text-label-sm:    500 0.6875rem/1.3 var(--font-body);
}
```

### 3.3 Hierarquia como Identidade

O contraste extremo entre um `display-md` e um `label-sm` cria fluxo editorial — como uma revista financeira, não uma planilha.

```css
/* Exemplo: card de KPI financeiro */
.kpi-value  { font: var(--text-display-md); color: var(--color-on-surface); }
.kpi-label  { font: var(--text-label-sm);   color: var(--color-on-surface-muted); }
.kpi-change { font: var(--text-label-md);   color: var(--color-success); }
```

---

## 4. Espaçamento & Grid

### 4.1 Escala de Espaçamento (base 4px)

Todos os valores de espaço devem derivar desta escala. **Nunca use valores arbitrários.**

```css
:root {
  --space-1:  4px;   /* micro — ícone/texto interno */
  --space-2:  8px;   /* xs — gap entre elementos inline */
  --space-3:  12px;  /* sm — padding de chip, badge */
  --space-4:  16px;  /* md — padding de card compacto, gap padrão */
  --space-5:  20px;  /* — separador de seção compacta */
  --space-6:  24px;  /* lg — padding de card, margin entre títulos */
  --space-8:  32px;  /* xl — separador de seção */
  --space-10: 40px;  /* 2xl — margin entre blocos maiores */
  --space-12: 48px;  /* 3xl — padding de hero section */
  --space-16: 64px;  /* 4xl — separação de página */
  --space-20: 80px;  /* 5xl — seções de destaque */
}
```

### 4.2 Grid de Layout

```css
/* Grid principal da aplicação */
.app-layout {
  display: grid;
  grid-template-columns: 240px 1fr;  /* sidenav + conteúdo */
  grid-template-rows: 64px 1fr;      /* topbar + main */
  min-height: 100vh;
}

/* Grid de conteúdo interno — 12 colunas */
.content-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--space-6);
  padding: var(--space-8);
}

/* Breakpoints */
@media (max-width: 1280px) { .app-layout { grid-template-columns: 200px 1fr; } }
@media (max-width: 1024px) { .app-layout { grid-template-columns: 1fr; } }
```

### 4.3 Raios de Borda

```css
:root {
  --radius-sm:   4px;   /* chips internos, badges */
  --radius-md:   8px;   /* botões, inputs, tags */
  --radius-lg:   12px;  /* cards de dados */
  --radius-xl:   16px;  /* cards financeiros, modais */
  --radius-2xl:  24px;  /* cards hero, painéis */
  --radius-full: 9999px; /* chips pill, avatares */
}
```

---

## 5. Elevação & Profundidade

### 5.1 O Princípio de Camadas

Trate a UI como folhas de papel fino empilhadas:

| Camada | Token | Valor | Analogia |
|--------|-------|-------|----------|
| Base | `--color-surface` | `#f7fafe` | A mesa |
| Baixo | `--color-surface-low` | `#f0f5f9` | A pasta |
| Médio | `--color-surface-lowest` | `#ffffff` | A folha ativa |
| Alto | `--color-surface-high` | `#e8edf2` | Área destacada |

Posicionar `surface-lowest` (mais brilhante) sobre um fundo `surface-low` (ligeiramente mais escuro) cria um lift natural **sem nenhuma borda**.

### 5.2 Sistema de Sombras Completo

Sombras devem ser **sentidas, não vistas**. Nunca use `box-shadow` com 0 de blur.

```css
:root {
  /* Tint: versão 10% do on-surface sobre fundo azulado */
  --shadow-color: rgba(24, 28, 31, 0.08);

  /* Elevação 0 — sem sombra, diferenciação só por cor */
  --shadow-0: none;

  /* Elevação 1 — cards base */
  --shadow-1:
    0 2px 8px var(--shadow-color),
    0 1px 3px rgba(24, 28, 31, 0.04);

  /* Elevação 2 — cards interativos, hover state */
  --shadow-2:
    0 4px 16px var(--shadow-color),
    0 2px 6px rgba(24, 28, 31, 0.05);

  /* Elevação 3 — dropdowns, popovers */
  --shadow-3:
    0 8px 24px rgba(24, 28, 31, 0.10),
    0 4px 10px rgba(24, 28, 31, 0.06);

  /* Elevação 4 — modais, painéis laterais */
  --shadow-4:
    0 16px 40px rgba(24, 28, 31, 0.12),
    0 8px 16px rgba(24, 28, 31, 0.07);

  /* Elevação 5 — toasts, alertas flutuantes */
  --shadow-5:
    0 24px 60px rgba(24, 28, 31, 0.14),
    0 12px 24px rgba(24, 28, 31, 0.08);
}
```

### 5.3 Ghost Border (Fallback de Acessibilidade)

Quando contraste de cor insuficiente comprometer acessibilidade, use:

```css
.ghost-border {
  outline: 1px solid var(--color-outline-variant); /* 15% opacity */
}
```

---

## 6. Motion & Animação

### 6.1 Tokens de Duração

```css
:root {
  --duration-instant:  50ms;   /* feedback imediato — ripple, checkbox tick */
  --duration-fast:     100ms;  /* micro-interações — hover, focus ring */
  --duration-base:     200ms;  /* transições padrão — cor, opacidade */
  --duration-moderate: 300ms;  /* movimento de elemento — slide, expand */
  --duration-slow:     400ms;  /* animações complexas — modal, drawer */
  --duration-lazy:     600ms;  /* onboarding, empty states */
}
```

### 6.2 Curvas de Easing

```css
:root {
  /* Para elementos que entram na tela */
  --ease-out:       cubic-bezier(0.0, 0.0, 0.2, 1.0);
  /* Para elementos que saem da tela */
  --ease-in:        cubic-bezier(0.4, 0.0, 1.0, 1.0);
  /* Para elementos que permanecem na tela */
  --ease-in-out:    cubic-bezier(0.4, 0.0, 0.2, 1.0);
  /* Para micro-interações com bounce sutil */
  --ease-spring:    cubic-bezier(0.34, 1.56, 0.64, 1.0);
  /* Para valores financeiros que mudam */
  --ease-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1.0);
}
```

### 6.3 Propriedades Animáveis

Apenas as propriedades abaixo são permitidas em transições de UI — performance garantida:

```css
/* ✅ PERMITIDO — composited properties */
transition:
  opacity       var(--duration-base) var(--ease-in-out),
  transform     var(--duration-base) var(--ease-out),
  color         var(--duration-fast) var(--ease-in-out),
  background    var(--duration-fast) var(--ease-in-out),
  box-shadow    var(--duration-base) var(--ease-in-out),
  border-color  var(--duration-fast) var(--ease-in-out);

/* ❌ EVITAR — causa layout thrashing */
/* width, height, top, left, margin, padding */
```

### 6.4 Padrões de Animação

```css
/* Entrada de modal */
@keyframes modal-in {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to   { opacity: 1; transform: scale(1)    translateY(0);   }
}
.modal { animation: modal-in var(--duration-slow) var(--ease-out); }

/* Entrada de toast / notificação */
@keyframes toast-in {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0);    }
}
.toast { animation: toast-in var(--duration-moderate) var(--ease-spring); }

/* Skeleton loading */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.6; }
  50%       { opacity: 1.0; }
}
.skeleton {
  background: var(--color-surface-high);
  animation: skeleton-pulse 1.5s var(--ease-in-out) infinite;
  border-radius: var(--radius-md);
}

/* Número financeiro atualizado */
@keyframes value-update {
  0%   { transform: translateY(-4px); opacity: 0; }
  100% { transform: translateY(0);    opacity: 1; }
}
.value-updated { animation: value-update var(--duration-moderate) var(--ease-spring); }

/* Respeitar preferência de redução de movimento */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7. Componentes

### 7.1 Botões

#### Variantes

```css
/* PRIMARY — ação principal da página */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px var(--space-6);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-container));
  color: var(--color-on-primary);
  font: var(--text-label-lg);
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-in-out),
              transform var(--duration-fast) var(--ease-out);
}
.btn-primary:hover  { opacity: 0.92; }
.btn-primary:active { transform: scale(0.98); opacity: 0.88; }
.btn-primary:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.btn-primary:disabled {
  opacity: 0.38;
  cursor: not-allowed;
  background: var(--color-surface-highest);
  color: var(--color-on-surface-muted);
}

/* SECONDARY — ação secundária */
.btn-secondary {
  padding: 10px var(--space-6);
  background: var(--color-surface-highest);
  color: var(--color-on-surface);
  font: var(--text-label-lg);
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out);
}
.btn-secondary:hover  { background: var(--color-surface-high); }
.btn-secondary:active { transform: scale(0.98); }
.btn-secondary:disabled { opacity: 0.38; cursor: not-allowed; }

/* GHOST — ação terciária / destrutiva discreta */
.btn-ghost {
  padding: 10px var(--space-6);
  background: transparent;
  color: var(--color-on-surface-variant);
  font: var(--text-label-lg);
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out),
              color var(--duration-fast) var(--ease-in-out);
}
.btn-ghost:hover  { background: var(--color-surface-low); color: var(--color-on-surface); }
.btn-ghost:active { transform: scale(0.98); }

/* DANGER — ação destrutiva */
.btn-danger {
  padding: 10px var(--space-6);
  background: var(--color-error-container);
  color: var(--color-on-error-container);
  font: var(--text-label-lg);
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
}
.btn-danger:hover { background: var(--color-error); color: var(--color-on-error); }
```

#### Estados de Loading

```css
.btn-loading {
  position: relative;
  color: transparent;
  pointer-events: none;
}
.btn-loading::after {
  content: '';
  position: absolute;
  width: 16px; height: 16px;
  top: 50%; left: 50%;
  margin: -8px 0 0 -8px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

### 7.2 Inputs

Abandonamos a caixa de 4 lados. Usamos fill com `surface-low` e bottom border animada.

```css
/* Wrapper */
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

/* Label */
.field-label {
  font: var(--text-label-md);
  color: var(--color-on-surface-variant);
}

/* Input base */
.input {
  width: 100%;
  padding: 10px var(--space-4);
  background: var(--color-surface-low);
  color: var(--color-on-surface);
  font: var(--text-body-md);
  border: none;
  border-bottom: 1.5px solid var(--color-outline-variant);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  outline: none;
  transition:
    border-color var(--duration-fast) var(--ease-in-out),
    background   var(--duration-fast) var(--ease-in-out);
}
.input::placeholder { color: var(--color-on-surface-faint); }

/* Focus — underline animado */
.input:focus {
  background: var(--color-surface-lowest);
  border-bottom-color: var(--color-primary);
  border-bottom-width: 2px;
}

/* Estados */
.input:hover:not(:focus) { border-bottom-color: var(--color-outline); }

.input[aria-invalid="true"] {
  border-bottom-color: var(--color-error);
  background: color-mix(in srgb, var(--color-error-container) 30%, var(--color-surface-low));
}

.input:disabled {
  opacity: 0.38;
  cursor: not-allowed;
  color: var(--color-on-surface-muted);
}

/* Mensagem de erro */
.field-error {
  font: var(--text-label-sm);
  color: var(--color-error);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

/* Mensagem de ajuda */
.field-hint {
  font: var(--text-label-sm);
  color: var(--color-on-surface-muted);
}
```

### 7.3 Cards

```css
/* Card base */
.card {
  background: var(--color-surface-lowest);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  box-shadow: var(--shadow-1);
  transition: box-shadow var(--duration-base) var(--ease-out),
              transform   var(--duration-base) var(--ease-out);
}

/* Card interativo */
.card-interactive {
  cursor: pointer;
}
.card-interactive:hover {
  box-shadow: var(--shadow-2);
  transform: translateY(-1px);
}
.card-interactive:active {
  transform: translateY(0);
  box-shadow: var(--shadow-1);
}

/* Card financeiro — destaque */
.card-financial {
  background: var(--color-surface-lowest);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  box-shadow: var(--shadow-1);
}
.card-financial .card-value {
  font: var(--text-display-md);
  color: var(--color-on-surface);
  font-feature-settings: "tnum"; /* números tabelados */
}
.card-financial .card-label {
  font: var(--text-label-sm);
  color: var(--color-on-surface-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Sem divisores em listas — use espaço vertical */
.card-list-item {
  padding: var(--space-4) 0;
  /* Sem border-bottom: 1px solid — PROIBIDO */
}
.card-list-item + .card-list-item {
  margin-top: var(--space-2); /* Respiro como separador */
}
```

### 7.4 Data Chips

```css
.chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  background: var(--color-secondary-container);
  color: var(--color-on-secondary-container);
  font: var(--text-label-sm);
  border-radius: var(--radius-full);
}

/* Variantes semânticas */
.chip-success { background: var(--color-success-container); color: var(--color-on-success-container); }
.chip-warning { background: var(--color-warning-container); color: var(--color-on-warning-container); }
.chip-error   { background: var(--color-error-container);   color: var(--color-on-error-container);   }
.chip-info    { background: var(--color-info-container);    color: var(--color-on-info-container);    }
```

### 7.5 Tabelas de Dados

```css
.data-table {
  width: 100%;
  border-collapse: collapse;
  font: var(--text-body-sm);
  font-feature-settings: "tnum"; /* alinhamento de números */
}

/* Header */
.data-table thead th {
  font: var(--text-label-sm);
  color: var(--color-on-surface-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  text-align: left;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface-low);
  /* Sem border-bottom — separação por cor de fundo */
}

/* Linhas — alternância tonal (sem linhas divisórias) */
.data-table tbody tr {
  transition: background var(--duration-fast) var(--ease-in-out);
}
.data-table tbody tr:nth-child(even) {
  background: var(--color-surface);
}
.data-table tbody tr:nth-child(odd) {
  background: var(--color-surface-lowest);
}
.data-table tbody tr:hover {
  background: var(--color-primary-light);
}

.data-table tbody td {
  padding: var(--space-3) var(--space-4);
  color: var(--color-on-surface);
  /* Nunca: border-bottom: 1px solid — PROIBIDO */
}

/* Coluna de valor financeiro */
.data-table .col-financial {
  font-family: var(--font-display);
  font-weight: 600;
  text-align: right;
}
```

### 7.6 Navegação Lateral

```css
.sidenav {
  width: 240px;
  height: 100vh;
  background: linear-gradient(
    180deg,
    rgba(247, 250, 254, 0.92) 0%,
    rgba(240, 245, 249, 0.88) 100%
  );
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-right: 1px solid var(--color-outline-subtle); /* permitido em nav */
  padding: var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-3);
  border-radius: var(--radius-md);
  font: var(--text-title-sm);
  color: var(--color-on-surface-variant);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out),
              color     var(--duration-fast) var(--ease-in-out);
  text-decoration: none;
}
.nav-item:hover {
  background: var(--color-surface-low);
  color: var(--color-on-surface);
}
.nav-item.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 600;
}
```

### 7.7 Toast / Notificações

```css
.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  background: rgba(24, 28, 31, 0.88);
  color: #ffffff;
  font: var(--text-body-sm);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-5);
  backdrop-filter: blur(12px);
  max-width: 360px;
  animation: toast-in var(--duration-moderate) var(--ease-spring);
}

/* Fallback */
@supports not (backdrop-filter: blur(12px)) {
  .toast { background: #1a1f22; }
}
```

### 7.8 Estados de Feedback

Todos os componentes devem implementar os seguintes estados:

| Estado | Descrição | Implementação |
|--------|-----------|---------------|
| `default` | Estado de repouso | Definição base do componente |
| `hover` | Cursor sobre o elemento | `:hover` — mudança sutil de bg/shadow |
| `focus` | Navegação por teclado | `:focus-visible` — outline 2px primary |
| `active` | Clique / pressionado | `:active` — `scale(0.98)`, opacity reduzida |
| `disabled` | Elemento não interativo | `opacity: 0.38`, `cursor: not-allowed` |
| `loading` | Aguardando resposta | Spinner interno, `pointer-events: none` |
| `error` | Validação falhou | Cor `error`, mensagem abaixo |
| `success` | Ação concluída | Cor `success`, feedback temporário |

---

## 8. Padrões de Layout

### 8.1 Dashboard Principal

```
┌─────────────────────────────────────────────────────┐
│  TOPBAR (64px) — logo, busca, notificações, avatar   │
├────────────┬────────────────────────────────────────┤
│            │  BREADCRUMB + TÍTULO DE PÁGINA          │
│  SIDENAV   ├────────────────────────────────────────┤
│  (240px)   │  CARDS DE KPI (grid 4 colunas)          │
│            ├────────────────────────────────────────┤
│  backdrop- │  GRÁFICO PRINCIPAL         │ PAINEL     │
│  blur      │  (8 colunas)               │ LATERAL    │
│            │                            │ (4 colunas)│
│            ├────────────────────────────┴────────────┤
│            │  TABELA DE DADOS (12 colunas)            │
└────────────┴────────────────────────────────────────┘
```

### 8.2 Regra de Assimetria Intencional

Não alinhe tudo em um eixo central. Use o grid de 8px para criar layouts escalonados que pareçam projetados sob medida:

```css
/* Exemplo: header de seção com valor e label deslocados */
.section-header {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  padding-bottom: var(--space-4);
}
.section-title { font: var(--text-headline-md); }
.section-meta  { font: var(--text-label-sm); color: var(--color-on-surface-muted); padding-bottom: 4px; }
```

---

## 9. Acessibilidade

### 9.1 Contraste Mínimo (WCAG 2.1 AA)

| Par de cores | Ratio mínimo | Uso |
|---|---|---|
| `on-surface` / `surface` | 4.5:1 | Texto corpo |
| `on-surface-variant` / `surface` | 4.5:1 | Labels |
| `on-surface-muted` / `surface` | 3:1 | Texto grande (18px+) |
| `primary` / `surface` | 4.5:1 | Links, ícones interativos |

### 9.2 Focus Visível

Nunca remova o outline de foco. Todo elemento interativo deve ter:

```css
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
```

### 9.3 ARIA e Semântica

- Inputs sempre associados a `<label>` via `for`/`id`
- Erros de validação referenciados via `aria-describedby`
- Ícones decorativos com `aria-hidden="true"`
- Modais com `role="dialog"`, `aria-modal="true"`, foco aprisionado interno
- Tabelas com `<caption>` ou `aria-label`

---

## 10. Do's and Don'ts

### DO ✅

- **Use whitespace como ferramenta funcional.** Se uma seção parece sobrecarregada, aumente a escala de espaçamento — não adicione uma borda.
- **Use "Plus Jakarta Sans" para todos os símbolos de moeda e totais financeiros grandes** — reforça a percepção "Premium".
- **Utilize backdrop blur na navegação lateral** para que o conteúdo do dashboard "sangre" sutilmente através, criando continuidade ambiental.
- **Derive todo espaçamento da escala de tokens.** Se um valor não existe na escala, discuta se deve ser adicionado — nunca hardcode px arbitrários.
- **Defina todos os 8 estados de interação** para cada novo componente: default, hover, focus, active, disabled, loading, error, success.
- **Teste com `prefers-reduced-motion: reduce`** — toda animação deve ter um fallback sem movimento.
- **Use `font-feature-settings: "tnum"`** em qualquer coluna com valores numéricos para alinhamento perfeito.

### DON'T ❌

- **NÃO use texto preto puro (#000000).** Use `--color-on-surface` (#181c1f) para manter o tom suave e profissional.
- **NÃO use bordas sólidas de 1px** para separar seções da UI — use mudança de cor de fundo ou espaçamento.
- **NÃO use sombras com 0 de blur** (`box-shadow: 0 2px 0 #ccc`). Sombras devem ser ambientais e expansivas.
- **NÃO alinhe tudo em eixo central.** Use o grid de 8px para criar layouts escalonados intencionais.
- **NÃO use `width`, `height`, `top`, `left` em transitions** — causam layout thrashing e animações travadas.
- **NÃO hardcode valores de cor.** Todo valor deve referenciar um token CSS (`var(--color-*)`).
- **NÃO omita o estado `disabled`.** Todo componente interativo deve comunicar visualmente quando não está disponível.
- **NÃO use glassmorphism sem fallback.** Sempre defina um `@supports not (backdrop-filter: blur())` com fundo sólido.
- **NÃO crie espaçamentos fora da escala de tokens.** Nem `13px`, nem `22px`, nem `37px` — apenas valores da escala definida.

---

*Design System Precision Atelier v2.0 — gerado para aplicação SaaS de gestão empresarial*
