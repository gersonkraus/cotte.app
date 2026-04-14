---
title: V2 Sprint 5 Engine Documental
tags:
  - arquitetura
  - v2
  - sprint-5
prioridade: alta
status: concluido
---

# Sprint 5 — Engine documental

## Objetivo

Separar a camada documental da conversa operacional, com superfície explícita, auditável e compatível com os contratos da V2.

## Entregas implementadas

1. Policy da engine documental consolidada
   - `assistant_engine_registry` atualizado com superfície documental explícita
   - allowlist inclui consulta de orçamento/clientes e anexo documental em orçamento

2. Catálogo documental dedicado
   - endpoint `GET /api/v1/ai/documental/catalogo`
   - retorno com metadados da engine e tools agrupadas por domínio

3. Fluxo composto documental (MVP)
   - endpoint `POST /api/v1/ai/documental/fluxo-orcamento`
   - etapas:
     - consultar orçamento (`obter_orcamento`)
     - montar dossiê documental (resumo do orçamento + documentos da empresa)
     - anexar documento no orçamento (opcional)
     - registrar auditoria
   - confirmação destrutiva padronizada via `pending_confirmation`

4. Contrato operacional reutilizado
   - `flow_id`, `trace`, `metrics`, `pending_action`
   - sem quebra do contrato existente da Sprint 4

## Arquivos principais

- `sistema/app/services/documental_engine_service.py`
- `sistema/app/services/assistant_engine_registry.py`
- `sistema/app/routers/ai_hub.py`
- `sistema/tests/test_documental_engine_service.py`
- `sistema/tests/test_ai_assistente_contract.py`

## Resultado

A engine documental passa a ter:

- fronteira própria de catálogo e fluxo
- isolamento por tenant (documentos por `empresa_id`)
- suporte a anexo documental em orçamento com confirmação destrutiva
- padrão de observabilidade e auditoria alinhado às engines operacionais
