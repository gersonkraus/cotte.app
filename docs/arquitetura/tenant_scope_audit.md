---
title: Tenant Scope Audit
tags:
  - arquitetura
  - tenant
  - sprint-0
prioridade: alta
status: draft
---

# Sprint 0 — Auditoria Tenant-Aware Atual

## Objetivo

Mapear como o isolamento por empresa funciona hoje no backend do Projeto-izi / COTTE, onde ele já existe, onde depende de disciplina manual e quais áreas precisam endurecimento na Sprint 1.

## Resumo executivo

O projeto já usa `empresa_id` como chave de escopo em boa parte do domínio. O problema principal não é ausência de campo tenant, e sim ausência de enforcement automático e uniforme no runtime.

Estado atual observado:

- há muitas entidades já marcadas por `empresa_id`
- o isolamento depende fortemente de filtros manuais em routers, services e repositories
- existem entidades híbridas com `empresa_id nullable`, o que exige classificação antes de automatizar filtros
- já existe base inicial de guard rails em `tenant_guard.py`, mas não há ainda filtro automático por sessão SQLAlchemy

## Evidência principal no código

Arquivos-base:

- `sistema/app/models/models.py`
- `sistema/app/routers/*.py`
- `sistema/app/repositories/*.py`
- `sistema/app/services/tenant_guard.py`

## Classificação inicial dos modelos

### Globais ou de plataforma

Modelos sem `empresa_id` explícito ou com papel de catálogo/plataforma:

- `ModuloSistema`
- `Plano`
- `PlanoModulo`
- `ConfigGlobal`
- estruturas públicas ou auxiliares ligadas a fluxo global

Esses modelos não devem receber filtro tenant automático por padrão.

### Tenant-scoped claros

Modelos com `empresa_id` obrigatório e comportamento claramente isolado por empresa:

- `BancoPIXEmpresa`
- `Papel`
- `Cliente`
- `CategoriaCatalogo`
- `Servico`
- `DocumentoEmpresa`
- `Orcamento`
- `Notificacao`
- `PropostaPublica`
- `FormaPagamentoConfig`
- `ContaFinanceira`
- `TemplateNotificacao`
- `HistoricoCobranca`
- `ConfiguracaoFinanceira`
- `MovimentacaoCaixa`
- `CategoriaFinanceira`
- `SaldoCaixaConfig`
- `LeadImportacao`
- `Campaign`
- `FeedbackAssistente`
- `AssistentePreferenciaUsuario`
- `Agendamento`
- `ConfigAgendamento`
- `ConfigAgendamentoUsuario`
- `SlotBloqueado`
- `AIChatSessao`

Esses são os primeiros candidatos ao `TenantScopedMixin` da Sprint 1.

### Híbridos ou sensíveis

Modelos com `empresa_id nullable` ou sem semântica tenant totalmente fechada:

- `Usuario`
- `AuditLog`
- `CommercialLead`
- `PagamentoFinanceiro`
- `WebhookEvent`
- `ToolCallLog`

Tratamento recomendado:

- classificar cada um na Sprint 0 como global, híbrido ou tenant-aware com exceção explícita
- não aplicar filtro automático cego até essa classificação estar fechada

### Dependentes de entidade pai

Há modelos que não exibem `empresa_id` no trecho mapeado, mas dependem de uma entidade pai tenant-scoped:

- `ItemOrcamento`
- `HistoricoEdicao`
- `OrcamentoDocumento`
- `LeadImportacaoItem`
- `CampaignLead`
- `AIChatMensagem`

Na Sprint 1 eles não devem ser tratados como “globais”; devem ser cobertos via relação com a entidade pai ou regra específica.

## Estado atual do enforcement

### Onde já existe proteção

- filtros manuais por `current_user.empresa_id` em routers críticos
- repositories especializados que recebem `empresa_id`
- services de IA que passam `empresa_id` para contexto, queries e tool execution
- `tenant_guard.py` já injeta e valida `empresa_id` em contexto sensível

### Onde o enforcement ainda é frágil

- `RepositoryBase` não aplica escopo tenant automaticamente
- parte das queries continua sendo feita direto em router
- o escopo ainda depende de o desenvolvedor lembrar de filtrar por `empresa_id`
- não há ainda um filtro automático central na sessão SQLAlchemy

## Rotas e módulos mais sensíveis

Módulos com uso intensivo de permissão e alto risco de vazamento:

- `ai_hub.py`
- `orcamentos.py`
- `financeiro.py`
- `clientes.py`
- `documentos.py`
- `empresa.py`
- `agendamentos.py`
- `comercial_*`

Módulos públicos que exigem atenção especial:

- `publico.py`
- `publico_propostas.py`
- `webhooks.py`

## Riscos arquiteturais identificados

### Alto

- vazamento cross-tenant por query manual esquecida
- divergência entre repositories com escopo e queries diretas sem escopo
- automatizar tenant sem classificar modelos híbridos pode quebrar fluxos administrativos e logs

### Médio

- duplicidade de regra entre router, service e repository
- falsa sensação de segurança por haver `empresa_id` no model, mas sem enforcement automático

## Decisão para a Sprint 1

Objetivo confirmado:

- manter `empresa_id` como tenant key oficial
- criar contexto tenant por request autenticado
- aplicar filtro automático a modelos tenant-scoped claros
- criar bypass de superadmin explícito e auditável
- cobrir híbridos com política declarada, não por exceção silenciosa

## Entregáveis derivados desta auditoria

- lista de candidatos ao `TenantScopedMixin`
- lista de modelos híbridos que exigem política explícita
- lista de módulos críticos para testes de isolamento
- escopo fechado da Sprint 1 tenant-aware runtime
