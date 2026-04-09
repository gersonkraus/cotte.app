---
title: Melhorias
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Melhorias
tags:
  - tecnico
prioridade: media
status: documentado
---
# melhorias.md

## PROMPT PRONTO PARA COLAR NO CLAUDE / CURSOR

Copie **todo o texto abaixo** e cole diretamente no Claude ou Cursor. Ele está organizado em tarefas sequenciais, com nome dos arquivos, o que fazer e testes obrigatórios.

---

**Você é um desenvolvedor sênior especialista em FastAPI + HTMX/Tailwind. Trabalhe no projeto COTTE.app.**

**Instruções gerais:**
- Sempre mantenha compatibilidade com o código existente.
- Use os padrões do projeto (exceções domain, logging estruturado, `@cached`, etc.).
- Depois de cada tarefa, teste tudo e me mostre o código modificado + testes realizados.
- Nunca remova funcionalidades existentes.

---

**TAREFA 1: Conectar LeadImportService na aba Importação (PRIORIDADE MÁXIMA)**

**Arquivos a editar:**
- `app/routers/comercial_import.py` (criar ou atualizar endpoint)
- `app/services/lead_import_service.py` (melhorar se necessário)
- `cotte-frontend/comercial.js` (lógica do stepper de importação)
- `cotte-frontend/comercial.html` (se precisar de pequenos ajustes no JS)

**O que fazer:**
1. Criar endpoint `POST /comercial/import` que aceite tanto texto colado quanto arquivo CSV.
2. Se for texto → usar IA (`ai_json_extractor`) para estruturar.
3. Se for CSV → usar `csv_parser.py`.
4. Passar tudo para `LeadImportService.process_import(data, empresa_id, usuario_id, config)`.
5. Retornar relatório completo (importados, duplicados, erros).
6. Atualizar o histórico de importações.

**Testes obrigatórios:**
- Colar texto com 5 leads → deve analisar com IA e mostrar preview correto.
- Upload de CSV com 10 linhas → deve importar sem duplicados.
- Importar com segmento e template selecionados → deve salvar corretamente.
- Verificar se o histórico aparece na aba.

---

**TAREFA 2: Conectar CampaignService e campanhas**

**Arquivos a editar:**
- `app/routers/comercial_campaigns.py`
- `app/services/campaign_service.py`
- `cotte-frontend/comercial.js` (tab Campanhas)

**O que fazer:**
- Criar endpoints completos para CRUD de campanhas.
- Integrar envio em lote (usando template).
- Conectar com leads importados.

**Testes:**
- Criar campanha → deve aparecer na tabela.
- Disparar campanha para 3 leads → verificar logs.

---

**TAREFA 3: Scheduler para Agendamentos Automáticos**

**Arquivos a editar:**
- `app/main.py` (adicionar startup)
- `app/services/agendamento_auto_service.py`
- Criar novo arquivo `app/services/scheduler.py` (se necessário)

**O que fazer:**
- Usar APScheduler (background task).
- Rodar `agendamento_auto_service` a cada 5 minutos.

**Testes:**
- Criar lembrete atrasado → deve disparar notificação automaticamente.

---

**TAREFA 4: Migrar Cache para Redis**

**Arquivos a editar:**
- `app/core/cache.py`
- `app/core/config.py` (já tem REDIS_URL)
- Atualizar todos os `@cached` usados

**Testes:**
- Verificar que cache funciona entre múltiplos workers.

---

**TAREFA 5: Melhorias de Responsividade (Frontend)**

**Arquivos a editar:**
- Todos os arquivos HTML que ainda usam tabelas grandes
- `cotte-frontend/css/comercial.css`
- `cotte-frontend/js/comercial.js`

**O que fazer:**
- Garantir que todas as tabelas usem mobile-cards (como já feito em usuarios.html).
- Usar Tailwind classes responsivas.

**Testes:**
- Testar em mobile (iPhone) todas as tabs da comercial.html.

---

**Fluxo de trabalho sugerido:**
1. Faça **uma tarefa por vez**.
2. Depois de cada tarefa, me mostre o diff dos arquivos alterados.
3. Rode os testes e confirme que passou.
4. Só passe para a próxima tarefa quando eu aprovar.

Vamos começar pela **Tarefa 1** (Importação de Leads).  
Quando estiver pronto, diga “Tarefa 1 concluída” e me mostre o código.

---

**Fim do prompt**