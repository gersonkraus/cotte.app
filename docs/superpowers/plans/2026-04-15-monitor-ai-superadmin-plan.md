# PLANO: Monitor AI — Superadmin Agent com Tool Calling

**Data**: 2026-04-15  
**Autor**: Gerson / Claude  
**Executor**: OpenCode + Gemini 2.5 Pro Preview  
**Prioridade**: Alta  
**Escopo**: Novo módulo superadmin-only com Agent IA que usa ferramentas reais do sistema

---

## 1. Visão Geral

O `monitor-ai.html` será um **painel de inteligência operacional exclusivo para superadmin**, que vai além do `copiloto-tecnico.html` (suporte técnico) ao oferecer um **Agent autônomo com tool-calling** capaz de:

- Consultar o banco de dados em linguagem natural
- Inspecionar logs e erros em tempo real
- Analisar o código via RAG
- Debugar problemas sem sair da interface
- Executar diagnósticos e gerar relatórios

---

## 2. Decisão de Stack

 O projeto não tem LangChain instalado. A dependência real é `anthropic>=0.34.0` + `litellm>=1.65.0`. Adicionar LangChain traria ~50 sub-dependências sem ganho real para este caso.

### ✅ USAR Anthropic Tool Use nativo
O SDK Anthropic já suporta `tools=[]` na chamada de API com loop de execução. É o mesmo padrão que as ferramentas "agentic" modernas usam (ex: Cursor, Claude Code).

```python
# Padrão Anthropic Tool Use (já disponível)
response = client.messages.create(
    model="claude-sonnet-4-5",
    tools=[tool1, tool2, ...],
    messages=messages
)
# Loop: se response.stop_reason == "tool_use" → executa tool → continua
```

### ✅ Manter code_rag_service existente como retriever_tool
Converter `CodeRAGService.search()` em tool Anthropic-compatible.

---

## 3. Funcionalidades do Monitor AI

### 3.1 Chat com Agent (Core)
- Caixa de mensagem com suporte markdown
- Exibição de **intermediate_steps** (qual tool foi chamada, com input/output resumido)
- Badge visual por tipo de tool executada (DB, Log, RAG, Schema)
- Histórico de conversas por sessão (localStorage)
- Modo "verbose" para ver o raciocínio completo do agent

### 3.2 Dashboard de Status (Sidebar)
- Últimas 5 entradas de AuditLog críticas (tempo real, polling 30s)
- Contador de empresas em trial expirando nos próximos 7 dias
- Status de filas/jobs pendentes
- Erros das últimas 24h (contagem)
- Botões de ação rápida: "Analisar erros recentes", "Ver schema drift", "Listar trials"

### 3.3 Query SQL em Linguagem Natural
- Usuário digita: *"quais empresas não logam há mais de 7 dias?"*
- Agent gera e executa SELECT seguro (somente leitura, sem DDL/DML)
- Resultado exibido como tabela formatada no chat
- Opção de exportar como CSV (frontend)

### 3.4 Busca de Logs e Erros
- Tool que lê as últimas N linhas de log (arquivo ou AuditLog)
- Filtro por: nível (ERROR/WARNING), empresa_id, usuário, endpoint, período
- Agent consegue correlacionar: *"qual empresa teve mais erros hoje?"*

### 3.5 Inspeção de Schema
- Tool que retorna estrutura de tabelas (colunas, tipos, índices, FKs)
- Compara com SQLAlchemy models para detectar drift
- Agent pode responder: *"a tabela orcamentos tem índice em cliente_id?"*

### 3.6 RAG sobre Código
- Baseado no `code_rag_service.py` existente (BM25)
- Agent pode responder: *"como funciona o cálculo de saldo?"* ou *"onde é chamado o envio de WhatsApp?"*

### 3.7 Audit Trail Intelligence
- Busca inteligente no AuditLog: *"o que o usuário X fez nas últimas 48h?"*
- Detecção de padrões suspeitos: muitos deletes, logins falhados, acesso a dados de outras empresas
- Relatório de atividade de empresa específica

### 3.8 Health Check Autônomo
- Comando especial: **"rodar diagnóstico completo"**
- Agent executa sequência: schema drift + erros recentes + trials expirando + performance de endpoints
- Retorna relatório consolidado em markdown

---

## 4. Arquitetura Backend

### 4.1 Estrutura de arquivos a criar

