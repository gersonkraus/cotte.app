---
title: Plano Tool Use V2
tags:
  - roadmap
prioridade: media
status: documentado
---
---
title: Plano Tool Use V2
tags:
  - roadmap
prioridade: media
status: documentado
---
# Plano — Tool Use v2 do Assistente COTTE

Última atualização: 2026-04-07

Documento de continuidade. Resume o que já foi feito nas fases anteriores e o que ainda falta para concluir a migração do assistente para Tool Use / function calling.

---

## Arquitetura (resumo)

- `app/services/ai_tools/` — registry de tools (`ToolSpec` + Pydantic `input_model` + handler async).
- `app/services/tool_executor.py` — valida input, checa permissão/ownership, aplica rate-limit, persiste `tool_call_log`, serializa confirmação de tools destrutivas (card com args).
- `app/services/cotte_ai_hub.py::assistente_unificado_v2` — loop tool-use (LiteLLM OpenAI format); popula `pending_action`, `tool_trace` no `AIResponse`.
- `cotte-frontend/js/assistente-ia.js` — renderiza `tool_trace` (🛠️ ✅ nome) e `pending-action-card` (Confirmar/Cancelar → `/ai/execute_pending`).
- Feature flag: `USE_TOOL_CALLING=true`.

---

## ✅ Fase 1 — Base (concluída)

- `ToolSpec` + registry + `openai_tools_payload()`.
- `tool_executor` com validação, permissão, ownership, rate-limit, log em `tool_call_log`, fluxo pending/confirm.
- Migration `tc001_tool_call_log.py`.
- Loop tool-use em `assistente_unificado_v2` com `tool_trace` e `pending_action`.
- Endpoint `/ai/execute_pending` (fast-path confirmação).
- Frontend: render de `tool_trace` e `pending-action-card` em `assistente-ia.js`.
- Tools de leitura: `listar_clientes`, `listar_materiais`, `listar_orcamentos`, `obter_orcamento`, `obter_saldo_caixa`, `listar_movimentacoes_financeiras`.
- Tools destrutivas iniciais: `criar_cliente`, `excluir_cliente`, `criar_movimentacao_financeira`, `criar_orcamento`.
- Testes unitários em `tests/test_tool_executor.py` (8/8 passando).

## ✅ Fase 2 — Ações operacionais (concluída)

Commits: `75d8562`, `aecc3c4`.

- `aprovar_orcamento` — status APROVADO + `financeiro_service.criar_contas_receber_aprovacao` + `handle_quote_status_changed`.
- `recusar_orcamento` — status RECUSADO com motivo opcional.
- `enviar_orcamento_whatsapp` — PDF on-the-fly + `whatsapp_service.enviar_orcamento_completo`.
- `enviar_orcamento_email` — PDF + `enviar_orcamento_por_email` com link público.
- `criar_agendamento` — wrapper sobre `agendamento_service.criar_agendamento`.
- `cadastrar_material` — cria `Servico` direto.
- **Bug fix**: `criar_orcamento` agora usa `gerar_numero` com 3x retry + `link_publico=secrets.token_urlsafe(24)` + `sequencial_numero`.

Registry atual: **16 tools** em `app/services/ai_tools/__init__.py`.

---

## 🚧 Pendências (o que ainda falta)

### A. Deploy & cleanup imediato

- [ ] **Push dos commits** `75d8562` e `aecc3c4` para `main` (Railway auto-deploy).
- [ ] **Limpar orçamento órfão** criado durante bug do numero NULL (id=123 no dev; conferir prod). SQL sugerido:
  ```sql
  DELETE FROM itens_orcamento WHERE orcamento_id = 123;
  DELETE FROM orcamentos WHERE id = 123 AND numero IS NULL;
  ```
- [ ] **Bump cache-buster** do `assistente-ia.html` (`?v=4` → `?v=5`) — ver `/home/gk/.claude/plans/concurrent-dazzling-trinket.md`. Card de confirmação não renderiza em prod por cache de JS antigo.

### B. Fase 3 — Cobertura funcional restante

Tools ainda ausentes mas úteis para o assistente operar o sistema completo:

