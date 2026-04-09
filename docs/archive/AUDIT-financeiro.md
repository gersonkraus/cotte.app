---
title: Audit Financeiro
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Audit Financeiro
tags:
  - documentacao
  - frontend
prioridade: media
status: documentado
---
# Auditoria de Funcionalidades — financeiro.html

> Data: 2026-03-16
> Status: [ ] Pendente | [x] OK | [!] Bug encontrado

---

## KPI Cards

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| K1 | `#kpi-recebido` | Preenchido após GET /financeiro/resumo | [ ] | |
| K2 | `#kpi-a-receber` | Preenchido após GET /financeiro/resumo | [ ] | |
| K3 | `#kpi-vencido` | Preenchido após GET /financeiro/resumo | [ ] | |
| K4 | `#kpi-ticket` | Preenchido após GET /financeiro/resumo | [ ] | |

---

## Tabelas

| # | Tabela | Comportamento esperado | Status | Observação |
|---|--------|----------------------|--------|------------|
| T1 | `#tabela-pagamentos` | Carrega dados ou exibe "Nenhum pagamento registrado." | [ ] | |
| T2 | `#tabela-contas-receber` | Carrega dados ou exibe "Nenhuma conta pendente." | [ ] | |
| T3 | `#tabela-inadimplentes` | Carrega dados ou exibe "Nenhuma conta vencida." | [ ] | |
| T4 | Botão "Confirmar" | Visível em contas com saldo > 0 | [ ] | |
| T5 | Botão "Estornar" | Visível em pagamentos confirmados | [ ] | |

---

## Modal — Registrar Pagamento

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| M1 | Botão "Registrar Pagamento" | Abre `#modal-pagamento` | [ ] | |
| M2 | `#forma-cards` | Cards de formas de pagamento carregados | [ ] | |
| M3 | Click em forma | Card fica selecionado (`.selected`) | [ ] | |
| M4 | `#pag-data` | Preenchida com data de hoje | [ ] | |
| M5 | `#pag-tipo` | Padrão = "quitacao" | [ ] | |
| M6 | Botão "Cancelar" | Fecha o modal | [ ] | |
| M7 | Click fora do modal | Fecha o modal | [ ] | |
| M8 | Salvar sem preencher | Exibe erro em `#pag-feedback` | [ ] | |
| M9 | Salvar sem forma | Exibe erro em `#pag-feedback` | [ ] | |
| M10 | Salvar com dados válidos | POST /financeiro/pagamentos → modal fecha | [ ] | |

---

## Pontos Críticos para Testes Playwright

Prioridade alta:

1. **KPIs** — K1 a K4: valores carregados da API
2. **Estado vazio** — T1 a T3: mensagens quando sem dados
3. **Modal** — M1 a M9: abertura, validação, cancelamento
