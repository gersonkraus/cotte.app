---
title: V2 Sprint 2 Hardening
tags:
  - arquitetura
  - tenant
  - auditoria
  - sprint-2
prioridade: alta
status: concluido
---

# Sprint 2 — Hardening de camadas e auditoria

## Objetivo

Endurecer a base tenant-aware da Sprint 1 sem refatoração ampla, focando em:

- trilha de auditoria confiável
- mutações sensíveis com escopo explícito
- redução de pontos perigosos fora do fluxo central
- validação dirigida por testes
- rastreabilidade de tool calls do assistente com `request_id`

## Ajustes implementados

- `registrar_auditoria()` passa a persistir em sessão própria, para não depender do `commit` do chamador
- detalhes de auditoria passam a carregar `request_id`, método e path quando houver `Request`
- mutações de notificações passam a gerar auditoria explícita
- exclusão de lead comercial deixa de aceitar lead global (`empresa_id null`) em fluxo tenant comum
- exclusão de lead passa a registrar resumo do impacto removido
- operações destrutivas de `financeiro` passam a registrar auditoria consistente
- remoção de documento de orçamento passa a registrar auditoria
- `tool_executor` passa a propagar `request_id` da camada HTTP até o `ToolCallLog`

## Decisões

- não houve alteração de contrato de API
- não houve migration nesta sprint
- o endurecimento foi local e reversível
- operações globais/superadmin continuam fora deste escopo quando intencionalmente administrativas

## Limites desta sprint

- ainda existem pontos legados com `db.query()` direto fora da trilha ideal
- models híbridos continuam exigindo política explícita por domínio
- o harness legado de testes ainda está instável para algumas suítes completas

## Testes adicionados

- persistência real da auditoria com `request_id`
- bulk update de notificações sem afetar outra empresa
- exclusão de lead tenant-scoped sem apagar lead global
- deletes e soft-deletes financeiros com auditoria
- remoção de documento de orçamento com auditoria
- tool log do assistente com `request_id`

## Resultado da sprint

Sprint 2 concluída com endurecimento incremental e sem migration:

- tenant runtime da Sprint 1 preservado
- auditoria operacional confiável
- mutações sensíveis com trilha mínima obrigatória
- `request_id` propagado do endpoint do assistente até o `ToolCallLog`

## Próximo passo natural

- revisar bulk mutations e deletes restantes nos domínios `orcamentos` e `financeiro`
- padronizar propagação de `request_id` em logs operacionais e trilhas internas de IA
