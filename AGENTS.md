---
title: Agents
tags:
  - documentacao
prioridade: alta
status: documentado
---
# COTTE Agent Guidelines (AGENTS.md)

Este guia destina-se a agentes de IA (como OpenCode, Claude Code) operando no repositório **Projeto iZi / COTTE**. Leia-o para evitar erros comuns de contexto.

## 🛠 Topologia e Comandos
### MCP e Inicialização
- **Sempre comece lendo o arquivo stacklit.json via MCP antes de qualquer coisa.**
- **Use as ferramentas stacklit para navegar no codebase.**


- **Raiz do Workspace:** `/home/gk/Projeto-izi` (Onde rodam Playwright e scripts de CI)
- **Backend:** `sistema/` (FastAPI)
- **Frontend Estático:** `sistema/cotte-frontend/` (Servido diretamente pelo FastAPI em `/app`)

### Comandos Backend (Executar dentro de `sistema/`)
- **Instalar:** `pip install -r requirements.txt`
- **Rodar Local:** `uvicorn app.main:app --reload` *(Atenção: o entrypoint está em `app/main.py`, não `main.py`)*
- **Migrations:** `python3 -m alembic upgrade heads` (Executado em prod via `release.sh`)
- **Testes (Pytest):** `pytest` ou `pytest tests/test_helpers.py` (O diretório de testes backend é `sistema/tests/`)

### Comandos Frontend / E2E (Executar na Raiz do Workspace)
- O Playwright está configurado na raiz (`/home/gk/Projeto-izi/playwright.config.js`). 
- **Rodar CLI:** `npm test`
- **Rodar UI:** `npm run test:ui`
- *Nota: O backend deve estar rodando localmente (porta 8000) para os testes E2E funcionarem.*

### qmd (Ferramenta de Busca Semântica)
- `source sistema/venv/bin/activate && qmd search cotte "termo"`

---

## 🐍 Diretrizes de Backend (FastAPI / SQLAlchemy)

- **Linguagem:** Código (variáveis, métodos, classes) em **inglês**. Comentários e Docstrings em **português brasileiro**.
- **Tipagem:** Use Type Hints rigorosamente em todas as assinaturas.
- **Camadas Arquiteturais:**
  - `app/routers/`: Apenas I/O HTTP, chamadas para services e dependências (`Depends(get_db)`). Nunca coloque regra de negócio aqui.
  - `app/services/`: Centraliza regras de negócio, integrações (Claude, WhatsApp/Evolution, PDF).
  - `app/repositories/`: Queries do SQLAlchemy isoladas (ex: `ClienteRepository`).
- **Banco de Dados:** PostgreSQL com `AsyncSession`. Prevenção de N+1 queries é mandatória: use `selectinload` ou `joinedload`. Transações são automáticas pelo dependêncy injection.
- **Idempotência e Segurança:** Operações críticas (aprovação, faturamento, envio de WhatsApp) precisam tratar concorrência e falhas de retry. Sempre use o wrapper `quote_notification_service.py` ao invés de chamar disparos no WhatsApp de forma avulsa.

---

## 🎨 Diretrizes de Frontend (Vanilla JS)

- **Frameworks Proibidos:** O sistema usa **Vanilla JavaScript** puro, HTML5 Semântico e CSS (Tailwind CDN + CSS Custom com variáveis). Não introduza React, Vue, ou bibliotecas de SPA.
- **Comunicação de API:** Use as classes baseadas no `cotte-frontend/js/services/ApiService.js` e `CacheService.js`. Abandone o antigo `apiFetch` cru.
- **Experiência do Usuário (UX):** Todo botão de ação ou formulário deve ter estado de *loading* explícito (desabilitar + spinner) e tratar cenários de erro via UI, evitando silent failures.

---

## 🧠 Skills Especializadas (Fluxos de Trabalho)

Invoque a skill local correspondente **antes** de começar a alterar o código nessas áreas:
- `cotte-arquiteto`: Planejamento de funcionalidades novas, refatorações amplas ou fluxos complexos.
- `cotte-backend`: Rotas, services, banco de dados ou integração LLM.
- `cotte-frontend`: Telas HTML, estilização ou refatoração de JS Vanilla.
- `cotte-financeiro`: Relatórios financeiros, orçamentos, faturas.
- `cotte-whatsapp`: Fluxos do bot, webhooks, mensagens automáticas.
- `cotte-debug`: Depuração e resolução de problemas difíceis ou que cruzam fronteiras (frontend <-> backend).

---

## 🤖 Learned Preferences & Workspace Facts

- **Atualização de Planos:** Se atuando sob um checklist/plano em `~/.cursor/plans/` (ou equivalente), modifique os checkboxes marcando progresso em ordem (`[x]` ou `in_progress`), sem destruir a formatação original do arquivo.
- **Inovações Obrigatórias:** Ao final de TODA tarefa concluída (bugfix ou feature), resuma o que foi feito e forneça exatamente **três sugestões inovadoras** (`[INOVAÇÃO]`) aplicáveis de verdade à stack atual (FastAPI/Vanilla JS), focando em negócio/UX/IA. Opcionalmente, até duas `[SUGESTÃO]` de refatoração para as áreas tocadas.
- **E-mails Transacionais:** Devem usar *Tabelas HTML* antiquadas e *CSS inline*. Proibido usar links externos para fontes e Tailwind CDN para estilizar o e-mail em si (os clientes bloqueiam).
- **Tratamento de Confirmações (WhatsApp/IA):** Ao solicitar uma confirmação de ação para o usuário via IA, exiba um resumo operacional legível e amigável (por ex: Nome do Cliente, Valor, O que será alterado), e NUNCA apresente dumps cruéis de JSON ou argumentos brutos da chamada de ferramenta.
- **Documentação de uso e base do Assistente IA:** Manuais de uso em `docs/guia-do-usuario.md` e `docs/tecnico/`; conhecimento principal do Assistente em `sistema/app/services/prompts/knowledge_base.md`. Ao mudar regras de produto, manter coerência com `docs/funcionalidades.md` quando aplicável.
- **Assistente IA — streaming no frontend:** Em `cotte-frontend/js/assistente-ia.js`, respostas via stream podem deixar `formatAIResponse` vazio de propósito (texto já veio nos chunks). Não tratar isso como falha nem anexar mensagem de fallback genérica quando já houver conteúdo renderizado.
- **Assistente IA — bloqueios de UI (embed/produção):** Evitar substituir o `innerHTML` de `.ai-assistant-container` inteiro em fluxos de permissão ou plano; isso remove o header (engrenagem) e invalida listeners. Preferir trocar só um slot interno (ex.: `#aiAssistantMainSlot`) e preservar elementos globais (ex.: painel de preferências no `body`). Falhas ou indisponibilidade de `/ai/status` tendem a ser mais frequentes em produção que em dev local.
- **Orçamentos — transição de status:** A API permite **Rascunho → Aprovado** (máquina de estados em `app/utils/orcamento_status.py`, alinhada ao painel). Fluxos de cliente público ou WhatsApp podem continuar exigindo **Enviado** onde já estiver explícito no código; não assumir o mesmo conjunto de transições em todos os canais.