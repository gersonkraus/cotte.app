---
title: Agendamento
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Técnico - Módulo de Agendamentos
tags:
  - documentacao
  - agendamento
  - mapa-tecnico
prioridade: alta
status: documentado
---

# Mapa Técnico — Módulo de Agendamentos

Este documento descreve o módulo de agendamentos do COTTE: funcionalidades, configurações, fluxo de integração com orçamentos públicos e análise de furos do processo.

---

## 1. Visão Geral do Módulo

### 1.1 O que é

O módulo de agendamentos permite criar, gerenciar e rastrear compromissos vinculados ou não a orçamentos. Suporta:

- CRUD completo de agendamentos
- Sistema de opções de data/hora (cliente escolhe)
- Configuração por empresa e por usuário
- Bloqueio de slots
- Integração automática com orçamento público
- Dashboard e visualização em calendário

### 1.2 Arquitetura de Banco de Dados

| Tabela | Descrição |
|--------|------------|
| `agendamentos` | Registro principal |
| `agendamento_opcoes` | Opções de data/hora oferecidas ao cliente |
| `config_agendamento` | Configuração por empresa |
| `config_agendamento_usuario` | Override por usuário |
| `slots_bloqueados` | Bloqueios de horário |
| `historico_agendamentos` | Auditoria de mudanças |

**Referências:**
- Modelos: `app/models/models.py:1672-1854`
- Schemas: `app/schemas/agendamento.py`

### 1.3 Enumerações

#### StatusAgendamento (`models.py:1645-1653`)

| Valor | Descrição |
|-------|------------|
| `AGUARDANDO_ESCOLHA` | Aguardando cliente escolher data/hora |
| `PENDENTE` | Agendado, aguardando confirmação |
| `CONFIRMADO` | Confirmado pelo operador |
| `EM_ANDAMENTO` | Em execução |
| `CONCLUIDO` | Finalizado |
| `REAGENDADO` | Substituído por novo agendamento |
| `CANCELADO` | Cancelado pelo operador |
| `NAO_COMPARECEU` | Cliente não compareceu |

#### TipoAgendamento (`models.py:1656-1662`)

| Valor | Descrição |
|-------|------------|
| `ENTREGA` | Entrega de produto |
| `SERVICO` | Prestação de serviço |
| `INSTALACAO` | Instalação |
| `MANUTENCAO` | Manutenção |
| `VISITA_TECNICA` | Visita técnica |
| `OUTRO` | Outro tipo |

#### OrigemAgendamento (`models.py:1665-1669`)

| Valor | Descrição |
|-------|------------|
| `MANUAL` | Criado manualmente pelo operador |
| `WHATSAPP` | Via integração WhatsApp |
| `ASSISTENTE_IA` | Via assistente IA |
| `AUTOMATICO` | Criado automaticamente na aprovação do orçamento |

#### ModoAgendamentoOrcamento (`models.py:648-651`)

Usado no orçamento para definir se o agendamento é requerido:

| Valor | Descrição |
|-------|------------|
| `NAO_USA` | Não usa agendamento |
| `OPCIONAL` | Oferece agendamento, mas não obriga |
| `OBRIGATORIO` | Cliente deve escolher data/hora |

---

## 2. Funcionalidades — Passo a Passo

### 2.1 Criar Agendamento Manual

**Endpoint:** `POST /api/v1/agendamentos/`

**Fluxo de Validações** (em `agendamento_service.py:380-485`):

1. Valida cliente existe
2. Calcula `data_fim` com base na duração
3. Valida data não está no passado
4. Obtém configuração da empresa + usuário
5. Valida antecedência mínima (`antecedencia_minima_horas`)
6. Valida dia de trabalho (`dias_trabalho`)
7. Valida horário de trabalho (`horario_inicio` a `horario_fim`)
8. Verifica conflitos com outros agendamentos
9. Verifica slots bloqueados
10. Cria registro com status inicial (`PENDENTE` ou `CONFIRMADO` conforme `requer_confirmacao`)
11. Registra histórico

**Status Inicial:**
- Se `requer_confirmacao = True` → `PENDENTE`
- Se `requer_confirmacao = False` → `CONFIRMADO`

---

### 2.2 Criar Agendamento a partir de Orçamento Aprovado

**Endpoint:** `POST /api/v1/agendamentos/criar-do-orcamento/{orcamento_id}`

