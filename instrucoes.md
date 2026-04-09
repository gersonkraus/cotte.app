---
title: Instruções para Parceiro de Programação — COTTE
tags:
  - documentacao
  - onboarding
prioridade: alta
status: ativo
---

# Instruções para Parceiro de Programação — COTTE

Este documento configura o comportamento esperado de um parceiro de programação IA (Gemini ou similar) ao trabalhar no projeto COTTE.

---

## Perfil do Projeto

**Nome:** COTTE
**Tipo:** SaaS B2B de gestão para pequenas empresas
**Dono do produto:** Gerson (empreendedor, background técnico intermediário — usa IA como principal apoio de desenvolvimento)
**Usuário final:** Pequenos empresários, baixo conhecimento técnico, precisam de rapidez, clareza e automação
**Deploy:** Railway (Root Directory = `sistema/`)
**Banco de dados:** PostgreSQL + Alembic (migrations versionadas)
**Repositório:** Monorepo com `sistema/` (backend + frontend juntos)

### Módulos principais
- Orçamentos (criação manual e via IA/WhatsApp)
- Clientes e CRM
- Financeiro (caixa, contas a receber/pagar)
- Catálogo de produtos/serviços
- Agendamentos
- Comercial (pipeline, leads, propostas, campanhas, templates)
- Assistente IA (chat + voz + WhatsApp)
- Documentos e relatórios
- Administração (superadmin, planos, broadcasts)
- WhatsApp (Evolution API, webhooks, bot)

---

## Stack Oficial — NUNCA ALTERE

A stack abaixo é definitiva. Não sugira substituições de framework ou biblioteca sem motivo crítico.

### Backend
- **Python 3.11+**
- **FastAPI** — framework web
- **SQLAlchemy** (async) — ORM
- **Alembic** — migrations
- **PostgreSQL** — banco de dados
- **Anthropic SDK** — IA (Claude Sonnet para interpretação, Haiku para tarefas simples)
- **WeasyPrint** — geração de PDF (motor moderno); fallback: **FPDF2**
- **Brevo** — envio de e-mails
- **Cloudflare R2** — armazenamento de arquivos (`r2_service.py`)
- **Evolution API** — WhatsApp (`whatsapp_evolution.py`)

### Frontend
- **HTML5 + CSS3** (Tailwind CDN + CSS custom)
- **JavaScript Vanilla puro** — sem frameworks (sem React, Vue, Angular)
- **ApiService.js** — toda chamada HTTP passa por aqui (nunca `fetch` direto)
- **CacheService.js** — cache local de dados

### Estrutura de pastas relevante
```
sistema/
  app/
    routers/       # Orquestração + validação (endpoints FastAPI)
    services/      # Toda regra de negócio
    repositories/  # Queries SQLAlchemy
    models/        # Models SQLAlchemy (models.py)
    alembic/       # Migrations (versions/)
    core/          # Config, segurança, dependências
  cotte-frontend/
    *.html         # Páginas (index, orcamentos, financeiro, etc.)
    js/
      services/    # ApiService.js, CacheService.js
      *.js         # Módulos por funcionalidade
    css/           # Estilos customizados
```

---

## Tarefas do Parceiro

Ao receber um pedido, o parceiro deve:

### Regra geral
1. **Entender o pedido** antes de qualquer código
2. **Apresentar um plano curto** (3-5 linhas) descrevendo o que vai fazer e os arquivos afetados
3. **Escrever o código completo e funcional** — nunca pseudocódigo, nunca esboço parcial
4. **Listar ao final:** arquivos alterados, o que mudou, impacto, riscos e testes recomendados

### Regras de código — Backend
- Seguir o fluxo obrigatório: `router → service → repository → model`
- `router`: apenas orquestração e validação de input
- `service`: toda lógica de negócio
- `repository`: apenas queries SQLAlchemy
- Endpoints protegidos: usar `exigir_permissao` + `verificar_ownership`
- Toda resposta de API deve seguir o padrão:
  ```json
  { "success": true, "data": {}, "error": null, "code": null }
  ```
- Usar `Decimal` para **todos** os valores monetários (nunca `float`)
- Preferir agregações no banco (`func.sum`, `func.count`) em vez de loops Python
- Usar `selectinload` / `joinedload` para evitar N+1 queries
- Ao adicionar colunas: **sempre** gerar a migration Alembic correspondente
- Idempotência em operações críticas (pagamentos, aprovações, envios)
- Aprovação de orçamento: **sempre** via `quote_notification_service` (nunca WhatsApp direto)
- WhatsApp: **sempre** passar por `whatsapp_sanitizer.py`

### Regras de código — Frontend
- **Nunca** usar `fetch` diretamente — sempre via `ApiService.js`
- **Nunca** criar scripts inline grandes — separar em arquivo `.js` próprio
- Todo botão/ação deve ter: loading state + error handling visível ao usuário
- Limite inicial de listas: 8 itens + botão "Carregar mais"
- Retry automático (3 tentativas) em chamadas críticas
- Feedback visual imediato para ações demoradas (PDF, WhatsApp, aprovação)
- Polling máximo de 30s para operações assíncronas
- Ao editar um arquivo HTML/JS: **retornar o arquivo completo** (nunca trechos isolados)

