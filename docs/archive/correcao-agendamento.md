---
title: Correcao Agendamento
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Correcao Agendamento
tags:
  - documentacao
prioridade: alta
status: documentado
---
# Correções — Módulo de Agendamento

Este documento lista correções objetivas e seguras para o módulo de agendamento do COTTE.

---

## 1. Typo na Mensagem de Erro

**Arquivo:** `app/services/agendamento_service.py`  
**Linha:** ~1378  
**Método:** `criar_agendamento_com_opcoes()`

### Problema
Formato de hora incorreto na mensagem de erro (`%H:%h`).

### Correção

```python
# Linha 1378 - ANTES (bug):
return None, f"Data {dt.strftime('%d/%m/%Y %H:%h')} está no passado."

# Linha 1378 - DEPOIS (corrigido):
return None, f"Data {dt.strftime('%d/%m/%Y %H:%M')} está no passado."
```

**Impacto:** Apenas corrige string de erro. Sem alteração funcional.

---

## 2. Vínculo Órfão: Orçamento Aponta para Agendamento Cancelado

**Arquivo:** `app/services/agendamento_service.py`  
**Método:** `atualizar_status()` e `reagendar()`

### Problema
Quando um agendamento é cancelado ou reagendado, o campo `agendamento_id` no orçamento permanece apontando para o agendamento antigo (cancelado/reativado).

### Correção

```python
# Dentro de atualizar_status(), após linha ~793:
elif novo_status == StatusAgendamento.CANCELADO:
    ag.cancelado_em = now
    ag.motivo_cancelamento = motivo
    
    # NOVO: limpar vínculo órfão
    if ag.orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == ag.orcamento_id).first()
        if orc and orc.agendamento_id == ag.id:
            orc.agendamento_id = None
```

**Impacto:** Impede que orçamentos apontem para agendamentos cancelados.

---

## 3. Race Condition: Duplicação ao Escolher Opção

**Arquivo:** `app/services/agendamento_service.py`  
**Linha:** ~1475  
**Método:** `escolher_opcao()`

### Problema
Se o cliente enviar duas requisições simultâneas para escolher uma opção de agendamento, pode haver duplicação.

### Correção

```python
# Após linha 1477 (após atualizar ag.data_agendada e antes de atualizar outras opções):
db.flush()  # Forçar gravação para evitar duplicação em requests simultâneos

# Marcar outras opções como indisponíveis
db.query(AgendamentoOpcao).filter(
    AgendamentoOpcao.agendamento_id == agendamento_id,
    AgendamentoOpcao.id != opcao_id,
).update({"disponivel": False}, synchronize_session=False)
```

**Impacto:** Garante idempotência na escolha de opção.

---

## 4. Recomendação: Feature Incompleta (Lembretes)

### Problema
A configuração `lembrete_antecedencia_horas` existe no schema e no banco, mas não há job que envie esses lembretes. O usuário configura mas nada acontece.

### Opções

| Opção | Ação | Esforço |
|-------|------|---------|
| **A** | Implementar job de lembretes | Alto (requer BGTask/cron) |
| **B** | Remover campos relacionados da UI | Baixo |
| **C** | Deixar como está e documentar | Baixo |

### Recomendação
Se não houver roadmap para implementar envio de lembretes, **remover da UI** os campos:
- `lembrete_antecedencia_horas`
- `mensagem_lembrete`

Manter apenas no schema para compatibilidade futura.

---

## Resumo das Alterações

| # | Arquivo | Método | Tipo |
|---|---------|--------|------|
| 1 | `agendamento_service.py` | `criar_agendamento_com_opcoes()` | Typo |
| 2 | `agendamento_service.py` | `atualizar_status()` | Lógica |
| 3 | `agendamento_service.py` | `escolher_opcao()` | Race condition |
| 4 | UI (frontend) | — | Remoção de feature |

---

## Como Aplicar

1. Aplique as correções 1-3 diretamente no arquivo `agendamento_service.py`
2. Para a correção 4, avalie o roadmap antes de agir

Nenhuma migration ou alteração de schema é necessária.
