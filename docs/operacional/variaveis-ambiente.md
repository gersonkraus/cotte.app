---
title: Variaveis Ambiente
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Variáveis de Ambiente — COTTE
tags:
  - config
  - deploy
  - infraestrutura
prioridade: alta
status: documentado
---

# Variáveis de Ambiente — COTTE

## Objetivo

Centralizar configurações sensíveis do sistema. Todas são lidas em `sistema/app/core/config.py` a partir do `.env` (local) ou do painel do Railway (produção).

## Principais variáveis

| Variável | Uso |
|----------|-----|
| `DATABASE_URL` | Conexão PostgreSQL (obrigatória). |
| `SECRET_KEY` | Assinatura JWT e sessão (obrigatória). |
| `APP_URL` | URL base do sistema (ex.: `https://seu-app.up.railway.app`), usada em links de e-mail e proposta. |
| `ANTHROPIC_API_KEY` | Chave da API Claude (IA). |
| `WHATSAPP_PROVIDER` | `zapi` ou `evolution` — define qual integração WhatsApp usar. |
| `EVOLUTION_API_URL` | URL base da Evolution API (quando WHATSAPP_PROVIDER=evolution). |
| `EVOLUTION_API_KEY` | Chave da Evolution API. |
| `EVOLUTION_INSTANCE` | Nome da instância global (fallback quando a empresa não tem WhatsApp próprio). |
| `ZAPI_BASE_URL`, `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN` | Configuração Z-API (quando WHATSAPP_PROVIDER=zapi). |
| `BREVO_API_KEY` | Envio de e-mails transacionais (orçamento ao cliente, reset de senha) via API Brevo. |
| `SMTP_*` | Alternativa ao Brevo: host, porta, usuário, senha e remetente para envio por SMTP. |

## Boas práticas

- Nunca commitar o arquivo `.env` no repositório.
- Usar variáveis de ambiente no Railway (ou outro host) para produção.
- Manter valores diferentes para desenvolvimento e produção quando necessário (ex.: `APP_URL`, `DATABASE_URL`).
