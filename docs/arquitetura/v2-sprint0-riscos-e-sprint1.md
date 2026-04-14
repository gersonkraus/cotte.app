---
title: V2 Sprint0 Riscos e Sprint1
tags:
  - arquitetura
  - sprint-0
  - sprint-1
prioridade: alta
status: draft
---

# Sprint 0 — Riscos Arquiteturais e Escopo da Sprint 1

## Principais riscos arquiteturais

### 1. Divergência entre tenancy declarada e tenancy real

Há `empresa_id` em muitas entidades, mas o enforcement ainda depende muito de filtros manuais.

Impacto:

- vazamento cross-tenant
- falsa sensação de isolamento

### 2. Superconcentração no `cotte_ai_hub.py`

Boa parte da inteligência atual do assistente ainda converge para um arquivo e fluxo central.

Impacto:

- alto acoplamento
- maior risco de regressão
- dificuldade de separar engines

### 3. Fronteira insuficiente entre produto e ferramenta interna

A interface atual do assistente ainda é a única superfície conversacional relevante.

Impacto:

- risco de o copiloto técnico nascer dentro da UI errada
- confusão entre contexto operacional e contexto de engenharia

### 4. Frontend sem camada explícita de capability flags

Hoje o frontend do assistente já é modular em vários arquivos, mas não existe uma camada formal de capability flags por tela/componente.

Impacto:

- rollout visual arriscado
- necessidade de trocas mais bruscas de UI

### 5. Models híbridos sem política formal

Há modelos com `empresa_id nullable` que não podem receber filtro automático cego.

Impacto:

- risco de quebrar admin, auditoria e fluxos híbridos

## Escopo objetivo da Sprint 1

Sprint 1 confirmada:

- tenant-aware real no backend

## Entregáveis da Sprint 1

- `TenantScopedMixin`
- `tenant_context.py`
- resolução de tenant por request autenticado
- filtro automático na sessão SQLAlchemy para entidades tenant-scoped claras
- bypass seguro e explícito para superadmin
- testes de isolamento cross-tenant
- documentação curta da abordagem

## Fora do escopo da Sprint 1

- reescrever o assistente inteiro
- introduzir SQL Agent
- criar copiloto técnico completo
- substituir a UI atual do assistente
- refatorar profundamente todo o domínio comercial

## Decisões já congeladas para sprints seguintes

- copiloto técnico interno terá interface separada
- frontend ganhará camada de capability flags por tela/componente
- engines analítica, operacional e documental serão explicitadas antes da expansão ampla de capabilities

## Critério de pronto da Sprint 0

- auditoria tenant-aware publicada
- matriz de capabilities publicada
- fronteira do assistente operacional documentada
- riscos arquiteturais consolidados
- escopo da Sprint 1 fechado
