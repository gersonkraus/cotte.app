# Briefing Diário de IA — Módulo Comercial

**Data:** 2026-04-28  
**Status:** Aprovado para implementação

---

## Contexto

O módulo comercial do COTTE é operado por uma única pessoa (operação solo) que faz prospecção ativa e mantém menos de 20 leads ativos ao mesmo tempo. O maior problema hoje é a fadiga de decisão: o operador precisa navegar entre abas, lembrar quem contatar, escrever mensagens do zero e decidir quando mover etapas — tudo manualmente.

A IA já existe no backend (`ia_service.py`, `cotte_ai_hub.py`) mas está usada apenas na importação de leads. Este design expande o uso de IA para o dia a dia do processo comercial.

---

## Solução: Aba "Hoje" com Briefing Gerado por IA

Uma nova aba **"Hoje"** (primeira posição, antes do Dashboard) que a IA popula com os leads que precisam de ação naquele dia — priorizados, com rascunho de mensagem pronto e ações em um clique.

**Objetivo:** o operador abre o comercial, executa o briefing em 10 minutos, fecha.

---

## Arquitetura

### Fluxo

1. Frontend abre → dispara `GET /tenant/comercial/briefing`
2. Backend busca todos os leads ativos da empresa
3. Para cada lead, monta contexto resumido e envia à IA — uma chamada por lead, executadas concorrentemente com `asyncio.gather` (máximo 20 leads = máximo 20 chamadas paralelas)
4. IA retorna por lead: prioridade + tipo de ação + rascunho de mensagem + motivo
5. Resultado é cacheado no `localStorage` com a data (`briefing_cache_YYYY-MM-DD`)
6. Expiração automática à meia-noite; botão "🔄 Atualizar" força nova geração
7. Ações (enviar WPP, enviar email, mover etapa) reutilizam endpoints existentes

### Componentes

| Componente | Tipo | Arquivo |
|---|---|---|
| `GET /tenant/comercial/briefing` | Endpoint novo | `app/routers/tenant/comercial_leads.py` (adicionar ao arquivo existente) |
| `gerar_briefing_lead()` | Função nova | `app/services/ia_service.py` |
| Aba "Hoje" + cards | HTML novo | `sistema/cotte-frontend/tenant-comercial.html` |
| Lógica de briefing | JS novo | `tenant-comercial-briefing.js` |

### Endpoints reutilizados (sem modificação)

- `POST /tenant/comercial/leads/{id}/whatsapp`
- `POST /tenant/comercial/leads/{id}/email`
- `PATCH /tenant/comercial/leads/{id}/status`

---

## Dados

### Input por lead (enviado à IA)

```json
{
  "nome": "João Silva",
  "empresa": "Empresa ABC",
  "etapa": "proposta_enviada",
  "score": "morno",
  "valor_proposto": 1200.00,
  "dias_sem_contato": 7,
  "proximo_contato_em": null,
  "historico": [
    { "tipo": "email", "dias_atras": 7, "resumo": "Proposta enviada" },
    { "tipo": "whatsapp", "dias_atras": 10, "resumo": "Interesse confirmado" }
  ]
}
```

Sem histórico completo de mensagens — apenas tipo, data e resumo das últimas 3 interações. Reduz tokens e protege privacidade.

### Output por lead (retornado pela IA)

```json
{
  "prioridade": "urgente",
  "tipo_acao": "mensagem_whatsapp",
  "rascunho": "Oi João! Tudo bem? Passei para saber se...",
  "motivo": "7 dias sem resposta após proposta enviada. Score morno sugere interesse ainda ativo.",
  "etapa_sugerida": null,
  "confianca": 0.87
}
```

### Valores possíveis

- `prioridade`: `urgente` | `hoje` | `esta_semana` | `ok`
- `tipo_acao`: `mensagem_whatsapp` | `mensagem_email` | `mover_etapa` | `nenhuma`
- `confianca < 0.5` → lead não aparece no briefing

---

## Regras de Priorização

| Prioridade | Condição |
|---|---|
| 🔴 Urgente | +5 dias sem contato em `proposta_enviada`; OU +3 dias com score quente; OU `proximo_contato_em` vencido |
| 🟡 Hoje | `proximo_contato_em` = hoje; OU +7 dias sem contato com score morno; OU última interação foi resposta do cliente |
| 🟢 Mover etapa | Última interação = cliente respondeu e etapa atual não reflete o momento. `etapa_sugerida` contém a etapa recomendada (ex: `"proposta_enviada"`). |
| ⚪ Ok (não aparece) | Contato recente (<2 dias); OU score frio em etapa inicial; OU confianca < 0.5 |

---

## Interface

### Aba "Hoje"

- Primeira posição no tab bar, antes de "Dashboard"
- Badge vermelho com contagem de ações pendentes
- Header com: data, quantidade de leads analisados, hora de geração, botão "🔄 Atualizar"
- Barra de progresso: "X de Y ações concluídas hoje"

### Cards de Ação

Três tipos visuais:

| Tipo | Cor borda | Conteúdo |
|---|---|---|
| Urgente | Vermelho | Badge, nome/empresa, score/etapa/valor, rascunho de mensagem, botões |
| Hoje | Âmbar | Idem |
| Mover Etapa | Verde | Badge, nome/empresa, explicação da IA, botão confirmar |

Cada card tem três ações:
- **✓ Enviar / Confirmar** — executa a ação imediatamente
- **✎ Editar** — abre textarea com rascunho editável antes de enviar
- **✗ Pular** — remove do briefing do dia; reaparece amanhã se sem contato

Itens concluídos ficam visíveis ao final da lista com estilo esmaecido.

---

## Error Handling

**Se a IA falhar:**
- Briefing gerado com regras locais (dias sem contato + score) sem rascunho de mensagem
- Botão "✎ Escrever mensagem" substitui o rascunho
- Nenhuma mensagem de erro técnico visível ao usuário

**Se não há ações:**
- Tela vazia: "✅ Tudo em dia! Nenhum lead precisa de atenção hoje."

**Cache:**
- Estado do dia (concluídos/pulados) salvo no `localStorage` com a data
- Recarregar a página preserva o progresso
- "🔄 Atualizar" invalida o cache e gera novo briefing

---

## Fora do Escopo

- Notificação push ou WhatsApp automático ao operador
- Análise de sentimento das respostas recebidas
- Briefing por email (só in-app)
- Multi-usuário

---

## Verificação (Como Testar)

**Backend:**
1. `GET /tenant/comercial/briefing` com leads em diferentes cenários → resposta ordenada, rascunhos presentes
2. Simular falha da IA → fallback com regras locais, sem rascunho, sem erro 500

**Frontend:**
1. Aba "Hoje" aparece primeira com badge correto
2. "✓ Enviar" → mensagem enviada via endpoint existente, card vira concluído
3. "✎ Editar" → textarea com rascunho, envio após edição
4. "✗ Pular" → card some, não reaparece no dia
5. Recarregar → estado preservado via localStorage
6. "🔄 Atualizar" → nova chamada à IA

**Smoke test:**
Criar 3 leads (1 urgente: 7 dias sem contato em proposta, 1 hoje: follow-up agendado, 1 recente: contato ontem) → abrir briefing → verificar ordem e prioridades.
