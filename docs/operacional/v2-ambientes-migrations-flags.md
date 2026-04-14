---
title: V2 Ambientes Migrations Flags
tags:
  - operacional
  - v2
  - migrations
  - feature-flags
prioridade: alta
status: draft
---

# Ambientes, Migrations e Feature Flags da V2

## Objetivo

Definir como a V2 deve ser testada e evoluída sem quebrar a versão atual, com isolamento de ambiente, disciplina de migration e feature flags desde o início.

## Ambientes oficiais

### `prod-atual`

- origem: `main`
- função: operação estável do produto atual
- regra: nunca receber blocos incompletos da V2

### `staging-atual`

- origem: `develop` ou trilho atual de homologação
- função: validar regressão do sistema existente

### `v2-staging`

- origem: `release/v2`
- função: homologação da arquitetura 2.0
- regra: ambiente exclusivo para validar tenancy automática, engines, copiloto e rollout paralelo

### `v2-lab`

- opcional
- função: testes mais arriscados ou exploratórios
- usos típicos:
  - SQL Agent
  - Code RAG
  - ingestão documental
  - observabilidade experimental

## Bancos recomendados

- `db-prod-atual`
- `db-staging-atual`
- `db-v2`
- `db-v2-dev` opcional

## Regra de isolamento

A V2 deve evoluir com banco separado enquanto houver mudanças estruturais relevantes.

Usar `db-v2` é obrigatório quando houver:

- mudança de tenancy runtime
- migrations novas ainda não promovidas para a linha estável
- engine analítica nova
- tabelas novas de auditoria, tracing ou ingestão
- SQL Agent ou RAG com superfícies novas

Não usar o banco atual para:

- validar enforcement automático de tenant
- validar writes da V2
- validar migrações estruturais ainda não convergidas

## Estratégia de migrations

### Princípio oficial

Aplicar o padrão:

- expandir primeiro
- migrar uso depois
- contrair por último

### Tipos de migration aceitos cedo

- novas tabelas
- novas colunas nullable
- novos índices
- novas views
- novas tabelas de log, auditoria e suporte

### Tipos de migration que devem esperar

- drop de coluna usada pela versão atual
- rename de coluna central sem compatibilidade dupla
- mudança semântica irreversível de dado
- alteração incompatível em tabela crítica compartilhada

### Regra por sprint

Toda migration da V2 deve informar:

- se é compatível com a versão atual
- se depende de feature flag
- se precisa de banco separado
- como reverter
- se a `main` consegue continuar funcionando com ela aplicada

## Estratégia de unificação de schema

O caminho oficial é:

1. criar suporte novo com compatibilidade
2. mover leitura e escrita para o caminho novo atrás de flags
3. validar em `v2-staging`
4. promover para `main`
5. só depois remover legado

## Feature flags oficiais da V2

Flags base:

- `V2_TENANT_RUNTIME`
- `V2_ANALYTICS_ENGINE`
- `V2_OPERATIONS_ENGINE`
- `V2_DOCUMENT_ENGINE`
- `V2_CODE_RAG`
- `V2_INTERNAL_COPILOT`
- `V2_SQL_AGENT`
- `V2_LANGGRAPH_ORCHESTRATION`

## Regras de uso de flags

- default desligado em `main`
- ativação controlada em `release/v2` e `v2-staging`
- ativação por empresa, usuário ou capability quando fizer sentido
- toda flag precisa de dono
- toda flag precisa de critério de remoção
- toda flag precisa de rollback claro

## Regra adicional de frontend

As flags da V2 não devem atuar apenas no backend. O frontend deve ter uma camada simples de capability flags para:

- ligar blocos novos por tela
- ligar componentes específicos dentro de telas existentes
- manter a interface atual ativa enquanto capacidades da V2 entram por partes

Diretriz inicial:

- `assistente-ia.html` continua sendo a interface do assistente operacional
- o copiloto técnico interno deve nascer em tela própria
- a navegação e os componentes devem reagir a flags sem exigir troca completa da UI

## Ordem recomendada de ativação

1. infraestrutura e observabilidade
2. tenancy runtime
3. engine analítica
4. capability flags de frontend
5. engine operacional
6. engine documental
7. SQL Agent
8. Code RAG
9. copiloto técnico
10. LangChain seletivo

## Matriz mínima que deve existir

Para cada capability da V2, manter:

- branch de origem
- ambiente onde roda
- banco usado
- flag de proteção
- status
- empresas piloto
- rollback

## Riscos operacionais principais

### V2 contaminar a versão atual

Mitigação:

- ambientes e banco separados
- flags desligadas na `main`

### Migration incompatível entrar cedo

Mitigação:

- migrations aditivas
- revisão arquitetural antes de promover

### Código convergir antes de telemetria

Mitigação:

- toda capability nova deve subir com observabilidade mínima

### Duas arquiteturas ficarem ativas por tempo demais

Mitigação:

- cada flag nasce com plano de remoção
- cleanup entra no fechamento de sprint madura
