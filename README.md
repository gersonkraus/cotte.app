---
title: Readme
tags:
  - documentacao
prioridade: alta
status: documentado
---
---
title: Readme
tags:
  - documentacao
prioridade: alta
status: documentado
---
# COTTE - Sistema de Gestão Comercial

Sistema completo de gestão comercial com orçamentos, clientes, produtos e integração com WhatsApp.

## Status do Sistema

**Última verificação:** Teste inicial realizado pelo agente
**Backend:** ✅ Operacional (FastAPI + SQLAlchemy)
**Frontend:** ✅ Vanilla JS funcionando
**Testes:** ✅ Configurados (pytest backend, Playwright E2E)
**Integrações:** ✅ WhatsApp, PDF, IA

## Como contribuir

- Guia completo: [CONTRIBUTING.md](CONTRIBUTING.md) (princípios, validação, commits e deploy).
- **Revisão:** abra um PR para `main`, descreva o problema e como validar; o [template de PR](.github/pull_request_template.md) referencia trechos do CONTRIBUTING por tipo de mudança.
- Alinhamento documental agente/humano: `npm run validate:contributing`.

## 🚀 Tecnologias

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- Pydantic v2
- Alembic (migrations)
- PostgreSQL

### Frontend
- Vanilla JavaScript
- HTML5 semântico
- CSS3 moderno (Flexbox/Grid)
- Font Awesome icons

### Integrações
- WhatsApp Business API
- OpenAI GPT-4
- PDF generation (WeasyPrint)
- Email (SMTP)

## 📁 Estrutura do Projeto

```
.
├── sistema/                    # Backend FastAPI
│   ├── app/
│   │   ├── models/           # Modelos SQLAlchemy
│   │   ├── schemas/          # Schemas Pydantic
│   │   ├── services/         # Lógica de negócio
│   │   └── routers/          # Rotas da API
│   ├── tests/               # Testes unitários
│   ├── main.py              # Aplicação principal
│   └── requirements.txt     # Dependências Python
├── sistema/cotte-frontend/  # Frontend Vanilla JS
│   ├── index.html
│   ├── styles/
│   ├── scripts/
│   └── assets/
├── playwright-tests/        # Testes E2E
├── CLAUDE.md               # Stack tecnológica
├── AGENTS.md              # Guia para agentes
└── README.md              # Este arquivo
```

## 🛠️ Instalação e Execução

### Backend
```bash
cd sistema
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd sistema/cotte-frontend
# Abra index.html no navegador ou use um servidor local
python -m http.server 8000
```

### Testes
```bash
# Backend
cd sistema
pytest

# E2E (Playwright)
npm test
```

## 📚 Documentação da API

A API está documentada automaticamente via Swagger UI:
- **Local:** http://localhost:8000/docs
- **Redoc:** http://localhost:8000/redoc

## 🔧 Comandos Úteis

### Desenvolvimento
- `cd sistema && uvicorn main:app --reload` - Inicia backend
- `cd sistema && pytest -v` - Executa testes backend
- `npm test` - Executa testes E2E Playwright

### Banco de Dados
- `cd sistema && alembic revision --autogenerate -m "descricao"` - Cria migration
- `cd sistema && alembic upgrade head` - Aplica migrations

### Análise de Código
- `source sistema/venv/bin/activate && qmd search cotte "termo"` - Busca na doc
- `source sistema/venv/bin/activate && qmd search cotte-py "termo"` - Busca no código

## 🤖 Skills do Agente

O projeto utiliza agentes especializados para diferentes tarefas:

- **🏗️ Arquiteto (`cotte-arquiteto`):** Planejamento e arquitetura
- **🐍 Backend (`cotte-backend`):** Desenvolvimento Python/FastAPI
- **🐛 Debug (`cotte-debug`):** Diagnóstico de problemas
- **💰 Financeiro (`cotte-financeiro`):** Módulos financeiros
- **🎨 Frontend (`cotte-frontend`):** Interface Vanilla JS
- **💬 WhatsApp (`cotte-whatsapp`):** Integração WhatsApp

