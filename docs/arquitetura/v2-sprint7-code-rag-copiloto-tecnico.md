---
title: V2 Sprint 7 Code RAG Copiloto Tecnico
tags:
  - arquitetura
  - v2
  - sprint-7
prioridade: alta
status: concluido
---

# Sprint 7 — Code RAG + copiloto técnico interno

## Objetivo

Separar formalmente o Code RAG técnico do RAG empresarial e consolidar uma superfície interna dedicada ao copiloto técnico.

## Entregas implementadas

1. Isolamento formal de contexto técnico
   - nova camada `code_rag_service.py` para busca contextual em codebase técnica
   - uso de fontes internas (`sistema/app`, `sistema/cotte-frontend/js`) com filtro de extensão e limites de varredura
   - sem reutilizar RAG empresarial por tenant

2. Política de acesso do copiloto técnico
   - `internal_copilot_service.can_use_internal_copilot` define acesso para perfis internos autorizados
   - rota do copiloto interno reforçada com validação explícita de perfil

3. Superfície técnica dedicada
   - novo endpoint `POST /api/v1/ai/copiloto-interno/consulta-tecnica`
   - fluxo técnico com `flow_id`, `trace`, `metrics`
   - suporte opcional a:
     - contexto de código (`include_code_context`)
     - consulta SQL técnica (`sql_query`) somente quando `V2_SQL_AGENT` ativo

4. Combinação Code RAG + SQL Agent sob contexto interno
   - `ENGINE_INTERNAL_COPILOT` com `allow_code_context=True`
   - tool SQL analítica permitida para engine interna, condicionada a flags
   - guardrails explícitos no prompt da engine interna para estado das flags

## Arquivos principais

- `sistema/app/services/code_rag_service.py`
- `sistema/app/services/internal_copilot_service.py`
- `sistema/app/services/assistant_engine_registry.py`
- `sistema/app/services/cotte_ai_hub.py`
- `sistema/app/routers/ai_hub.py`

## Testes

- `sistema/tests/test_code_rag_service.py`
- `sistema/tests/test_internal_copilot_service.py`
- `sistema/tests/test_ai_assistente_contract.py`

## Resultado

A Sprint 7 entrega:

- separação concreta entre RAG empresarial e Code RAG técnico
- fluxo interno técnico dedicado e auditável
- combinação de contexto de código e SQL sob controles de acesso/flag
