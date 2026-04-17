---
title: Assistente Ia
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Tec Assistente
tags:
  - tecnico
  - mapa
  - tecnico
prioridade: media
status: documentado
---
# Mapa Técnico Completo — Assistente IA (COTTE)

> Rastreamento ponta a ponta da funcionalidade `assistente-ia.html`.
> Mapeado em 23/03/2026. Todos os caminhos são relativos a `sistema/`.

---

## 1. Entrada do Fluxo

O fluxo começa em **`cotte-frontend/assistente-ia.html`** (linha 710), que carrega `js/assistente-ia.js`. O usuário digita uma mensagem ou clica num atalho rápido (ex: "Quanto tenho em caixa hoje?"). O JavaScript chama `sendMessage()` que faz `api.post('/ai/assistente', {mensagem, sessao_id})`.

A URL real montada pelo `api.js` é: `{API_URL}/api/v1/ai/assistente`

---

## 2. Caminho Completo dos Arquivos

### Frontend (Vanilla JS)

| Arquivo | Função | Linha |
|---|---|---|
| `cotte-frontend/assistente-ia.html` | HTML da página, botões de atalho | L646-L673 |
| `cotte-frontend/js/assistente-ia.js` | `sendMessage()` | L112 |
| `cotte-frontend/js/assistente-ia.js` | `processAIResponse()` | L178 |
| `cotte-frontend/js/assistente-ia.js` | `formatAIResponse()` | L253 |
| `cotte-frontend/js/assistente-ia.js` | `confirmarOrcamento()` | L513 |
| `cotte-frontend/js/assistente-ia.js` | `enviarFeedback()` | L629 |
| `cotte-frontend/js/assistente-ia.js` | `enviarPorWhatsapp()` | L668 |
| `cotte-frontend/js/assistente-ia.js` | `enviarPorEmail()` | L696 |
| `cotte-frontend/js/api.js` | `api.post()` → `apiRequest()` | L109, L43 |

### Backend — Router

| Arquivo | Função | Linha |
|---|---|---|
| `app/routers/ai_hub.py` | `assistente_universal()` — `POST /ai/assistente` | L534 |
| `app/routers/ai_hub.py` | `confirmar_orcamento_ia()` — `POST /ai/orcamento/confirmar` | L167 |
| `app/routers/ai_hub.py` | `registrar_feedback()` — `POST /ai/feedback` | L581 |
| `app/routers/ai_hub.py` | `listar_feedbacks()` — `GET /ai/feedbacks` | L604 |
| `app/routers/ai_hub.py` | `AIAssistenteRequest` (schema inline) | L73 |
| `app/routers/ai_hub.py` | `AIFeedbackRequest` (schema inline) | L572 |
| `app/routers/ai_hub.py` | `AIConfirmarOrcamentoRequest` (schema inline) | L85 |

### Backend — Services

