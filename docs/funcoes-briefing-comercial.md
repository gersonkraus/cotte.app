# Briefing Diário IA — Módulo Comercial

**Arquivo:** `tenant-comercial.html` → aba **"Hoje"** (primeira posição)  
**Criado em:** 2026-04-28

---

## O que é

Uma aba no topo do módulo Comercial que substitui a abertura pelo Dashboard. A IA analisa todos os leads ativos e monta uma lista de ações prioritárias com rascunhos de mensagem prontos — sem precisar navegar, lembrar ou decidir o que fazer.

---

## Arquivos envolvidos

| Arquivo | Função |
|---|---|
| `app/services/ia_service.py` | `gerar_briefing_lead()` — chama a IA por lead; `_briefing_fallback()` — fallback por regras locais |
| `app/routers/tenant/comercial_leads.py` | `GET /tenant/comercial/leads/briefing` — endpoint que monta contextos e agrega resultados |
| `cotte-frontend/tenant-comercial.html` | Aba "Hoje" com painel `#tab-hoje` e badge de pendências |
| `cotte-frontend/js/tenant-comercial-briefing.js` | Toda a lógica de frontend: fetch, cache, renderização, ações |

---

## Fluxo de funcionamento

1. Usuário abre o Comercial → aba "Hoje" está ativa por padrão
2. Frontend chama `GET /tenant/comercial/leads/briefing`
3. Backend busca todos os leads ativos (excluindo ganhos/perdidos, limite 30)
4. Para cada lead, monta contexto com: nome, empresa, etapa, score, dias sem contato, próximo contato agendado e resumo das últimas 3 interações
5. Envia todos à IA em paralelo (`asyncio.gather`) para minimizar tempo de espera
6. Resultado cacheado no `localStorage` com a data do dia — recarregar a página não rechama a IA
7. Cards ordenados por prioridade: urgente → hoje → esta semana

---

## Tipos de card

| Prioridade | Cor | Condição de ativação |
|---|---|---|
| 🔴 Urgente | Vermelho | +5 dias sem contato em `proposta_enviada`; OU +3 dias com score quente; OU follow-up vencido |
| 🟡 Hoje | Âmbar | Follow-up agendado para hoje; OU +7 dias sem contato com score morno; OU cliente respondeu recentemente |
| 🟢 Mover etapa | Verde | Cliente respondeu e etapa do pipeline não reflete o momento atual |
| ⚪ Ok (não aparece) | — | Contato recente (<2 dias); OU score frio em etapa inicial; OU confiança da IA < 0.5 |

---

## Ações disponíveis por card

| Botão | Comportamento |
|---|---|
| **✓ Enviar agora** | Dispara mensagem via `POST /leads/{id}/whatsapp` ou `/email`; card vira "concluído" |
| **✎ Editar** | Abre rascunho em textarea editável; "💾 Salvar" confirma o texto antes de enviar |
| **✗ Pular** | Remove o card do dia; reaparece amanhã se o lead ainda não foi contatado |
| **✓ Mover etapa** | Atualiza `status_pipeline` via `PUT /leads/{id}`; card vira "concluído" |
| **Ver lead** | Navega para aba Leads e abre o detalhe do lead |

---

## Progresso e persistência

- Barra de progresso no topo: "X de Y ações concluídas hoje"
- Badge vermelho na aba "Hoje" mostra ações pendentes
- Estado do dia (concluídos/pulados) salvo em `localStorage` com a data — sobrevive a recarregamentos
- Botão **🔄 Atualizar** invalida o cache e força nova análise da IA

---

## Cache

| Chave | Conteúdo | Expiração |
|---|---|---|
| `briefing_cache_YYYY-MM-DD` | Dados retornados pela API | Automático no dia seguinte |
| `briefing_estado_YYYY-MM-DD` | Itens concluídos/pulados | Automático no dia seguinte |

---

## Fallback (IA indisponível)

Se a chamada à IA falhar, o briefing é gerado por regras locais usando apenas: dias sem contato + score + data do próximo contato. Os cards aparecem sem rascunho de mensagem. Nenhuma mensagem de erro técnico é exibida ao usuário.

---

## Input enviado à IA (por lead)

```json
{
  "lead_id": 1,
  "nome": "João Silva",
  "empresa": "Empresa ABC",
  "etapa": "proposta_enviada",
  "score": "morno",
  "valor_proposto": 1200.0,
  "dias_sem_contato": 7,
  "proximo_contato_em": null,
  "historico": [
    { "tipo": "email", "dias_atras": 7, "resumo": "Proposta enviada" },
    { "tipo": "whatsapp", "dias_atras": 10, "resumo": "Interesse confirmado" }
  ]
}
```

## Output retornado pela IA (por lead)

```json
{
  "prioridade": "urgente",
  "tipo_acao": "mensagem_whatsapp",
  "rascunho": "Oi João! Tudo bem? Passei para saber se você teve chance de analisar a proposta...",
  "motivo": "7 dias sem resposta após proposta enviada. Score morno sugere interesse ainda ativo.",
  "etapa_sugerida": null,
  "confianca": 0.87
}
```

---

## Endpoints reutilizados (sem modificação)

- `POST /tenant/comercial/leads/{id}/whatsapp`
- `POST /tenant/comercial/leads/{id}/email`
- `PUT /tenant/comercial/leads/{id}` (para mover etapa via `status_pipeline`)
