---
title: Assistente Ia Ultimas Melhorias 2026 04 10
tags:
  - tecnico
prioridade: media
status: arquivado
---
# Assistente IA — Últimas Melhorias e Modificações (2026-04-10)

> **Arquivado:** snapshot de melhorias na data acima; para arquitetura atual do assistente, veja `docs/tecnico/assistente-ia-arquitetura.md` e `docs/tecnico/plano-tool-use-v2.md`.

Este documento consolida as melhorias recentes aplicadas ao `assistente-ia`, com foco em precisão contextual, segurança operacional, UX de confirmação e personalização por empresa/usuário.

## 1) Evolução da memória contextual (v2)

### 1.1 Memória semântica por empresa
- Foi adicionada uma camada de memória semântica no backend para o assistente v2, com:
  - identificação de domínio da pergunta (financeiro, orçamentos, clientes, agendamentos, geral),
  - recuperação de perguntas semelhantes no histórico da empresa,
  - consolidação de ferramentas mais usadas por domínio,
  - contexto de cliente quando a pergunta referencia `cliente X`,
  - cache contextual em RAM para reduzir custo de recomputação.

### 1.2 Perfil operacional dinâmico (7/30/90 dias)
- A memória foi expandida para gerar perfil operacional por janelas `7d`, `30d` e `90d`:
  - frequência operacional por domínio,
  - recorrência de perguntas semelhantes,
  - recomendação de estilo de resposta (`tom`, `granularidade`),
  - priorização de KPIs por contexto.
- Esse perfil é inserido no prompt do assistente v2 para aumentar precisão e consistência das respostas.

## 2) Preferências de visualização e instruções por empresa

### 2.1 Instruções da empresa (guardrails)
- Foi criado campo de instruções por empresa para definir diretrizes de resposta do assistente.
- Regra de governança:
  - somente gestor/admin pode editar instruções da empresa.

### 2.2 Preferência visual por usuário
- Foi criada persistência de preferência de visualização por usuário e domínio:
  - formatos suportados: `auto`, `resumo`, `tabela`,
  - confiança associada à preferência.

### 2.3 Regra híbrida aplicada
- Em conflitos de personalização:
  - instruções da empresa funcionam como guardrails obrigatórios,
  - preferência do usuário ajusta formato e ordem dentro desses limites.

## 3) Playbook automático por setor

- Foi adicionado serviço de playbook setorial para `Financeiro`, `Comercial`, `Gestão` (com fallback `Geral`):
  - priorização de KPIs por setor,
  - ordenação de ações sugeridas por contexto,
  - ajuste por histórico de sucesso da empresa em `7/30/90 dias`.
- A base de sinal utiliza dados já existentes (ex.: logs de tools e feedback de respostas).

## 4) Integração no pipeline do assistente v2

- O contexto adaptativo passou a ser injetado no prompt em:
  - fluxo síncrono (`assistente_unificado_v2`),
  - fluxo streaming SSE (`assistente_v2_stream_core`).
- A resposta final mantém retrocompatibilidade e agora inclui metadados opcionais:
  - `dados.visualizacao_recomendada`,
  - `dados.playbook_setor`.

## 5) Melhorias de UX no `assistente-ia.html`

- Foi adicionada seção de preferências no frontend do assistente:
  - seletor de formato de resposta (`auto`, `resumo`, `tabela`),
  - campo de instruções da empresa,
  - botão de salvar com feedback visual de sucesso/erro,
  - indicação de permissão para edição de instruções.
- O fluxo de chat existente foi preservado, sem quebra de SSE, confirmação pendente ou atalhos atuais.

## 6) Transparência em ações destrutivas (orçamentos)

- Foi enriquecido o preview de ações de recusa/desaprovação de orçamento com impacto financeiro explícito:
  - quantidade de contas pendentes afetadas,
  - valor total pendente previsto para remoção,
  - explicação operacional clara para confirmação.
- A knowledge base funcional também foi atualizada com essa regra.

## 7) Compatibilidade e segurança de contrato

- O contrato de resposta do assistente v2 foi mantido.
- Novas capacidades foram adicionadas de forma incremental (campos opcionais), evitando regressões no frontend e integrações.
- O controle de permissão aproveita o modelo RBAC já existente (gestor/admin para edição de instruções da empresa).

## 8) Testes e validação executados

As alterações foram validadas com testes de regressão e testes novos:
- `sistema/tests/test_assistente_unificado_v2.py`
- `sistema/tests/test_ai_tools_fase3.py`
- `sistema/tests/test_assistant_preferences_service.py`

Foram adicionados cenários para:
- injeção de memória semântica e contexto adaptativo no prompt,
- consistência de metadados de resposta (visualização/playbook),
- funcionamento de preferências por usuário e contexto por empresa,
- preservação de comportamentos já existentes do assistente.

## 9) Arquivos principais impactados

### Backend
- `sistema/app/services/cotte_context_builder.py`
- `sistema/app/services/cotte_ai_hub.py`
- `sistema/app/services/assistant_preferences_service.py`
- `sistema/app/routers/ai_hub.py`
- `sistema/app/models/models.py`
- `sistema/app/services/ai_tools/destructive_preview.py`
- `sistema/app/services/ai_tools/orcamento_tools.py`
- `sistema/app/services/prompts/knowledge_base.md`

### Frontend
- `sistema/cotte-frontend/assistente-ia.html`
- `sistema/cotte-frontend/css/assistente-ia.css`
- `sistema/cotte-frontend/js/assistente-ia.js`

### Testes
- `sistema/tests/test_assistente_unificado_v2.py`
- `sistema/tests/test_ai_tools_fase3.py`
- `sistema/tests/test_assistant_preferences_service.py`

## 10) Observações para manutenção futura

- Em ambiente de produção com migrations controladas, garantir criação/execução de migration para os novos campos/tabelas de preferências.
- Monitorar uso real dos playbooks para calibrar heurísticas de setor e priorização de ações.
- Evoluir a preferência visual para aprendizagem contínua com peso por feedback explícito de utilidade.
