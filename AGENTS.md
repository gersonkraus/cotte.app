---
title: Agents
tags:
  - documentacao
prioridade: alta
status: documentado
---

# AGENTS.md

## Objetivo do projeto
Este projeto usa FastAPI no backend e frontend em HTML/CSS/JavaScript.
A prioridade é manter o sistema funcionando, corrigir problemas reais e implementar mudanças com o menor impacto possível.

## Complemento de orientação
Para detalhes complementares de contribuição, validação, boas práticas e organização do trabalho, consultar também `CONTRIBUTING.md`.

Índice gerado a partir de `docs/contribuicao.yaml` (resumos e ligações): [docs/contribuicao.md](docs/contribuicao.md).

## Idioma
- Responder sempre em português do Brasil.
- Explicar de forma clara, direta e objetiva.

## Ordem de precedência
Em caso de conflito, seguir esta ordem:

1. Segurança, integridade do sistema e prevenção de ações destrutivas.
2. Regras específicas deste projeto.
3. Evidência observável no código, configuração, logs, testes e comportamento real.
4. Menor alteração possível para resolver corretamente o problema.
5. Preferências de estilo e organização.

## Postura de execução
- Executar a tarefa até a conclusão quando o caminho estiver claro e for seguro.
- Não pedir confirmação para próximos passos óbvios, reversíveis e de baixo risco.
- Só pedir confirmação quando houver ambiguidade real, risco destrutivo, impacto irreversível ou mudança material de escopo.
- Se houver bloqueio, tentar uma abordagem alternativa segura antes de escalar.
- Não assumir comportamento sem evidência.
- Priorizar correção comprovável sobre hipótese.

## Regras gerais
- Entender o pedido antes de editar.
- Investigar os arquivos relevantes antes de propor ou aplicar mudanças.
- Fazer a menor alteração possível.
- Não refatorar áreas grandes sem pedido explícito.
- Não mudar arquitetura, stack, organização de pastas ou padrões sem necessidade clara.
- Não remover código existente sem verificar impacto.
- Não inventar dependências, serviços, rotas, arquivos ou comportamentos.
- Reutilizar padrões e utilitários existentes antes de criar algo novo.
- Manter diffs pequenos, legíveis, revisáveis e reversíveis.

## Prioridades
1. Corrigir bugs reais.
2. Preservar o funcionamento atual.
3. Evitar regressão no frontend.
4. Evitar quebra de integração entre frontend e backend.
5. Manter mudanças pequenas, legíveis e fáceis de validar.

## Critério de alteração mínima
Sempre preferir, nesta ordem:

1. Corrigir o ponto exato do problema.
2. Ajustar lógica, validação ou tratamento já existente.
3. Reutilizar utilitário, função ou padrão já presente no projeto.
4. Criar pequena função auxiliar local apenas se necessário.
5. Refatorar trechos maiores somente com justificativa clara.

## Antes de alterar
Antes de editar, sempre que aplicável:

- localizar o arquivo exato envolvido
- identificar rota, função, classe, componente, seletor ou fluxo afetado
- mapear quem chama e quem depende do trecho
- verificar se o problema é de código, configuração, dados, integração ou ambiente
- avaliar impacto em backend, frontend e contrato de API

## Regras para backend
- Preservar contratos de API existentes sempre que possível.
- Manter coerência com FastAPI.
- Respeitar schemas, validações e tipagem.
- Evitar duplicação de lógica.
- Antes de alterar endpoint, verificar onde ele é chamado.
- Antes de alterar payload, verificar impacto no frontend.
- Não alterar formato de resposta sem necessidade comprovada.
- Se uma mudança de contrato for inevitável, apontar claramente impacto, risco e validação necessária.

## Regras para frontend
- Não quebrar layout existente sem necessidade.
- Não alterar estrutura visual só por preferência.
- Evitar mudanças amplas em CSS.
- Evitar mudanças globais em seletores.
- Antes de alterar JavaScript, verificar eventos, seletores, chamadas de API e comportamento do DOM.
- Preservar responsividade e fluxo atual.
- Preservar estados visuais, feedbacks de carregamento, erro e sucesso sempre que existirem.
- Se houver risco de quebrar interface, apontar isso claramente.
- Não misturar correção funcional com mudança estética desnecessária.

## Regras para debug
Fluxo obrigatório:

1. Reproduzir o problema.
2. Localizar a causa raiz.
3. Corrigir com a menor mudança possível.
4. Validar a correção.
5. Explicar o que mudou.
6. Informar riscos restantes.

## Regras para configuração
- Verificar arquivos de ambiente e configuração com cuidado.
- Não alterar variáveis de ambiente sem necessidade.
- Não assumir valores de produção.
- Identificar claramente quando o problema é de configuração e não de código.
- Nunca expor segredos, chaves, tokens ou credenciais.

## Regras para limpeza e simplificação
Quando a tarefa envolver cleanup, refactor ou simplificação:

