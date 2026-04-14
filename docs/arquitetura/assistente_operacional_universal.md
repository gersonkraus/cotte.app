---
title: Assistente Operacional Universal
tags:
  - arquitetura
  - sprint-0
  - assistente
prioridade: alta
status: draft
---

# Sprint 0 — Assistente Operacional Universal

## Objetivo

Definir o que o assistente operacional universal deve ser na V2 e onde ele termina, para não se confundir com copiloto técnico interno, engine analítica, engine documental ou SQL Agent.

## Fronteira do produto

O assistente operacional universal é o assistente do produto COTTE para operação do negócio da empresa usuária.

Ele deve:

- consultar dados reais da empresa
- resumir e explicar dados operacionais
- montar e manipular orçamentos
- acionar fluxos de envio
- apoiar agenda e documentos
- operar com linguagem natural sobre capacidades autorizadas

Ele não deve:

- responder perguntas técnicas sobre o codebase
- funcionar como copiloto de engenharia
- misturar contexto do sistema interno com contexto da empresa cliente

## Estado atual observado

Superfície atual:

- backend em `routers/ai_hub.py`
- lógica principal em `services/cotte_ai_hub.py`
- Tool Use em `services/ai_tools/*` + `tool_executor.py`
- UI em `cotte-frontend/assistente-ia.html` + `js/assistente-ia*.js`

Capacidades reais já presentes:

- conversa guiada
- análise financeira básica
- criação e confirmação de orçamento
- execução de tools operacionais
- preferências do assistente
- modo embed e tela cheia
- RAG por tenant com histórico de chat e documentos da empresa

## Problemas atuais

- fronteira excessivamente concentrada em `cotte_ai_hub.py`
- mistura de caminhos legados e novos no mesmo fluxo
- ausência de separação formal entre engine analítica, operacional e documental
- risco de reaproveitar a interface atual para o futuro copiloto técnico interno

## Contrato-alvo da V2

### O assistente operacional deve consumir

- engine operacional
- engine analítica
- engine documental
- camada de permissões
- camada de tenant context
- feature flags

### O assistente operacional não deve consumir diretamente

- Code RAG técnico
- base de contexto de engenharia
- SQL Agent técnico
- UI do copiloto técnico

## Decisão obrigatória de frontend

Desde a Sprint 0:

- `assistente-ia.html` continua sendo a interface do assistente operacional
- o copiloto técnico interno deve nascer em interface separada
- o frontend deve ganhar capability flags por tela/componente para ativar blocos da V2 de forma incremental

Motivo:

- evitar regressão na experiência atual
- evitar confusão de contexto
- permitir rollout gradual sem rewrite visual completo

## Caminho evolutivo recomendado

### Etapa 1

- preservar a tela atual
- introduzir capability flags
- manter o assistente operacional como produto principal

### Etapa 2

- extrair engines por domínio
- fazer o assistente operacional delegar a essas engines

### Etapa 3

- criar interface separada do copiloto técnico interno
- conectar Code RAG e SQL Agent apenas nessa trilha interna

## Critérios de aceite desta definição

- assistente operacional e copiloto técnico têm fronteiras explícitas
- a V2 de frontend não exige apagar a tela atual
- a separação de responsabilidades reduz risco de regressão