### O que NÃO fazer
- Não refatorar partes não relacionadas ao pedido
- Não adicionar frameworks novos sem necessidade crítica
- Não criar helpers/abstrações para uso único
- Não adicionar validações para cenários impossíveis
- Não criar arquivos desnecessários
- Não alterar stack, arquitetura ou convenções sem aprovação explícita

---

## Contexto de Trabalho

### Sobre o usuário final
- Pequenos empresários com pouco conhecimento técnico
- Interface deve ser **autoexplicativa** — zero necessidade de treinamento
- UX: simples, direto, sem terminologia técnica

### Sobre o desenvolvimento
- Preferir melhorias incrementais — não grandes refatorações sem ganho claro
- Validar rapidamente no sistema real (sem staging complexo)
- Baixo custo operacional é prioridade (tokens de IA, infra, APIs)
- Performance é obrigatória — respostas rápidas, sem travamentos

### Sobre a IA no sistema
- Assistente responde em linguagem natural e executa ações operacionais
- Nunca executar ação operacional (criar orçamento, aprovar, etc.) sem ID explícito confirmado
- `ia_service.py` — interpretação de intenção (Claude)
- `cotte_ai_hub.py` — hub de IA com streaming SSE
- `ai_prompt_loader.py` — carregamento de prompts (sempre usar, nunca hardcodar prompts)
- Limite de tokens sempre configurado em chamadas de IA

---

## Formato de Resposta

### Idioma
**Sempre em português.** Termos técnicos (nome de funções, variáveis, bibliotecas) permanecem em inglês/original.

### Estrutura padrão de resposta

**Antes de editar:**
```
Plano:
1. [o que vai fazer]
2. [arquivos que serão tocados]
3. [impacto esperado]
```

**Após o código:**
```
Arquivos alterados:
- sistema/app/routers/exemplo.py — [o que mudou]
- sistema/cotte-frontend/exemplo.html — [o que mudou]

Impacto: [performance, integração, UX]
Riscos: [se houver]
Testes recomendados: [pytest ou Playwright ou manual]
```

### Sinalizadores especiais

Use os marcadores abaixo para enriquecer respostas sem misturar com o código pedido:

- `[SUGESTAO]` — Melhoria de performance, segurança ou qualidade de código que pode ser aplicada junto ou depois
- `[INOVACAO]` — Ideia de nova funcionalidade, automação com IA ou melhoria de UX que vai além do pedido atual
- `[ATENCAO]` — Risco identificado, efeito colateral ou ponto que exige revisão manual
- `[DUVIDA]` — Separar claramente: fato | hipótese | incerteza quando não houver certeza sobre o comportamento atual do sistema

### Exemplo de resposta bem formatada

```
Plano:
1. Adicionar campo `desconto_percentual` na tabela `orcamentos`
2. Criar migration Alembic
3. Atualizar service e router de orçamentos
4. Atualizar frontend orcamentos.html (campo no formulário + cálculo em tempo real)

[código completo aqui]

Arquivos alterados:
- sistema/app/models/models.py — novo campo Decimal desconto_percentual
- sistema/app/alembic/versions/xxxx_add_desconto.py — migration nova
- sistema/app/services/orcamento_service.py — lógica de desconto
- sistema/app/routers/orcamentos.py — schema atualizado
- sistema/cotte-frontend/orcamentos.html — campo e cálculo JS

Impacto: novo campo opcional, sem quebra de dados existentes
Riscos: verificar se PDF usa o valor com desconto aplicado
Testes: criar orçamento com desconto e verificar total calculado

[SUGESTAO] Adicionar limite máximo de desconto por plano (evitar margem negativa)
[INOVACAO] IA poderia sugerir desconto automático baseado no histórico do cliente
```

---

## Referências Internas Importantes

| Arquivo | Função |
|---|---|
| `app/services/ia_service.py` | Interpretação de mensagens com Claude |
| `app/services/cotte_ai_hub.py` | Hub IA com streaming SSE |
| `app/services/quote_notification_service.py` | Aprovação e notificação de orçamentos |
| `app/services/whatsapp_evolution.py` | Integração Evolution API |
| `app/services/pdf_service.py` | Geração de PDF (WeasyPrint + FPDF2) |
| `app/services/financeiro_service.py` | Caixa, contas a receber/pagar |
| `app/services/r2_service.py` | Upload/download Cloudflare R2 |
| `app/utils/pdf_utils.py` | Montagem de dicionários para PDF |
| `app/services/ai_prompt_loader.py` | Carregamento de prompts de IA |
| `cotte-frontend/js/services/ApiService.js` | Cliente HTTP do frontend |
| `cotte-frontend/js/services/CacheService.js` | Cache local do frontend |

---

*Este documento deve ser mantido atualizado sempre que houver decisões técnicas relevantes ou mudanças de arquitetura.*
*Última atualização: 09/04/2026*
