---
title: V2 Sprint 4 Engine Operacional
tags:
  - arquitetura
  - v2
  - sprint-4
prioridade: alta
status: concluido
---

# Sprint 4 — Engine operacional universal

## Objetivo

Organizar a execução operacional em uma superfície explícita e auditável, preservando compatibilidade do assistente atual.

## Entregas implementadas (base)

1. Catálogo operacional explícito por domínio:
   - endpoint `GET /api/v1/ai/operacional/catalogo`
   - agrupamento por domínio (`orcamentos`, `financeiro`, `clientes`, `catalogo`, `agendamentos`, `auditoria`)

2. Fluxo composto operacional de orçamento:
   - endpoint `POST /api/v1/ai/operacional/fluxo-orcamento`
   - etapas padronizadas:
     - consultar/montar orçamento
     - gerar PDF
     - enviar por canal (email/whatsapp)
     - registrar resultado auditável

3. Confirmação destrutiva padronizada:
   - `pending_action` com `confirmation_required`, `action_category`, `idempotency_window_seconds`

4. Idempotência de envios:
   - proteção para `enviar_orcamento_whatsapp` e `enviar_orcamento_email`
   - replay seguro de chamada equivalente em janela configurável (`TOOL_SEND_IDEMPOTENCY_TTL_SECONDS`)

## Incrementos desta fase (continuidade)

1. Catálogo operacional agora respeita a policy da engine operacional:
   - remove tools fora do escopo operacional (ex.: `analisar_tool_logs`)
   - mantém agrupamento por domínio sem alterar contrato do endpoint

2. Fluxo composto com confirmação padronizada:
   - retorno `pending_confirmation` passa a incluir `pending_action.flow_step`
   - `confirmation_required` garantido no payload de pendência

3. Idempotência de envios fechada também no caminho de confirmação por token:
   - evita reexecução de envio quando existirem tokens pendentes duplicados
   - replay retorna `code=idempotent_replay` de forma consistente

4. Observabilidade operacional por fluxo:
   - `flow_id` único por execução do fluxo composto
   - `trace` com `duration_ms` e `executado_em_utc` por etapa
   - `metrics` agregadas (`total_steps`, `total_duration_ms`, `steps_with_error`, `steps_pending`)

5. Novo fluxo composto financeiro (MVP):
   - endpoint `POST /api/v1/ai/operacional/fluxo-financeiro`
   - etapas padronizadas:
     - consultar contexto financeiro (`obter_saldo_caixa`)
     - executar ação financeira (`criar_movimentacao_financeira`)
     - registrar resultado auditável
   - suporta pendência destrutiva com o mesmo contrato `pending_confirmation`

6. Novo fluxo composto de agenda (MVP):
   - endpoint `POST /api/v1/ai/operacional/fluxo-agendamento`
   - etapas padronizadas:
     - consultar contexto de agenda (`listar_agendamentos`)
     - executar ação (`criar_agendamento` ou `remarcar_agendamento`)
     - registrar resultado auditável
   - suporta pendência destrutiva com o mesmo contrato `pending_confirmation`

## Arquivos principais

- `sistema/app/services/operational_engine_service.py`
- `sistema/app/routers/ai_hub.py`
- `sistema/app/services/tool_executor.py`
- `sistema/app/services/ai_tools/__init__.py`
- `sistema/tests/test_tool_executor.py`
- `sistema/tests/test_ai_assistente_contract.py`
- `sistema/tests/test_operational_engine_service.py`
- `sistema/app/routers/ai_hub.py`

## Testes de referência

- `sistema/tests/test_tool_executor.py`
- `sistema/tests/test_ai_assistente_contract.py`

## Resultado

Engine operacional passa a ter:

- superfície clara de execução
- catálogo auditável de tools
- fluxo composto padronizado para orçamento
- confirmação destrutiva consistente
- idempotência de envio para reduzir duplicidade operacional
