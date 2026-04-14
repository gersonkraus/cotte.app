---
title: V2 Evolução
tags:
  - arquitetura
  - v2
  - handoff
  - roadmap
prioridade: alta
status: em_andamento
---

# V2 — Contexto Completo de Evolução

## Finalidade deste arquivo

Este documento é o contexto principal para qualquer agente continuar e concluir a V2 do Projeto-izi / COTTE.

Ele deve responder com clareza:

- qual é a estratégia vigente
- o que já foi implantado de verdade
- o que ainda falta por sprint
- quais arquivos e testes importam
- quais decisões já estão congeladas
- quais riscos não podem ser ignorados
- qual ordem exata deve ser seguida para concluir 100%

Se houver conflito entre este documento e hipóteses não verificadas, prevalece a evidência do código atual.

## Resumo executivo

### Estado atual

- a V2 está sendo implantada incrementalmente na `main`
- não existe mais separação por branch entre sistema atual e V2
- a separação entre “atual” e “novo” será garantida por:
  - compatibilidade retroativa
  - feature flags
  - rollout gradual
  - testes dirigidos
  - diffs pequenos e reversíveis

### O que já foi concluído

- Sprint 0: diagnóstico, contratos e decisões-base
- Sprint 1: tenant-aware real no núcleo backend
- Sprint 2: hardening de camadas, auditoria e trilha operacional do assistente

### O próximo passo real

- Sprint 3: separação estrutural entre:
  - assistente operacional do produto
  - copiloto técnico interno
  - engine analítica
  - engine operacional
  - engine documental

## Estratégia operacional vigente

### Decisão atual

O desenvolvimento da V2 seguirá na `main`.

Isso significa que:

- a V2 não será construída como fork paralelo de longo prazo
- toda capability nova deve ser introduzida com o menor impacto possível
- nenhuma sprint futura deve assumir liberdade para reescrever grandes áreas sem proteção

### Como evitar mistura caótica na `main`

Toda continuação deve obedecer:

1. feature flag para mudanças com impacto funcional
2. contratos claros antes de mexer em comportamento
3. testes focados por domínio
4. sem migration destrutiva precoce
5. sem refatoração ampla “aproveitando embalo”
6. separação explícita entre contexto do produto e contexto interno técnico

## Commits-base já realizados

### Commit 1

- hash: `34f0dfa`
- mensagem: `v2: adiciona base tenant-aware e docs das sprints 0-1`

### Commit 2

- hash: `cda28f6`
- mensagem: `v2: conclui sprint 2 com hardening e trilha operacional`

### Commit 3

- hash: `b0d389a`
- mensagem: `assistente: atualiza frontend, contratos e suporte operacional`

### Uso prático desses commits

Outro agente deve tratar esses três commits como baseline atual da V2.

Não reabrir Sprint 0, Sprint 1 ou Sprint 2 como se estivessem “por fazer”.

## Decisões arquiteturais congeladas

### 1. Tenant key oficial

- `empresa_id` é a tenant key oficial
- não criar `tenant_id` novo

### 2. Fluxo de backend

- preservar o fluxo `router -> service -> repository -> model`
- quando houver exceção, documentar e limitar

### 3. Assistente operacional x copiloto técnico

- o assistente operacional é o assistente do produto para operação da empresa usuária
- o copiloto técnico interno é produto separado, com contexto e interface próprios
- não compartilhar a mesma UI como se fossem o mesmo produto

### 4. Frontend

- `assistente-ia.html` continua sendo a interface do assistente operacional
- o copiloto técnico deve nascer em interface separada
- o frontend deve ganhar capability flags por tela/componente

### 5. LangChain / LangGraph

- opcional
- nunca obrigatório
- sempre com fallback legado

### 6. SQL Agent

- somente leitura
- auditado
- whitelist
- sem DML/DDL

## Contexto funcional da V2

## O que a V2 precisa entregar ao final

### Produto