## 📞 Contato

Para suporte ou dúvidas, consulte a documentação interna ou entre em contato com a equipe de desenvolvimento.---
title: COTTE — Projeto iZi
tags:
  - documentacao
  - geral
  - overview
prioridade: alta
status: ativo
---

# COTTE — Projeto iZi

Sistema de geração de orçamentos via WhatsApp com inteligência artificial (Claude).
Backend em FastAPI, frontend em HTML/CSS/JS; deploy no Railway.

## Estrutura do repositório

```
Projeto iZi/
├── sistema/                    # Aplicação principal (backend + frontend)
│   ├── main.py                 # Ponto de entrada FastAPI
│   ├── requirements.txt
│   ├── Procfile                # Comando de start (Railway)
│   ├── cotte-frontend/         # Frontend estático (servido em /app)
│   ├── app/
│   │   ├── core/               # config, database, auth
│   │   ├── models/             # SQLAlchemy
│   │   ├── schemas/            # Pydantic (incl. notifications)
│   │   ├── routers/            # orcamentos, whatsapp, empresa, publico, etc.
│   │   ├── services/           # ia, pdf, email, whatsapp, quote_notification
│   │   └── utils/              # phone (normalização)
│   └── tests/
├── CLAUDE.md                   # Referência rápida para o assistente
├── arquitetura_sistema.md
├── fluxo_do_sistema.md
├── variaveis_ambiente.md
├── stack_tecnologica.md
├── produto_cotte.md
├── roadmap_cotte.md
└── README.md                   # Este arquivo
```

## Rodar localmente

```bash
cd sistema
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edite com suas chaves
uvicorn main:app --reload
```

- **API:** http://localhost:8000/docs  
- **App:** http://localhost:8000/app  
- **Health:** http://localhost:8000/health  

## Deploy (Railway)

O deploy é automático ao fazer push na branch `main`:

```bash
git push origin main
```

Configure **Root Directory** = `sistema` no serviço do Railway e todas as variáveis de ambiente no painel.  
Guia detalhado: [sistema/DEPLOY-RAILWAY.md](sistema/DEPLOY-RAILWAY.md).

## Documentação adicional

| Arquivo | Conteúdo |
|---------|----------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como contribuir, revisão e flags de desenvolvimento (ex.: assistente IA) |
| [CLAUDE.md](CLAUDE.md) | Stack, arquivos-chave e convenções para o assistente |
| [arquitetura_sistema.md](arquitetura_sistema.md) | Visão geral da arquitetura |
| [fluxo_do_sistema.md](fluxo_do_sistema.md) | Fluxo principal de orçamentos e notificações |
| [variaveis_ambiente.md](variaveis_ambiente.md) | Variáveis de ambiente |
| [stack_tecnologica.md](stack_tecnologica.md) | Stack e integrações |
| [produto_cotte.md](produto_cotte.md) | Visão de produto |
| [roadmap_cotte.md](roadmap_cotte.md) | Roadmap do produto |
| [BREVO_SETUP.md](BREVO_SETUP.md) | Setup do Brevo (e-mail ao cliente, reset de senha) |
| [identidade_visual.md](identidade_visual.md) | Paleta, tipografia e estilo visual |
| [padroes_interface.md](padroes_interface.md) | Padrões de UI (layout, sidebar, cards) |
| [sistema/README.md](sistema/README.md) | Estrutura e endpoints da API |
| [sistema/DOCUMENTACAO_MUDANCAS.md](sistema/DOCUMENTACAO_MUDANCAS.md) | Histórico de mudanças |
# Teste de automação
# Teste 2
# Teste 3
# Teste 4
# Teste 5
# Teste 6
# Teste 7
# Teste 8
# Teste 9
# Teste 10
# Automação concluída