```
sistema/app/routers/
  monitor_ai.py              ← Novo router superadmin

sistema/app/services/
  monitor_ai_service.py      ← Agent loop principal
  monitor_ai_tools.py        ← Definição e execução das tools
```

### 4.2 Tools do Agent (Anthropic Tool Use)

#### Tool 1: `rag_retriever`
```python
{
  "name": "rag_retriever",
  "description": "Busca no código-fonte do projeto por trechos relevantes. Use para responder como algo funciona, onde está implementado, qual serviço cuida de X.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "O que buscar no código"}
    },
    "required": ["query"]
  }
}
# Execução: CodeRAGService.search(query, top_k=5)
```

#### Tool 2: `sql_query`
```python
{
  "name": "sql_query",
  "description": "Executa uma query SELECT somente-leitura no banco de dados do COTTE. NUNCA use INSERT/UPDATE/DELETE/DROP. Retorna até 100 linhas.",
  "input_schema": {
    "type": "object",
    "properties": {
      "sql": {"type": "string", "description": "Query SELECT a executar"},
      "params": {"type": "object", "description": "Parâmetros nomeados opcionais"}
    },
    "required": ["sql"]
  }
}
# Execução: db.execute(text(sql), params) com validação SELECT-only
```

#### Tool 3: `audit_log_search`
```python
{
  "name": "audit_log_search",
  "description": "Busca no log de auditoria do sistema. Retorna ações, quem fez, quando e detalhes.",
  "input_schema": {
    "type": "object",
    "properties": {
      "usuario_id": {"type": "integer"},
      "empresa_id": {"type": "integer"},
      "acao": {"type": "string", "description": "Ex: CRIAR_ORCAMENTO, APROVAR, LOGIN"},
      "recurso": {"type": "string"},
      "periodo_horas": {"type": "integer", "description": "Últimas N horas (padrão: 24)"},
      "limit": {"type": "integer", "description": "Máximo de resultados (padrão: 50)"}
    }
  }
}
```

#### Tool 4: `schema_inspector`
```python
{
  "name": "schema_inspector",
  "description": "Inspeciona a estrutura do banco de dados: tabelas, colunas, índices. Também detecta drift entre models Python e banco real.",
  "input_schema": {
    "type": "object",
    "properties": {
      "tabela": {"type": "string", "description": "Nome da tabela (opcional, se omitido lista todas)"},
      "verificar_drift": {"type": "boolean", "description": "Se true, compara models Python com banco"}
    }
  }
}
```

#### Tool 5: `log_reader`
```python
{
  "name": "log_reader",
  "description": "Lê logs recentes do sistema. Filtra por nível, endpoint ou texto.",
  "input_schema": {
    "type": "object",
    "properties": {
      "nivel": {"type": "string", "enum": ["ERROR", "WARNING", "INFO", "ALL"]},
      "filtro_texto": {"type": "string", "description": "Texto para filtrar nas mensagens"},
      "ultimas_horas": {"type": "integer", "description": "Janela de tempo em horas (padrão: 24)"},
      "limit": {"type": "integer", "description": "Máximo de linhas (padrão: 100, máx: 1000)"}
    }
  }
}
# Fonte: AuditLog + tabela de erros ou arquivo de log do Railway
```

### 4.3 Agent Loop (monitor_ai_service.py)

```python
async def run_agent(
    pergunta: str,
    db: AsyncSession,
    historico: list[dict],
    verbose: bool = False
) -> dict:
    """
    Loop Anthropic Tool Use:
    1. Envia mensagem + tools disponíveis
    2. Se stop_reason == "tool_use": executa tools, adiciona resultados
    3. Reenvia com resultados até stop_reason == "end_turn"
    4. Retorna resposta final + intermediate_steps para o frontend
    """
    tools = get_all_tools()  # lista das 5 tools definidas
    messages = historico + [{"role": "user", "content": pergunta}]
    intermediate_steps = []
    max_iterations = 10  # evitar loops infinitos
    
    for _ in range(max_iterations):
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=MONITOR_AI_SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )
        
        if response.stop_reason == "end_turn":
            return {
                "resposta": extract_text(response),
                "intermediate_steps": intermediate_steps,
                "tokens_usados": response.usage.input_tokens + response.usage.output_tokens
            }
        
        # Executar tools
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                resultado = await execute_tool(block.name, block.input, db)
                intermediate_steps.append({
                    "tool": block.name,
                    "input": block.input,
                    "output_resumo": str(resultado)[:500]
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(resultado, ensure_ascii=False, default=str)
                })
        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
    
    return {"resposta": "Limite de iterações atingido.", "intermediate_steps": intermediate_steps}
```

