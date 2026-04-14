---
title: Sugestoes Futuras
tags:
  - arquitetura
  - v2
  - backlog
  - handoff
prioridade: media
status: draft
---

# Sugestões Futuras

## Objetivo

Este arquivo consolida todas as sugestões levantadas ao longo da conversa de hoje, com prioridade maior para aquilo que efetivamente faz sentido para a V2 do Projeto-izi / COTTE.

## Regra de leitura

- o bloco **Prioridade V2** vem primeiro
- depois vêm sugestões úteis, mas secundárias
- por fim vêm ideias complementares e de apoio operacional

## Prioridade V2 — Melhorias essenciais sugeridas

### 1. Criar e manter uma matriz viva de capability

Criar uma matriz operacional viva no formato:

- `capability -> flag -> tela -> backend -> ambiente -> owner -> rollback`

Motivo:

- isso vira a principal ferramenta de controle da V2 na `main`
- ajuda rollout, rollback, ownership e rastreabilidade

### 2. Formalizar ADRs curtos das decisões estruturais

Criar ADRs curtos para decisões realmente estruturais da V2.

Motivo:

- sem isso a trilha V2 acumula decisões implícitas e conflitantes
- reduz retrabalho e discussão repetida nas próximas sprints

### 3. Implantar capability flags no frontend por tela/componente

Criar uma camada simples de capability flags no frontend.

Aplicação inicial recomendada:

- assistente operacional
- financeiro
- orçamentos
- documentos

Motivo:

- rollout incremental
- redução de regressão visual
- ativação gradual de blocos da V2 sem trocar toda a UI

### 4. Separar cedo a interface do copiloto técnico interno

Criar entrada, navegação e tela própria para o copiloto técnico interno.

Motivo:

- impedir mistura entre contexto operacional e contexto técnico
- evitar regressão na UX do assistente operacional

### 5. Revisar e classificar todos os models híbridos

Classificar formalmente todos os models com `empresa_id nullable`.

Motivo:

- esses models são o principal ponto de risco para ampliar tenant enforcement sem quebrar admin, logs e fluxos híbridos

### 6. Revisar bulk operations fora da trilha central

Revisar `update()` e `delete()` fora de `RepositoryBase`.

Motivo:

- Sprint 1 protegeu o núcleo
- mas bulk mutations fora da trilha central continuam exigindo endurecimento manual

### 7. Estabilizar o harness de testes da trilha tenant-aware

Criar uma suíte pequena e estável de testes tenant-aware por domínio crítico.

Domínios prioritários:

- `clientes`
- `orcamentos`
- `financeiro`

Motivo:

- a suíte global ainda é instável
- a V2 precisa de testes confiáveis e pequenos para seguir com segurança

### 8. Continuar o endurecimento por domínio crítico

Ampliar a validação tenant-aware e auditável em:

- `orcamentos`
- `financeiro`
- demais rotas críticas que ainda usam queries e mutações diretas

Motivo:

- esses domínios ainda concentram maior risco de vazamento ou regressão

### 9. Padronizar classificação operacional das ações

Criar padrão único para operações:

- `read_only`
- `mutable`
- `destructive`

Motivo:

- facilita rollout
- facilita auditoria
- facilita confirmação e observabilidade

### 10. Tratar `cotte_ai_hub.py` como alvo de extração gradual

Não reescrever tudo de uma vez.

Motivo:

- o arquivo continua sendo área crítica
- a extração deve acontecer por engine e por capability, não por refactor amplo

### 11. Começar a Sprint 3 pela separação estrutural, não pelo visual

Antes de redesenhar qualquer tela, separar:

- contexto permitido
- contratos de engine
- fontes autorizadas
- capability flags

Motivo:

- reduz risco de UI bonita sobre arquitetura errada

### 12. Usar este handoff como fonte de verdade da V2

Atualizar `v2-evolução.md` ao final de cada sprint.

Motivo:

- evita perda de contexto
- acelera handoff entre agentes

## Prioridade V2 — Ideias inovadoras

### 1. Painel interno de convergência da V2

Criar um painel interno mostrando:

- quais blocos já estão na `main`
- quais capabilities estão ativas
- quais flags existem
- quais empresas piloto estão usando cada capability

### 2. Painel de correlação operacional por `request_id`

Criar um painel interno correlacionando:

- `request_id`
- `AuditLog`
- `ToolCallLog`
- sessão do assistente

Motivo:

- suporte técnico
- debugging operacional
- rollout seguro

### 3. Modo de auditoria tenant

Criar um modo temporário de auditoria tenant que registre:

- tenant ativo
- usuário
- bypass
- mutações sensíveis

Objetivo:

- detectar pontos ainda frágeis durante a evolução da V2

### 4. Test profile sem IA e sem integrações externas