- [ ] `editar_cliente` (atualizar telefone/email/endereço sem precisar recriar).
- [ ] `editar_orcamento` (alterar itens/observações enquanto RASCUNHO).
- [ ] `duplicar_orcamento`.
- [ ] `registrar_pagamento_recebivel` (marcar conta a receber como paga com valor/data/forma).
- [ ] `criar_despesa` + `marcar_despesa_paga`.
- [ ] `criar_parcelamento` (receita/despesa).
- [ ] `listar_agendamentos` + `cancelar_agendamento` + `remarcar_agendamento`.
- [ ] `listar_leads` + `criar_lead` + `mover_lead_pipeline` + `registrar_interacao_lead`. **⚠️ Restritas a `is_superadmin=True`** — leads/pipeline hoje só existem no painel admin; a tool deve checar `current_user.is_superadmin` e retornar `forbidden` caso contrário.
- [ ] `listar_despesas`.
- [ ] `anexar_documento_orcamento`.

Critério de pronto por tool: Pydantic input, handler async, permissão, teste unitário (happy + forbidden + not_found), registro no `__init__`.

### C. Fase 4 — Qualidade & robustez

- [ ] **Testes E2E** do loop completo em `test_assistente_unificado_v2.py` — cada nova tool precisa de um cenário (pending → confirm → ok).
- [ ] **Rate-limit por tool destrutiva** (hoje é global): definir thresholds específicos para `criar_orcamento`, `enviar_orcamento_*`.
- [ ] **Idempotência** em `enviar_orcamento_whatsapp`/`email` — evitar duplo envio se usuário confirmar duas vezes (chave: `orcamento_id + canal + janela 60s`).
- [ ] **Retry automático** no loop tool-use quando tool devolve `rate_limited` ou erro transitório de rede (hoje abortamos).
- [ ] **Telemetria**: dashboard simples de `tool_call_log` (taxa de erro, p95 latência, top tools). Rota admin.
- [ ] **Tracing**: adicionar `request_id` propagado do router até o `tool_executor` para correlacionar no log.

### D. Fase 5 — UX do frontend

- [ ] Card de confirmação com **resumo legível** dos args (hoje mostra JSON cru). Mapear por tool: "Criar orçamento para **Ana Silva** — Mesa R$ 500,00".
- [ ] Botão **Cancelar** envia feedback pro assistente ("usuário cancelou") para continuar a conversa com contexto.
- [ ] Estado de loading no card enquanto `/ai/execute_pending` roda.
- [ ] Toast de erro rico com `code` vindo da tool (`forbidden`, `not_found`, `rate_limited`).
- [ ] Acessibilidade: card com `role="dialog"` + foco no botão Confirmar.

### E. Fase 6 — Manual e prompts

- [ ] Atualizar `app/services/prompts/manual_sistema.md` seção "Tools disponíveis" com a lista completa (hoje lista apenas as da Fase 1).
- [ ] Adicionar exemplos few-shot de uso correto para tools complexas (`criar_orcamento` com múltiplos itens, `enviar_orcamento_email` com link).
- [ ] Regra explícita: nunca chamar `enviar_*` sem antes o orçamento estar em status ENVIADO ou superior (hoje só valida telefone/email).

### F. Follow-ups técnicos menores

- [ ] Trocar `?v=N` hardcoded dos HTMLs por hash de build no `release.sh` (elimina esquecimento futuro do cache-buster).
- [ ] Remover arquivos `-old` (`ia_service-old.py`, `ApiService-old.js`, `ux-improvements copy.js`) após confirmação que v2 está estável em prod.
- [ ] Consolidar `test_assistente_unificado_v2.py` e `test_tool_executor.py` em um único pacote `tests/assistente/`.

---

## Como retomar

1. Ler este arquivo + `memory/decisions.md`.
2. Rodar `pytest sistema/tests/test_tool_executor.py -q` para baseline.
3. Escolher o próximo item da seção B ou C.
4. Seguir padrão de `agendamento_tools.py` (mais enxuto) como template para novas tools simples, ou `orcamento_tools.py::_criar_orcamento` para tools com retry/side-effects.
5. Atualizar este plano ao concluir cada item (marcar `[x]` e anotar commit).
