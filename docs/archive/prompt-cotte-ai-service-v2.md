---
title: Prompt Cotte Ai Service V2
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Prompt Cotte Ai Service V2
tags:
  - tecnico
prioridade: media
status: documentado
---
# 🚀 PROMPT — CRIAR SERVIÇO COTTE AI (ARQUITETURA SEPARADA) v2

Atue como um engenheiro de software sênior especialista em:

- FastAPI
- Arquitetura de microserviços
- Integração com LLM (Anthropic / tool use)
- Sistemas multi-tenant seguros
- Integração via API entre serviços

Você irá criar um novo serviço chamado:

👉 cotte-ai-service

Esse serviço será responsável exclusivamente pela IA do sistema COTTE.

---

# 🎯 OBJETIVO

Criar um serviço de IA desacoplado do ERP principal, com as seguintes responsabilidades:

- Interpretar mensagens do usuário
- Decidir ações (tools)
- Chamar endpoints do ERP via HTTP
- Retornar respostas estruturadas

⚠️ IMPORTANTE:
Este serviço NÃO pode acessar banco de dados diretamente.
Toda regra de negócio deve permanecer no ERP.

---

# 🧠 CONTEXTO DO SISTEMA

O COTTE é um ERP SaaS multi-tenant para pequenas empresas.

Stack atual do ERP:
- FastAPI
- SQLAlchemy
- PostgreSQL

A IA atual está acoplada ao backend e precisa ser separada.

---

# 🏗️ ARQUITETURA DESEJADA

```
[Frontend / WhatsApp]
        ↓
cotte-ai-service
        ↓
  (HTTP REST + SERVICE_TOKEN)
        ↓
    COTTE ERP
```

---

# ⚠️ REGRAS CRÍTICAS

## Segurança
- Nunca acessar banco diretamente
- Nunca executar lógica crítica internamente
- Sempre chamar API do ERP
- Sempre enviar empresa_id
- Sempre enviar SERVICE_TOKEN no header `X-Service-Token` em toda chamada ao ERP
- O SERVICE_TOKEN deve ser configurado via variável de ambiente e nunca hardcoded

## Multi-tenant
- Toda requisição deve conter empresa_id
- Nunca misturar dados entre empresas
- empresa_id deve ser validado antes de qualquer operação

## Arquitetura
- Código modular
- Fácil de expandir
- Sem overengineering

## Integração
- Toda ação via HTTP (httpx async)
- Base URL do ERP configurável via env
- Timeouts obrigatórios em todas as chamadas

---

# 📁 ESTRUTURA DO PROJETO

```
cotte-ai-service/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── settings.py
│   ├── agent/
│   │   ├── executor.py
│   │   ├── tool_registry.py
│   │   ├── policy.py
│   │   ├── prompts.py
│   │   └── memory.py           ← NOVO: gerencia histórico de conversa por sessão
│   ├── tools/
│   │   ├── financeiro.py
│   │   ├── orcamento.py
│   │   └── comunicacao.py      ← RENOMEADO: separado do domínio de negócio
│   ├── infra/
│   │   ├── anthropic_client.py
│   │   ├── http_client.py
│   │   └── session_store.py    ← NOVO: Redis ou in-memory para histórico
│   ├── schemas/
│   │   └── agent.py
│   └── services/
│       └── agent_service.py
├── .env.example
├── requirements.txt
└── README.md
```

---

# ⚙️ FUNCIONALIDADES A IMPLEMENTAR

## 1. Endpoints principais

### POST /agent/execute

Request:
```json
{
  "mensagem": "string",
  "empresa_id": "int",
  "sessao_id": "string"
}
```

Response:
```json
{
  "resposta": "string",
  "requer_confirmacao": false,
  "token_acao": null
}
```

---

### POST /agent/confirm

Usado para confirmar ações WRITE que retornaram `requires_confirmation`.

Request:
```json
{
  "token_acao": "string",
  "empresa_id": "int",
  "sessao_id": "string",
  "confirmado": true
}
```

Response:
```json
{
  "resposta": "string"
}
```

Regras:
- `token_acao` deve ser gerado no momento em que uma ação WRITE é solicitada
- O token deve ter TTL curto (ex: 5 minutos) — armazenar no session_store
- Se expirado ou inválido, retornar erro claro
- Nunca executar ação WRITE sem confirmação explícita