### 4.4 Endpoint (monitor_ai.py)

```python
router = APIRouter(prefix="/api/superadmin/monitor-ai", tags=["Monitor AI"])

@router.post("/agent")
async def monitor_ai_agent(
    payload: MonitorAIRequest,
    db: AsyncSession = Depends(get_db),
    superadmin = Depends(get_superadmin)  # garante is_superadmin=True
):
    """
    Body: { "pergunta": str, "historico": list, "verbose": bool }
    Response: { "resposta": str, "intermediate_steps": list, "tokens_usados": int }
    """
    return await run_agent(payload.pergunta, db, payload.historico, payload.verbose)
```

### 4.5 System Prompt do Agent

```
Você é o Monitor AI do COTTE — um assistente técnico de nível superadmin com acesso total ao sistema.

Seu papel:
- Diagnosticar problemas operacionais
- Responder perguntas sobre o banco de dados, código e logs
- Identificar padrões suspeitos ou críticos
- Ajudar o superadmin a entender e tomar decisões sobre a plataforma

Regras:
- Sempre use tools para dados reais (nunca invente números)
- Para SQL: somente SELECT, nunca modificar dados
- Seja direto e técnico — o usuário é o administrador da plataforma
- Quando identificar problemas, proponha ações concretas
- Exiba dados em tabelas markdown quando houver múltiplos registros
```

---

## 5. Arquitetura Frontend

### 5.1 Arquivo
`sistema/cotte-frontend/monitor-ai.html`

### 5.2 Layout (Split View)

```
┌─────────────────────────────────────────────────────┐
│  🔴 MONITOR AI  [SUPERADMIN]          [Diagnóstico] │
├──────────────────────────┬──────────────────────────┤
│                          │   STATUS DO SISTEMA      │
│   CHAT COM AGENT         │  • Erros 24h: 3          │
│                          │  • Trials expirando: 2   │
│  [Thinking Steps]        │  • AuditLog recente      │
│  ├─ 🔍 rag_retriever     │    [lista 5 items]       │
│  ├─ 🗄️ sql_query         │                          │
│  └─ 📋 audit_log_search  │  AÇÕES RÁPIDAS           │
│                          │  [Analisar Erros]        │
│  [Resposta do Agent]     │  [Schema Drift]          │
│                          │  [Trials]                │
├──────────────────────────┴──────────────────────────┤
│  [Pergunta...                           ] [Enviar]  │
│  [Diagnóstico] [SQL] [Logs] [Código]                │
└─────────────────────────────────────────────────────┘
```

### 5.3 Componentes UI

**Thinking Steps Accordion**
- Expandível por padrão (mostra 1a tool, recolhe o resto)
- Cada step: ícone da tool + nome + input resumido + output resumido
- Badge colorido por tipo: 🗄️ SQL (azul), 📋 Audit (amarelo), 🔍 RAG (roxo), 🏗️ Schema (verde), 📜 Log (vermelho)

**Prompt Chips (ações rápidas)**
- Clique insere texto pré-definido no input:
  - "Analisar erros das últimas 24h"
  - "Verificar schema drift"
  - "Listar empresas em trial expirando"
  - "Qual o uso de tokens desta semana?"
  - "Rodar diagnóstico completo"

**Tabelas dinâmicas**
- Respostas com dados tabulares renderizadas como `<table>` estilizada
- Suporte a ordenação de colunas (JS puro)
- Botão "Copiar CSV"

**Status sidebar** (polling 30s via `/api/superadmin/monitor-ai/status`)
- Contador de erros 24h
- Trials expirando em 7 dias
- Último AuditLog crítico (DELETE/APROVAR_MASSA)

### 5.4 JS (monitor-ai.js, Vanilla)

```javascript
class MonitorAIChat {
  constructor() {
    this.historico = [];
    this.verbose = false;
  }

  async enviarPergunta(pergunta) {
    this.addUserMessage(pergunta);
    this.mostrarThinking();
    
    const response = await ApiService.post('/api/superadmin/monitor-ai/agent', {
      pergunta,
      historico: this.historico.slice(-10), // janela de 10 turnos
      verbose: this.verbose
    });
    
    this.renderThinkingSteps(response.intermediate_steps);
    this.addAssistantMessage(response.resposta);
    this.historico.push(
      { role: 'user', content: pergunta },
      { role: 'assistant', content: response.resposta }
    );
    this.atualizarTokenCounter(response.tokens_usados);
  }

  renderThinkingSteps(steps) {
    // Renderiza accordion com cada tool call
  }
}
```