- escrever primeiro um plano curto e seguro
- proteger comportamento existente com validação adequada antes de mexer
- preferir remoção a adição
- preferir simplificar fluxo existente a criar nova abstração
- não adicionar dependências sem pedido explícito
- não misturar limpeza ampla com correção funcional sem necessidade clara

## Regras para testes e validação
Sempre que fizer sentido:

- rodar testes existentes
- validar rotas afetadas
- validar chamadas frontend/backend
- validar logs
- validar build ou execução local
- validar manualmente o fluxo alterado

Ao validar:
- verificar resultado esperado e ausência de regressão óbvia
- ler o resultado real antes de concluir
- não declarar sucesso sem evidência suficiente
- declarar explicitamente o que não foi validado quando houver limitação

## Regras para verificações, análises e alterações
Ao realizar qualquer verificação, análise, correção ou alteração, incluir também:

### Melhorias essenciais
- Sugestão de pelo menos 2 sugestões de melhorias relevantes e essenciais ligadas ao contexto analisado

### Ideias inovadoras
- Sugestão de pelo menos 2 ideias inovadoras para facilitar o processo ligado ao contexto analisado

### Melhorias de frontend de alto impacto
- Sugestão de pelo menos 2 melhorias específicas de frontend que fariam diferença real no contexto analisado

Esses pontos devem ser contextuais, práticos e conectados ao problema avaliado.
Não sugerir melhorias genéricas sem relação com o caso.

## Regras para tarefas grandes
Antes de implementar:

- quebrar em etapas pequenas
- identificar riscos
- propor ordem segura de execução
- apontar o que deve ser validado em cada etapa
- evitar mudar múltiplos fluxos críticos ao mesmo tempo
- priorizar entregas incrementais e verificáveis

## Regras para deploy e commits
- O processo de deploy e espelhamento é 100% automatizado via hook `post-commit`.
- Quando o usuário pedir "commit e push" ou "faça o deploy", apenas rodar `git commit` e `git push` no repositório local principal (`/home/gk/Projeto-izi`).
- Não fazer deploy manual.
- Não rodar scripts de deploy arbitrários.
- Não copiar arquivos manualmente para outras pastas do sistema, como `/home/gk/cotte.app`.
- O hook automático executará em background:
  1. sincronização do changelog com o Notion
  2. limpeza da pasta de destino e extração de arquivos rastreados com `git archive`
  3. verificação bloqueadora de segurança para impedir cópia acidental de `.env`, `.key` e `.pem`
  4. commit na pasta de destino e deploy final para a Railway
  5. script de rebuild do `graphify`

## O que evitar
- Refatoração ampla sem pedido.
- Mudança estética desnecessária.
- Alteração de múltiplos fluxos ao mesmo tempo.
- Correções criativas sem confirmar causa raiz.
- Mudanças grandes em CSS global.
- Alterar API e frontend ao mesmo tempo sem mapear impacto.
- Alterar contratos sem verificar consumidores.
- Declarar conclusão sem validar.
- Adicionar complexidade para resolver problema simples.

## Resultado esperado
Toda resposta técnica deve deixar claro:

- o que foi entendido
- onde está o problema
- quais arquivos importam
- qual é o plano
- o que foi alterado, quando houver alteração
- como validar
- quais riscos existem
- 2 melhorias essenciais relacionadas ao contexto
- 2 ideias inovadoras relacionadas ao contexto
- 2 melhorias de frontend de alto impacto relacionadas ao contexto

## Formato padrão da resposta técnica
Sempre que possível, usar esta ordem:

1. Entendimento
2. Problema identificado
3. Arquivos relevantes
4. Plano
5. Alterações realizadas
6. Como validar
7. Riscos restantes
8. Melhorias essenciais sugeridas
9. Ideias inovadoras
10. Melhorias de frontend de alto impacto

## Princípio final
Resolver com segurança, evidência e o menor impacto possível.
Quando houver dúvida entre uma solução maior e uma solução menor que resolve corretamente, preferir a menor.
Quando houver dúvida entre suposição e verificação, verificar.

## Learned User Preferences
- Em pedidos de commit, preferir incluir apenas os ficheiros do escopo da alteração, evitando misturar mudanças não relacionadas no mesmo commit.
- No assistente IA, preferir evolução visual limpa e moderna (menos gradiente chamativo; evitar loading com aparência de “engrenagem” girando); em cards de orçamento em telas pequenas, preferir ações compactas (ícone + texto curto) para não quebrar o layout.
- No fluxo do assistente IA, priorizar estabilidade e anti-regressão: contratos claros, testes de regressão e mudanças incrementais antes de refactors amplos.
- Para autonomia do assistente, privilegiar desenho arquitetural (políticas, orquestração, capacidades) em detrimento de multiplicar tools como solução principal (“tool sprawl”).
- Na evolução do assistente IA, priorizar autonomia real para consultar dados e gerar relatórios completos, sem restringir o foco apenas a ranking/receita.
- Quando o usuário solicitar visualização analítica, priorizar respostas com tabela renderizada e formatação condicional (cores/estilo), em vez de texto simples.
- Em análises de consumo de tokens do assistente IA, preferir diagnóstico detalhado de causa raiz com proposta de ajuste que preserve funcionalidades e desempenho.

