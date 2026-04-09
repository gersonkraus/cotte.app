---
title: Arquitetura Sistema
tags:
  - tecnico
prioridade: alta
status: documentado
---
---
title: Arquitetura do Sistema — COTTE
tags:
  - arquitetura
  - tecnico
  - backend
  - frontend
prioridade: alta
status: documentado
---

# Arquitetura do Sistema — COTTE

## Visão geral

O COTTE é um SaaS para criação e envio de orçamentos profissionais.  
A arquitetura prioriza simplicidade, clareza e manutenção fácil.

## Estrutura geral

| Camada | Tecnologia |
|--------|------------|
| Frontend | HTML, CSS, JavaScript (vanilla) |
| Backend | Python, FastAPI |
| Banco de dados | PostgreSQL (SQLAlchemy) |
| Infraestrutura | Railway |

## Componentes principais

### Interface do usuário
- Dashboard, orçamentos, clientes, catálogo, configurações, equipe, relatórios
- Bot integrado no dashboard (comando em linguagem natural)
- Link público para o cliente visualizar e aprovar/recusar a proposta

### Backend API
- Regras de negócio, CRUD de orçamentos e clientes
- Geração de PDF e link público
- Envio de orçamento ao cliente por e-mail ou WhatsApp
- **Notificações internas:** orçamento aprovado → WhatsApp para o responsável (atendente/criador/gestor); orçamento expirado → sem notificação interna
- Integrações: Brevo (e-mail transacional), Evolution API ou Z-API (WhatsApp)

### Serviços de domínio
- `quote_notification_service` — centraliza o tratamento de mudança de status (aprovado/expirado) e envio de notificação interna por WhatsApp (apenas aprovado, com idempotência)
- `whatsapp_service` — envio de mensagens (provider Z-API ou Evolution, multi-tenant por empresa)
- `email_service` — envio de orçamento ao cliente, reset de senha (Brevo ou SMTP)
- `ia_service` — interpretação de mensagens e comandos (Claude)
- `pdf_service` — geração de PDF do orçamento

### Banco de dados
- Usuários, empresas, clientes, orçamentos, itens, histórico de edições
- Notificações in-app, log de e-mail por orçamento
- Campo `approved_notification_sent_at` no orçamento para evitar duplicidade da notificação de aprovação

### Integrações
- **Brevo** — e-mails transacionais (orçamento ao cliente, recuperação de senha). Não é usado para notificações internas de aprovado/expirado.
- **Evolution API ou Z-API** — WhatsApp (envio ao cliente, lembretes, notificação interna de aprovação ao atendente)

## Fluxo simplificado

1. Usuário cria orçamento (dashboard ou bot WhatsApp).
2. Backend salva dados; sistema gera PDF e link público.
3. Usuário envia para o cliente (e-mail, WhatsApp ou link).
4. Cliente visualiza a proposta e pode aprovar ou recusar.
5. Ao aprovar: status atualizado; notificação interna enviada por WhatsApp ao responsável (uma vez por aprovação).
6. Ao expirar: status atualizado para expirado; nenhuma notificação interna é enviada.
