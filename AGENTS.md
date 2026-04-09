---
title: Agents
tags:
  - documentacao
prioridade: alta
status: documentado
---
# COTTE Agent Guidelines (AGENTS.md)

Este guia destina-se a agentes de IA que operam no repositório **Projeto iZi / COTTE**.

## 🛠 Comandos de Desenvolvimento

O backend está em `sistema/` e o frontend em `sistema/cotte-frontend/`.

### Backend (FastAPI)
- **Instalar dependências:** `cd sistema && pip install -r requirements.txt`
- **Rodar localmente:** `cd sistema && uvicorn main:app --reload`
- **Rodar todos os testes:** `cd sistema && pytest`
- **Rodar um único arquivo de teste:** `cd sistema && pytest tests/test_helpers.py`
- **Rodar um teste específico:** `cd sistema && pytest tests/test_helpers.py::TestCalcularTotal::test_sem_desconto`
- **Migrations (Alembic):** As tabelas são criadas pelo SQLAlchemy no `main.py` durante testes. Em produção, use Alembic se configurado.

### Testes (Backend)
- Os testes usam SQLite em memória por padrão.
- Fixtures comuns estão em `tests/conftest.py`.
- Serviços externos (WhatsApp, IA, PDF) são mockados automaticamente.
- Para rodar testes async, use `pytest-asyncio`.

### Frontend & E2E
- **Testes Playwright:** `npm test` (na raiz do frontend)
- **Playwright UI:** `npm run test:ui`

### Ferramentas de Análise (qmd)
O `qmd` está instalado no venv do sistema para busca semântica e localização de código.
- **Busca na documentação:** `source sistema/venv/bin/activate && qmd search cotte "termo"`
- **Busca no código Python:** `source sistema/venv/bin/activate && qmd search cotte-py "termo"`
- **Atualizar índice:** `source sistema/venv/bin/activate && qmd update cotte && qmd update cotte-py`

---

## 🐍 Diretrizes de Código: Backend (Python/FastAPI)

### Estilo e Formatação
- **Linguagem:** Código (variáveis, funções, classes) em **inglês**. Comentários e Docstrings em **português**.
- **Naming:** `snake_case` para funções/variáveis, `PascalCase` para classes/modelos.
- **Tipagem:** Use **Type Hints** em todas as assinaturas de função.
- **Imports:**
  1. Standard library
  2. Third-party (FastAPI, SQLAlchemy, Pydantic)
  3. Local imports (app.models, app.services, etc.)
  - Use caminhos absolutos baseados na raiz do backend: `from app.models.models import Orcamento`.

### Arquitetura (Camadas)
- **Routers:** Apenas entrada/saída HTTP e chamadas de dependência (`Depends(get_db)`).
- **Services:** Toda a lógica de negócio, cálculos e integrações (IA, WhatsApp, PDF).
- **Models:** Definições SQLAlchemy em `app/models/models.py`.
- **Schemas:** Validação Pydantic em `app/schemas/`. Separe schemas de entrada (`Create`, `Update`) e resposta (`Response`).
- **Repositories:** Acesso a dados isolado quando necessário (ex: `ClienteRepository`).

### Banco de Dados (SQLAlchemy)
- Use `AsyncSession` para operações assíncronas.
- Prefira `select(Model).where(...)` (estilo 2.0).
- Use `joinedload` ou `selectinload` para evitar N+1 queries.
- Transações são gerenciadas automaticamente pelo FastAPI/SQLAlchemy.

### Autenticação e Segurança
- Use `get_usuario_atual` e `exigir_permissao` nos routers.
- Senhas são hasheadas com `bcrypt` via `passlib`.
- Tokens JWT são gerados com `python-jose`.

### Tratamento de Erros
- Use `HTTPException` do FastAPI para erros de negócio.
- Retorne códigos HTTP apropriados (400, 404, 409, 500).

---

## 🎨 Diretrizes de Código: Frontend (Vanilla JS)

