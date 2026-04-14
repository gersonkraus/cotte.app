---
title: V2 Sprint 3 Separacao Engines
tags:
  - arquitetura
  - v2
  - sprint-3
prioridade: alta
status: em_andamento
---

# Sprint 3 — Separacao estrutural das inteligencias

## Objetivo desta etapa

Formalizar, no codigo, a fronteira entre:

- assistente operacional (produto)
- engine analitica
- engine documental
- copiloto tecnico interno

Sem reescrever o assistente atual e mantendo compatibilidade.

## O que foi implantado nesta primeira entrega

1. Registry central de engines em `app/services/assistant_engine_registry.py`
2. Contrato de engine no endpoint do assistente (`engine` no payload)
3. Guardrails por engine aplicados no prompt da orquestracao v2
4. Filtragem de tools por engine (evita mistura de superficie)
5. Endpoint separado para capacidades e flags:
   - `GET /api/v1/ai/assistente/capabilities`
6. Endpoint separado do copiloto tecnico interno:
   - `POST /api/v1/ai/copiloto-interno`
7. Base de capability flags no frontend:
   - `js/services/CapabilityFlagsService.js`

## Fases executadas na Sprint 3

### Fase 1 — Contratos e guardrails

- contrato `engine` no backend do assistente
- politicas de engine com ferramentas permitidas
- guardrails de prompt por engine

### Fase 2 — Capabilities por tela/componente

- endpoint de capabilities com flags, componentes e engines disponiveis
- service frontend para carregar e consultar capabilities
- aplicacao de capability no menu lateral

### Fase 3 — Superficie separada do copiloto tecnico interno

- endpoint dedicado `/ai/copiloto-interno`
- bloqueio do engine interno no endpoint operacional (`/ai/assistente`)
- pagina dedicada `copiloto-tecnico.html` com cliente proprio

## Mapa engine -> fontes -> permissao -> superficie

### 1) Operational

- Fontes: contexto de negocio + RAG tenant + tools operacionais
- Permissao: `ia/leitura` (normal do assistente)
- Superficie: `POST /api/v1/ai/assistente` e `/assistente/stream`
- Flag principal: `V2_OPERATIONS_ENGINE`

### 2) Analytics

- Fontes: dados operacionais read-only
- Permissao: mesma trilha do assistente (sem mutacao)
- Superficie: mesma rota do assistente com `engine=analytics`
- Flag principal: `V2_ANALYTICS_ENGINE`

### 3) Documental

- Fontes: documentos empresariais e contexto correlato
- Permissao: mesma trilha do assistente
- Superficie: mesma rota do assistente com `engine=documental`
- Flag principal: `V2_DOCUMENT_ENGINE`

### 4) Internal Copilot

- Fontes: trilha interna tecnica (sem contexto operacional de cliente)
- Permissao: gestor/superadmin + flag habilitada
- Superficie: `POST /api/v1/ai/copiloto-interno` (rota separada)
- Flag principal: `V2_INTERNAL_COPILOT`

## Guardrails adotados

- copiloto interno nao reutiliza endpoint/contrato principal do assistente operacional
- engine define lista de tools permitidas
- policy por engine declara se pode usar:
  - contexto de negocio
  - rag tenant
  - contexto tecnico de codebase

## Proximos passos da Sprint 3

1. Expandir policy documental com catalogo de documentos por dominio
2. Adicionar testes E2E cobrindo isolamento de contexto por engine
3. Conectar rollout por empresa piloto usando as flags atuais
