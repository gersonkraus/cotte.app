# Sistema de Sugestoes Proativas Hibridas no Assistente IA

## 1) Visao Geral

Objetivo: aumentar a taxa de acao do usuario no assistente, oferecendo sugestoes proativas contextualizadas (acoes recomendadas) em momentos-chave da jornada.

A proposta e hibrida:
- Regras deterministicas para sinais claros e auditaveis.
- Enriquecimento por IA para priorizacao fina, texto da sugestao e adequacao ao contexto conversacional.

Escopo funcional aprovado:
- Momentos: abertura do assistente, durante conversa e pos-acao.
- Dominios: orcamentos, financeiro, clientes, comercial/leads e agendamentos.
- Priorizacao: guiada pelo contexto atual da conversa.

Nao objetivos desta fase:
- Motor de recomendacao totalmente autonomo sem regras.
- Alteracao de contratos legados que nao participam do fluxo do assistente.

## 2) Objetivos de Negocio e Criterios de Sucesso

### Objetivos
- Aumentar execucao de acoes de alto impacto (follow-up, cobranca, confirmacao, reagendamento).
- Reduzir inercia operacional em casos evidentes (pendencias, atrasos, risco de perda).
- Tornar o assistente consultivo, nao apenas reativo.

### Metricas (MVP)
- Taxa de clique/aceite de sugestao (CTR de sugestoes).
- Taxa de conclusao da acao sugerida em ate 24h.
- Tempo medio entre insight exibido e primeira acao.
- Cobertura por dominio (quantas sessoes receberam sugestoes relevantes).
- Taxa de repeticao rejeitada (sugestoes ignoradas repetidamente).

### SLOs iniciais
- P95 de `GET /ai/insights` <= 250 ms com cache quente.
- P95 de enrich IA <= 1.2 s quando executado sob demanda.

## 3) Arquitetura

## 3.1 Componentes

### Insight Engine
Orquestrador principal que compoe os blocos abaixo:

1. Rule Engine
- Avalia regras por dominio com base no estado operacional da empresa.
- Gera candidatos de insight padronizados.

2. AI Enricher
- Opcional por insight.
- Refina titulo, descricao, CTA e prioridade em cenarios ambiguos.

3. Context Matcher
- Usa contexto da conversa/sessao para filtrar e ranquear insights por dominio ativo.

4. Dedupe and Cooldown
- Evita repeticao excessiva por sessao e por empresa.
- Aplica janelas de supressao por insight.

5. Insight Cache
- Cache por empresa com TTL 5 minutos.
- Guardara lista base de candidatos e metadados de ranking.

## 3.2 Integracao com fluxos existentes

- Abertura do assistente:
  - Frontend consulta `GET /ai/insights` e mostra top 5.

- Durante conversa (`POST /ai/assistente`):
  - Backend injeta `insights` na resposta final, filtrados por dominio da conversa.

- Pos-acao de tool:
  - Apos sucesso de acao executada, retorna sugestao complementar contextual (next best action).

## 3.3 Dependencias internas

- `SessionStore` para contexto de sessao e historico curto.
- `ContextBuilder` para snapshots de dados de negocio por intencao.
- `SemanticMemoryStore` para reforco de contexto semantico.

## 4) Modelo de Dados e Contratos

## 4.1 Estrutura canonica de insight

```json
{
  "id": "string",
  "tipo": "acao_sugerida|alerta|oportunidade",
  "prioridade": "critica|alta|media|baixa",
  "dominio": "orcamentos|financeiro|clientes|comercial|agendamentos",
  "titulo": "string",
  "descricao": "string",
  "acao": {
    "tipo": "abrir_tela|executar_prompt|executar_tool",
    "label": "string",
    "prompt": "string",
    "tool": "string",
    "args": {}
  },
  "contexto": {},
  "score": 0.0,
  "fonte": "regra|ia|hibrido",
  "expira_em": "2026-04-29T15:00:00Z",
  "cooldown_ate": "2026-04-29T16:00:00Z"
}
```

