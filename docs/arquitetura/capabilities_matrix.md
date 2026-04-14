---
title: Capabilities Matrix
tags:
  - arquitetura
  - sprint-0
  - capabilities
prioridade: alta
status: draft
---

# Sprint 0 — Matriz de Capabilities Atuais

## Objetivo

Mapear o que o sistema já faz hoje, em qual camada isso vive, o nível de maturidade e o que precisa mudar para a V2.

## Matriz resumida

| Capability atual | Superfície principal | Estado atual | Risco principal | Direção V2 |
|---|---|---|---|---|
| Assistente conversacional web | `assistente-ia.html` + `js/assistente-ia*.js` + `routers/ai_hub.py` + `services/cotte_ai_hub.py` | funcional e em evolução | acoplamento alto em `cotte_ai_hub.py` | separar assistente operacional, copiloto técnico e engines |
| Tool Use operacional | `services/ai_tools/*` + `tool_executor.py` | já existe base com registry e confirmação | cobertura parcial de domínios e risco de crescimento desorganizado | virar engine operacional com contratos por domínio |
| RAG por tenant | `services/rag/*` | incremental | contexto limitado a chats e documentos da empresa | consolidar como engine documental do produto |
| LangGraph opcional | `assistant_langgraph.py` | placeholder com fallback | pode virar abstração vazia ou dependência prematura | manter estritamente opcional |
| Orçamentos por IA | `ai_hub.py` + `cotte_ai_hub.py` + `orcamentos.py` | funcional | mistura de preview, confirmação e fluxo legado | migrar para engine operacional por capability |
| Envio por WhatsApp | `whatsapp_service.py` + `quote_notification_service.py` | funcional | idempotência e acoplamento com status | manter, mas atrás da engine operacional |
| Envio por e-mail | `email_service.py` | funcional | duplicidade de pontos de entrada | padronizar pela engine operacional/documental |
| Financeiro analítico conversacional | `ai_hub.py` + `financeiro_service.py` + `cotte_context_builder.py` | funcional para perguntas recorrentes | queries espalhadas e sem camada analítica dedicada | extrair engine analítica |
| CRM/comercial | `routers/comercial_*` + `campaign_service.py` | funcional | fronteira tenant híbrida em parte do domínio | endurecer tenancy e contratos |
| Documentos empresariais | `documentos.py` + `documentos_service.py` + `DocumentoEmpresa` | funcional | ainda não é uma engine documental explícita | transformar em engine documental |
| Preferências do assistente | `AssistantPreferencesService` + UI atual | funcional | está misturado na mesma tela do assistente operacional | manter no assistente operacional; não compartilhar com copiloto técnico |
| Copiloto técnico interno | inexistente como produto separado | ausente | risco de nascer dentro do assistente operacional atual | criar interface, contexto e permissões próprios |
| SQL Agent seguro | inexistente | ausente | alto risco se nascer sem whitelist/auditoria | criar só depois da engine analítica |
| Capability flags frontend | inexistente como camada explícita | ausente | rollout visual arriscado e regressivo | criar camada simples por tela/componente |

## Capacidades operacionais já observáveis no assistente

### Leitura

- saldo de caixa
- movimentações financeiras
- listagem e detalhe de orçamentos
- listagem de clientes
- listagem de materiais
- listagem de despesas
- listagem de agendamentos
- análise de logs de tools

### Mutação confirmável ou destrutiva

- criar movimentação financeira
- registrar pagamento
- criar despesa
- marcar despesa paga
- criar, editar e excluir cliente
- criar, duplicar e editar orçamento
- editar item do orçamento
- aprovar e recusar orçamento
- enviar orçamento por WhatsApp
- enviar orçamento por e-mail
- cadastrar material
- criar, cancelar e remarcar agendamento
- criar parcelamento
- anexar documento ao orçamento

Fonte principal:

- `sistema/app/services/ai_tools/__init__.py`

## Capacidades de frontend já existentes

Na interface atual do assistente:

- tela dedicada `assistente-ia.html`
- modo embed e modo tela cheia
- barra de contexto no embed
- preferências do assistente
- nova conversa
- renderização incremental e streaming
- cards específicos por tipo de resposta
- render de pending action/tool trace

Fontes principais:

- `sistema/cotte-frontend/assistente-ia.html`
- `sistema/cotte-frontend/js/assistente-ia.js`
- `sistema/cotte-frontend/js/assistente-ia-shell.js`

## Gaps que a V2 precisa fechar

### Estruturais

- separar engine analítica, operacional e documental
- separar copiloto técnico do assistente operacional
- reduzir centralização excessiva em `cotte_ai_hub.py`

### Tenant-aware

- tirar o peso do filtro manual
- classificar entidades híbridas antes de automatizar

### Frontend

- não usar a tela atual do assistente como host do copiloto técnico
- criar camada simples de capability flags por tela e componente
- permitir rollout incremental sem trocar a UI inteira

## Escopo recomendado da V2 a partir desta matriz

### Volta cedo para `main`

- feature flags
- observabilidade
- abstrações de contexto
- capacidade de frontend por tela/componente

### Fica no trilho V2 até maturar

- tenant runtime automático
- engines especializadas
- copiloto técnico interno
- SQL Agent