**Fluxo:**
1. Busca orçamento e valida que está `APROVADO`
2. Chama `criar_agendamento()` com os dados do orçamento
3. Vincula `orcamento.agendamento_id = ag.id`

**Referência:** `agendamento_service.py:488-526`

---

### 2.3 Criar Agendamento com Opções de Data

**Endpoint:** `POST /api/v1/agendamentos/com-opcoes`

**Características:**
- Status inicial: `AGUARDANDO_ESCOLHA`
- `data_agendada` fica `NULL` até cliente escolher
- Cria registro em `agendamento_opcoes` para cada opção
- Usado no fluxo público (orçamento aceito pelo cliente)

**Fluxo em `agendamento_service.py:1308-1440`:**
1. Valida orçamento aprovado
2. Valida cliente
3. Valida datas (não no passado, não duplicadas)
4. Cria agendamento com `status = AGUARDANDO_ESCOLHA`
5. Cria opções em `agendamento_opcoes`
6. Vincula ao orçamento

---

### 2.4 Listar Agendamentos

**Endpoint:** `GET /api/v1/agendamentos/`

**Parâmetros de filtro:**
- `status` — filtro por status
- `data_inicio`, `data_fim` — período
- `responsavel_id` — responsável
- `cliente_id` — cliente
- `pagina`, `por_pagina` — paginação

**Referência:** `agendamentos.py:150-170`

---

### 2.5 Visualização Calendário

**Frontend:** FullCalendar em `agendamentos.html`

**Endpoint:** Usa `GET /agendamentos/` com parâmetros de período

**Características:**
- Vista mensal, semanal, diária
- Cores por status
- Click para editar

**Referência:** `js/agendamentos.js`

---

### 2.6 Dashboard

**Endpoint:** `GET /api/v1/agendamentos/dashboard`

**Retorna:**
- `agendamentos_hoje` — quantidade para hoje
- `pendentes` — aguardando confirmação
- `confirmados` — confirmados
- `em_andamento` — em execução
- `concluidos_semana` — concluídos na semana
- `cancelados_semana` — cancelados na semana

**Referência:** `agendamento_service.py:900-969`

---

### 2.7 Agendamentos de Hoje

**Endpoint:** `GET /api/v1/agendamentos/hoje`

Retorna lista de agendamentos com `data_agendada` no dia atual.

**Referência:** `agendamentos.py:175-190`

---

### 2.8 Atualizar Agendamento

**Endpoint:** `PUT /api/v1/agendamentos/{id}`

**Regras:**
- Não permite editar status `CANCELADO`, `CONCLUIDO`, `NAO_COMPARECEU`
- Se mudar data, re-executa validações (antecedência, dia, horário, conflito, bloqueio)

**Referência:** `agendamento_service.py:529-629`

---

### 2.9 Atualizar Status

**Endpoint:** `PATCH /api/v1/agendamentos/{id}/status`

**Máquina de Estados — Transições Permitidas:**

```
PENDENTE     → CONFIRMADO, CANCELADO
CONFIRMADO   → EM_ANDAMENTO, CANCELADO, NAO_COMPARECEU
EM_ANDAMENTO→ CONCLUIDO, CANCELADO
```

Status finais (sem transição): `CONCLUIDO`, `CANCELADO`, `NAO_COMPARECEU`, `REAGENDADO`, `AGUARDANDO_ESCOLHA`

**Referência:** `agendamento_service.py:743-820`

---

### 2.10 Reagendar

**Endpoint:** `PATCH /api/v1/agendamentos/{id}/reagendar`

**Fluxo:**
1. Valida status atual é `PENDENTE` ou `CONFIRMADO`
2. Valida nova data (não passado, validações de config)
3. Marca antigo como `REAGENDADO`
4. Cria novo agendamento com referência `reagendamento_anterior_id`
5. Atualiza vínculo no orçamento (`orcamento.agendamento_id = novo.id`)

**Referência:** `agendamento_service.py:632-740`

---

### 2.11 Ver Histórico

**Endpoint:** `GET /api/v1/agendamentos/{id}/historico`

Retorna lista de alterações com status anterior, novo status, descrição e data.

**Referência:** `agendamentos.py:395-410`

---

### 2.12 Slots Disponíveis

**Endpoint:** `GET /api/v1/agendamentos/disponiveis`

**Parâmetros:**
- `data` — data a verificar
- `responsavel_id` — (opcional) filtrar por responsável