Observacoes:
- `id` deve ser deterministico para dedupe (ex.: hash de tipo+dominio+entidade).
- `score` normalizado de 0 a 1 para ranking final.
- `fonte` explicita a origem para auditoria.

## 4.2 Endpoint de abertura

`GET /api/v1/ai/insights`

Query params:
- `limit` (opcional, default 5, max 10)
- `dominio` (opcional)

Response:

```json
{
  "insights": [],
  "total": 0,
  "cache": {
    "hit": true,
    "gerado_em": "2026-04-29T15:00:00Z",
    "expira_em": "2026-04-29T15:05:00Z"
  }
}
```

## 4.3 Integracao no `POST /api/v1/ai/assistente`

Sem quebrar contrato atual: adicionar campo opcional `insights` no payload de resposta.

```json
{
  "resposta": "...",
  "insights": []
}
```

## 4.4 Registro de feedback

`POST /api/v1/ai/insights/feedback`

Payload:

```json
{
  "insight_id": "string",
  "acao": "clicou|executou|dispensou|ignorado",
  "sessao_id": "string"
}
```

Objetivo: alimentar aprendizado de priorizacao e evitar repeticao de baixa utilidade.

## 5) Regras de Negocio por Dominio (Rule Engine)

## 5.1 Orcamentos

1. Pendente ha mais de 5 dias
- Sugestao: follow-up com cliente.
- Prioridade: alta.

2. Orcamento aprovado sem agendamento vinculado
- Sugestao: agendar execucao.
- Prioridade: media.

3. Taxa de aprovacao dos ultimos 30 dias abaixo de 30%
- Sugestao: revisar precificacao e condicoes.
- Prioridade: media.

## 5.2 Financeiro

1. Conta relevante vencendo em ate 3 dias
- Sugestao: confirmar pagamento/recebimento.
- Prioridade: alta.

2. Saldo projetado negativo na janela curta
- Sugestao: alerta de caixa e acao de contingencia.
- Prioridade: critica.

3. Inadimplencia acima de 20%
- Sugestao: iniciar rotina de cobranca segmentada.
- Prioridade: alta.

## 5.3 Clientes

1. Cliente ativo sem contato ha mais de 30 dias
- Sugestao: campanha de reativacao.
- Prioridade: media.

2. Cliente estrategico com queda de recorrencia
- Sugestao: contato consultivo proativo.
- Prioridade: alta.

## 5.4 Comercial/Leads

1. Lead sem interacao ha mais de 7 dias
- Sugestao: retomar contato.
- Prioridade: alta.

2. Proposta enviada sem resposta ha mais de 5 dias
- Sugestao: follow-up com argumento orientado.
- Prioridade: alta.

## 5.5 Agendamentos

1. Agendamentos de amanha sem confirmacao
- Sugestao: confirmar automaticamente.
- Prioridade: alta.

2. Slots ociosos no dia
- Sugestao: acao comercial rapida para ocupacao.
- Prioridade: media.

## 6) Priorizacao e Ranking

Formula de score final (exemplo):

`score_final = score_regra * 0.55 + score_contexto * 0.30 + score_hist_feedback * 0.15`

Onde:
- `score_regra`: severidade e urgencia da regra.
- `score_contexto`: aderencia ao dominio/entidade da conversa.
- `score_hist_feedback`: utilidade historica daquela classe de insight na empresa.

Desempate:
1. Maior prioridade semantica (`critica > alta > media > baixa`)
2. Menor tempo para expiracao
3. Maior recencia do evento de origem

## 7) Fluxos de Entrega

## 7.1 Abertura do assistente

1. Frontend abre `assistente-ia.html`.
2. Chama `GET /ai/insights?limit=5`.
3. Renderiza chips/cards com CTA.

## 7.2 Durante conversa

1. Usuario envia mensagem.
2. Assistente processa intencao normal.
3. Context Matcher identifica dominio corrente.
4. Retorna ate 3 insights relevantes anexos a resposta.

## 7.3 Pos-acao

1. Tool executada com sucesso.
2. Motor busca next best action da mesma entidade.
3. Injeta 1 sugestao de continuidade.

