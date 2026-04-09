---
title: Financeiro Playbook
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Financeiro Playbook Operacional
tags:
  - tecnico
prioridade: media
status: documentado
---
# Playbook operacional — pagamentos e caixa (COTTE)

Documento interno para operadores e integrações. Objetivo: evitar **dupla contagem**, **pagamento na parcela errada** e **requisições duplicadas** em produção.

---

## 1. Onde registrar cada tipo de recebimento

| Situação | Canal recomendado | Observação |
|----------|-------------------|------------|
| Cliente pagou um **orçamento** (com ou sem parcelas geradas na aprovação) | `POST /api/v1/financeiro/pagamentos` com `orcamento_id` | O sistema escolhe a **próxima parcela com saldo** na ordem: `numero_parcela` → vencimento → id. |
| Quitar uma **conta a receber** específica (avulsa ou parcela pontual) | `POST /api/v1/financeiro/contas/{conta_id}/receber` | Informe `valor` até o **saldo em aberto** daquela conta. Sem `valor`, usa o saldo restante. |
| **Entrada genérica** no caixa (troco, depósito não vinculado a orçamento) | `POST /api/v1/financeiro/caixa/entrada` | Não substitui pagamento de orçamento/conta; evita usar para o mesmo evento de dinheiro que já foi registrado como `PagamentoFinanceiro`. |

**Regra de ouro:** o mesmo evento de dinheiro não deve ser lançado duas vezes em canais diferentes (ex.: “receber conta” **e** “entrada de caixa” para o mesmo pagamento).

---

## 2. Idempotência (reenvio seguro)

Integrações e o painel podem repetir a mesma requisição (timeout, duplo clique, webhook reenviado).

- Envie um header **`Idempotency-Key`** (ou o campo JSON `idempotency_key` em `PagamentoCreate`) com valor **único por tentativa de negócio** (recomendado: UUID).
- Escopo: **por empresa**. A mesma chave repetida devolve o **mesmo** registro de pagamento, sem duplicar valor.
- Endpoints que aceitam hoje: `POST .../financeiro/pagamentos`, `POST .../contas/{id}/receber`, `POST .../despesas/{id}/pagar` (header).

---

## 3. Parcelas e saldo máximo

- Cada pagamento contra orçamento é validado contra o **saldo em aberto da parcela alvo**, não contra o total do orçamento inteiro (exceto quando só existe uma conta legada).
- Se precisar pagar uma parcela específica, use `parcela_numero` no corpo de `PagamentoCreate` (deve existir como conta a receber daquele orçamento).
- Valores acima do saldo da parcela retornam **HTTP 400** com mensagem explícita.

---

## 4. Despesas (contas a pagar)

- `POST .../despesas/{id}/pagar` usa o saldo em aberto como teto; pagamento parcial é permitido quando o valor informado não excede o saldo.
- Pode-se usar `Idempotency-Key` para evitar duplicar quitação em reenvio.

---

## 5. Estornos e conciliação

- Estorno de pagamento: `POST .../pagamentos/{id}/estornar` (permissão admin). Recalcula conta e orçamento.
- Para divergência entre caixa e contas, priorizar rastreio por **`PagamentoFinanceiro`** e só então ajustar movimentações manuais de caixa, com observação no lançamento.

---

## 6. Deploy e banco

- Migration **`w004_pagto_idemp_empresa`**: adiciona `empresa_id`, `idempotency_key` e índice único parcial em `pagamentos_financeiros`. Aplicar Alembic em produção antes de depender das novas validações.
