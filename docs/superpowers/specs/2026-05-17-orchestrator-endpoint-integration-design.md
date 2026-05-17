# Orquestrador LangGraph: Integração com Endpoints Reais

## Objetivo
Conectar a nova arquitetura em camadas (Canais, Eventos e Orquestrador LangGraph) diretamente aos endpoints públicos do FastAPI (`ai_hub.py` e `whatsapp.py`), substituindo as chamadas engessadas ao `cotte_ai_hub.py`. O objetivo é desacoplar o roteamento HTTP da execução da inteligência artificial, mantendo fallbacks de segurança ativos.

## Arquitetura e Fluxo de Dados

O fluxo das requisições mudará para a seguinte arquitetura limpa:

1. **Camada HTTP (FastAPI Routers):**
   - Os endpoints não invocam mais as rotinas core de IA diretamente.
   - Sua única função será extrair as requisições (`Request`, `payloads` JSON do WhatsApp), montar um dicionário básico e delegar para o "Canal".

2. **Camada de Adaptação de Canais (`app.ai.channels`):**
   - Os adaptadores (`from_web_payload`, `from_whatsapp_payload`) convertem os payloads arbitrários num `ChannelMessage` padronizado, realizando os deepcopies defensivos necessários e emitindo erros nativos do Pydantic se o contrato faltar (ex: ausência de `empresa_id`).

3. **Camada de Orquestração (`app.ai.orchestrator.service.AssistantOrchestrator`):**
   - O orquestrador será instanciado pelas rotas, recebendo não só a mensagem do canal, mas referências seguras "vivas" de ambiente como a conexão com banco de dados (`db`) e o utilizador atual (`current_user`).
   - Ele decidirá de forma autônoma e flaggada se a requisição viaja pelo LangGraph ou sofre *fallback* em caso de falha ou desativação.

## Detalhamento de Componentes

### 1. Extensão do AssistantOrchestrator (Streaming)
O orquestrador atual tem apenas o método `run()` (bloqueante/retorno único). Ele deverá ser ampliado com:
- `run_stream(message: ChannelMessage) -> AsyncGenerator`
- O `run_stream` verificará a flag `direct_agents_enabled()` e `langgraph_enabled()` (herdadas das tasks anteriores).
- Se habilitado, consumirá `run_assistant_v2_graph_stream()`, emitindo a padronização recém implementada de `agent_event`, `tool_event` e `final_event`.
- Se desabilitado, ou houver erro irrecuperável, o stream recairá de forma transparente para o motor legado (`assistente_unificado_stream`).

### 2. Modificações em Endpoints (`ai_hub.py` e `whatsapp.py`)
- O `router.post("/assistente/stream")` processará a chamada invocando a Factory de canais (Web) e repassará ao `orchestrator.run_stream(msg)`, retornando um `StreamingResponse`.
- O `router.post("/assistente")` usará a mesma lógica, mas consumirá `orchestrator.run(msg)`, retornando o objeto unificado.
- A função de Background Task em `whatsapp.py` (ex: `processar_mensagem` / `processar_audio_operador`) montará o dicionário focado no WhatsApp, submeterá à adaptação (`from_whatsapp_payload`) e usará o `.run(msg)` não-streamado para despachar respostas à EvolutionAPI.

## Gestão de Dependências (Sessões e Usuário)
Para que a abstração `ChannelMessage` continue pura/simples (sem injetar instâncias complexas do SQLAlchemy no schema de modelo), o `AssistantOrchestrator` será instanciado através de Injeção de Dependências, ou inicialização imediata dentro do endpoint:
`orchestrator = AssistantOrchestrator(db=db, current_user=current_user, legacy_runner=..., legacy_stream_runner=...)`

## Tratamento de Erros e Segurança
A camada de endpoints envolverá a conversão do `from_*_payload` em blocos de tentativa. Falhas do `ValidationError` devem responder limpos para os clientes (HTTP 422 para web, log para webhook assíncrono), evitando poluição do logger principal.
O Orquestrador manterá o princípio do Fail-Safe: se o LangGraph disparar falha interna grave no `run_stream`, o iterador de fall-back legado tentará resolver.
