# Design: WhatsApp Interativo com Listas (Evolution API 2.4.0-rc1)

**Data:** 2026-05-07
**Status:** Aprovado para implementação

## Contexto

A Evolution API foi atualizada para 2.4.0-rc1, tornando as mensagens interativas de lista (`sendList`) funcionais. O objetivo é criar fluxos guiados de orçamento via WhatsApp para dois públicos:

- **Operador/vendedor:** monta orçamentos pelo WhatsApp sem precisar abrir o dashboard
- **Cliente final:** aprova, escolhe forma de pagamento e solicita desconto diretamente pelo WhatsApp

## Abordagem: Híbrida (Stateless + Sessão Leve)

**Stateless (cliente):** o `rowId` de cada item de lista codifica `ação:orcamento_id`. Sem estado no servidor — bot decodifica e age imediatamente.

**Session-based (operador):** tabela `sessao_whatsapp` rastreia o wizard multi-passo. Sessão expira em 15 min.

## Arquitetura

```
Dashboard
    └── [Botão "Enviar menu interativo"]
              │
              ▼
    POST /whatsapp/enviar-menu-orcamento/{id}
              │
              ▼
    whatsapp_interativo_service
    ├── enviar_menu_orcamento_cliente()  → operador_interacao_service.enviar_lista_selecao()
    └── (aguarda resposta do cliente)

WhatsApp Webhook (Evolution API)
    └── POST /whatsapp/webhook
              │
              ├── tipo == "listResponseMessage"?
              │         ├── sessao ativa? → processar_resposta_operador()
              │         └── sem sessão?  → processar_resposta_cliente()
              │
              └── tipo == texto → fluxo bot existente (sem mudança)
```

## Fluxo do Cliente (Stateless)

```
Operador clica "Enviar menu interativo" no modal do orçamento
    ↓
Bot envia lista ao cliente:
  ┌────────────────────────────────────────┐
  │ Orçamento ORC-123 — R$ 1.200,00        │
  │  → Aprovar orçamento    rowId: aprovar:123 │
  │  → Recusar orçamento    rowId: recusar:123 │
  │  → Pedir desconto       rowId: desconto:123│
  └────────────────────────────────────────┘
    ↓ Cliente seleciona "Aprovar"
Bot envia lista de formas de pagamento:
  ┌────────────────────────────────────────┐
  │ Como prefere pagar?                    │
  │  → Pix                  rowId: pix:123     │
  │  → Cartão de crédito    rowId: cartao:123  │
  │  → Boleto               rowId: boleto:123  │
  └────────────────────────────────────────┘
    ↓ Cliente seleciona "Pix"
Bot executa aprovação via handle_quote_status_changed()
Operador recebe notificação (fluxo existente preservado)
```

## Fluxo do Operador via WhatsApp (Session-based)

```
Operador envia "novo orçamento" ao número da empresa
    ↓
Bot detecta operador → cria sessão (etapa: selecionando_cliente)
Bot envia lista com últimos 5 clientes
    ↓
Operador seleciona cliente
Sessão: etapa = selecionando_categoria, contexto = {cliente_id: X}
Bot envia lista de categorias do catálogo
    ↓
Operador seleciona categoria
Sessão: etapa = selecionando_item
Bot envia lista de itens da categoria com preços
    ↓
Operador seleciona item → adicionado ao rascunho
Bot: [Adicionar mais itens] [Finalizar orçamento]
    ↓ Finalizar
Bot chama criar_orcamento_core() → ORC-456 criado
Bot: [Enviar ao cliente agora] [Deixar como rascunho]
```

## Modelo de Dados

### Nova tabela: `sessao_whatsapp`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | — |
| `telefone` | VARCHAR(20) UNIQUE | Telefone do operador |
| `empresa_id` | FK → empresa | Multi-tenant |
| `etapa` | VARCHAR(50) | Estado atual do wizard |
| `contexto` | JSONB | Dados do rascunho em andamento |
| `expira_em` | TIMESTAMP | NOW() + 15 min |
| `atualizado_em` | TIMESTAMP | Auto-update |

**Etapas válidas:**
- `selecionando_cliente`
- `selecionando_categoria`
- `selecionando_item`
- `confirmando_orcamento`

### rowId Format (cliente, stateless)

| rowId | Ação |
|---|---|
| `aprovar:{id}` | Aprovar orçamento |
| `recusar:{id}` | Recusar orçamento |
| `desconto:{id}` | Solicitar desconto |
| `pix:{id}` | Selecionar Pix como pagamento |
| `cartao:{id}` | Selecionar cartão |
| `boleto:{id}` | Selecionar boleto |

## Componentes Criados/Modificados

| Componente | Tipo | Descrição |
|---|---|---|
| `app/services/whatsapp_interativo_service.py` | **NOVO** | Núcleo da lógica interativa |
| `alembic/versions/xxxx_sessao_whatsapp.py` | **NOVO** | Migration da nova tabela |
| `app/models/models.py` | **MODIFICAR** | Adicionar `SessaoWhatsapp` |
| `app/routers/whatsapp.py` | **MODIFICAR** | Novo endpoint + roteador no webhook |
| `app/services/whatsapp_bot_service.py` | **MODIFICAR** | Handler listResponse + intenção "novo orçamento" |
| `cotte-frontend/js/orcamento-detalhes.js` | **MODIFICAR** | Botão "Enviar menu interativo" |

## Reutilização de Código Existente

- `operador_interacao_service.enviar_lista_selecao()` — envia as listas interativas
- `orcamento_core_service.criar_orcamento_core()` — cria orçamento no final do wizard
- `quote_notification_service.handle_quote_status_changed()` — executa aprovação com idempotência
- `whatsapp_sanitizer.sanitizar_telefone()` — valida telefone do webhook
- `whatsapp_service.enviar_mensagem_texto()` — mensagens de confirmação/erro

## Decisões Chave

- **Sem quebra de compatibilidade:** mensagens de texto continuam pelo bot existente
- **Aprovação mantém idempotência:** passa por `handle_quote_status_changed()`, nunca diretamente
- **Cliente não seleciona serviços:** apenas aprova/recusa/paga
- **Sessão expira em 15 min:** evita estado zumbi sem cleanup assíncrono
- **rowId simples (`acao:id`):** decodificável com `split(":", 1)` sem regex
