---
title: V2 Paralela Git Strategy
tags:
  - arquitetura
  - git
  - v2
prioridade: alta
status: draft
---

# Estratégia de Git e Evolução Paralela da V2

## Objetivo

Definir como a arquitetura 2.0 do Projeto-izi / COTTE deve evoluir em paralelo à versão atual, sem interromper a operação da `main`, sem criar um merge final inviável e sem transformar a V2 em um fork descontrolado.

## Decisão principal

A estratégia oficial da V2 é:

- manter `main` como trilho estável e deployável
- usar `release/v2` como branch de integração da nova arquitetura
- trabalhar em branches curtas por sprint ou capability a partir de `release/v2`
- promover blocos maduros de `release/v2` para `main` de forma gradual, atrás de feature flags

Essa estratégia evita dois erros comuns:

1. criar uma branch V2 eterna e desconectada da evolução real do produto
2. tentar fazer um big bang merge no final

## Branches oficiais

### `main`

Papel:

- produção
- hotfixes
- correções do sistema atual
- base estável do projeto

Regras:

- sempre deve estar deployável
- não recebe experimentos incompletos da V2
- tudo que vier da V2 deve entrar atrás de flag quando houver impacto de comportamento

### `develop`

Papel:

- homologação da linha atual e integração de curto prazo, se o time precisar de um trilho pré-`main`

Regra:

- opcional
- se não houver disciplina de uso, é melhor não forçar

### `release/v2`

Papel:

- branch de integração da arquitetura 2.0
- base do ambiente paralelo da V2
- ponto de convergência das entregas de sprint da V2

Regras:

- não receber trabalho cru ou experimental sem critério
- só receber PR revisado, validado e com escopo fechado
- deve ser atualizada com `main` de forma frequente
- deve refletir o estado corrente mais avançado da V2

### Branches curtas da V2

Tipos permitidos:

- `feat/v2-sXX-*`
- `refactor/v2-sXX-*`
- `fix/v2-sXX-*`
- `test/v2-sXX-*`
- `docs/v2-sXX-*`

Exemplos:

- `feat/v2-s00-diagnostico-contratos`
- `feat/v2-s01-tenant-aware-runtime`
- `test/v2-s01-isolamento-cross-tenant`
- `feat/v2-s03-separacao-engines`
- `feat/v2-s07-sql-agent-readonly`

Regra:

- sempre nascer de `release/v2`
- sempre voltar para `release/v2` por PR
- vida curta
- escopo pequeno o suficiente para revisão real

## Fluxo oficial de trabalho

### Fluxo por sprint

1. abrir branch da sprint a partir de `release/v2`
2. fechar contrato técnico da sprint
3. implementar base mínima
4. adicionar testes e documentação curta
5. abrir PR para `release/v2`
6. validar no ambiente paralelo da V2
7. decidir se algum bloco já pode ser promovido para `main`

### Fluxo de integração com `main`

1. `main` continua recebendo correções do sistema atual
2. `release/v2` deve incorporar `main` com frequência alta
3. blocos maduros e compatíveis da V2 devem voltar para `main` antes do final do programa

Cadência mínima recomendada:

- merge ou rebase de `main` em `release/v2` duas vezes por semana
- atualização imediata após hotfix relevante na `main`

## Política de PR

Todo PR da V2 deve responder:

- qual sprint ou capability cobre
- qual contrato toca
- se altera comportamento atual
- qual feature flag protege a mudança
- qual é o plano de rollback
- quais testes cobrem o bloco

Um PR da V2 não deve:

- misturar tenancy com frontend visual sem necessidade
- misturar infraestrutura com cleanup grande
- misturar engines diferentes no mesmo diff
- tocar arquivo central e múltiplos fluxos críticos sem prova de isolamento

## Estratégia de convergência

### Fronteira de interface obrigatória

Desde a Sprint 0, a V2 deve assumir duas regras de frontend:

- o copiloto técnico interno terá interface própria e separada da interface do assistente operacional
- a ativação gradual da V2 no frontend deve ocorrer por capability flags por tela e componente, evitando troca integral de UI

Motivo:

- reduzir regressão visual e funcional no assistente operacional atual
- impedir mistura de contexto entre uso interno técnico e uso operacional do produto
- permitir rollout incremental no frontend sem precisar lançar uma “nova interface completa”

### O que deve voltar cedo para `main`

- utilitários neutros
- infraestrutura compatível
- abstrações de contexto
- observabilidade
- feature flags
- adapters novos com fallback
- camada simples de capability flags no frontend

### O que só volta quando maduro

- runtime automático de tenant
- engine analítica
- SQL Agent
- copiloto técnico
- caminhos novos do assistente operacional

### O que volta por último

- desligamento de código legado
- remoção de flags mortas
- contração de schema

## Regras para evitar bagunça

- nenhuma branch de feature da V2 deve durar sem sincronização real por mais de 5 a 7 dias úteis
- nenhum PR da V2 deve ser “só para subir tudo e revisar depois”
- nenhuma migration destrutiva entra cedo
- nenhum caminho novo deve depender exclusivamente de LangChain
- nenhum acoplamento entre copiloto técnico interno e assistente operacional deve ser aceito
- nenhuma tela do copiloto técnico deve nascer dentro de `assistente-ia.html`

## Anti-padrões proibidos

- branch `v2` isolada por meses sem merges da `main`
- reescrever arquivos centrais sem encapsular antes
- subir V2 no mesmo ambiente principal
- usar o banco atual para testar runtime novo de tenancy
- misturar rollout funcional e cleanup estrutural no mesmo bloco

## Critério de sucesso da estratégia

Ao final da evolução:

- a V2 não terá exigido um merge final gigante
- `main` terá absorvido blocos maduros progressivamente
- a operação atual terá permanecido estável
- a arquitetura nova terá sido validada por feature flags, ambientes paralelos e rollout gradual
- o frontend terá evoluído por capabilities sem precisar substituir a tela atual do assistente de uma vez