| Arquivo | Classe/Função | Linha |
|---|---|---|
| `app/services/cotte_ai_hub.py` | `assistente_unificado()` — **função central** | L1478 |
| `app/services/cotte_ai_hub.py` | `criar_orcamento_ia()` | L1002 |
| `app/services/cotte_ai_hub.py` | `executar_comando_operador_ia()` | L1090 |
| `app/services/cotte_ai_hub.py` | `CotteAIHub.processar()` — pipeline Anti-Delírios | L767 |
| `app/services/cotte_ai_hub.py` | `AIResponse` (Pydantic model) | L57 |
| `app/services/cotte_ai_hub.py` | `AntiDeliriumSystem` | L316 |
| `app/services/cotte_ai_hub.py` | `FallbackManual` | L635 |
| `app/services/cotte_ai_hub.py` | `SimpleCache` | L85 |
| `app/services/cotte_ai_hub.py` | `SYSTEM_PROMPT_ASSISTENTE` | L972 |
| `app/services/cotte_ai_hub.py` | `_buscar_dados_financeiros()` | L1746 |
| `app/services/ai_intention_classifier.py` | `IntentionClassifier.classificar()` | L70 |
| `app/services/ai_intention_classifier.py` | `detectar_intencao_assistente_async()` | L695 |
| `app/services/ai_intention_classifier.py` | `saldo_rapido_ia()` | L711 |
| `app/services/ai_intention_classifier.py` | `IntencaoUsuario` (Enum, 15 intenções) | L33 |
| `app/services/cotte_context_builder.py` | `SessionStore` — histórico em memória | L34 |
| `app/services/cotte_context_builder.py` | `ContextBuilder.build()` — roteador de contexto | L117 |
| `app/services/cotte_context_builder.py` | `_ctx_financeiro()` | L173 |
| `app/services/cotte_context_builder.py` | `_ctx_orcamentos()` | L220 |
| `app/services/cotte_context_builder.py` | `_ctx_clientes()` | L319 |
| `app/services/cotte_context_builder.py` | `_ctx_leads()` | L350 |
| `app/services/cotte_context_builder.py` | `_ctx_empresa_usuario()` | L155 |
| `app/services/ai_json_extractor.py` | `AIJSONExtractor.extract()` | L27 |
| `app/services/ai_prompt_loader.py` | `AIPromptLoader.get_dict()` | L34 |
| `app/services/onboarding_service.py` | `get_onboarding_status()` | L1 |
| `app/services/onboarding_service.py` | `formatar_resposta_onboarding()` | L1 |
| `app/services/ia_service.py` | `interpretar_comando_operador()` (legacy) | L97 |

### Backend — Models/Schemas

| Arquivo | Classe | Linha |
|---|---|---|
| `app/models/models.py` | `FeedbackAssistente` | L1489 |
| `app/models/models.py` | `OrigemRegistro.ASSISTENTE_IA` | L120 |
| `app/models/models.py` | `Orcamento` | — |
| `app/models/models.py` | `Cliente` | — |
| `app/models/models.py` | `ContaFinanceira` | — |
| `app/models/models.py` | `SaldoCaixaConfig` | — |
| `app/models/models.py` | `CommercialLead` | — |
| `app/schemas/schemas.py` | `IAInterpretacaoOut` | L489 |
| `app/schemas/schemas.py` | `IAInterpretacaoRequest` | L485 |
| `app/schemas/schemas.py` | `OrcamentoCreate` | — |
| `app/schemas/schemas.py` | `ItemOrcamentoCreate` | — |

### Cross-cutting (outros routers que reutilizam)

| Arquivo | Função | Linha |
|---|---|---|
| `app/routers/whatsapp.py` | `_processar_assistente_gestor()` | L469 |
| `app/routers/orcamentos.py` | Chamadas a funções do AI hub | L748 |

### App Init

| Arquivo | Ponto | Linha |
|---|---|---|
| `app/main.py` | `from app.routers.ai_hub import router as ai_hub_router` | L49 |
| `app/main.py` | Router registrado em prefixo `/api/v1` | L156 |

---

## 3. Sequência de Chamadas

### Fluxo Principal: Pergunta genérica (ex: "Quanto tenho em caixa hoje?")

```
FRONTEND                                              BACKEND
──────────────────────────────────────               ──────────────────────────────────────────────
assistente-ia.html
  └─ <button onclick="sendQuickMessage('...')">
      assistente-ia.js:sendQuickMessage()
        └─ sendMessage()
            ├─ Gera sessaoId (crypto.randomUUID)
            ├─ api.post('/ai/assistente', {mensagem, sessao_id})
            │                                                   └─ ai_hub.py:assistente_universal()
            │                                                       ├─ exigir_permissao("ia", "leitura")  ← AUTH
            │                                                       ├─ empresa.total_mensagens_ia++       ← CONTADOR
            │                                                       └─ assistente_unificado(...)
            │                                                           │
            │                                                           ├─ [1] SessionStore.get_or_create(sessao_id)
            │                                                           │     └─ Retorna histórico em memória
            │                                                           │
            │                                                           ├─ [2] detectar_intencao_assistente_async(mensagem)
            │                                                           │     └─ IntentionClassifier.classificar()
            │                                                           │         ├─ _classificar_regex()
            │                                                           │         └─ fallback CONVERSACAO (sem LLM no classificador)
            │                                                           │
            │                                                           ├─ [3] Checagem permissão financeira
            │                                                           │
            │                                                           ├─ [4] Roteamento por intenção (if/elif)
            │                                                           │     └─ Ver fluxos alternativos abaixo
            │                                                           │
            │                                                           ├─ [5] ContextBuilder.build(intencao, db, empresa_id)
            │                                                           │     └─ Busca dados reais do banco
            │                                                           │
            │                                                           ├─ [6] LLM via LiteLLM (`AI_MODEL` / normalização em `ia_service`, ~800 tokens)
            │                                                           │     └─ SYSTEM_PROMPT_ASSISTENTE + messages
            │                                                           │
            │                                                           ├─ [7] AIJSONExtractor.extract(raw)
            │                                                           ├─ [8] SessionStore.append() — persiste turno
            │                                                           └─ [9] Filtra sugestões repetidas
            │
            ├─ processAIResponse(data, loadingMessage)
            │   └─ formatAIResponse(data)
            │       └─ Renderiza card específico por tipo_resposta
            │
            └─ addMessage(html, false)
```