**Retorna:** Lista de horários livres para o dia, considerando:
- Horário de trabalho da empresa/usuário
- Intervalo mínimo entre agendamentos
- Agendamentos existentes
- Bloqueios

**Referência:** `agendamento_service.py:972-1074`

---

## 3. Configurações de Agendamento

### 3.1 Configuração da Empresa

**Tabela:** `config_agendamento`

**Campos:**

| Campo | Tipo | Default | Descrição |
|-------|------|---------|------------|
| `horario_inicio` | String (HH:MM) | `08:00` | Início do expediente |
| `horario_fim` | String (HH:MM) | `18:00` | Fim do expediente |
| `dias_trabalho` | JSON | `[0,1,2,3,4]` | Dias úteis (0=seg..4=sex) |
| `duracao_padrao_min` | Integer | `60` | Duração padrão em minutos |
| `intervalo_minimo_min` | Integer | `30` | Intervalo mínimo entre agendamentos |
| `antecedencia_minima_horas` | Integer | `1` | Mínimo de antecedência em horas |
| `permite_agendamento_cliente` | Boolean | `False` | Permite cliente agendar via link público |
| `requer_confirmacao` | Boolean | `True` | Agendamento precisa de confirmação manual |
| `lembrete_antecedencia_horas` | JSON | `[24, 2]` | Intervalos de lembrete (não implementado) |
| `mensagem_confirmacao` | Text | NULL | Mensagem customizada de confirmação |
| `mensagem_lembrete` | Text | NULL | Mensagem de lembrete (não usada) |
| `mensagem_reagendamento` | Text | NULL | Mensagem de reagendamento (não usada) |
| `usa_agendamento` | Boolean | `False` | Habilita módulo de agendamento |

**Endpoints:**
- `GET /agendamentos/config/empresa` — obter
- `PUT /agendamentos/config/empresa` — salvar

**UI:** Modal "Configurações da Agenda" → aba "Empresa" em `agendamentos.html:1204-1317`

**Referência:** `models.py:1773-1801`

---

### 3.2 Configuração por Usuário

**Tabela:** `config_agendamento_usuario`

**Override campos:**
- `horario_inicio` — NULL = usa empresa
- `horario_fim` — NULL = usa empresa
- `dias_trabalho` — NULL = usa empresa
- `duracao_padrao_min` — NULL = usa empresa

**Merge:** `_merge_config()` — config do usuário sobrepõe a da empresa

**Endpoints:**
- `GET /agendamentos/config/usuarios` — listar
- `POST /agendamentos/config/usuario` — criar/atualizar
- `DELETE /agendamentos/config/usuario/{usuario_id}` — remover

**Referência:** `models.py:1804-1831`, `agendamento_service.py:99-141`

---

### 3.3 Bloqueio de Slots

**Tabela:** `slots_bloqueados`

**Campos:**
- `empresa_id` — (FK)
- `usuario_id` — NULL = empresa-wide, caso contrário é individual
- `data_inicio`, `data_fim` — período bloqueado
- `motivo` — reason
- `recorrente` — Boolean
- `recorrencia_tipo` — "diario" ou "semanal" (não implementado)

**Endpoints:**
- `POST /agendamentos/bloquear-slot` — criar
- `GET /agendamentos/bloqueados` — listar
- `DELETE /agendamentos/bloquear-slot/{id}` — remover

**Referência:** `models.py:1834-1849`

---

### 3.4 Validações que Usam Configuração

| Função | Config Usada |
|--------|--------------|
| `_verificar_antecedencia()` | `antecedencia_minima_horas` |
| `_verificar_dia_trabalho()` | `dias_trabalho` |
| `_verificar_horario_trabalho()` | `horario_inicio`, `horario_fim` |
| `_verificar_conflito()` | `duracao_estimada_min` (implicitamente) |
| `_verificar_slot_bloqueado()` | `slots_bloqueados` |

**Referência:** `agendamento_service.py:144-256`

---

## 4. Fluxo Orçamento Público → Agendamento

### 4.1 Passo 1: Operador Define Modo no Orçamento

Ao criar/editar orçamento, o operador define `agendamento_modo`:
- `NAO_USA` — sem agendamento
- `OPCIONAL` — oferece, mas não exige
- `OBRIGATORIO` — força escolha

**Referência:** `models.py:728-732`

---

