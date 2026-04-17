---
title: Stack Tecnologica
tags:
  - tecnico
prioridade: alta
status: documentado
---
---
title: Stack Tecnológica — COTTE
tags:
  - tecnico
  - stack
  - infraestrutura
prioridade: alta
status: documentado
---

# Stack Tecnológica — COTTE

## Backend
- Python 3.x
- FastAPI
- SQLAlchemy (PostgreSQL)
- Pydantic

## Frontend
- HTML, CSS, JavaScript (vanilla)
- Servido como arquivos estáticos em `/app` (cotte-frontend)

## Infraestrutura
- Railway (hosting e PostgreSQL)

## Integrações

| Serviço | Uso |
|---------|-----|
| **Brevo** | E-mails transacionais: envio de orçamento ao cliente, recuperação de senha. Não usado para notificações internas de aprovado/expirado. |
| **Evolution API ou Z-API** | WhatsApp: envio de orçamento ao cliente, lembretes automáticos, notificação interna quando o cliente aprova (para o atendente responsável). Provider escolhido via `WHATSAPP_PROVIDER`. |
| **LiteLLM** (modelos via `.env`: `AI_MODEL`, `AI_TECHNICAL_MODEL`, etc.) | Interpretação de mensagens em linguagem natural e geração de respostas do bot; rota típica OpenRouter (`OPENROUTER_API_KEY` ou `AI_API_KEY`). |

## Outros recursos
- Geração de PDF do orçamento
- Link público para proposta (cliente aprova/recusa sem login)
- Serviço central de notificações de orçamento (quote_notification_service) com idempotência
