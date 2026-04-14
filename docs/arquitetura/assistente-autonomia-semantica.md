---
title: Assistente Autonomia Semantica
tags:
  - tecnico
prioridade: media
status: documentado
---
# Assistente IA — Arquitetura de Autonomia Semântica

## Objetivo

Evoluir o assistente para operar por intenção de negócio e contratos semânticos, evitando crescimento linear de tools específicas.

## Camadas implementadas

1. **Intent Router**  
   Arquivo: `sistema/app/services/assistant_autonomy/intent_router.py`
2. **Semantic Planner**  
   Arquivo: `sistema/app/services/assistant_autonomy/semantic_planner.py`
3. **Semantic Model (métricas/dimensões)**  
   Arquivo: `sistema/app/services/assistant_autonomy/semantic_model.py`
4. **Policy Engine**  
   Arquivo: `sistema/app/services/assistant_autonomy/policy_engine.py`
5. **Execution Graph**  
   Arquivo: `sistema/app/services/assistant_autonomy/execution_graph.py`
6. **Response Composer**  
   Arquivo: `sistema/app/services/assistant_autonomy/response_composer.py`
7. **Telemetry/Audit**  
   Arquivo: `sistema/app/services/assistant_autonomy/telemetry.py`

## Capability map (sem tool sprawl)

- `GenerateAnalyticsReport`: relatório semântico orientado por métricas e período.
- `PrepareQuotePackage`: criação estruturada de orçamento via capability transacional.
- `DeliverQuoteMultiChannel`: entrega multicanal (WhatsApp/e-mail) como capability única.
- `CreateCommercialProposal`: geração orientada a proposta comercial.

As tools atuais permanecem como adapters internos no `capability_layer.py`.

## Semantic model inicial

### Métricas canônicas
- `revenue_total`
- `overdue_receivables`
- `top_customers`
- `seller_performance`
- `quote_conversion`

### Dimensões iniciais
- `time_month`
- `time_quarter`
- `customer`
- `seller`
- `channel`

## Policy engine central

Políticas já aplicadas:
- exigência de escopo tenant (`empresa_id`);
- validação de disponibilidade de engine para usuário;
- gating de SQL Agent para capability analítica;
- limites operacionais (linhas/período) para execução semântica.

## Contratos de resposta

Contrato multiformato padronizado:
- `summary` (texto executivo),
- `table` (detalhamento tabular),
- `chart` (payload gráfico),
- `printable` (payload para saída imprimível).

Implementação em `response_composer.py`.

## Migração incremental (sem ruptura)

1. Ativar por flag: `V2_SEMANTIC_AUTONOMY=true`.
2. Quando ativo, `assistente_unificado_v2` tenta o runtime semântico.
3. Em erro ou indisponibilidade, fallback para fluxo legado é automático.
4. Rollout recomendado: analytics -> comercial -> transacional.

Integração de entrada: `sistema/app/services/cotte_ai_hub.py`.

## Observabilidade e SLOs

Cada execução semântica registra:
- capability, domínio e métricas;
- `request_id`, `sessao_id`, `empresa_id`;
- sucesso/erro e código;
- duração total e número de passos.

Registro via `registrar_auditoria` em `telemetry.py`.

### SLOs iniciais recomendados
- p95 `total_duration_ms` por capability < 2500ms (analytics simples);
- taxa de sucesso por capability > 97%;
- erro de política < 2% para intents válidas.