### 4.2 Passo 2: Cliente Abre Link Público

O cliente acessa: `https://app.cotte.com.br/app/orcamento-publico.html?token={link_publico}`

O backend retorna orçamento com campo `agendamento_modo`.

**Endpoint:** `GET /o/{link_publico}`

**Referência:** `publico.py:585`

---

### 4.3 Passo 3: Cliente Aceita Orçamento

**Endpoint:** `POST /o/{link_publico}/aceitar`

**Backend (`publico.py:585-699`):**
1. Valida OTP se exigido
2. Muda status orçamento → `APROVADO`
3. Cria contas a receber
4. Chama `criar_agendamento_automatico()` se modo `OPCIONAL` ou `OBRIGATORIO`

**Em `agendamento_auto_service.py:62-148`:**
1. Verifica idempotência (não cria duplicata)
2. Gera 3 opções automáticas de data (`_gerar_opcoes_automaticas()`)
3. Chama `criar_agendamento_com_opcoes()`
4. Retorna agendamento com status `AGUARDANDO_ESCOLHA`

---

### 4.4 Passo 4: Frontend Exibe Seção de Agendamento

Após aceite, frontend chama `exibirSecaoAgendamento()` (`orcamento-publico.html:1612-1678`):

**Modo OBRIGATORIO:**
- Modal azul ("Agendamento obrigatório")
- Botão "Escolher data e horário"
- **Sem botão fechar** (força escolha)

**Modo OPCIONAL:**
- Modal índigo ("Agendamento disponível")
- Botão "Ver opções de agendamento"
- Botão fechar disponível

**Referência:** `orcamento-publico.html:578-600`

---

### 4.5 Passo 5: Cliente Escolhe Data

**Endpoint:** `POST /o/{link_publico}/agendamento/escolher`

**Backend (`escolher_opcao()` em `agendamento_service.py:1443-1521`):**
1. Marca opção como escolhida (`opcao_escolhida_id`)
2. Define `data_agendada`
3. Calcula `data_fim`
4. Atualiza status:
   - Se `requer_confirmacao = True` → `PENDENTE`
   - Se `requer_confirmacao = False` → `CONFIRMADO`
5. Registra histórico
6. **Notifica operador via WhatsApp**
7. **Notifica cliente via WhatsApp** (com `mensagem_confirmacao`)

---

### 4.6 Aprovação Interna

Orçamentos aprovados internamente (via painel) também disparam `criar_agendamento_automatico()`:

```python
# orcamentos.py:1294-1305
if novo_status == StatusOrcamento.APROVADO:
    fin_svc.criar_contas_receber_aprovacao(orc, usuario.empresa_id, db)
    criar_agendamento_automatico(db, orc, usuario_id=usuario.id)
```

---

### 4.7 Diagrama do Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│ OPERADOR                                                            │
│ 1. Cria orçamento com agendamento_modo = OPCIONAL/OBRIGATORIO     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CLIENTE                                                             │
│ 2. Abre link público (orcamento-publico.html?token=xxx)          │
│ 3. Aceita orçamento (POST /o/{link}/aceitar)                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND - aceitar_orcamento()                                      │
│  • Status → APROVADO                                              │
│  • Criar contas a receber                                         │
│  • criar_agendamento_automatico()                                 │
│      └─ _gerar_opcoes_automaticas() → 3 datas                     │
│      └─ criar_agendamento_com_opcoes() → AGUARDANDO_ESCOLHA      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                            │
│ 4. exibirSecaoAgendamento() → mostra opções de data               │
│    • OBRIGATORIO: modal sem fechar                                 │
│    • OPCIONAL: modal com fechar                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CLIENTE                                                             │
│ 5. Escolhe opção (POST /o/{link}/agendamento/escolher)           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BACKEND - escolher_opcao()                                         │
│  • Marca opção escolhida                                          │
│  • Define data_agendada                                           │
│  • Status → PENDENTE ou CONFIRMADO                                │
│  • Notifica operador (WhatsApp)                                    │
│  • Notifica cliente (WhatsApp)                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Análise de Furos do Processo Orçamento → Agendamento

### 5.1 Furos Já Corrigidos

