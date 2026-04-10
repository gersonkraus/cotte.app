---
title: Teste Manual Ultimos 20 Commits 2026 04 10
tags:
  - tecnico
prioridade: media
status: documentado
---
# Roteiro de Teste Manual — Últimos 20 commits

Data da análise: 2026-04-10  
Branch base analisada: `main`  
Faixa de commits: de `d4d222f` até `833837d`

## Objetivo

Guiar o teste manual das mudanças mais recentes, mostrando **onde ir no sistema**, **o que executar** e **o que validar**.

## Visão rápida do que mudou

### 1) Assistente IA (maior impacto)
- Redesign mobile e ajustes de composer/loading/stream.
- Novas preferências visuais por empresa.
- Memória semântica por empresa.
- Perfil operacional dinâmico 7/30/90.
- Guardrail com `instrucoes_empresa` no prompt.
- Novas tools e ajustes de queries reais, incluindo logs de tools.

### 2) Admin — Schema Drift
- Backend para snapshots e preview dry-run.
- Dashboard visual de diff no admin.

### 3) Banco de dados
- Migration para coluna `assistente_instrucoes`.
- Migration para snapshots de schema drift.

### 4) WhatsApp / Operador
- Confirmações com prévia rica (mais contexto antes de confirmar ação).

### 5) PWA
- Manifest, Service Worker e ajustes de `assetlinks.json`.

---

## Pré-requisitos para executar os testes

1. Backend rodando (`uvicorn`) e sem erro de startup.
2. Frontend acessível no navegador.
3. Banco com migrations aplicadas.
4. Usuário com acesso ao admin e usuário com fluxo normal de assistente.