### Fluxo Alternativo A: SALDO_RAPIDO (sem LLM)

```
assistente_unificado()
  ├─ IntentionClassifier → SALDO_RAPIDO (regex match)
  └─ saldo_rapido_ia(db, empresa_id)  ← NÃO PASSA PELO LLM
      ├─ SaldoCaixaConfig → saldo_inicial
      ├─ financeiro_service.calcular_saldo_caixa_kpi()
      └─ AIResponse(tipo_resposta="saldo_caixa", dados={saldo_atual, saldo_inicial})
```

### Fluxo Alternativo B: CRIAR_ORCAMENTO

```
assistente_unificado()
  ├─ IntentionClassifier → CRIAR_ORCAMENTO
  └─ criar_orcamento_ia(mensagem, db, empresa_id, usuario_id)
      ├─ ai_hub.processar("orcamentos", mensagem)  ← USA LLM (LiteLLM; modelo em config)
      │     ├─ AntiDelirium.camada_1_sanitizar_entrada()
      │     ├─ LLM (prompt "orcamentos") → extrai JSON
      │     ├─ AIJSONExtractor.extract(raw)
      │     ├─ camada_2_validar_schema()
      │     ├─ camada_3_validar_dominio()
      │     ├─ camada_4_verificar_consistencia(db)
      │     └─ AIResponse(dados={cliente_nome, servico, valor, desconto, ...})
      ├─ Cliente.query(ilike(nome)) → match ou sugestões
      └─ AIResponse(tipo_resposta="orcamento_preview")

  [Frontend]
  └─ formatAIResponse() → renderiza .orc-preview-card
      └─ Usuário clica "Confirmar e Criar"
          └─ confirmarOrcamento()
              └─ api.post('/ai/orcamento/confirmar', body)
                  └─ confirmar_orcamento_ia()
                      ├─ Resolve/cria Cliente
                      ├─ OrcamentoCreate + ItemOrcamentoCreate
                      └─ _criar_orcamento() (reutiliza router de orçamentos)
                          └─ AIResponse(tipo_resposta="orcamento_criado")
```

### Fluxo Alternativo C: OPERADOR (ver, aprovar, recusar, desconto)

```
assistente_unificado()
  ├─ IntentionClassifier → OPERADOR
  └─ executar_comando_operador_ia(mensagem, db, empresa_id, usuario_id)
      ├─ interpretar_comando_operador(mensagem)  ← ia_service.py (LiteLLM; modelo técnico / fallback conforme `.env`)
      │     └─ Retorna {acao: "VER", orcamento_id: 5}
      ├─ Orcamento.query(like("ORC-5-%")) ou query(id=5)
      └─ Match por ação:
          VER → AIResponse(dados={itens, total, status, ...})
          APROVAR → Orcamento.status = APROVADO + notificação
          RECUSAR → Orcamento.status = RECUSADO
          DESCONTO → Atualiza Orcamento.desconto
          ADICIONAR → Novo ItemOrcamento
          REMOVER → Remove ItemOrcamento
```

