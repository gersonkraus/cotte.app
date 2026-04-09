---
title: Roadmap Connected
tags:
  - roadmap
prioridade: media
status: em-andamento
---
---
title: Roadmap Connected
tags:
  - roadmap
prioridade: media
status: em-andamento
---
# ROADMAP_CONNECTED.md

## Objetivo
Conectar **todas** as funcionalidades que já foram criadas (services, repositories, utils) mas ainda estão desconectadas ou só parcialmente usadas nos routers e no frontend.

Vamos conectar **um por um**, priorizando impacto alto e facilidade de implementação.

---

## ✅ Status Atual (31/03/2026)

| Feature                          | Status          | Prioridade | Próximo Passo                          |
|----------------------------------|-----------------|------------|----------------------------------------|
| LeadImportService                | Parcialmente usado | ★★★★★     | Conectar na aba Importação             |
| CampaignService + campanhas      | Desconectado    | ★★★★      | Integrar com tab Campanhas             |
| TemplateSegmentoService          | Desconectado    | ★★★       | Usar no cadastro de segmentos          |
| QuoteNotificationService         | Desconectado    | ★★★★      | Notificações automáticas após status   |
| AgendamentoAutoService           | Desconectado    | ★★★★      | Agendar lembretes automáticos          |
| AuditService                     | Pouco usado     | ★★★       | Log de auditoria central               |
| R2 + PDF Service                 | Parcial         | ★★        | Garantir uso em todos os documentos    |

---

## Plano de Conexão (Fazer na ordem)

### Fase 1 – Importação de Leads (Fazer HOJE)
- [ ] Atualizar `routers/comercial_import.py` para usar `LeadImportService`
- [ ] Conectar o botão “Analisar com IA” com `ai_json_extractor`
- [ ] Integrar preview + seleção no frontend (`comercial.js`)
- [ ] Testar upload CSV + cola de texto
- [ ] Adicionar histórico de importações

### Fase 2 – Campanhas & Templates
- [ ] Conectar `campaign_service.py` no router `comercial_campaigns.py`
- [ ] Integrar `template_segmento_service.py` no cadastro de segmentos
- [ ] Criar envio em lote após importação (usando template escolhido)

### Fase 3 – Notificações & Agendamentos
- [ ] Conectar `quote_notification_service.py` em mudanças de status de orçamento
- [ ] Adicionar APScheduler + `agendamento_auto_service.py`
- [ ] Criar trigger automático de lembretes

### Fase 4 – Qualidade & Manutenção
- [ ] Migrar cache in-memory → Redis
- [ ] Ativar `audit_service.py` em todas as ações importantes
- [ ] Unificar sistema de planos (novo RBAC + módulos)
- [ ] Adicionar soft-delete em todos os modelos principais

---

**Como usar este arquivo:**
1. Marque como feito `[x]` quando terminar cada item.
2. Depois de cada fase, rode os testes descritos em `melhorias.md`.
3. Atualize este arquivo sempre que conectar algo novo.

Próxima ação recomendada: **Fase 1 (Importação)** — é a mais visível e que você mais usa.

---
Última atualização: 31/03/2026