- assistente operacional universal
- tenant-aware real
- engine analítica
- engine operacional
- engine documental
- Code RAG
- copiloto técnico interno
- SQL Agent seguro
- LangChain seletivo
- observabilidade e rollout controlado

### Separações obrigatórias

- assistente operacional do produto
- copiloto técnico interno
- camada analítica
- camada operacional
- camada documental
- Code RAG
- SQL Agent
- orquestração opcional

## Mapa do estado atual do código

## Áreas centrais já sensíveis

### Tenant-aware

- [database.py](/home/gk/Projeto-izi/sistema/app/core/database.py)
- [auth.py](/home/gk/Projeto-izi/sistema/app/core/auth.py)
- [tenant_context.py](/home/gk/Projeto-izi/sistema/app/core/tenant_context.py)
- [tenant.py](/home/gk/Projeto-izi/sistema/app/models/tenant.py)
- [models.py](/home/gk/Projeto-izi/sistema/app/models/models.py)
- [base.py](/home/gk/Projeto-izi/sistema/app/repositories/base.py)

### Assistente / IA

- [ai_hub.py](/home/gk/Projeto-izi/sistema/app/routers/ai_hub.py)
- [cotte_ai_hub.py](/home/gk/Projeto-izi/sistema/app/services/cotte_ai_hub.py)
- [tool_executor.py](/home/gk/Projeto-izi/sistema/app/services/tool_executor.py)
- [audit_service.py](/home/gk/Projeto-izi/sistema/app/services/audit_service.py)
- [tenant_guard.py](/home/gk/Projeto-izi/sistema/app/services/tenant_guard.py)
- `sistema/app/services/ai_tools/*`

### RAG / orquestração

- `sistema/app/services/rag/*`
- [assistant_langgraph.py](/home/gk/Projeto-izi/sistema/app/services/assistant_langgraph.py)

### Frontend do assistente operacional

- [assistente-ia.html](/home/gk/Projeto-izi/sistema/cotte-frontend/assistente-ia.html)
- `sistema/cotte-frontend/js/assistente-ia*.js`
- [assistente-ia.css](/home/gk/Projeto-izi/sistema/cotte-frontend/css/assistente-ia.css)

## Estado por sprint

## Sprint 0 — Diagnóstico, inventário e contratos

### Status

- concluída

### Objetivo original

- mapear o sistema atual
- fechar contratos de evolução
- impedir que a V2 nasça como refactor cego

### O que foi feito

- estratégia geral da V2 documentada
- auditoria tenant-aware inicial documentada
- matriz de capabilities atual documentada
- fronteira do assistente operacional documentada
- riscos arquiteturais consolidados
- escopo da Sprint 1 fechado
- decisão explícita de frontend:
  - copiloto técnico com interface própria
  - capability flags por tela/componente

### Documentos principais

- [v2-paralela-git-strategy.md](/home/gk/Projeto-izi/docs/arquitetura/v2-paralela-git-strategy.md)
- [tenant_scope_audit.md](/home/gk/Projeto-izi/docs/arquitetura/tenant_scope_audit.md)
- [capabilities_matrix.md](/home/gk/Projeto-izi/docs/arquitetura/capabilities_matrix.md)
- [assistente_operacional_universal.md](/home/gk/Projeto-izi/docs/arquitetura/assistente_operacional_universal.md)
- [v2-sprint0-riscos-e-sprint1.md](/home/gk/Projeto-izi/docs/arquitetura/v2-sprint0-riscos-e-sprint1.md)
- [v2-ambientes-migrations-flags.md](/home/gk/Projeto-izi/docs/operacional/v2-ambientes-migrations-flags.md)
- [v2-checklist-inicial.md](/home/gk/Projeto-izi/docs/operacional/v2-checklist-inicial.md)

### Decisões que vieram da Sprint 0

- `empresa_id` segue como tenant key oficial
- assistente operacional e copiloto técnico não se misturam
- engines especializadas precisam ser explicitadas
- o frontend não pode trocar a UI inteira de uma vez