### Fluxo Alternativo D: ONBOARDING (sem LLM)

```
assistente_unificado()
  ├─ IntentionClassifier → ONBOARDING (ou CONVERSACAO com progresso < 60%)
  └─ get_onboarding_status(db, empresa_id)
      ├─ Verifica 5 etapas: empresa_configurada, servico_cadastrado,
      │   cliente_cadastrado, orcamento_criado, orcamento_enviado
      └─ AIResponse(tipo_resposta="onboarding", dados={progresso_pct, checklist, ...})
```

### Fluxo WhatsApp (mesma função central)

```
WhatsApp message → whatsapp.py: _processar_assistente_gestor()
  └─ assistente_unificado(sessao_id=f"wpp_{telefone}", ...)
      └─ Mesmo pipeline do chat web
          └─ Retorna ai_resp.resposta como texto puro (sem cards/botões)
```

---

## 4. Estruturas de Dados Envolvidas

### Requisição Principal (Frontend → Backend)

```json
// POST /api/v1/ai/assistente
// Schema: AIAssistenteRequest (ai_hub.py:73)
{
  "mensagem": "Quanto tenho em caixa hoje?",
  "sessao_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Resposta Padrão (Backend → Frontend)

```json
// Schema: AIResponse (cotte_ai_hub.py:57)
{
  "sucesso": true,
  "dados": {
    "tipo": "saldo_caixa",
    "saldo_atual": 45230.75,
    "saldo_inicial": 10000.0
  },
  "resposta": "Seu caixa atual é R$ 45.230,75...",
  "tipo_resposta": "saldo_caixa",
  "acao_sugerida": null,
  "confianca": 0.98,
  "erros": [],
  "fallback_utilizado": false,
  "cache_hit": false,
  "modulo_origem": "financeiro_saldo"
}
```

### Tipos de Resposta (tipo_resposta)

| tipo_resposta | Renderização no Frontend | Origem |
|---|---|---|
| `saldo_caixa` | `.saldo-rapido-resposta` card | `saldo_rapido_ia()` |
| `orcamento_preview` | `.orc-preview-card` com botões | `criar_orcamento_ia()` |
| `orcamento_criado` | `.orc-success-card` | `confirmar_orcamento_ia()` |
| `operador_resultado` | `.opr-card` ou `.opr-result` | `executar_comando_operador_ia()` |
| `onboarding` | Checklist com progresso | `onboarding_service` |
| `sem_permissao` | Mensagem de erro | `assistente_unificado()` |
| `erro` | Mensagem de erro | Múltiplas origens |
| Qualquer outro | Resposta textual direta | LLM principal (`AI_MODEL` via LiteLLM) |

### Sessão em Memória (Python dict)

```python
# cotte_context_builder.py:21
_sessions[sessao_id] = {
    "messages": deque(maxlen=6),           # [{role: "user"|"assistant", content: str}]
    "seen_suggestions": deque(maxlen=50),  # [str, ...] normalizados em lowercase
    "last_seen": datetime.utcnow()         # para TTL de 60 minutos
}
```

### Feedback (Model → Tabela)

```python
# FeedbackAssistente (models.py:1489) → tabela feedback_assistente
{
    id: int (PK),
    empresa_id: int (FK → empresas.id),
    sessao_id: str(64),
    pergunta: Text,
    resposta: Text,
    avaliacao: str(10),         # "positivo" | "negativo"
    comentario: Text | None,
    modulo_origem: str(50) | None,
    criado_em: DateTime (server_default=now)
}
```

### Requisição de Confirmação de Orçamento

```json
// POST /api/v1/ai/orcamento/confirmar
// Schema: AIConfirmarOrcamentoRequest (ai_hub.py:85)
{
  "cliente_id": 42,
  "cliente_nome": "João Silva",
  "servico": "Pintura residencial",
  "valor": 800.0,
  "desconto": 10,
  "desconto_tipo": "percentual",
  "observacoes": "Inclui tinta e mão de obra"
}
```

### Requisição de Feedback

```json
// POST /api/v1/ai/feedback
// Schema: AIFeedbackRequest (ai_hub.py:572)
{
  "sessao_id": "550e8400-...",
  "pergunta": "Quanto tenho em caixa?",
  "resposta": "Seu caixa atual é R$ 45.230,75...",
  "avaliacao": "positivo",
  "comentario": null,
  "modulo_origem": "financeiro_saldo"
}
```

---

## 5. Regras de Negócio Encontradas

| # | Regra | Localização | Descrição |
|---|---|---|---|
| 1 | **RBAC por recurso "ia"** | `ai_hub.py:538` | `exigir_permissao("ia", "leitura")` em todos os endpoints AI |
| 2 | **RBAC financeiro** | `cotte_ai_hub.py:1510-1522` | Intenções financeiras bloqueadas se `permissoes.financeiro` ausente e não é gestor |
| 3 | **Contador de mensagens IA** | `ai_hub.py:552-556` | Incrementa `empresa.total_mensagens_ia` a cada mensagem |
| 4 | **Anti-Delírios (4 camadas)** | `cotte_ai_hub.py:316-634` | Sanitização → Schema → Domínio → Consistência DB |
| 5 | **Roteamento sem LLM** | `cotte_ai_hub.py:1524-1553` | SALDO_RAPIDO, ONBOARDING não passam pelo LLM |
| 6 | **Fallback regex** | `cotte_ai_hub.py:635-724` | Se o LLM falha, `FallbackManual` extrai dados por regex |
| 7 | **Cache TTL 5min** | `cotte_ai_hub.py:85-116` | Respostas com confiança ≥ 0.7 são cacheadas (módulos antigos) |
| 8 | **Histórico de sessão** | `cotte_context_builder.py:21-23` | Máximo 6 mensagens, TTL 60min, em memória |
| 9 | **Filtro de sugestões repetidas** | `cotte_context_builder.py:73-78` | Sugestões já vistas são filtradas |
| 10 | **Onboarding interrompe conversação** | `cotte_ai_hub.py:1564-1583` | Se onboarding < 60%, CONVERSACAO vira ONBOARDING |
| 11 | **Permissão UI no frontend** | `assistente-ia.html:699-708` | `Permissoes.pode('ia')` bloqueia a tela |
| 12 | **Confirmação de orçamento em 2 etapas** | `assistente-ia.js:513-550` | Preview → seleção de cliente → confirmação |
| 13 | **Busca de cliente por ILIKE** | `cotte_ai_hub.py:1030-1049` | Match exato primeiro, depois sugestões por primeiro nome |
| 14 | **Resolução de orçamento por número** | `cotte_ai_hub.py:1136-1157` | Prioriza `ORC-{id}-%`, fallback por `id` numérico |
| 15 | **Limites anti-delírios** | `cotte_ai_hub.py:320-387` | Valor máx orçamento R$ 500k, financeiro R$ 1M, nome 2-100 chars |

---

## 6. Problemas de Arquitetura

### 🔴 Críticos

| # | Problema | Localização | Impacto |
|---|---|---|---|
| 1 | **Sessões em memória** | `cotte_context_builder.py:21` | Restart do servidor perde todo histórico. Múltiplos workers (gunicorn) não compartilham sessão. |
| 2 | **Schemas inline no router** | `ai_hub.py:73,85,572` | `AIAssistenteRequest`, `AIConfirmarOrcamentoRequest`, `AIFeedbackRequest` definidos no router em vez de `app/schemas/`. |
| 3 | **Duplicação `mockAIResponse`** | `assistente-ia.js:555` e `api.js:639` | Duas implementações similares mas não idênticas. |
| 4 | **Acoplamento entre routers** | `ai_hub.py:180` | `confirmar_orcamento_ia` importa `_criar_orcamento` de `orcamentos.py` diretamente. |
| 5 | **Serviço legacy ainda ativo** | `cotte_ai_hub.py:1106` | `executar_comando_operador_ia` chama `ia_service.py:interpretar_comando_operador`. Dupla camada de IA (roteamento + interpretação). |

### 🟡 Médios

| # | Problema | Localização | Impacto |
|---|---|---|---|
| 6 | **`AIResponse` em service, não em schemas** | `cotte_ai_hub.py:57` | Router importa Pydantic model do service. |
| 7 | **Contador sem transação protegida** | `ai_hub.py:552-556` | `db.commit()` sem try/except. Falha não tratada. |
| 8 | **Anti-Delírios bypassado no assistente_unificado** | `cotte_ai_hub.py:~1776` | O fluxo principal chama `ia_service.chat()` (LiteLLM) sem passar pelas 4 camadas de validação do `processar()`. Anti-Delírios só é usado em `ai_hub.processar()` (ex.: `criar_orcamento_ia`). |
| 9 | **XSS em sugestões** | `assistente-ia.js:202` | Texto da sugestão interpolado em HTML sem `escapeHtml()`. |
| 10 | **Sem testes** | `tests/` | Apenas `test_saldo_caixa_unificado.py` testa roteamento. Sem testes para `assistente_unificado`, `criar_orcamento_ia`, `IntentionClassifier`. |

### 🟢 Menores

| # | Problema | Localização | Impacto |
|---|---|---|---|
| 11 | **Ícones de sugestão hardcoded no JS** | `assistente-ia.js:17-30` | Backend gera sugestões, frontend mapeia ícones. Sem garantia de alinhamento. |
| 12 | **`formatValue` vs `formatarMoeda`** | `assistente-ia.js:499` e `api.js:567` | Funções equivalentes com nomes diferentes. |
| 13 | **sessao_id gerado no cliente** | `assistente-ia.js:143` | Fallback `Math.random()` não garante unicidade. |

---

## 7. Melhor Ponto para Alterar com Segurança

### Para mudar comportamento geral do chat

| Alvo | Arquivo | Linha | Observação |
|---|---|---|---|
| Orquestração | `app/services/cotte_ai_hub.py` | L1478 (`assistente_unificado`) | Ponto único. Afeta web + WhatsApp. |
| System prompt | `app/services/cotte_ai_hub.py` | L972 (`SYSTEM_PROMPT_ASSISTENTE`) | Altera comportamento geral do assistente (LLM configurável). |
| Roteamento | `app/services/cotte_ai_hub.py` | L1524-1583 | Adicionar/remover intenções especiais. |

### Para adicionar nova intenção (checklist)

1. Adicionar ao enum `IntencaoUsuario` em `app/services/ai_intention_classifier.py:33`
2. Adicionar padrões regex no `IntentionClassifier`
3. Adicionar handler de contexto no `ContextBuilder._INTENT_MAP` (`cotte_context_builder.py:102`)
4. Adicionar roteamento no `assistente_unificado()` (`cotte_ai_hub.py:1524`)
5. Adicionar renderização no `formatAIResponse()` (`assistente-ia.js:253`)
6. Adicionar botão de atalho no HTML (`assistente-ia.html:646`)

### Para alterar criação de orçamento via IA

| Alvo | Arquivo | Linha | Risco |
|---|---|---|---|
| Extração de dados | `cotte_ai_hub.py` | L1002 (`criar_orcamento_ia`) | Médio — alterar schema de resposta exige sync com frontend |
| Confirmação | `cotte_ai_hub.py` | L167 (`confirmar_orcamento_ia`) | Alto — reutiliza `_criar_orcamento` do router de orçamentos |
| Renderização preview | `assistente-ia.js` | L262 (`formatAIResponse`) | Médio — JSON embutido em `<script>` no card |

### Para alterar validações/permissões

| Alvo | Arquivo | Linha |
|---|---|---|
| Auth do endpoint | `app/routers/ai_hub.py` | L538 (`exigir_permissao`) |
| Permissão financeira | `app/services/cotte_ai_hub.py` | L1510 |
| Permissão UI | `cotte-frontend/assistente-ia.html` | L699 |
| Anti-Delírios | `app/services/cotte_ai_hub.py` | L316 |

---

## 8. Resumo Visual do Fluxo

```
┌─────────────────────────────────────────────────────────────┐
│                    assistente-ia.html                        │
│  [Atalhos rápidos] [Input de mensagem] [Chat messages]      │
└─────────────────────────┬───────────────────────────────────┘
                          │ api.post('/ai/assistente', {mensagem, sessao_id})
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              ai_hub.py: assistente_universal()               │
│  • exigir_permissao("ia", "leitura")                         │
│  • empresa.total_mensagens_ia++                              │
│  • → assistente_unificado()                                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│        cotte_ai_hub.py: assistente_unificado()               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [1] SessionStore.get_or_create() — histórico memória  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [2] IntentionClassifier.classificar()                 │   │
│  │     ├─ Regex → retorna intenção quando há match         │   │
│  │     └─ Senão CONVERSACAO (fallback; sem LLM aqui)      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [3] Roteamento por intenção:                          │   │
│  │     SALDO_RAPIDO → saldo_rapido_ia()  [SEM LLM]      │   │
│  │     CRIAR_ORCAMENTO → criar_orcamento_ia()            │   │
│  │     OPERADOR → executar_comando_operador_ia()         │   │
│  │     ONBOARDING → onboarding_service  [SEM LLM]       │   │
│  │     CONVERSACAO + setup < 60% → onboarding  [SEM LLM]│   │
│  │     OUTROS → segue para [4]                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [4] ContextBuilder.build() — injeta dados do banco    │   │
│  │     _ctx_financeiro → ContaFinanceira + SaldoCaixa    │   │
│  │     _ctx_orcamentos → Orcamento + Cliente             │   │
│  │     _ctx_clientes → Cliente                           │   │
│  │     _ctx_leads → CommercialLead                       │   │
│  │     _ctx_empresa_usuario → Empresa + Usuario          │   │
│  │     _ctx_ajuda_sistema → manual_sistema.md            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [5] LLM (LiteLLM)                                     │   │
│  │     model = settings.AI_MODEL (normalizado p/ rota)    │   │
│  │     max_tokens=800                                    │   │
│  │     system=SYSTEM_PROMPT_ASSISTENTE                   │   │
│  │     messages = historico + [{user: msg + contexto}]   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [6] AIJSONExtractor.extract() → parse JSON resposta   │   │
│  │ [7] SessionStore.append() — persiste turno na sessão  │   │
│  │ [8] Filtra sugestões repetidas (seen_suggestions)     │   │
│  └──────────────────────────────────────────────────────┘   │
│  → Retorna AIResponse                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Dependências Externas

