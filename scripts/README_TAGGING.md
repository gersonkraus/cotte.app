---
title: Readme Tagging
tags:
  - documentacao
prioridade: alta
status: documentado
---
---
title: Auto-Tagging Base — Guia de Uso
tags:
  - ferramentas
  - automacao
  - base
prioridade: media
status: ativo
---

# Auto-Tagging Base — Script de Automação

Script Python que mantém a **COTTE_Documentacao.base** sempre alimentada com tags, prioridades e status automáticos.

## Como Usar

### 1️⃣ Escanear Documentos (sem fazer mudanças)

```bash
python scripts/auto_tagging_base.py --scan
```

Mostra quais arquivos `.md` precisam de propriedades YAML frontmatter.

### 2️⃣ Aplicar Mudanças Automaticamente

```bash
python scripts/auto_tagging_base.py --apply
```

Adiciona/atualiza YAML frontmatter em todos os arquivos detectados com:
- `title` — extraído do nome do arquivo
- `tags` — detectadas automaticamente por padrão
- `prioridade` — alta/media/baixa
- `status` — ativo/documentado/planejado/concluído/em-andamento

### 3️⃣ Ver Histórico

```bash
python scripts/auto_tagging_base.py --history
```

Mostra os últimos 5 execuções com resumo de mudanças.

---

## 🎯 Detecção Automática

### Tags por Padrão de Caminho

| Padrão | Tag Detectada | Exemplos |
|--------|---------------|----------|
| `*DEPLOY*.md` | `deploy` | `DEPLOY-RAILWAY.md` |
| `variaveis_ambiente.md` | `deploy` | `variaveis_ambiente.md` |
| `*roadmap*.md` | `roadmap` | `roadmap_cotte.md` |
| `PLANO*.md` | `implementacao` | `PLANO_IMPLEMENTACAO_FINANCEIRO.md` |
| `mapa-*.md` | `tecnico` | `mapa-tec-banco.md` |
| `docs/*.md` | `tecnico` | Qualquer arquivo em `/docs` |
| `memory/*.md` | `memoria` | `memory/decisions.md` |
| `README.md` | `documentacao` | Root e subpastas |

### Prioridade Detectada

- **Alta** (`alta`): ROOT files, roadmap, arquitetura, stack, deploy crítico
- **Média** (`media`): Documentação técnica, mapas, análises
- **Baixa** (`baixa`): Templates, exemplos

### Status Detectado

- `ativo` — Arquivos em `/memory` (vivos)
- `concluído` — `IMPLEMENTACAO_COMPLETA.md`
- `planejado` — Arquivos `PLANO_*`
- `em-andamento` — Roadmap
- `documentado` — Demais

---

## 🔧 Configuração

### Ignorar Diretórios (não serão escaneados)

Edite a variável `DOCS_IGNORE` em `scripts/auto_tagging_base.py`:

```python
DOCS_IGNORE = {
    'venv', 'node_modules', '.pytest_cache', 'playwright-report', '.git', 'tests',
    '.agentlens', '.claude', '.clinerules', '.windsurf', '.vscode', '.cursor',
    '.continue', '.gemini', '.rtk', '__pycache__', 'memoriaclaude', 'ob-claude'
}
```

### Adicionar Padrões Customizados

Edite o dicionário `PATTERNS` em `scripts/auto_tagging_base.py`:

```python
PATTERNS = {
    'sua_categoria': [
        r'seu_padrão.*\.md',
        r'outro_padrão.*\.md',
    ],
    # ... resto das categorias
}
```

---

## 📅 Automação Recorrente

### Opção 1: Via Cron (Linux/Mac)

```bash
# Rodar script toda segunda-feira às 09:00
0 9 * * 1 cd /home/gk/Projeto-izi && python scripts/auto_tagging_base.py --apply
```

### Opção 2: Via Git Hook (Pre-commit)

Crie `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
python scripts/auto_tagging_base.py --apply
git add COTTE_Documentacao.base
```

### Opção 3: Via Claude Code Hook

Adicione ao `CLAUDE.md`:

```yaml
hooks:
  - event: post_init
    command: "python scripts/auto_tagging_base.py --apply"
```

---

## 📊 Histórico de Execuções

O script mantém histórico em `.rtk/tagging_history.json`:

```json
[
  {
    "timestamp": "2026-03-28T12:34:56.789123",
    "updated": [
      { "path": "README.md", "category": "documentacao" },
      { "path": "roadmap_cotte.md", "category": "roadmap" }
    ],
    "errors": []
  }
]
```

Últimos 10 registros são mantidos.

---

## ✨ Como a Base Usa Isso

### No Obsidian

1. Abra `COTTE_Documentacao.base`
2. As **7 views** mostram documentos organizados por:
   - 📋 **Todos os Documentos** — grouped por categoria
   - 🛣️ **Roadmap & Planos** — apenas items com tag roadmap/plano
   - 📘 **Implementações Ativas** — implementações em andamento
   - 🏗️ **Documentação Técnica** — mapas, arquitetura, fluxos
   - 🚀 **Deploy & Infra** — configuração e railway
   - 💭 **Memória do Projeto** — decisions, preferences, people
   - 🎨 **Documentação em Cards** — visualização em cards

### Para Claude em Novas Implementações

Quando você pedir para Claude implementar algo, o script garante que:

1. ✅ Base sempre tem **contexto atualizado**
2. ✅ Claude pode **consultar o roadmap** antes de codificar
3. ✅ Tags deixam **claro o status** de cada feature
4. ✅ Prioridades **guiam decisões arquiteturais**

---

## 🚨 Troubleshooting

### Script falha por módulo faltando

```bash
pip install pyyaml
```

### Arquivo não está sendo detectado

1. Verificar se está em `DOCS_IGNORE`
2. Rodar `--scan` para ver detecção
3. Adicionar padrão em `PATTERNS` se necessário

### Quer revert de uma mudança?

Histórico está em `.rtk/tagging_history.json` — você pode reverter manualmente ou remover o entry.

---

## 📝 Exemplo de Saída

**Antes:**
```markdown
# Meu Documento

Conteúdo...
```

**Depois:**
```markdown
---
title: Meu Documento
tags:
  - documentacao
  - tecnico
prioridade: media
status: documentado
---

# Meu Documento

Conteúdo...
```

---

**Mantém sua base sempre pronta para Claude usar em novas implementações!** 🚀