| # | Arquivo | Problema | Status |
|---|---------|----------|--------|
| 1 | `agendamento_service.py:~1378` | Typo `%H:%h` → `%H:%M` na mensagem de erro | Corrigido |
| 2 | `agendamento_service.py:793-799` | Vínculo órfão: orçamento aponta para agendamento cancelado | Corrigido |
| 3 | `agendamento_service.py:1482-1502` | Race condition ao escolher opção (duplicação) | Corrigido |
| 4 | UI frontend | Lembretes configuráveis mas não enviados | Pendente |

---

### 5.2 Novos Furos Identificados

#### Furo 5: Opções Automáticas Ignoram Conflitos e Bloqueios

**Arquivo:** `agendamento_auto_service.py:23-59`

**Problema:** `_gerar_opcoes_automaticas()` gera 3 opções nos próximos dias úteis no `horario_inicio` (09:00), mas **não verifica** se esses horários estão:
- Ocupados por outro agendamento
- Bloqueados em `slots_bloqueados`

**Impacto:** Cliente pode escolher um horário que já está ocupado ou bloqueado.

**Recomendação:** Alterar `_gerar_opcoes_automaticas()` para chamar `_verificar_conflito()` e `_verificar_slot_bloqueado()` antes de propor cada opção.

---

#### Furo 6: Criação com Opções Não Valida Regras de Negócio

**Arquivo:** `agendamento_service.py:1308-1440`

**Problema:** `criar_agendamento_com_opcoes()` salva opções **sem validar**:
- `_verificar_horario_trabalho()`
- `_verificar_conflito()`
- `_verificar_slot_bloqueado()`

Isso acontece porque as validações existem em `criar_agendamento()` (com data definida), mas não são executadas quando `data_agendada = NULL`.

**Impacto:** Opções geradas automaticamente podem estar fora do horário de trabalho.

**Recomendação:** Implementar validação das opções em `criar_agendamento_com_opcoes()`.

---

#### Furo 7: Escolher Opção Não Re-valida Regras

**Arquivo:** `agendamento_service.py:1443-1521`

**Problema:** Quando cliente escolhe uma opção, `escolher_opcao()` não executa:
- `_verificar_horario_trabalho()`
- `_verificar_antecedencia()`
- `_verificar_slot_bloqueado()`

**Impacto:** Se um bloqueio foi criado depois das opções serem geradas, o cliente pode confirmar um horário bloqueado.

**Recomendação:** Adicionar validações em `escolher_opcao()` antes de confirmar.

---

#### Furo 8: Sem Follow-up para AGUARDANDO_ESCOLHA

**Problema:** Não existe mecanismo para alertar o operador se o cliente não escolhe uma data. O agendamento fica "pendurado" indefinidamente.

**Impacto:** Agendamentos órfãos sem acompanhamento.

**Recomendação:** Implementar job para notificar operador após X dias sem escolha.

---

#### Furo 9: Modo OPCIONAL Sem Segundo Lembrete

**Problema:** No modo opcional, o cliente pode aceitar o orçamento e ignorar o agendamento. Não há segundo lembrete nem timeout.

**Impacto:** Potencial perda de agendamentos opcionais.

**Recomendação:** Adicionar lembrete adicional para mode OPCIONAL.

---

#### Furo 10: Responsável Errado no Auto-service

**Arquivo:** `agendamento_auto_service.py:111, 116`

**Problema:** Assume `orcamento.criado_por_id` como `responsavel_id`. Se o orçamento foi criado por bot/sistema (NULL), o responsável fica vazio ou inválido.

**Impacto:** Agendamento sem responsável válido.

**Recomendação:** Validar `criado_por_id` antes de usar; usar fallback de responsável padrão da empresa.

---

#### Furo 11: Erro Silenciado no Aceite Público

**Arquivo:** `publico.py:666-674`

**Problema:** `criar_agendamento_automatico()` está em try/except que engole o erro. Se falhar, o orçamento é aprovado sem agendamento, sem notificação ao operador.

```python
try:
    criar_agendamento_automatico(db, orc)
except Exception:
    logger.exception(...)
```

**Impacto:** Erros críticos silenciados.

**Recomendação:** Se criação falhar, incluir flag de alerta na resposta ou criar notificação para operador.

---

#### Furo 12: Não Dá para Cancelar AGUARDANDO_ESCOLHA

**Arquivo:** `agendamento_service.py:764-779`

**Problema:** A máquina de estados não permite cancelar um agendamento que está em `AGUARDANDO_ESCOLHA`.

**Impacto:** Se cliente sumir, operador não consegue cancelar via rota de status.

