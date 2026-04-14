---
title: V2 Orquestracao Oficial
tags:
  - tecnico
prioridade: media
status: documentado
---
# V2 — Estratégia Oficial de Orquestração IA

## Decisão técnica

- O backend V2 **não usa LangChain** como dependência obrigatória.
- A orquestração padrão continua no runner legado (`assistente_unificado_v2`).
- LangGraph permanece **opcional e behind feature flag** para cenários onde um grafo explícito for útil.

## Flags suportadas

- `V2_LANGGRAPH_ORCHESTRATION=true` ativa a orquestração opcional por LangGraph.
- `USE_LANGGRAPH_ASSISTANT=true` permanece apenas por compatibilidade retroativa.

## Racional

- Reduz acoplamento de runtime e risco operacional em produção.
- Evita retrabalho amplo no core enquanto mantém caminho evolutivo para grafo.
- Permite rollout controlado por ambiente, com fallback automático para o fluxo legado.

## Diretriz de evolução

- Adotar novos nós de orquestração somente para fluxos com benefício comprovado (auditoria, retries, estado multi-etapa).
- Manter o contrato de resposta da API estável durante qualquer experimento de grafo.