---

## 2. Executor do agente

Implementar executor com:

- Loop de tool use (até 5 iterações)
- Suporte a múltiplas tools
- Fallback seguro em caso de erro
- Separação de responsabilidades
- Injeção do histórico de conversa da sessão em cada chamada

---

## 3. Memória de Sessão

Criar módulo `agent/memory.py`:

- Armazena histórico de conversa por `sessao_id`
- Cada entrada: `{ role: "user|assistant", content: "..." }`
- TTL configurável (ex: 30 minutos de inatividade)
- Limite de mensagens por sessão (ex: últimas 20)
- Interface:
  - `get_history(sessao_id) → List[dict]`
  - `append(sessao_id, role, content)`
  - `clear(sessao_id)`

Criar módulo `infra/session_store.py`:

- Implementar com Redis (preferido para produção)
- Ter fallback in-memory para desenvolvimento local
- Configurar via env: `SESSION_BACKEND=redis|memory`

---

## 4. Integração com Anthropic

Criar client em `infra/anthropic_client.py`:

- Modelo configurável via env: `ANTHROPIC_MODEL=claude-sonnet-4-5`
- Preparar para troca futura de modelo
- Injetar histórico de conversa em cada chamada
- Timeout configurável
- Nunca logar o conteúdo completo das mensagens (privacidade)

---

## 5. Autenticação entre serviços

Criar mecanismo de autenticação do cotte-ai-service ao ERP:

- Variável de ambiente: `ERP_SERVICE_TOKEN`
- Enviado em toda requisição ao ERP via header: `X-Service-Token: <token>`
- O ERP deve validar esse token antes de processar qualquer requisição vinda do AI service
- Nunca logar o token

Implementar em `infra/http_client.py`:
- O header `X-Service-Token` deve ser injetado automaticamente em todas as chamadas
- Nunca passar o token manualmente em cada tool

---

## 6. Tool Registry

Criar dispatcher central em `agent/tool_registry.py`:

```python
TOOLS = {
  "consultar_saldo_caixa": fn,
  "consultar_valor_a_receber": fn,
  "buscar_orcamento": fn,
  "aprovar_orcamento": fn,
  "enviar_mensagem_whatsapp": fn,
}

async def executar_tool(nome: str, input: dict, empresa_id: int) → dict
```

---

## 7. Policy de Segurança

Criar `agent/policy.py`:

Classificar tools em três níveis:

```python
READ  = ["consultar_saldo_caixa", "consultar_valor_a_receber", "buscar_orcamento"]
DRAFT = []
WRITE = ["aprovar_orcamento", "enviar_mensagem_whatsapp"]
```

Regras:
- `READ` → executar direto
- `DRAFT` → executar, mas avisar que é rascunho
- `WRITE` → NÃO executar direto. Gerar `token_acao`, armazenar no session_store e retornar `requires_confirmation`
- Nunca executar WRITE sem confirmação explícita via `/agent/confirm`

---

## 8. Tools via HTTP (NÃO DB)

### financeiro.py

**consultar_saldo_caixa:**
- `GET /financeiro/saldo?empresa_id={id}`
- Retorna JSON padronizado

**consultar_valor_a_receber:**
- `GET /financeiro/a_receber?empresa_id={id}`
- Retorna JSON padronizado

---

### orcamento.py

**buscar_orcamento:**
- `GET /orcamentos/{id}?empresa_id={empresa_id}`

**aprovar_orcamento:**
- `POST /orcamentos/{id}/aprovar`
- Body: `{ "empresa_id": int }`
- WRITE: exige confirmação

---

### comunicacao.py

**enviar_mensagem_whatsapp:**
- `POST /whatsapp/enviar`
- Body: `{ "empresa_id": int, "destinatario": str, "mensagem": str }`
- WRITE: exige confirmação
- ⚠️ Este módulo é de canal de comunicação, não de domínio de negócio

---

## 9. HTTP Client

Criar client reutilizável em `infra/http_client.py`:

