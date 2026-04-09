---
title: Report
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Report
tags:
  - documentacao
prioridade: media
status: documentado
---
# Relatório de Auditoria Completa — Sistema COTTE

Este documento consolida os achados da auditoria técnica e de produto realizada no sistema.

## 1. Mapa dos Fluxos do Sistema
O sistema opera em um fluxo circular focado em conversão e automação:
1.  **Captação (Leads)**: Entrada via IA (texto colado) ou CSV -> Armazenamento em `CommercialLead`.
2.  **Conversão**: Lead -> Redirecionamento para `orcamentos.html` com parâmetros -> Abertura de Modal.
3.  **Proposta (Orçamento)**: 
    - Criação via IA (`/whatsapp/interpretar`) ou Manual (Catálogo).
    - Persistência em `Orcamento` + `ItemOrcamento`.
    - Geração de PDF e Link Público (`/api/v1/o/`).
4.  **Fechamento (Aprovação)**: Aceite do cliente (OTP opcional) -> Transição de Status -> Gatilho Financeiro.
5.  **Financeiro**: Snapshot da regra de pagamento -> Geração de `PagamentoFinanceiro` (Entrada/Saldo) -> PIX/Webhook.
6.  **Execução**: Integração com `Agendamento` após aprovação/sinal.

---

## 2. Lista de Erros Críticos (Prioridade 1)
- **Precisão Monetária (Risco Financeiro)**: Uso de `float` em 96 locais (ex: `pdf_utils.py`, `financeiro_service.py`). Cálculos de desconto e subtotal em PDFs usam float, podendo causar divergências de centavos em orçamentos grandes.
- **Falha de Isolamento de Dados (Segurança)**: Endpoint `GET /orcamentos/{orcamento_id}/pix/gerar` valida o criador mas não filtra explicitamente por `empresa_id` na query inicial, e o `is_superadmin` pode permitir acesso cruzado indevido se não for tratado como admin global estrito.
- **Privilégios de Gestão**: Gestores (`is_gestor`) podem ser bloqueados de ver orçamentos da própria equipe devido à trava de `criado_por_id == usuario.id` em endpoints de detalhe.

---

## 3. Pontos Desconectados (Integração)
- **Duplicidade de IA**: Existem dois fluxos de interpretação (`/orcamentos/criar-pelo-texto` e `/whatsapp/interpretar`). O frontend usa o de WhatsApp, mas o backend mantém um endpoint orcamento-centrado que pode divergir em lógica.
- **Idempotência de Notificações**: O `quote_notification_service` é robusto, mas o trigger manual em `orcamentos.html` via `api.post` direto pode ignorar regras de "não reenviar" se o estado do frontend não for validado.
- **Snapshot de Pagamento**: Se uma `FormaPagamentoConfig` for alterada, orçamentos em rascunho mantêm o snapshot antigo até serem editados, o que pode causar confusão sobre regras de sinal/PIX.

---

## 4. Problemas de UX e Interface
- **Reatividade da Lista de Itens**: A remoção de itens via `removeItem(this)` no frontend permite que a lista fique com zero itens. Se o usuário salvar assim, o backend pode aceitar um orçamento de valor zero.
- **Feedback de IA**: O erro na interpretação de IA exibe mensagens técnicas. O "fallback" manual no backend (`_parse_fallback`) nem sempre é comunicado de forma clara para o usuário ajustar os dados.
- **Estilo de Código UI**: Uso misto de `onchange/onclick` inline e `addEventListener`. O ideal é padronizar para evitar perda de eventos em re-renders futuros.

---

## 5. Plano Priorizado de Correção
| Ordem | Item | Categoria | Esforço |
| :--- | :--- | :--- | :--- |
| **1** | Migrar cálculos de `float` para `Decimal` em Services e Utils | Integridade | Médio |
| **2** | Revisar filtros de `empresa_id` em todos os endpoints de `/orcamentos` | Segurança | Baixo |
| **3** | Ajustar permissão de visualização para `is_gestor` ver toda a empresa | Lógica | Baixo |
| **4** | Validar "mínimo de 1 item" no frontend e backend | UX/Lógica | Baixo |
| **5** | Unificar endpoints de IA e padronizar retornos de erro | Arquitetura | Médio |