### Pendência residual

- manter classificação viva dos models híbridos

## Sprint 1 — Tenant-aware real

### Status

- concluída no núcleo backend

### Objetivo original

- tornar tenancy enforcement algo central de runtime, não convenção manual

### O que foi implantado

- `TenantScopedMixin`
- `tenant_context.py`
- contexto tenant associado à sessão
- filtro automático de leitura tenant-scoped via SQLAlchemy
- autofill de `empresa_id` em criação
- bypass explícito de superadmin
- hardening de `RepositoryBase.delete()`

### Arquivos principais

- [tenant.py](/home/gk/Projeto-izi/sistema/app/models/tenant.py)
- [tenant_context.py](/home/gk/Projeto-izi/sistema/app/core/tenant_context.py)
- [database.py](/home/gk/Projeto-izi/sistema/app/core/database.py)
- [auth.py](/home/gk/Projeto-izi/sistema/app/core/auth.py)
- [models.py](/home/gk/Projeto-izi/sistema/app/models/models.py)
- [base.py](/home/gk/Projeto-izi/sistema/app/repositories/base.py)
- [tenant-runtime-sprint1.md](/home/gk/Projeto-izi/docs/arquitetura/tenant-runtime-sprint1.md)

### Testes criados

- [test_tenant_context.py](/home/gk/Projeto-izi/sistema/tests/test_tenant_context.py)
- [test_tenant_routes.py](/home/gk/Projeto-izi/sistema/tests/test_tenant_routes.py)

### O que está estável

- leitura tenant-scoped em models claros
- criação com `empresa_id` automático
- bypass explícito de superadmin
- delete básico via `RepositoryBase`

### O que continua fora do enforcement automático

- models híbridos com `empresa_id nullable`
- relações dependentes de entidade pai sem `empresa_id` próprio
- bulk operations fora da trilha de repositório

### Pendências residuais

- ampliar revisão manual de bulk `update/delete`
- endurecer domínio por domínio conforme sprints futuras

## Sprint 2 — Hardening de camadas, auditoria e trilha operacional

### Status

- concluída

### Objetivo original

- reduzir risco operacional da base tenant-aware
- criar trilha de auditoria confiável
- propagar correlação mínima de requisição até a camada de tools

### O que foi implantado

- `registrar_auditoria()` persiste em sessão própria
- auditoria registra `request_id`, método e path
- notificações auditadas
- exclusão de lead comercial tenant-safe e auditada
- operações destrutivas de `financeiro` auditadas
- remoção de documento de orçamento auditada
- `tool_executor` registra `request_id` no `ToolCallLog`
- endpoint do assistente encaminha `request_id` até a execução de tools

### Arquivos principais

- [audit_service.py](/home/gk/Projeto-izi/sistema/app/services/audit_service.py)
- [tool_executor.py](/home/gk/Projeto-izi/sistema/app/services/tool_executor.py)
- [ai_hub.py](/home/gk/Projeto-izi/sistema/app/routers/ai_hub.py)
- [cotte_ai_hub.py](/home/gk/Projeto-izi/sistema/app/services/cotte_ai_hub.py)
- [notificacoes.py](/home/gk/Projeto-izi/sistema/app/routers/notificacoes.py)
- [comercial_leads.py](/home/gk/Projeto-izi/sistema/app/routers/comercial_leads.py)
- [financeiro.py](/home/gk/Projeto-izi/sistema/app/routers/financeiro.py)
- [orcamentos.py](/home/gk/Projeto-izi/sistema/app/routers/orcamentos.py)
- [v2-sprint2-hardening.md](/home/gk/Projeto-izi/docs/arquitetura/v2-sprint2-hardening.md)

### Teste focal de referência

- [test_sprint2_hardening.py](/home/gk/Projeto-izi/sistema/tests/test_sprint2_hardening.py)

Resultado conhecido:

- `7 passed`

### O que a Sprint 2 já resolveu

