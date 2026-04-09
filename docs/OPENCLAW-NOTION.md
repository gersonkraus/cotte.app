---
title: Openclaw Notion
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Openclaw Notion
tags:
  - tecnico
prioridade: media
status: documentado
---
# Guia de Configuração do OpenClaw para Notion

Este documento explica como configurar o OpenClaw para usar as mesmas automações do Notion que estão configuradas neste projeto.

## 📋 Pré-requisitos

1. **Token do Notion** (já configurado):
   ```
   ntn_u15160279237JsHCPSTgk1Bm9sDzylBzOugxDzCTHRjg6p
   ```

2. **IDs dos bancos de dados**:
   - Tarefas: `45ec8ca9-a98d-46f8-9cb9-891b1dea67e4`
   - Changelog: `9e7c839c-0b2a-4d30-861f-37a1d0c45d54`
   - Roadmap: `32e05a5c-c013-8165-b1e5-c6d1b9c656cd`

## 🔧 Configuração

### 1. Copiar scripts

Os scripts estão em `scripts/`:
- `notion-sync.sh` - Sincroniza tarefas via commit
- `notion-tasks.sh` - Lista tarefas pendentes

### 2. Configurar Git Hooks

Os hooks estão em `.git/hooks/`:
- `post-commit` - Registra commits no changelog
- `post-tag` - Cria releases no Roadmap

### 3. Como usar no OpenClaw

Quando estiver usando o OpenClaw, peça para ele:

#### Listar tarefas pendentes
```
Liste as tarefas pendentes do Notion
```
ou
```
Execute ./scripts/notion-tasks.sh
```

#### Criar nova tarefa
```
Crie uma nova tarefa no Notion com título "Implementar feature X", prioridade Alta, responsável IA
```

#### Atualizar status de tarefa
```
Atualize a tarefa #4 para Em progresso
```

#### Criar release
```
Crie uma tag v1.0 para gerar release no Roadmap
```

## 📊 Estrutura dos Bancos

### Tarefas
| Campo | Tipo | Opções |
|-------|------|--------|
| Tarefa | title | - |
| Status | select | Backlog, A fazer, Em progresso, Feito |
| Prioridade | select | 🔴 Alta, 🟡 Média, 🟢 Baixa |
| Responsável | select | GK, IA |
| Prazo | date | - |
| Descrição | rich_text | - |
| Sprint | select | Backlog, Sprint 1, Sprint 2 |
| Ref | number | ID sequencial |
| Último Commit | url | Link do commit |

### Changelog
| Campo | Tipo | Opções |
|-------|------|--------|
| O que mudou | title | - |
| Módulo | select | Backend, Frontend, Banco, IA, WhatsApp, Deploy |
| Data | date | - |
| Tipo | select | ✨ feat, 🐛 fix, ♻️ refactor, 📝 docs, 🔧 chore, ⚡ perf |
| Commit/PR | url | - |
| Impacto | select | 🔴 Breaking, 🟡 Minor, 🟢 Patch |

### Roadmap
| Campo | Tipo | Opções |
|-------|------|--------|
| Versão | title | - |
| Status | select | 📋 Planejado, 🔨 Em andamento, ✅ Lançado |
| Data alvo | date | - |
| Descrição | rich_text | - |
| Features | rich_text | - |

## 🚀 Automações Ativas

1. **Changelog automático**: Todo commit é registrado
2. **Sincronização de tarefas**: Commits com `#ID` atualizam tarefa
3. **Releases automáticas**: Tags criam releases no Roadmap

## 📝 Exemplos de uso

### No OpenClaw
```
# Listar tarefas pendentes
./scripts/notion-tasks.sh

# Criar tarefa
curl -X POST 'https://api.notion.com/v1/pages' \
  -H 'Authorization: Bearer ntn_u15160279237JsHCPSTgk1Bm9sDzylBzOugxDzCTHRjg6p' \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d '{
    "parent": {"database_id": "45ec8ca9-a98d-46f8-9cb9-891b1dea67e4"},
    "properties": {
      "Tarefa": {"title": [{"text": {"content": "Nova tarefa"}}]},
      "Status": {"select": {"name": "A fazer"}},
      "Prioridade": {"select": {"name": "🔴 Alta"}},
      "Responsável": {"select": {"name": "IA"}},
      "Ref": {"number": 5}
    }
  }'

# Atualizar status
curl -X PATCH 'https://api.notion.com/v1/pages/PAGE_ID' \
  -H 'Authorization: Bearer ntn_u15160279237JsHCPSTgk1Bm9sDzylBzOugxDzCTHRjg6p' \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d '{
    "properties": {
      "Status": {"select": {"name": "Em progresso"}}
    }
  }'
```

## 🔗 Links

- Workspace do Notion: https://www.notion.so/COTTE-Gest-o-do-Projeto-32e05a5cc0138108a095caf6e90e4b89
- Repositório: https://github.com/gersonkraus/Projeto-izi
