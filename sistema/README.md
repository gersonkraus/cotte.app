---
title: Readme
tags:
  - documentacao
prioridade: alta
status: documentado
---
---
title: COTTE — Backend API
tags:
  - backend
  - tecnico
  - api
prioridade: alta
status: documentado
---

# COTTE — Backend API

Sistema de geração de orçamentos via WhatsApp com inteligência artificial (Claude).
FastAPI, PostgreSQL, frontend em HTML/JS servido em `/app`.

## Estrutura do Projeto

```
sistema/
├── main.py                         # Ponto de entrada FastAPI e migrations
├── requirements.txt
├── Procfile                        # Railway: uvicorn main:app
├── cotte-frontend/                 # Frontend — servido em /app
├── static/                         # PDFs, logos (static/pdfs, static/logos)
│
└── app/
    ├── core/
    │   ├── config.py               # Configurações (lê .env)
    │   ├── database.py             # PostgreSQL (SessionLocal)
    │   └── auth.py                 # JWT e autenticação
    │
    ├── models/
    │   └── models.py               # SQLAlchemy (Orcamento, Empresa, Usuario, etc.)
    │
    ├── schemas/
    │   ├── schemas.py              # Pydantic (request/response)
    │   └── notifications.py       # SendResult para WhatsApp
    │
    ├── routers/
    │   ├── auth_clientes.py        # Login, registro, clientes
    │   ├── orcamentos.py           # CRUD, comando-bot, status, timeline, envio e-mail
    │   ├── whatsapp.py             # Webhook WhatsApp (Z-API/Evolution), bot
    │   ├── publico.py              # Link público (ver proposta, aceitar, recusar)
    │   ├── empresa.py              # Dados e logo da empresa, WhatsApp próprio
    │   ├── admin.py                # Painel admin
    │   ├── catalogo.py             # CRUD de serviços
    │   ├── notificacoes.py         # Notificações in-app
    │   ├── relatorios.py           # Resumo e exportação
    │   ├── config.py               # Configurações
    │   └── webhooks.py             # Webhooks externos
    │
    ├── services/
    │   ├── ia_service.py           # Claude (interpretar mensagem, comando operador)
    │   ├── whatsapp_service.py     # Factory Z-API/Evolution, send_whatsapp_message
    │   ├── quote_notification_service.py  # Notificações internas (aprovado → WhatsApp)
    │   ├── email_service.py        # Brevo/SMTP (orçamento ao cliente, reset senha)
    │   ├── pdf_service.py          # Geração de PDF
    │   ├── plano_service.py        # Limites e permissões por plano
    │   └── whatsapp_base.py        # Interface do provider WhatsApp
    │
    └── utils/
        └── phone.py               # normalize_phone_number
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
- **Frontend:** http://localhost:8000/app  
- **Health:** http://localhost:8000/health  

## Endpoints principais

### Autenticação e clientes
| Método | Rota                | Descrição                  |
|--------|---------------------|----------------------------|
| POST   | /auth/registrar     | Cadastra empresa + usuário |
| POST   | /auth/login         | Login, retorna token JWT   |
| GET    | /clientes           | Lista clientes             |
| POST   | /clientes           | Cria cliente               |

### Empresa
| Método | Rota           | Descrição           |
|--------|----------------|---------------------|
| GET    | /empresa       | Dados da empresa    |
| PATCH  | /empresa       | Atualiza empresa    |
| POST   | /empresa/logo  | Envia logo          |
| DELETE | /empresa/logo  | Remove logo         |

### Orçamentos
| Método | Rota                              | Descrição                        |
|--------|-----------------------------------|----------------------------------|
| GET    | /orcamentos                       | Lista orçamentos                 |
| POST   | /orcamentos                       | Cria orçamento                   |
| GET    | /orcamentos/{id}                  | Detalhe do orçamento             |
| PUT    | /orcamentos/{id}                  | Atualiza orçamento               |
| PATCH  | /orcamentos/{id}/status           | Atualiza status (dispara notificação interna se aprovado) |
| POST   | /orcamentos/comando-bot           | Bot do dashboard (linguagem natural) |
| POST   | /orcamentos/{id}/enviar-email     | Envia orçamento por e-mail ao cliente |
| POST   | /orcamentos/{id}/enviar-whatsapp   | Envia orçamento via WhatsApp     |

### WhatsApp
| Método | Rota                  | Descrição                    |
|--------|-----------------------|-----------------------------|
| GET    | /whatsapp/status      | Status da conexão           |
| GET    | /whatsapp/qrcode      | QR Code para conectar       |
| DELETE | /whatsapp/desconectar | Desconecta                  |
| POST   | /whatsapp/webhook     | Recebe mensagens (Z-API ou Evolution) |
| POST   | /whatsapp/interpretar | Testa interpretação de texto |

### Público (sem autenticação)
| Método | Rota                         | Descrição                |
|--------|------------------------------|--------------------------|
| GET    | /o/{link_publico}            | Ver proposta             |
| POST   | /o/{link_publico}/aceitar     | Cliente aceita           |
| POST   | /o/{link_publico}/recusar     | Cliente recusa           |

### Catálogo, Admin, Notificações, Relatórios
- Catálogo: CRUD em `/catalogo`
- Admin: `/admin/*` (superadmin)
- Notificações: `/notificacoes`, contagem e marcar lidas
- Relatórios: `/relatorios/resumo`, exportar CSV

## Fluxo do WhatsApp

```
Mensagem recebida no WhatsApp
        ↓
Webhook (Z-API ou Evolution) chama /whatsapp/webhook
        ↓
Claude interpreta (comando ou criação de orçamento)
        ↓
Orçamento criado / comando executado
        ↓
PDF gerado; confirmação enviada ao usuário
        ↓
"ENVIAR {id}" → PDF enviado ao cliente
        ↓
Cliente "ACEITO" → status aprovado + notificação interna por WhatsApp ao responsável
```

## Deploy no Railway

Root Directory = `sistema`. Variáveis no painel. Deploy automático em `git push origin main`.  
Guia completo: [DEPLOY-RAILWAY.md](DEPLOY-RAILWAY.md).
