---
title: Plan
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Plan
tags:
  - tecnico
prioridade: media
status: documentado
---
# Plano de Implementação

## Phase 1: Revisão da Infraestrutura Base e Testes Iniciais [checkpoint: ab84b71]
- [x] Task: Escrever testes automatizados (pytest) para garantir que as rotas da IA (Claude) extraiam as entidades de orçamentos e retornem o payload esperado. [de08bab]
  - [x] Sub-task: Revisar dependências em `ia_service.py` e rotas base.
- [x] Task: Escrever testes e aplicar mocks na rotina de envio de mensagens do WhatsApp para manter a idempotência das requisições. [5a0865f]
  - [x] Sub-task: Integrar com a estrutura do `quote_notification_service`.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Revisão da Infraestrutura Base e Testes Iniciais' (Protocol in workflow.md) [ab84b71]

## Phase 2: Refinamento da Geração de PDF (WeasyPrint) [checkpoint: 378eb10]
- [x] Task: Criar e validar o CSS semântico do layout PDF para adequar-se à nova identidade visual minimalista B2B. [9f8a40a]
  - [x] Sub-task: Renderizar PDFs estáticos contendo logos corporativos e fontes.
- [x] Task: Acoplar o conversor de PDF ao Controller do orçamento que recebe a confirmação do Claude e do Frontend. [9f8a40a]
- [x] Task: Conductor - User Manual Verification 'Phase 2: Refinamento da Geração de PDF (WeasyPrint)' (Protocol in workflow.md) [378eb10]

## Phase 3: Integração Completa (Frontend + Backend + WhatsApp)
- [x] Task: Atualizar o fluxo do Vanilla JS no painel (em `cotte-frontend/`) para disparar a solicitação de processamento e aguardar o PDF. [d4d4be6]
  - [x] Sub-task: Implementar alertas intrusivos e double opt-in para a finalização do orçamento pelo vendedor. (Revertido conforme feedback - movido para configurações opcionais)
- [x] Task: Acoplar a trilha de logs transacionais para manter o registro de rastreabilidade (Conforme UX guidelines). [d4d4be6]
- [x] Task: Conductor - User Manual Verification 'Phase 3: Integração Completa (Frontend + Backend + WhatsApp)' (Protocol in workflow.md) [d4d4be6]