---
title: Tenant Runtime Sprint1
tags:
  - arquitetura
  - tenant
  - sprint-1
prioridade: alta
status: draft
---

# Sprint 1 — Tenant Runtime

## Objetivo

Endurecer o isolamento por empresa no backend sem trocar a tenant key atual e sem quebrar a autenticação existente.

## Abordagem adotada

- `empresa_id` continua como tenant key oficial
- models tenant-scoped claros passam a herdar `TenantScopedMixin`
- a sessão SQLAlchemy recebe contexto tenant após a autenticação
- leituras ORM passam a receber filtro automático para entities marcadas
- novas entities tenant-scoped recebem `empresa_id` automático no `before_flush`
- `delete()` no `RepositoryBase` passa a respeitar tenant scope para models marcados
- superadmin só obtém bypass total por ativação explícita

## Componentes introduzidos

- `app/models/tenant.py`
- `app/core/tenant_context.py`
- listeners na sessão em `app/core/database.py`

## Limites intencionais desta sprint

- models híbridos com `empresa_id nullable` não entram no filtro automático por enquanto
- entities dependentes de pai tenant-scoped continuam exigindo atenção por relação ou regra específica
- bulk `update()`/`delete()` feitos fora de `RepositoryBase` continuam exigindo revisão manual na Sprint 2
- esta sprint não reescreve routers/services legados; ela cria a camada central de enforcement

## Validação mínima

- leitura cross-tenant filtrada automaticamente
- criação de model tenant-scoped com `empresa_id` automático
- bypass de superadmin apenas quando ativado explicitamente