Comandos úteis:
- Backend: `cd sistema && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Testes backend pontuais:
  - `cd sistema && pytest tests/test_assistente_unificado_v2.py`
  - `cd sistema && pytest tests/test_ai_tools_fase3.py`
  - `cd sistema && pytest tests/test_admin_schema_drift.py`

---

## Roteiro de teste manual (por área)

## A. Assistente IA — UI/UX e mobile

### Caso A1 — Layout mobile do assistente
**Onde ir:** `assistente-ia.html` no mobile (DevTools iPhone/Android)  
**Passos:**
1. Abrir o assistente em viewport mobile.
2. Verificar cabeçalho, área de mensagens e composer.
3. Abrir teclado virtual (ou simular) e enviar mensagem.
**Esperado:**
- Sem quebra visual.
- Composer estável, sem “pular” ou sobrepor elementos.
- Scroll permanece utilizável durante conversa.

### Caso A2 — Loading com dots + “Processando...”
**Onde ir:** tela do assistente após enviar pergunta  
**Passos:**
1. Enviar uma pergunta que leve alguns segundos para responder.
2. Observar a bolha de loading.
**Esperado:**
- Dots visíveis junto com texto “Processando...”.
- Indicador não some antes do primeiro conteúdo real.

### Caso A3 — Contrato de stream
**Onde ir:** conversa no assistente  
**Passos:**
1. Fazer 3 perguntas seguidas com respostas de tamanhos diferentes.
2. Interromper e repetir uma pergunta.
**Esperado:**
- Renderização progressiva sem travar UI.
- Sem duplicação de blocos.
- Estado final coerente ao término do stream.

## B. Assistente IA — contexto, memória e preferências

### Caso B1 — Guardrail com instruções da empresa
**Onde ir:** fluxo de pergunta sensível no assistente  
**Passos:**
1. Definir instruções da empresa (quando disponível na configuração da empresa).
2. Fazer pergunta que normalmente conflita com regras internas.
**Esperado:**
- Resposta respeita instruções da empresa.
- Sem ignorar contexto operacional definido.

### Caso B2 — Memória semântica por empresa
**Onde ir:** assistente com duas empresas diferentes  
**Passos:**
1. Na Empresa A, enviar mensagens com contexto específico.
2. Trocar para Empresa B e perguntar algo semelhante.
3. Voltar para Empresa A e repetir consulta.
**Esperado:**
- Contexto lembrado corretamente na Empresa A.
- Sem vazamento de memória entre empresas.

### Caso B3 — Perfil operacional 7/30/90
**Onde ir:** assistente, perguntas sobre operação histórica  
**Passos:**
1. Solicitar visão curta (7 dias), média (30) e longa (90).
2. Comparar consistência entre períodos.
**Esperado:**
- Resposta muda de acordo com janela temporal.
- Sem contradições óbvias entre períodos.

### Caso B4 — Preferências visuais + playbook setorial
**Onde ir:** assistente e configurações relacionadas  
**Passos:**
1. Ajustar preferências visuais.
2. Fazer pergunta operacional setorial.
**Esperado:**
- Assistente reflete preferências visuais configuradas.
- Conteúdo segue playbook setorial quando aplicável.

## C. Assistente IA — tools e confirmação de ações

### Caso C1 — TODOs com queries reais
**Onde ir:** perguntas que listam pendências/TODOs  
**Passos:**
1. Solicitar TODOs reais para o contexto da empresa.
2. Validar com dados da UI/DB.
**Esperado:**
- Dados retornados batem com a base real.
- Sem placeholders falsos.

### Caso C2 — Tool de análise de logs (`analisar_tool_logs`)
**Onde ir:** fluxo de diagnóstico no assistente  
**Passos:**
1. Pedir análise de execução de tools.
2. Observar retorno e robustez quando não há dados.
**Esperado:**
- Resposta útil quando há logs.
- Tratamento elegante quando não há histórico.

### Caso C3 — Confirmação rica (assistente + WhatsApp)
**Onde ir:** ação destrutiva/confirmável pelo assistente  
**Passos:**
1. Disparar uma ação que peça confirmação.
2. Ler o resumo apresentado antes de confirmar.
**Esperado:**
- Resumo operacional claro (cliente, orçamento, valores, alterações).
- Sem descrição técnica crua de tool.

## D. Admin — Schema drift

### Caso D1 — Snapshot e preview dry-run
**Onde ir:** admin de configuração/schema drift  
**Passos:**
1. Acessar tela/rota de schema drift.
2. Executar snapshot.
3. Rodar preview dry-run.
**Esperado:**
- Snapshot salvo sem erro.
- Preview mostra impacto sem aplicar mudança real.

### Caso D2 — Dashboard visual de diff
**Onde ir:** `admin-config.html`  
**Passos:**
1. Abrir dashboard de diff.
2. Comparar duas referências/snapshots.
**Esperado:**
- Diferenças visuais legíveis.
- Sem quebrar layout do admin.

## E. Banco e infraestrutura

### Caso E1 — Migration `assistente_instrucoes`
**Onde ir:** startup backend + operação no assistente  
**Passos:**
1. Aplicar migrations.
2. Subir backend.
3. Executar fluxo que use instruções da empresa.
**Esperado:**
- Sem erro de coluna ausente.
- Campo persistindo corretamente.

### Caso E2 — Migration de schema drift snapshots
**Onde ir:** backend/admin  
**Passos:**
1. Aplicar migrations.
2. Executar Caso D1.
**Esperado:**
- Tabelas/colunas necessárias existem.
- Fluxo completo sem erro SQL.

## F. PWA

### Caso F1 — Manifest + Service Worker
**Onde ir:** `index.html` e install prompt do navegador  
**Passos:**
1. Abrir app em navegador compatível.
2. Verificar se app é instalável.
3. Checar registro do Service Worker.
**Esperado:**
- Manifest carregado.
- SW ativo sem erro crítico de console.

### Caso F2 — `assetlinks.json` atualizado
**Onde ir:** rota pública de `assetlinks.json`  
**Passos:**
1. Abrir endpoint da associação digital.
2. Validar presença do SHA-256 esperado.
**Esperado:**
- Conteúdo consistente com configuração Bubblewrap.

---

## Mapa commit -> foco principal de teste

- `d4d222f`, `fb6194b` -> Casos A2, A3  
- `acd8e2d`, `a6342e1` -> Casos A1, A2  
- `0b263ef`, `10f4e8a`, `5a72933`, `f34b807` -> Casos B1, B2, B3, B4  
- `88c9d8c`, `c71fc30` -> Casos C1, C2, C3  
- `e469e42`, `e2c0401` -> Caso C3  
- `7cb6ee4`, `f08c8c5` -> Casos D1, D2  
- `5504235` -> Caso E1  
- `9d2d255`, `84a1c99`, `3f28fd9` -> Casos F1, F2  
- `bf7c200`, `833837d` -> documentação/regra interna (sem fluxo funcional obrigatório)

---

## Ordem sugerida de execução (otimizada)

1. **E1 + E2** (garantir base e migrations ok).  
2. **A1/A2/A3** (UI e stream).  
3. **B1/B2/B3/B4** (inteligência e personalização).  
4. **C1/C2/C3** (tools e segurança de confirmação).  
5. **D1/D2** (admin/schema drift).  
6. **F1/F2** (PWA e asset links).

---

## Critérios de aceite geral

- Nenhum erro 500 no backend durante os fluxos.
- Nenhum erro crítico no console do frontend durante cenários A–F.
- Sem regressão visual relevante no mobile do assistente.
- Confirmações sensíveis sempre com contexto operacional legível.
- Fluxos de admin schema drift executáveis de ponta a ponta.