## 8) Frontend (UX e Integracao)

## 8.1 Estados de exibicao
- `loading`: skeleton curto.
- `ready`: lista de insights.
- `empty`: nenhum insight relevante.
- `error`: fallback silencioso sem quebrar chat.

## 8.2 Padrao visual
- Abertura: cards compactos acima da area de input.
- Conversa: quick replies contextuais abaixo da ultima resposta da IA.
- Pos-acao: CTA inline na resposta da tool.

## 8.3 Interacoes
- Clique em insight preenche prompt sugerido ou executa acao direta.
- Dismiss registra feedback e aciona cooldown local.
- Nao repetir insight dispensado na mesma sessao.

## 8.4 Acessibilidade
- Navegacao por teclado nos chips.
- `aria-live` para atualizacao de sugestoes novas.
- Contraste e foco visivel conforme padrao da pagina.

## 9) Persistencia, Cache e Confiabilidade

## 9.1 Cache
- Escopo: por `empresa_id`.
- TTL: 5 minutos.
- Invalida por eventos-chave (mudanca de status relevante).

## 9.2 Persistencia de telemetria
- Registrar exposicao, clique, execucao e dismiss.
- Associar `sessao_id`, `empresa_id`, `dominio`, `insight_id`.

## 9.3 Resiliencia
- Falha no AI Enricher nao derruba sugestoes de regra.
- Falha no endpoint de insights nao bloqueia chat principal.
- Timeout curto para enriquecimento sob demanda.

## 10) Seguranca e Guardrails

- Respeitar escopo tenant por `empresa_id` em todas as consultas.
- Nao expor dados sensiveis no texto do insight.
- Sanitizar prompts gerados para evitar injecao operacional.
- Auditar origem (`fonte`) e acao sugerida para rastreabilidade.

## 11) Plano de Implementacao (alto nivel)

1. Backend core
- Criar `app/services/insight_engine.py`.
- Implementar Rule Engine modular por dominio.
- Implementar ranking, dedupe e cooldown.

2. APIs
- Criar `GET /ai/insights`.
- Injetar `insights` em `POST /ai/assistente` sem quebra de contrato.
- Criar endpoint de feedback.

3. Frontend
- Consumir endpoint na abertura em `assistente-ia.js`.
- Renderizar chips/cards e quick replies contextuais.
- Enviar feedback de uso.

4. Observabilidade
- Logs estruturados por insight lifecycle.
- Metricas de exposicao e conversao.

## 12) Testes e Validacao

## 12.1 Unitarios
- Regras por dominio.
- Ranking e desempate.
- Dedupe/cooldown.

## 12.2 Integracao
- `GET /ai/insights` com cache hit/miss.
- Injecao de `insights` em `POST /ai/assistente`.
- Feedback persistido corretamente.

## 12.3 E2E funcional
- Abertura exibe top 5.
- Conversa em dominio especifico recebe sugestoes aderentes.
- Pos-acao apresenta next best action.

## 12.4 Criterios de aceite
- Sem regressao no fluxo atual de chat.
- Insights relevantes em pelo menos 3 dominios no MVP.
- Telemetria disponivel para acompanhamento semanal.

## 13) Riscos, Trade-offs e Mitigacoes

1. Risco: ruido de sugestoes (spam)
- Mitigacao: cooldown, limite por resposta, feedback de dismiss.

2. Risco: latencia extra durante conversa
- Mitigacao: cache base + enrich seletivo com timeout.

3. Risco: recomendacao pouco acionavel
- Mitigacao: CTA objetivo com acao direta sempre que possivel.

4. Trade-off principal
- Regras entregam previsibilidade e velocidade.
- IA adiciona qualidade contextual, com custo/latencia controlados.

## 14) Evolucoes Futuras (fora do MVP)

- Personalizacao por perfil de usuario (gestor, operador, comercial).
- Aprendizado continuo de ranking por empresa.
- Experimentos A/B de copy e formato de sugestao.
- Explicabilidade opcional: "por que esta sugestao apareceu".
