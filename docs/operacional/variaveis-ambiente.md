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
| `AI_PROVIDER` | Ex.: `openrouter`, `openai`, `anthropic` — usado com a normalização em `ia_service`. |
| `AI_MODEL` | Modelo principal do assistente (slug LiteLLM / catálogo do provider). |
| `AI_TECHNICAL_MODEL` | Modelo do copilot técnico / overrides onde o código usa modelo técnico. |
| `AI_MODEL_FALLBACK` | Usado quando `AI_MODEL` está vazio ou é o placeholder `default`. |
| `AI_API_KEY` | Chave unificada (opcional; tem prioridade sobre chaves por provider). |
| `OPENROUTER_API_KEY` | Chave OpenRouter (quando a rota LiteLLM é `openrouter/...`). |
| `ANTHROPIC_API_KEY` | Só necessária se usar rota **nativa** Anthropic (`anthropic/...` com `AI_PROVIDER=anthropic`), não para o fluxo padrão OpenRouter. |
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