**Recomendação:** Adicionar transição `AGUARDANDO_ESCOLHA` → `CANCELADO`.

---

#### Furo 13: Reagendar Não Funciona para AGUARDANDO_ESCOLHA

**Arquivo:** `agendamento_service.py:653`

**Problema:** Apenas `PENDENTE` e `CONFIRMADO` podem ser reagendados. Se o cliente não escolheu data e o operador quer forçar, não consegue.

**Impacto:** Limitação operacional.

**Recomendação:** Permitir reagendar a partir de `AGUARDANDO_ESCOLHA`.

---

#### Furo 14: Link Público Pode Quebrar com Reenvio

**Problema:** Se operador reenvia o orçamento (novo `link_publico`), o agendamento anterior ainda referencia o orçamento antigo. O endpoint usa `link_publico`, então o cliente acessa URL obsoleta.

**Impacto:** Confusão com links antigos.

**Recomendação:** Ao reenviar orçamento, atualizar link no agendamento ou invalidar link antigo.

---

#### Furo 15: Duração Hardcoded no Auto-service

**Arquivo:** `agendamento_auto_service.py:122`

**Problema:** Usa `duracao_estimada_min=60` fixo, ignorando `config.duracao_padrao_min`.

**Impacto:** Configuração da empresa não respeitada no agendamento automático.

**Recomendação:** Usar `config.duracao_padrao_min` do `ConfigAgendamento`.

---

#### Furo 16: Mensagens Customizadas Não Usadas

**Problema:** `mensagem_confirmacao` é usada após escolha, mas:
- `mensagem_reagendamento` **nunca** é usada
- `mensagem_lembrete` **nunca** é usada

**Impacto:** Feature incompleta.

**Recomendação:** Usar `mensagem_reagendamento` em `reagendar()` e implementar job para lembretes.

---

#### Furo 17: Sem Permissão Granular

**Problema:** O router exige `exigir_permissao("agendamentos", "escrita")` mas não diferencia:
- Quem pode criar agendamentos
- Quem pode configurar a agenda da empresa

**Impacto:** Qualquer usuário com acesso pode alterar configurações globais.

**Recomendação:** Adicionar permissão separada para `configuracao_agendamento`.

---

### 5.3 Resumo dos Furos

| # | Severidade | Arquivo | Descrição |
|---|------------|---------|------------|
| 5 | Alta | `agendamento_auto_service.py` | Opções automáticas ignoram conflitos |
| 6 | Alta | `agendamento_service.py` | Criação com opções não valida regras |
| 7 | Alta | `agendamento_service.py` | Escolher opção não re-valida |
| 8 | Média | — | Sem follow-up para AGUARDANDO_ESCOLHA |
| 9 | Média | — | Modo OPCIONAL sem segundo lembrete |
| 10 | Média | `agendamento_auto_service.py` | Responsável errado se criado por sistema |
| 11 | Alta | `publico.py` | Erro silenciado no aceite público |
| 12 | Baixa | `agendamento_service.py` | Não dá para cancelar AGUARDANDO_ESCOLHA |
| 13 | Baixa | `agendamento_service.py` | Reagendar não funciona para AGUARDANDO_ESCOLHA |
| 14 | Baixa | — | Link público pode quebrar com reenvio |
| 15 | Média | `agendamento_auto_service.py` | Duração hardcoded |
| 16 | Baixa | — | Mensagens customizadas não usadas |
| 17 | Baixa | `agendamentos.py` | Sem permissão granular |

---

## 6. Referência de Endpoints