| Dependência | Uso | Localização |
|---|---|---|
| **LiteLLM** | Gateway único para chamadas de chat/completion | `ia_service.py`, `cotte_ai_hub.py` (ex.: `llm_gateway`: `litellm`) |
| **`AI_MODEL` / `AI_MODEL_FALLBACK`** | Modelo principal do assistente (slug normalizado: OpenRouter, OpenAI, Anthropic nativo, etc.) | `app/core/config.py`, `ia_service.normalize_litellm_model` |
| **`AI_TECHNICAL_MODEL`** | Overrides de modelo “técnico” onde o código usa modelo dedicado | `app/core/config.py` |
| **`OPENROUTER_API_KEY` / `AI_API_KEY`** | Autenticação conforme rota (`openrouter/...`, `openai/...`, etc.) | `app/core/config.py`; `ANTHROPIC_API_KEY` só se usar rota nativa Anthropic |
| **IntentionClassifier** | Apenas regex + fallback `CONVERSACAO` (sem LLM no classificador) | `ai_intention_classifier.py` |

---

## 10. Cobertura de Testes

| Área | Teste | Status |
|---|---|---|
| Roteamento SALDO_RAPIDO | `tests/test_saldo_caixa_unificado.py:98` | ✅ Existe |
| `assistente_unificado` geral | — | ❌ Não existe |
| `criar_orcamento_ia` | — | ❌ Não existe |
| `executar_comando_operador_ia` | — | ❌ Não existe |
| `IntentionClassifier` | — | ❌ Não existe |
| `ContextBuilder` | — | ❌ Não existe |
| `AntiDeliriumSystem` | — | ❌ Não existe |
| `AIJSONExtractor` | — | ❌ Não existe |
| `SessionStore` | — | ❌ Não existe |
| Feedback endpoint | — | ❌ Não existe |
