---
title: V2 Sprint 9 Observabilidade e Rollout
tags:
  - arquitetura
  - v2
  - sprint-9
prioridade: alta
status: concluido
---

# Sprint 9 — Observabilidade e rollout controlado

## Objetivo

Fechar a V2 com rastreabilidade operacional e controle de ativação por empresa, sem depender de rollout global cego.

## Entregas concluídas

1. Observabilidade de IA por engine:
   - endpoint `GET /api/v1/ai/observabilidade/resumo`
   - visão consolidada de volume, taxa de erro, latência e saúde por engine
2. Telemetria de engine no `ToolCallLog`:
   - metadado `_meta.engine` propagado no executor para consultas de observabilidade
3. Rollout controlado por empresa:
   - persistência de plano em `config_global` (`ai_rollout_v2_plan`)
   - endpoint `GET /api/v1/ai/rollout/status` para resolução efetiva por empresa
   - endpoints admin:
     - `GET /api/v1/ai/rollout/plan`
     - `PUT /api/v1/ai/rollout/plan`
4. Cobertura de testes:
   - contrato de observabilidade
   - contrato de status de rollout
   - permissão de admin para leitura/atualização do plano

## Modelo de rollout aplicado

- fases suportadas: `disabled`, `pilot`, `ga`
- configuração por empresa:
  - `phase`
  - `enabled_engines`
  - `notes`
- fallback por `default_phase`

## Checklist operacional

- [ ] definir empresas piloto para analytics/documental/internal_copilot
- [ ] validar painéis de erro/latência por janela de 24h e 7d
- [ ] revisar auditoria de alterações de plano (`ai_rollout_plan_update`)
- [ ] documentar política de promoção `pilot -> ga`

## Riscos residuais

- como o rollout está em `config_global`, mudanças manuais no banco sem validação de payload podem gerar inconsistência operacional.
- a observabilidade atual usa janela de leitura por banco transacional; para escala maior, migrar para pipeline de métricas dedicado.

## Próximo passo recomendado (V2 pós-fechamento)

Evoluir o resumo de observabilidade para um painel visual no frontend admin com filtros por empresa, engine e erro dominante.