| Método | Path | Descrição | Permissão |
|--------|------|------------|-----------|
| `POST` | `/agendamentos/` | Criar agendamento | `agendamentos:escrita` |
| `POST` | `/agendamentos/criar-do-orcamento/{id}` | Criar a partir de orçamento | `agendamentos:escrita` |
| `POST` | `/agendamentos/com-opcoes` | Criar com opções de data | `agendamentos:escrita` |
| `GET` | `/agendamentos/` | Listar com filtros | `agendamentos:leitura` |
| `GET` | `/agendamentos/dashboard` | Dados do dashboard | `agendamentos:leitura` |
| `GET` | `/agendamentos/hoje` | Agendamentos de hoje | `agendamentos:leitura` |
| `GET` | `/agendamentos/disponiveis` | Slots disponíveis | `agendamentos:leitura` |
| `GET` | `/agendamentos/responsaveis` | Lista responsáveis | `agendamentos:leitura` |
| `GET` | `/agendamentos/config/empresa` | Get config empresa | `agendamentos:leitura` |
| `PUT` | `/agendamentos/config/empresa` | Save config empresa | `agendamentos:escrita` |
| `GET` | `/agendamentos/config/usuarios` | List user configs | `agendamentos:leitura` |
| `POST` | `/agendamentos/config/usuario` | Save user config | `agendamentos:escrita` |
| `DELETE` | `/agendamentos/config/usuario/{id}` | Remove user config | `agendamentos:escrita` |
| `POST` | `/agendamentos/bloquear-slot` | Block slot | `agendamentos:escrita` |
| `GET` | `/agendamentos/bloqueados` | List blocked slots | `agendamentos:leitura` |
| `DELETE` | `/agendamentos/bloquear-slot/{id}` | Remove blocked slot | `agendamentos:escrita` |
| `GET` | `/agendamentos/{id}/historico` | Get history | `agendamentos:leitura` |
| `PATCH` | `/agendamentos/{id}/reagendar` | Reschedule | `agendamentos:escrita` |
| `PATCH` | `/agendamentos/{id}/status` | Update status | `agendamentos:escrita` |
| `GET` | `/agendamentos/{id}` | Get details | `agendamentos:leitura` |
| `PUT` | `/agendamentos/{id}` | Update | `agendamentos:escrita` |

### Endpoints Públicos (orçamento)

| Método | Path | Descrição |
|--------|------|------------|
| `GET` | `/o/{link_publico}/agendamento` | Ver agendamento vinculado |
| `POST` | `/o/{link_publico}/agendamento/escolher` | Cliente escolhe opção |

---

## 7. Máquina de Estados — Transições

```
                                    ┌─────────────┐
                                    │ AGUARDANDO  │
                                    │   ESCOLHA   │
                                    └──────┬──────┘
                                           │ escolher_opcao()
                                           ▼
┌─────────────┐     ┌─────────────┐      ┌─────────────┐
│   PENDENTE  │◄────│  CONFIRMADO  │      │   PENDENTE  │
└──────┬──────┘     └──────┬──────┘      └──────┬──────┘
       │                   │                     │
       │ confirma()       │ inicia()           │ confirma()
       ▼                   ▼                     ▼
┌─────────────┐     ┌─────────────┐      ┌─────────────┐
│  CONFIRMADO  │     │ EM_ANDAMENTO│      │  CONFIRMADO │
└─────────────┘     └──────┬──────┘      └─────────────┘
                           │
                           │ conclude()
                           ▼
                    ┌─────────────┐
                    │  CONCLUIDO  │ ◄─── final
                    └─────────────┘

┌─────────────┐     ┌─────────────┐      ┌─────────────┐
│  CANCELADO  │◄────│  PENDENTE   │      │ NAO COMPAR │
│    final    │     └─────────────┘      │    ECEU    │
└─────────────┘                           └─────────────┘

┌─────────────┐     ┌─────────────┐
│ REAGENDADO  │◄────│  CONFIRMADO │      ┌─────────────┐
│    final    │     │   ou        │      │ EM_ANDAMENTO│
└─────────────┘     │  PENDENTE   │──────│  ou         │
                    └─────────────┘      │  PENDENTE   │
                                         └─────────────┘
```

---

## 8. Referências de Código

| Recurso | Arquivo | Linhas |
|---------|---------|--------|
| Models (enums, Agendamento) | `app/models/models.py` | 648-651, 1645-1854 |
| Schemas | `app/schemas/agendamento.py` | — |
| Service principal | `app/services/agendamento_service.py` | 1684 linhas |
| Service automático | `app/services/agendamento_auto_service.py` | 148 linhas |
| Router | `app/routers/agendamentos.py` | 539 linhas |
| Router público | `app/routers/publico.py` | 930-1066 |
| Frontend página | `cotte-frontend/agendamentos.html` | 1377 linhas |
| Frontend JS | `cotte-frontend/js/agendamentos.js` | 1106 linhas |
| Frontend público | `cotte-frontend/orcamento-publico.html` | 357-369, 578-600, 1320-1678 |
| Correções | `correcao-agendamento.md` | — |
| Testes | `sistema/tests/test_agendamentos.py` | 267 linhas |

---

*Documento gerado em 2026-03-30*