- auditoria que antes podia ser perdida após `commit`
- ausência de `request_id` na trilha operacional do assistente
- deletes sensíveis sem trilha mínima

### O que ainda não resolveu

- todos os `db.query()` diretos do sistema
- toda a observabilidade da V2
- isolamento completo de todas as mutações legadas

## Sprint 3 — Separação estrutural das inteligências

### Status

- concluída no escopo de separação estrutural inicial
- pronta para transição da Sprint 4 (engine operacional universal)

### Objetivo

Separar estruturalmente:

- assistente operacional do produto
- copiloto técnico interno
- engine analítica
- engine operacional
- engine documental

### Por que ela é a próxima

Sem a Sprint 3:

- a V2 continua concentrada demais em `cotte_ai_hub.py`
- o copiloto técnico corre risco de nascer acoplado à UI errada
- engines continuam implícitas em vez de explícitas

### O que precisa ser feito

#### Backend

- definir contratos de engine
- separar contexto permitido por engine
- impedir mistura entre:
  - contexto do produto
  - contexto técnico interno
  - documentos empresariais
  - codebase técnico

#### Frontend

- criar camada de capability flags por tela/componente
- reservar navegação/tela própria do copiloto técnico
- manter `assistente-ia.html` como interface do assistente operacional

#### Documentação

- criar documento de separação de engines
- mapear `engine -> fontes -> permissões -> superfície`

### Entregáveis mínimos recomendados

- `docs/arquitetura/v2-sprint3-separacao-engines.md`
- registry ou mapa de capabilities por engine
- guardrails claros para copiloto técnico
- base de capability flags no frontend

### Marco já implantado (fase 1)

- contrato de `engine` exposto no assistente (`/ai/assistente` e stream)
- registry de engines/capabilities em backend
- endpoint separado do copiloto técnico (`/ai/copiloto-interno`)
- endpoint de capabilities para frontend (`/ai/assistente/capabilities`)
- base de capability flags no frontend (`CapabilityFlagsService`)
- rota e interface separadas do copiloto técnico interno (`/ai/copiloto-interno` + `copiloto-tecnico.html`)

## Sprint 4 — Engine operacional universal

### Status

- concluída

### Objetivo

Organizar a execução operacional em superfície explícita e auditável.

### Entregas finais consolidadas

- catálogo operacional explícito por domínio com filtros por policy da engine
- fluxo composto de orçamento com geração de PDF, envio e auditoria
- confirmação destrutiva padronizada (`pending_confirmation`)
- idempotência de envios críticos (incluindo confirmação por token)
- observabilidade por fluxo (`flow_id`, `trace` por etapa, `metrics`)
- expansão de fluxo composto para financeiro e agenda

### Dependências

- Sprint 3 minimamente pronta
- capability flags em nível operacional

## Sprint 5 — Engine documental

### Status

- concluída

### Objetivo

Separar a camada documental da conversa.

### Entregas finais consolidadas

- policy documental explicitada no registry de engines
- catálogo dedicado da engine documental
- fluxo composto documental por orçamento (dossiê + anexo opcional)
- isolamento por tenant para consulta de documentos
- confirmação destrutiva padronizada em anexo documental
- trilha de observabilidade por fluxo (`flow_id`, `trace`, `metrics`)

### Regra importante

- engine documental do produto não se mistura com Code RAG técnico

## Sprint 6 — Engine analítica + SQL Agent seguro

### Status

- concluída

### Objetivo

Criar camada analítica explícita e superfície SQL segura.

### Entregas finais consolidadas

- catálogo explícito da engine analítica com superfície read-only
- fluxo analítico MVP com escopos de consulta e auditoria
- SQL Agent analítico read-only em endpoint dedicado
- guardrails de segurança para SQL:
  - SELECT/CTE apenas
  - bloqueio de multi-statement
  - bloqueio de DML/DDL
  - whitelist de fontes permitidas
- rollout por flag (`V2_SQL_AGENT`)