### Regras de Ouro
- **NUNCA** use frameworks (React, Vue, etc.). Use **Vanilla JavaScript**.
- **CSS Moderno:** Use Flexbox, Grid e Custom Properties (`--cor-primaria`).
- **HTML Semântico:** Use `<header>`, `<main>`, `<section>`, etc.
- **Eventos:** Use `addEventListener`, nunca `onclick` no HTML.

### Estrutura
- JavaScript fica em `cotte-frontend/js/`.
- CSS fica em `cotte-frontend/css/`.
- HTML fica na raiz de `cotte-frontend/`.

### API Calls
- Use a função `apiFetch()` definida em `js/api.js` para chamadas à API.
- Tokens JWT são armazenados em `localStorage`.

---

## 🧠 Skills Especializadas (Fluxos de Trabalho)

O agente possui skills específicas que devem ser invocadas conforme o contexto da tarefa:

### 🏗️ Arquiteto (`cotte-arquiteto`)
Use para planejar funcionalidades novas, refatorações controladas ou fluxos complexos.
**Regra de Ouro:** Não comece editando. Entenda o objetivo, localize com `qmd`, mapeie o fluxo e proponha uma abordagem em etapas.

### 🐍 Backend (`cotte-backend`)
Use para alterações em rotas, services, models e schemas.
**Regra de Ouro:** Preserve contratos de API e compatibilidade. Nunca altere migrations antigas.

### 🐛 Debug (`cotte-debug`)
Use para diagnosticar erros no backend, frontend ou integrações.
**Regra de Ouro:** Identifique a causa raiz antes de propor mudanças amplas. Use logs de forma seletiva.

### 💰 Financeiro (`cotte-financeiro`)
Use para módulos de orçamento, contas a pagar/receber e fluxo de caixa.
**Regra de Ouro:** Garanta consistência de cálculos e rastreabilidade de valores.

### 🎨 Frontend (`cotte-frontend`)
Use para ajustes em telas HTML/CSS/JS.
**Regra de Ouro:** Mantenha o padrão Vanilla JS e reaproveite estilos existentes.

### 💬 WhatsApp (`cotte-whatsapp`)
Use para fluxos de mensagens, webhooks e automação comercial.
**Regra de Ouro:** Garanta idempotência e trate inputs como não confiáveis.

---

## 🤖 Instruções Finais para o Agente
- **Proatividade:** Se criar uma nova rota, sugira ou crie o teste unitário correspondente.
- **Contexto:** Sempre verifique `CLAUDE.md` para a stack tecnológica atualizada.
- **Segurança:** Nunca exponha ou salve chaves `.env` no código.
- **Português:** Comunique-se com o usuário e documente o código em português brasileiro.

---

## Learned User Preferences

- Quando o pedido vier de um plano anexo no Cursor, não modificar o arquivo do plano em `~/.cursor/plans/`; executar a partir dos to-dos já existentes sem recriar a lista (marcar `in_progress` em ordem até concluir).
- Após cada implementação, melhoria ou correção concluída, o agente deve sugerir **três** ideias novas de melhorias inovadoras (concretas, aplicáveis à stack atual), além do resumo do que foi feito.

## Learned Workspace Facts

- E-mails HTML transacionais devem seguir práticas de cliente de e-mail: tabelas para layout, estilos inline e sem dependências externas (Tailwind CDN, Google Fonts ou scripts).
- No assistente IA, cards de confirmação de ações pendentes não devem exibir ao operador a descrição técnica bruta da tool; usar resumo operacional dos argumentos e copy curta de revisão.
- Instruções persistentes de produto ou backlog para o agente no Cursor: preferir Project Rules e/ou `.cursor/rules/` e documentação durável (por exemplo `memory/decisions.md`); o par [SUGESTÃO]/[INOVAÇÃO] do `CLAUDE.md` padroniza o fechamento das respostas, não substitui especificação de features.