Criar um perfil de testes do sistema que não dependa de IA, WhatsApp, provedores externos ou harness pesado.

Motivo:

- validar tenancy, contratos e rotas com mais estabilidade

### 5. Snapshots mascarados do banco real para `db-v2`

Usar snapshots mascarados e reproduzíveis do banco atual para validar:

- tenant-aware
- engine analítica
- SQL Agent
- fluxos reais do assistente

### 6. Painel de cobertura por mutação auditada

Criar um relatório de:

- routers auditados
- endpoints destrutivos sem auditoria
- capabilities com rollback definido

### 7. Mapa sprint -> commit -> teste -> rollback

Criar um mapa operacional da V2 contendo:

- sprint
- commit
- testes de referência
- flags
- rollback

## Prioridade V2 — Melhorias de frontend de alto impacto

### 1. Separar UI do copiloto técnico da UI do assistente operacional

Não reaproveitar `assistente-ia.html` como host do copiloto técnico.

### 2. Capability flags reais no frontend

Criar um registry simples de capability flags por:

- tela
- componente
- fluxo

### 3. Alinhar capability flags com os domínios endurecidos no backend

Primeiros domínios sugeridos:

- `clientes`
- `orcamentos`
- `financeiro`
- `documentos`

### 4. Expor estados de rollout por tela

Mostrar internamente quais blocos da V2 estão ativos por tela/componente.

### 5. Reservar navegação própria para o copiloto técnico

Mesmo que inicialmente atrás de flag e sem funcionalidade completa.

### 6. Separar commits de frontend por capability

Para próximas sprints:

- não misturar UI do assistente operacional
- UI do copiloto técnico
- flags de rollout

## Sugestões úteis, mas secundárias

## Melhorias essenciais sugeridas

### 1. Criar documento ou matriz de owner por capability

Definir com clareza:

- owner técnico
- flag correspondente
- critério de remoção

### 2. Criar suite pequena de smoke tests por capability

Além dos testes já criados, manter smoke tests pequenos para:

- `clientes`
- `orcamentos`
- `financeiro`
- assistente

### 3. Revisar pontos de query direta em routers

Principalmente em áreas que ainda dependem muito de filtro manual.

### 4. Criar marcador de testes tenant-aware

Exemplo:

- `tenant_runtime`

Para concentrar execução dos testes de isolamento.

### 5. Introduzir logs de teste opcionais de tenant ativo

Útil para debugar vazamentos rapidamente.

### 6. Manter commits pequenos por capability

Especialmente agora que a evolução seguirá na `main`.

## Ideias inovadoras

### 1. Modo de “trilha reforçada” para o assistente

Registrar temporariamente em ambiente interno:

- capability acionada
- request_id
- tool
- resultado
- status de confirmação

### 2. Relatório interno de pontos fora da trilha oficial

Gerar periodicamente uma lista de:

- rotas com acesso direto a model
- mutações fora de service
- bulk operations sem trilha clara

### 3. Registro visual de estado da capability no frontend

Mostrar internamente se a tela/componente está:

- legado
- v2-base
- v2-piloto
- v2-estável

## Melhorias de frontend de alto impacto

### 1. Bootstrap independente da futura UI do copiloto técnico

O shell do copiloto técnico deve nascer independente do shell do assistente operacional.

### 2. Rollout visual gradual por capability

Evitar lançamento de “nova interface completa”.

### 3. Separar evolução visual de estabilidade funcional

Não misturar no mesmo ciclo:

- melhoria estética
- mudança de comportamento crítico

## Sugestões complementares e de apoio

## Melhorias essenciais sugeridas

### 1. Manter um baseline documental por sprint

Atualizar documentação de sprint no fechamento de cada etapa.

### 2. Criar convenção de commits por sprint/capability

Exemplos:

- `v2/sprint-03`
- `v2/sprint-04`
- `assistente/*`

### 3. Revisar continuamente o escopo de models tenant-scoped

Sempre que um domínio novo for endurecido.

## Ideias inovadoras

### 1. Painel de rollout da V2 por empresa piloto

Visualizar:

- empresas usando capability nova
- flags ativas
- incidentes ou rollback

### 2. Visão histórica da convergência V2

Manter histórico simples de:

- capabilities criadas
- capabilities ativadas
- capabilities estáveis

## Melhorias de frontend de alto impacto

### 1. Documentar telas e componentes sensíveis da V2

Especialmente:

- assistente operacional
- financeiro
- orçamentos
- copiloto técnico

### 2. Evitar grandes mudanças visuais sem flag

Toda nova experiência sensível deve nascer protegida e reversível.

## Observação final

Quando houver dúvida de prioridade:

1. priorizar o que reduz risco estrutural da V2
2. depois priorizar o que melhora rollout e observabilidade
3. por último priorizar melhorias complementares