## Sprint 7 — Code RAG + copiloto técnico interno

### Status

- concluída

### Entregas finais consolidadas

- separação formal entre Code RAG técnico e RAG empresarial
- política explícita de acesso ao copiloto técnico interno
- superfície dedicada `POST /ai/copiloto-interno/consulta-tecnica`
- fluxo técnico com `flow_id`, `trace`, `metrics` e auditoria
- combinação de Code RAG + SQL Agent condicionada a contexto interno e flags

## Sprint 8 — LangChain seletivo

### Status

- concluída (escopo de hardening + rollout controlado)

### O que já existe

- [assistant_langgraph.py](/home/gk/Projeto-izi/sistema/app/services/assistant_langgraph.py)
- hardening de isolamento de engines e superfície do copiloto interno
- testes adicionais de contrato/capabilities e bloqueio de engine no stream
- cobertura específica de policy de tools do registry por flag de SQL Agent
- trilha consolidada em `docs/arquitetura/v2-sprint8-hardening-rollout.md`

### O que falta fazer

- ampliar adoção de LangGraph por domínio de forma seletiva
- manter fallback legado sempre disponível em todo rollout incremental

## Sprint 9 — Observabilidade e rollout controlado

### Status

- parcialmente preparada
- não concluída

### O que já existe

- `request_id` no middleware
- auditoria mínima
- `ToolCallLog` com correlação básica de requisição

### O que falta fazer

- métricas por capability
- dashboards por engine
- métricas de erro e latência
- rollout por empresa piloto
- playbook de rollback
- indicadores de feature flags

## Feature flags recomendadas

Estas flags devem existir ou ser criadas conforme a implantação:

- `V2_TENANT_RUNTIME`
- `V2_ANALYTICS_ENGINE`
- `V2_OPERATIONS_ENGINE`
- `V2_DOCUMENT_ENGINE`
- `V2_CODE_RAG`
- `V2_INTERNAL_COPILOT`
- `V2_SQL_AGENT`
- `V2_LANGGRAPH_ORCHESTRATION`

### Regras para flags

- default desligado quando houver risco de comportamento
- dono claro
- rollback claro
- critério de remoção claro
- medição mínima do efeito

## Estado atual por domínio

## Assistente operacional

### Já existe

- UI funcional
- tool use
- histórico
- streaming
- traces de tool
- preferências
- parte de RAG por tenant

### Problema atual

- acoplamento ainda alto em `cotte_ai_hub.py`

### Próximo passo

- Sprint 3: separar engines e responsabilidades

## Copiloto técnico interno

### Já existe

- apenas decisões arquiteturais e peças reutilizáveis

### Não existe ainda

- interface própria
- endpoint próprio
- política de acesso
- contrato final

## Tenant-aware

### Já existe

- enforcement base de leitura
- autofill de `empresa_id`
- bypass explícito
- hardening inicial de mutações

### Falta

- completar revisão de híbridos
- revisar bulk operations residuais

## Analítica

### Já existe

- análises dispersas e perguntas recorrentes

### Falta

- engine explícita
- contratos próprios
- SQL Agent seguro

## Documental

### Já existe

- documentos empresariais
- PDFs
- anexos de orçamento

### Falta

- engine documental explícita
- RAG documental formalizado

## Code RAG

### Já existe

- base inicial de infraestrutura

### Falta

- separação formal do RAG empresarial
- superfície de copiloto técnico

## Testes e validação

## Testes já criados que importam para a trilha V2

- [test_tenant_context.py](/home/gk/Projeto-izi/sistema/tests/test_tenant_context.py)
- [test_tenant_routes.py](/home/gk/Projeto-izi/sistema/tests/test_tenant_routes.py)
- [test_sprint2_hardening.py](/home/gk/Projeto-izi/sistema/tests/test_sprint2_hardening.py)
- `sistema/tests/test_tool_executor.py`
- `sistema/tests/test_ai_tools_fase3.py`
- `sistema/tests/test_ai_assistente_contract.py`
- `sistema/tests/test_cotte_ai_hub_listar_heuristic.py`

