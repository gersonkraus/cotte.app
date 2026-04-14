---
title: V2 Sprint 6 Engine Analitica SQL Agent
tags:
  - arquitetura
  - v2
  - sprint-6
prioridade: alta
status: concluido
---

# Sprint 6 — Engine analítica + SQL Agent seguro

## Objetivo

Criar uma camada analítica explícita, read-only e auditável, com SQL Agent seguro atrás de flag.

## Entregas implementadas

1. Policy e catálogo analítico
   - atualização da engine `analytics` no registry
   - endpoint `GET /api/v1/ai/analytics/catalogo`
   - catálogo com `sql_agent_enabled` e tools agrupadas por domínio

2. Fluxo analítico MVP
   - endpoint `POST /api/v1/ai/analytics/fluxo`
   - fluxo composto read-only:
     - consulta por escopo (`financeiro_resumo`, `orcamentos_resumo`, `clientes_resumo`, `despesas_resumo`)
     - registro auditável
   - contrato padrão com `flow_id`, `trace`, `metrics`

3. SQL Agent seguro (read-only)
   - endpoint `POST /api/v1/ai/analytics/sql-agent`
   - protegido por flag `V2_SQL_AGENT`
   - validação de segurança:
     - aceita apenas `SELECT`/`WITH`
     - bloqueia multi-statement
     - bloqueia DML/DDL
     - aplica whitelist de fontes permitidas (`ANALYTICS_SQL_ALLOWED_SOURCES`)
   - auditoria de SQL original/final e quantidade de linhas retornadas

## Arquivos principais

- `sistema/app/services/analytics_sql_guard.py`
- `sistema/app/services/ai_tools/sql_analytics_tools.py`
- `sistema/app/services/analytics_engine_service.py`
- `sistema/app/services/assistant_engine_registry.py`
- `sistema/app/services/ai_tools/__init__.py`
- `sistema/app/routers/ai_hub.py`

## Testes

- `sistema/tests/test_analytics_sql_guard.py`
- `sistema/tests/test_analytics_engine_service.py`
- `sistema/tests/test_ai_assistente_contract.py`

## Resultado

A Sprint 6 entrega:

- engine analítica separada e explícita
- fluxo analítico read-only com observabilidade
- SQL Agent com guardrails de segurança e rollout por flag