## Learned Workspace Facts
- No desenvolvimento local, o frontend em `cotte-frontend` costuma ser servido com o prefixo `/app/`; se a UI parecer desatualizada mas o HTML/CSS servido já contiver as mudanças, tratar como problema provável de cache do navegador ou de service worker antes de concluir falha do servidor.
- Na tool `listar_orcamentos`, perguntas sobre aprovação em dias civis (“ontem”, “hoje”, intervalo) devem usar `aprovado_em_de`/`aprovado_em_ate` (YYYY-MM-DD, dia civil em America/Sao_Paulo); o parâmetro `dias` filtra pela data de criação (`criado_em`). O executor normaliza argumentos comuns (ajusta `dias`/`limit` e converte literais “ontem”/“hoje” para datas ISO). No card de lista, o botão “Carregar mais” repassa `cursor`, `limit` e, quando o filtro for por aprovação, `aprovado_em_de`/`aprovado_em_ate` (não apenas `dias`), para manter o mesmo critério na página seguinte.
- Orçamentos em estado `APROVADO` sem `aprovado_em` preenchido podem não aparecer em listagens filtradas por data de aprovação até correção ou backfill dos dados.
- No assistente V2 (hub), o payload pode incluir `engine` (ex.: `operational` por omissão); o copiloto técnico interno deve usar o endpoint dedicado `POST /ai/copiloto-interno` — não enviar `engine=internal_copilot` no fluxo operacional de `/ai/assistente` (a API rejeita com 400). No registry de engines, a disponibilidade da tool `executar_sql_analitico` no engine `internal_copilot` segue a flag de SQL Agent (`is_sql_agent_enabled`), não a de Code RAG. `GET /ai/assistente/capabilities` expõe para o frontend flags, engines, `components` e `available_engines` (consumo típico via `CapabilityFlagsService` em `cotte-frontend`).
- O Code RAG do código-fonte do repositório usa índice lexical incremental/persistente; não há embeddings vetoriais por omissão (implica trade-offs de recall semântico face a busca vetorial).
- Operação IA V2 inclui `GET /api/v1/ai/observabilidade/resumo` (resumo por janela) e rollout por empresa via `GET /api/v1/ai/rollout/status`; leitura/alteração do plano global de rollout é restrita a superadmin em `GET`/`PUT /api/v1/ai/rollout/plan` (persistência em `config_global`, chave típica `ai_rollout_v2_plan`). O executor pode propagar a engine atual em `_meta` nos argumentos registrados no `ToolCallLog` para agregações por engine.
- No `assistente_unificado_v2`, o caminho padrão ainda executa o fluxo legado de `tool calling` (`ia_service.chat` + `tool_calls` + `tool_executor`); a autonomia semântica entra por rollout/flag (`V2_SEMANTIC_AUTONOMY`) e convive com fallback legado para evitar regressões.
- Na configuração atual do `IAService`, quando `AI_PROVIDER=openrouter`, valores como `AI_MODEL=google/gemini-2.5-flash` e `AI_TECHNICAL_MODEL=google/gemini-2.5-flash` são aceitos no `.env` (formato `KEY=value`) e normalizados internamente para o formato esperado pelo LiteLLM/OpenRouter. No assistente IA V2, o valor de `input_tokens` reportado na resposta agrega o consumo de múltiplas chamadas LLM no mesmo turno (loop de tools e eventuais retries), não apenas uma chamada única.
- No `ToolResult.to_llm_payload`, a flag `_llm_disable_preview` desativa a compactação para `rows_preview` e envia ao LLM a lista completa do payload (sem a própria flag), usada em cenários como pedido explícito de “todos os clientes”.
- No fluxo do assistente IA para orçamentos, o endpoint `POST /api/v1/ai/orcamento/confirmar` reutiliza o mesmo resolvedor de catálogo da tool `criar_orcamento`, tentando vincular automaticamente itens a `Servico` existente (por nome aproximado) antes de tratá-los como material novo; o parâmetro `cadastrar_materiais_novos` define se itens não encontrados geram cadastro novo em catálogo.
- A timeline/histórico de orçamentos (`HistoricoEdicao`) registra de forma consistente as ações disparadas pelo assistente (aprovar/recusar, editar orçamento/itens, envio por WhatsApp/e-mail, anexar documento), permitindo auditar detalhadamente o que foi feito via IA.
- Monitor AI (`/api/v1/superadmin/monitor-ai`, ex.: `/status`, `/agent`): o frontend deve usar os helpers de `api.js` (base com `/api/v1`), evitando `/api/superadmin/...` sem `v1`. Em `ai_chat_sessoes`, `UniqueViolation` na PK costuma ser corrida entre inserts; alertas de empresa diferente sugerem o mesmo `sessao_id` noutro tenant — gerar novo identificador de sessão ao mudar de empresa ou utilizador.
