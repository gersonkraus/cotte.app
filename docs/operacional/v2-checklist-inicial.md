---
title: V2 Checklist Inicial
tags:
  - operacional
  - v2
  - checklist
prioridade: alta
status: draft
---

# Checklist Inicial de Implantação da V2 Paralela

## Objetivo

Transformar a estratégia da V2 paralela em passos executáveis, na ordem certa, sem quebrar a linha atual.

## Ordem exata de execução

### Fase 1 — Preparar o trilho da V2

1. confirmar `main` como branch estável do produto atual
2. criar a branch base `release/v2`
3. provisionar o ambiente `v2-staging`
4. provisionar o banco `db-v2`
5. registrar a política oficial de feature flags da V2
6. registrar a diretriz de frontend:
   - copiloto técnico em interface separada
   - capability flags por tela/componente

### Fase 2 — Congelar contratos e diagnóstico

7. abrir `feat/v2-s00-diagnostico-contratos`
8. inventariar models com `empresa_id`
9. inventariar rotas, services e repositories críticos
10. fechar a matriz de capabilities atuais do sistema
11. definir o contrato de evolução para:
   - tenant-aware real
   - assistente operacional
   - engines especializadas
   - copiloto técnico
   - SQL Agent
   - capability flags de frontend

### Fase 3 — Começar a implementação estrutural

12. abrir `feat/v2-s01-tenant-aware-runtime`
13. implementar a base de tenancy em paralelo
14. validar isolamento cross-tenant no ambiente V2
15. integrar a sprint em `release/v2`
16. promover apenas infraestrutura compatível para `main`, atrás de flag

### Fase 4 — Repetir o ciclo por capability

17. abrir branch curta por sprint
18. implementar bloco pequeno
19. validar no ambiente V2
20. integrar em `release/v2`
21. promover parcialmente para `main` quando maduro

## Branches iniciais recomendadas

- `release/v2`
- `feat/v2-s00-diagnostico-contratos`
- `feat/v2-s01-tenant-aware-runtime`
- `test/v2-s01-isolamento-cross-tenant`
- `docs/v2-s00-roadmap-operacional`

## Checklist por PR da V2

- escopo fechado
- sprint identificada
- flag definida
- impacto em `main` mapeado
- impacto em banco mapeado
- testes executados
- rollback descrito
- documentação mínima atualizada

## Checklist de merge `main` -> `release/v2`

- verificar hotfixes recentes da linha atual
- atualizar `release/v2` no mínimo duas vezes por semana
- tratar conflitos imediatamente
- não acumular semanas de divergência

## Checklist de promoção `release/v2` -> `main`

- bloco compatível com a linha atual
- protegido por flag quando necessário
- sem dependência escondida de ambiente V2
- testes mínimos verdes
- observabilidade disponível
- rollback definido

## Top 10 ações imediatas

1. criar `release/v2`
2. documentar a estratégia da V2 no repositório
3. provisionar `v2-staging`
4. provisionar `db-v2`
5. registrar as flags da V2
6. abrir Sprint 0
7. gerar a auditoria tenant-aware
8. gerar a matriz de capabilities atuais
9. abrir Sprint 1 tenant-aware
10. definir a cadência fixa de sincronização com `main`

## Erros que não devem acontecer

- manter a V2 isolada da `main` por muito tempo
- usar o banco da versão atual para validar runtime novo
- fazer PRs gigantes por sprint
- empurrar migrations destrutivas cedo
- misturar copiloto técnico com assistente operacional
- deixar flag sem dono e sem plano de remoção
- tentar lançar a V2 de frontend como substituição total da tela atual

## Resultado esperado

Ao final dessa etapa inicial:

- existe um trilho Git claro para a V2
- existe ambiente paralelo seguro
- existe política objetiva para migrations e flags
- existe ordem de execução para as primeiras sprints
- a convergência futura com `main` já começa prevista desde o início