- Async (httpx)
- Timeout padrão configurável (ex: 10s)
- Tratamento de erro com retorno padronizado
- Base URL do ERP configurável via env
- Injeção automática do header `X-Service-Token`
- Rate limiting simples por `empresa_id` (ex: máx 30 req/min)
- Nunca logar bodies completos de resposta (privacidade)

---

## 10. Padronização de retorno

Todas as tools devem retornar:

```json
{
  "status": "success | error | requires_confirmation",
  "data": {},
  "message": "string opcional",
  "token_acao": "string | null"
}
```

---

## 11. Prompts do agente

Criar em `agent/prompts.py`:

Instruções obrigatórias no system prompt:

- Usar tools sempre que necessário para buscar dados reais
- Nunca inventar dados financeiros
- Nunca assumir valores sem consultar o ERP
- Nunca executar ação de escrita sem avisar o usuário
- Sempre responder em português
- Ser objetivo e direto
- Nunca expor detalhes técnicos ao usuário (nomes de tools, endpoints, etc.)

---

## 12. Logging

Logar, de forma estruturada (JSON):

- Entrada de cada requisição: `empresa_id`, `sessao_id`, `mensagem` (sem dados sensíveis)
- Tool chamada: nome da tool, `empresa_id`
- Resultado da tool: `status` (sem dados sensíveis do body)
- Erros: tipo, mensagem, `empresa_id`, `sessao_id`
- Nunca logar: valores financeiros, tokens, conteúdo de mensagens completo

---

## 13. Variáveis de ambiente (.env.example)

```env
# Anthropic
ANTHROPIC_API_KEY=sk-...
ANTHROPIC_MODEL=claude-sonnet-4-5

# ERP
ERP_BASE_URL=http://localhost:8000
ERP_SERVICE_TOKEN=seu-token-secreto-aqui

# Sessão
SESSION_BACKEND=memory   # ou redis
REDIS_URL=redis://localhost:6379
SESSION_TTL_MINUTES=30
SESSION_MAX_MESSAGES=20

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30

# App
DEBUG=false
LOG_LEVEL=INFO
```

---

# 🧪 EXEMPLOS QUE DEVEM FUNCIONAR

**Exemplo 1 — READ:**
```
Entrada: "quanto tenho em caixa?"
→ chama tool consultar_saldo_caixa
→ retorna valor (sem análise extra)
→ requer_confirmacao: false
```

**Exemplo 2 — WRITE bloqueado:**
```
Entrada: "aprovar orçamento 123"
→ NÃO executa
→ retorna requer_confirmacao: true
→ token_acao: "abc123..."
→ resposta: "Você confirma a aprovação do orçamento 123?"
```

**Exemplo 3 — Confirmação:**
```
POST /agent/confirm
{ "token_acao": "abc123...", "confirmado": true }
→ executa aprovar_orcamento
→ retorna resultado
```

**Exemplo 4 — Memória:**
```
Turno 1: "qual meu saldo?"       → R$ 5.000
Turno 2: "e o que tenho a receber?" → histórico injetado → responde no contexto correto
```

---

# 🚫 O QUE NÃO FAZER

- Não acessar banco
- Não importar models do ERP
- Não duplicar regra de negócio
- Não fazer lógica crítica dentro do prompt
- Não criar endpoints desnecessários
- Não hardcodar tokens ou secrets
- Não logar dados financeiros ou tokens
- Não executar WRITE sem confirmação
- Não misturar dados de empresas diferentes

---

# 📌 RESULTADO ESPERADO

Ao final quero:

1. Projeto completo criado
2. Código funcional
3. Estrutura modular
4. Executor com tool use e memória de sessão funcionando
5. Autenticação entre serviços (SERVICE_TOKEN)
6. Fluxo completo de confirmação para ações WRITE
7. Integração HTTP com ERP
8. Rate limiting básico
9. Pronto para expansão

---

# 🧾 ENTREGA

Você deve:

1. Explicar rapidamente a estrutura criada
2. Mostrar os principais arquivos com código completo
3. Garantir que está pronto para rodar com `uvicorn app.main:app`
4. Listar próximos passos recomendados

---

# ⚠️ IMPORTANTE FINAL

Se tiver dúvida entre:

- fazer algo mais inteligente
- fazer algo mais seguro

Escolha sempre o mais seguro.

Este serviço vai operar dados reais de clientes.
