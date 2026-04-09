---
title: Automation Proposal Acceptance
tags:
  - documentacao
prioridade: media
status: documentado
---
---
title: Automation Proposal Acceptance
tags:
  - documentacao
prioridade: media
status: documentado
---
# Plano de Implementação: Automação de Aceite de Proposta

## Objetivo
Conectar o aceite de propostas públicas ao CRM (pipeline de leads), garantindo que o status do lead mude automaticamente para "Fechado Ganho".

## Arquivos Afetados
- `sistema/app/routers/publico_propostas.py`: Lógica de aceite.
- `sistema/app/models/models.py`: Modelos de dados (referência).

## Passos da Implementação

### 1. Backend: Atualizar endpoint de aceite
Modificar `sistema/app/routers/publico_propostas.py`:
- Importar `CommercialLead` e `StatusPipeline`.
- Na função `aceitar_proposta`:
    1. Buscar o lead associado via `proposta_enviada.lead_id`.
    2. Se o lead existir, atualizar `lead.status_pipeline = StatusPipeline.FECHADO_GANHO`.
    3. Garantir o `db.commit()`.

### 2. Verificação e Testes
- **Teste de Unidade/Integração (Backend):** Criar script que valida a mudança de status do lead após o aceite.
- **Teste de UI (Frontend):** Verificar se o fluxo no `proposta.html` continua funcionando conforme o esperado.

## Critérios de Aceite
- Ao aceitar uma proposta, o status da proposta deve ser `ACEITA`.
- Ao aceitar uma proposta, o status do lead correspondente deve ser `fechado_ganho`.
- O histórico de visualizações deve permanecer funcionando.
