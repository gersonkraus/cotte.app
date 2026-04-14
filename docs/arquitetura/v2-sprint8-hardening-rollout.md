---
title: V2 Sprint 8 Hardening e Rollout
tags:
  - arquitetura
  - v2
  - sprint-8
prioridade: alta
status: concluido
---

# Sprint 8 — Hardening e rollout controlado

## Objetivo

Fechar a separação de engines com foco em:

- isolamento de superfícies (`assistente` vs `copiloto interno`)
- robustez de contrato de capabilities para frontend
- guardrails de tool access por engine
- checklist de rollout seguro

## Entregas concluídas

1. Hardening no registry de engines para o copiloto interno:
   - `executar_sql_analitico` agora respeita exclusivamente a flag de SQL Agent.
2. Cobertura de testes de isolamento:
   - bloqueio de `engine=internal_copilot` também no endpoint `POST /ai/assistente/stream`.
3. Cobertura de contrato de capabilities:
   - validação explícita de `flags`, `engines`, `components`, `available_engines`.
   - validação dos engines obrigatórios no payload e tipo boolean em disponibilidade.
4. Testes unitários da política de tools do registry:
   - garante remoção de SQL quando SQL Agent está desabilitado.
   - garante exposição de SQL quando SQL Agent está habilitado (mesmo com Code RAG desligado).

## Checklist de rollout (produção)

- [ ] ativar `V2_INTERNAL_COPILOT=true` apenas para perfis internos autorizados
- [ ] ativar `V2_SQL_AGENT=true` de forma gradual por ambiente
- [ ] validar logs de 400/403 em `/ai/assistente` e `/ai/copiloto-interno`
- [ ] monitorar taxa de fallback de capabilities no frontend
- [ ] revisar auditoria dos fluxos internos (`fluxo_copiloto_tecnico`)

## Riscos residuais

- Divergência de contrato entre backend e frontend em mudanças futuras sem versionamento.
- Acoplamento entre rollout por flags e permissões de perfil pode causar bloqueio inesperado se não houver observabilidade.

## Próximo passo recomendado (Sprint 9)

Adicionar telemetria padronizada por engine (latência, erro, bloqueio por policy) com dashboard único de operação IA.