---

## 6. Segurança

- **Rota protegida por `get_superadmin`** — `is_superadmin=True` obrigatório
- **SQL somente leitura**: validar que a query começa com `SELECT` e não contém `;` (multi-statement)
- **Rate limit no agent**: máximo 20 chamadas por hora por superadmin
- **Log de uso**: cada chamada ao `/agent` registrada no AuditLog com a pergunta e tokens usados
- **Limite de tokens**: máximo 4096 output, janela de histórico limitada a 10 turnos
- **Sem execução de código arbitrário**: não implementar Python REPL (risco alto, sem ganho claro nesta fase)

---

## 7. Fases de Implementação

### Fase 1 — Backend Core (Prioridade Alta)
1. Criar `sistema/app/services/monitor_ai_tools.py` com as 5 tools
2. Criar `sistema/app/services/monitor_ai_service.py` com o agent loop
3. Criar `sistema/app/routers/monitor_ai.py` com endpoint `/agent` e `/status`
4. Registrar o router em `main.py`
5. Testar via curl/Postman

### Fase 2 — Frontend Base (Prioridade Alta)
1. Criar `sistema/cotte-frontend/monitor-ai.html` com layout split
2. Criar `sistema/cotte-frontend/js/monitor-ai.js` com MonitorAIChat
3. Criar `sistema/cotte-frontend/css/monitor-ai.css` com estilos dark/premium
4. Implementar renderização de thinking steps
5. Implementar prompt chips

### Fase 3 — Status Sidebar (Prioridade Média)
1. Endpoint `/api/superadmin/monitor-ai/status` com dados em tempo real
2. Polling 30s no sidebar
3. Ações rápidas funcionais

### Fase 4 — Polimento UX (Prioridade Baixa)
1. Exportar resposta como markdown/PDF
2. Histórico de sessões (últimas 10 conversas)
3. Modo verbose toggle
4. Tabelas ordenáveis com exportação CSV

---

## 8. Migrations Necessárias

**Nenhuma migration necessária** — todas as queries usam tabelas existentes (AuditLog, Empresa, Usuario, Orcamento).

---

## 9. Dependências Novas

**Nenhuma dependência nova** — usa apenas:
- `anthropic` (já instalado)
- `sqlalchemy` (já instalado)  
- `fastapi` (já instalado)

---

## 10. Testes Recomendados

```bash
# Testar endpoint diretamente
curl -X POST /api/superadmin/monitor-ai/agent \
  -H "Authorization: Bearer <token_superadmin>" \
  -d '{"pergunta": "quantas empresas existem?", "historico": []}'

# Verificar proteção de rota (deve retornar 403)
curl -X POST /api/superadmin/monitor-ai/agent \
  -H "Authorization: Bearer <token_usuario_normal>"

# Testar SQL injection protection
curl -X POST com sql: "SELECT 1; DROP TABLE usuarios"
```

---

## 11. Arquivos a Criar/Modificar

| Ação | Arquivo |
|------|---------|
| CRIAR | `sistema/app/routers/monitor_ai.py` |
| CRIAR | `sistema/app/services/monitor_ai_service.py` |
| CRIAR | `sistema/app/services/monitor_ai_tools.py` |
| CRIAR | `sistema/cotte-frontend/monitor-ai.html` |
| CRIAR | `sistema/cotte-frontend/js/monitor-ai.js` |
| CRIAR | `sistema/cotte-frontend/css/monitor-ai.css` |
| MODIFICAR | `sistema/main.py` (registrar router) |
| MODIFICAR | `sistema/cotte-frontend/index.html` (link no menu superadmin) |

---

## 12. Referências no Projeto

- `sistema/app/routers/admin.py` — padrão de rotas superadmin existentes
- `sistema/app/services/code_rag_service.py` — RAG a converter em tool
- `sistema/app/models/models.py` → `AuditLog` — tabela de logs disponível
- `sistema/cotte-frontend/copiloto-tecnico.html` — referência de UI de chat
- `sistema/app/services/cotte_ai_hub.py` — padrão de chamada Anthropic existente
