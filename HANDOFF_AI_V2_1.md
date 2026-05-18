# Handoff: Evolução Assistente IA v2.1 (Multi-Agentes & pgvector)

**Data:** 17 de Maio de 2026
**Status:** Em andamento (Fase de Integração de UI Finalizada, aguardando testes de campo)

## 1. Objetivo
Migrar o Assistente IA de um fluxo linear e básico (v2.0) para um ecossistema **Multi-Agente autônomo (v2.1)**. O objetivo é permitir que a IA entenda o sistema dinamicamente (via RAG vetorial e indexação de schema) e suporte interações multimodais (áudio bidirecional) com isolamento total por empresa.

## 2. Contexto essencial
- **Stack:** FastAPI, LangGraph 1.1+, SQLAlchemy (Async), PostgreSQL 16 + **pgvector**, LiteLLM.
- **Arquitetura:** Padrão **Supervisor** no LangGraph roteando para 7 agentes especialistas.
- **RAG:** Substituído Jaccard por busca vetorial semântica (`vector(1536)`) usando embeddings do `text-embedding-3-small`.
- **Multimodal:** Entrada via Blobs de áudio (STT) e saída via OpenAI/ElevenLabs (TTS).
- **Isolamento:** Toda busca vetorial e execução de tool é filtrada obrigatoriamente por `empresa_id`.

## 3. O que já foi feito
- **Isolamento de Módulo:** Criado `app/ai/` para centralizar a inteligência, movendo lógica de `services/`.
- **Infraestrutura pgvector:** Migration `z037` executada; extensão `vector` ativa no banco local porta 5433.
- **Multi-Agentes:** Implementados `FinanceAgent`, `SalesAgent`, `InventoryAgent`, `SupportAgent`, `OperadorAgent`, `DataAgent` e `ConversationalAgent`.
- **Autonomia de Dados:** Criado `schema_indexer.py` e executado script de indexação inicial; Agente de Dados agora "vê" as tabelas.
- **Refatoração de Voz:** Criado `VoiceProcessor.js` (Vanilla JS) para gravação via Blobs, contornando limitações da Web Speech API.
- **Integração TTS:** Implementado `triggerAutoTTS` no frontend para falar as respostas da IA automaticamente.

## 4. Estado atual
- **Backend:** 100% funcional. Grafo roteando bem, tools migradas e funcionando, busca vetorial ativa.
- **Frontend:** `assistente-ia.html` atualizado. Breadcrumbs visuais (Thinking Steps) integrados ao stream do LangGraph.
- **Ponto de Parada:** Acabamos de registrar a nova tool `obter_cliente` e validar as importações do hub. A infraestrutura está estável e o banco indexado.

## 5. Próximos passos
1. **Refinamento de RAG de Conhecimento:** Implementar interface para a empresa subir manuais PDF/TXT que alimentem a tabela `ai_documentos_conhecimento`.
2. **Testes de Agente de Dados:** Validar se o `DataAgent` consegue montar queries complexas usando o `schema_json` indexado.
3. **UI de Feedback de Áudio:** Adicionar uma barra de ondas (visualizer) no microfone durante a gravação.
4. **Configuração ElevenLabs:** Se o usuário desejar vozes mais naturais, substituir o endpoint do OpenAI TTS pelo da ElevenLabs em `app/ai/audio/service.py`.

## 6. Perguntas em aberto
- Devemos habilitar o TTS por padrão para todos os usuários ou apenas sob demanda (botão de play)? Atualmente está em "Auto" nas preferências.
- O `DataAgent` deve ter permissão para rodar apenas `SELECT` ou também `EXPLAIN ANALYZE` para auditoria?

## 7. Artefatos relevantes
- **Módulo Raiz:** `sistema/app/ai/`
- **Grafo:** `sistema/app/ai/graph/assistant.py`
- **Serviço de Voz (JS):** `sistema/cotte-frontend/js/voice/VoiceProcessor.js`
- **Script de Indexação:** `python sistema/scripts/index_db_schema.py` (Usar venv python3.14)
- **Comando de Teste:** `cd sistema && ./venv/bin/python3.14 -c "from app.ai.graph.assistant import get_assistant_app; print('OK')"`

## 8. Instruções pra próxima sessão
- **Tom:** Técnico, pragmático e direto (Mentalidade YOLO autorizada).
- **Atenção:** Ao mexer no `intention_classifier.py`, sempre rodar os testes de roteamento (`pytest tests/test_ai_tool_routing.py`).
- **Ambiente:** O PostgreSQL local precisa estar com o serviço ativo na porta 5433 para o pgvector funcionar.