## Limitação conhecida de testes

- o harness legado ainda apresenta instabilidade em parte da suíte ampla
- por isso, mudanças da V2 devem seguir usando:
  - testes focados pequenos
  - validação de compilação
  - smoke tests por domínio

## Riscos que outro agente não pode ignorar

### Alto risco

- reabrir tenant-aware como refactor amplo
- misturar copiloto técnico com assistente operacional
- introduzir capability nova sem feature flag quando houver impacto
- fazer migration destrutiva cedo
- assumir que `cotte_ai_hub.py` pode ser reescrito de uma vez sem regressão

### Risco médio

- duplicar lógica entre assistente, services e tools
- deixar Code RAG e RAG empresarial convergirem para o mesmo contexto
- expandir LangGraph antes de provar necessidade

## Instruções para outro agente continuar sem se perder

## Antes de editar qualquer coisa

1. ler este arquivo inteiro
2. ler:
   - `v2-paralela-git-strategy.md`
   - `assistente_operacional_universal.md`
   - `tenant_scope_audit.md`
   - `v2-sprint2-hardening.md`
3. inspecionar os arquivos centrais listados neste handoff
4. decidir explicitamente em qual sprint a próxima mudança cai
5. não misturar duas sprints na mesma alteração sem necessidade real

## Se for continuar a Sprint 3

- começar pela separação de fronteiras
- não começar por visual
- primeiro definir contratos, contexto permitido e capability flags

## Se for mexer no assistente

- assumir que `cotte_ai_hub.py` é área crítica
- preservar compatibilidade com o assistente operacional atual
- não usar a UI atual para o copiloto técnico

## Se for mexer em tenancy

- não mexer cegamente em models híbridos
- revisar impacto em admin, logs e objetos globais

## Ordem recomendada para concluir a V2

1. Sprint 3 — separação estrutural das inteligências
2. capability flags por tela/componente no frontend
3. UI própria do copiloto técnico interno
4. Sprint 4 — engine operacional
5. Sprint 5 — engine documental
6. Sprint 6 — engine analítica + SQL Agent
7. Sprint 7 — Code RAG + copiloto técnico
8. Sprint 8 — LangGraph seletivo com fallback
9. Sprint 9 — observabilidade e rollout controlado

## Checklist objetivo até 100%

### Concluído

- [x] estratégia-base da V2 documentada
- [x] Sprint 0 concluída
- [x] Sprint 1 concluída no núcleo backend
- [x] Sprint 2 concluída no escopo planejado

### Pendente

- [x] Sprint 3 concluída
- [x] Sprint 4 concluída
- [x] Sprint 5 concluída
- [x] Sprint 6 concluída
- [x] Sprint 7 concluída
- [x] Sprint 8 concluída
- [ ] Sprint 9 concluída
- [x] capability flags de frontend implantadas
- [x] interface separada do copiloto técnico implantada
- [x] SQL Agent seguro implantado
- [x] Code RAG formalmente separado do RAG empresarial
- [ ] dashboards e rollout por capability implantados

## Critério final de conclusão da V2

A V2 só deve ser considerada concluída quando:

- o sistema estiver tenant-aware de forma robusta nos domínios críticos
- assistente operacional e copiloto técnico estiverem claramente separados
- engines analítica, operacional e documental estiverem explícitas
- SQL Agent estiver seguro e auditado
- Code RAG estiver isolado do RAG empresarial
- o frontend estiver preparado para rollout incremental por capability
- observabilidade e rollback por capability estiverem fechados

## Resumo final para handoff

Se um agente assumir a partir daqui:

- não recomeçar o projeto
- tratar Sprint 3 como próximo passo real
- preservar o que já foi consolidado nas Sprints 0, 1 e 2
- usar este arquivo como fonte de verdade da trilha V2

