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

> **[REGRA CRÍTICA PARA INTELIGÊNCIA ARTIFICIAL (ROTEAMENTO)]:**
> Qualquer alteração nos arquivos `ai_intention_classifier.py`, em descrições de ferramentas (tools) ou adição de novos gatilhos **OBRIGA** a execução do teste de regressão antes do término da tarefa: `cd sistema && pytest tests/test_ai_tool_routing.py`. Nenhuma PR ou commit dessa área deve seguir sem os testes verdes.

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
- Preferir definir fallback de modelos IA e opções equivalentes na `.env` (em conjunto com `AI_MODEL` / `AI_TECHNICAL_MODEL`), em vez de fornecedores ou modelos fixos no código, para permitir troca só por configuração.
- Não sobrescrever ou recriar `sistema/.env` sem pedido explícito; quando já existir configuração, inspecionar e diagnosticar antes de propor escrita.
- Em pedidos de commit, preferir incluir apenas os ficheiros do escopo da alteração, evitando misturar mudanças não relacionadas no mesmo commit; se pedirem “tudo o pendente”, separar por tema (ex.: NF-e vs docs), confirmar artefatos locais (`graphify-out/`, pastas de outro projeto, HTML solto na raiz) e em geral ignorá-los com `.gitignore` em vez de versionar no repositório principal.
- No assistente IA, preferir evolução visual limpa e moderna (menos gradiente chamativo; evitar loading com aparência de “engrenagem” girando); em cards de orçamento em telas pequenas, preferir ações compactas (ícone + texto curto) para não quebrar o layout; no mesmo fluxo, priorizar estabilidade e anti-regressão (contratos claros, testes de regressão, mudanças incrementais antes de refactors amplos).
- Quando o utilizador pedir para fixar respostas em português do Brasil no repositório, além do `AGENTS.md` pode valer a pena manter `.cursor/rules/idioma-pt-br.mdc` com `alwaysApply: true` para injeção consistente no workspace.
- Para autonomia do assistente, privilegiar desenho arquitetural (políticas, orquestração, capacidades) em detrimento de multiplicar tools como solução principal (“tool sprawl”).
- Na evolução do assistente IA, priorizar autonomia real para consultar dados e gerar relatórios completos, sem restringir o foco apenas a ranking/receita.
- Em telas usadas por operadores leigos, priorizar UX simplificada com menos botões visíveis e agrupamento de ações secundárias em menu “Mais”, preservando acesso ao modo avançado.
- Quando o usuário solicitar visualização analítica, priorizar respostas com tabela renderizada e formatação condicional (cores/estilo), em vez de texto simples.
- Em análises de consumo de tokens do assistente IA, preferir diagnóstico detalhado de causa raiz com proposta de ajuste que preserve funcionalidades e desempenho.
- Para Mercado Livre em produção, definir `ML_TOKEN_CRYPTO_SECRET` com segredo aleatório longo gerado localmente (ex.: `openssl rand -hex 32`); não é fornecido pelo ML e alterações posteriores podem invalidar tokens já cifrados com o prefixo `encv1:` até reautenticação.
- No fluxo de emissão de NF-e no COTTE, priorizar verificação e pré-visualização do payload (incluindo prévia local estilo DANFE em HTML/PDF com dados locais quando fizer sentido) antes de confirmar o envio à Notaas/SEFAZ ou à Focus NFe; no provedor Focus, alinhar com `docs/ApiFocus.md` e com a API oficial (emitir/consultar/cancelar/CC-e/pré-visualização de DANFE e reenvio de hook).

## Learned Workspace Facts
- No desenvolvimento local, o frontend em `cotte-frontend` costuma ser servido com o prefixo `/app/`; se a UI parecer desatualizada mas o HTML/CSS servido já contiver as mudanças, tratar como problema provável de cache do navegador ou de service worker antes de concluir falha do servidor. Em páginas HTTPS (ex.: produção na Railway), chamadas de diagnóstico no browser para `http://127.0.0.1` tendem a falhar (mixed content); preferir logs no servidor ou Railway CLI/MCP autenticados (`railway login`).
- Na tool `listar_orcamentos`, perguntas sobre aprovação em dias civis (“ontem”, “hoje”, intervalo) devem usar `aprovado_em_de`/`aprovado_em_ate` (YYYY-MM-DD, dia civil em America/Sao_Paulo); o parâmetro `dias` filtra pela data de criação (`criado_em`). O executor normaliza argumentos comuns (ajusta `dias`/`limit` e converte literais “ontem”/“hoje” para datas ISO). No card de lista, o botão “Carregar mais” repassa `cursor`, `limit` e, quando o filtro for por aprovação, `aprovado_em_de`/`aprovado_em_ate` (não apenas `dias`), para manter o mesmo critério na página seguinte.
- Assistente V2 (hub): o payload pode incluir `engine` (ex.: `operational` por omissão); o copiloto técnico interno deve usar `POST /ai/copiloto-interno` — não enviar `engine=internal_copilot` no fluxo operacional de `/ai/assistente` (a API rejeita com 400). A tool `executar_sql_analitico` em `internal_copilot` segue `is_sql_agent_enabled`, não a de Code RAG. `GET /ai/assistente/capabilities` expõe flags, engines, `components` e `available_engines` (consumo típico via `CapabilityFlagsService` em `cotte-frontend`). Operação inclui `GET /api/v1/ai/observabilidade/resumo`, rollout por empresa (`GET /api/v1/ai/rollout/status`) e plano global em `GET`/`PUT /api/v1/ai/rollout/plan` (superadmin, `config_global` / `ai_rollout_v2_plan`); o executor pode propagar a engine em `_meta` no `ToolCallLog`.
- No `assistente_unificado_v2`, o caminho padrão ainda executa o fluxo legado de `tool calling` (`ia_service.chat` + `tool_calls` + `tool_executor`); a autonomia semântica entra por rollout/flag (`V2_SEMANTIC_AUTONOMY`) e convive com fallback legado para evitar regressões. Com `AI_PROVIDER=openrouter`, valores como `AI_MODEL=google/gemini-2.5-flash` e `AI_TECHNICAL_MODEL=google/gemini-2.5-flash` no `.env` são aceitos e normalizados para LiteLLM/OpenRouter; `input_tokens` na resposta agrega consumo de múltiplas chamadas LLM no mesmo turno (loop de tools e retries), não uma única chamada.
- Se `AI_API_KEY` estiver definida no `.env`, a resolução de chave no `IAService` pode priorizá-la sobre chaves específicas do provedor (ex.: `OPENAI_API_KEY`); para erros genéricos do LiteLLM (ex.: mensagens com “Provider List”), verificar valor vazio, modelo incompatível com a chave ou precedência inesperada.
- No assistente, relatórios de vendas e contas a receber usam `gerar_relatorio_vendas` e `gerar_relatorio_contas_a_receber` em `financeiro_tools` (registry em `ai_tools/__init__.py`); `POST /api/v1/ai/orcamento/confirmar` reutiliza o resolvedor de catálogo de `criar_orcamento` (vínculo a `Servico` por nome aproximado; `cadastrar_materiais_novos` controla materiais novos). A timeline `HistoricoEdicao` regista ações do assistente (aprovar/recusar, editar, envios, anexos) para auditoria.
- Monitor AI (`/api/v1/superadmin/monitor-ai`, ex.: `/status`, `/agent`): o frontend deve usar os helpers de `api.js` (base com `/api/v1`), evitando `/api/superadmin/...` sem `v1`. Em `ai_chat_sessoes`, `UniqueViolation` na PK costuma ser corrida entre inserts; alertas de empresa diferente sugerem o mesmo `sessao_id` noutro tenant — gerar novo identificador de sessão ao mudar de empresa ou utilizador.
- Em deploy com Alembic (ex.: Railway, imagem com `sistema/release.sh`), `Can't locate revision '…'` indica que o Postgres já registra uma revisão em `alembic_version` que não existe nos ficheiros da migração no commit deployado (Root Directory típico `sistema`); alinhar a branch/commit de deploy com as migrações já aplicadas ao banco antes de redeploy. No OAuth Mercado Livre, `ML_REDIRECT_URI` deve coincidir exatamente com o app; a plataforma pode exigir PKCE (`code_challenge` na autorização e `code_verifier` na troca do código); após autorizar, o fluxo costuma voltar para `configuracoes.html` com `ml=connected` ou `ml=error`; em desenvolvimento local, abrir integrações na mesma origem (host/porta) da API para não perder o JWT no redirect.
- No catálogo (`cotte-frontend/catalogo.html`), o botão `🔗 ML` e o badge de vínculo só são exibidos quando `GET /api/v1/mercadolivre/status` indica `connected: true`; falha ou mudança de contrato nesse endpoint tende a ocultar a ação por desenho defensivo.
- Integração NF-e: **Notaas** (legado NF-e/NFC-e) — polling de status em NF-e deve usar `GET /nfe/invoices/{invoiceId}/status` (o path `GET /invoices/{invoiceId}/status` é de NFS-e; path errado em NF-e retorna 404). Rejeições SEFAZ frequentes: cStat 209 (IE do emitente); cStat 972 (`infRespTec`) — em geral cadastro no painel do provedor da API key. **Focus NFe** — HTTP Basic (token como utilizador, senha vazia) e `FOCUS_AMBIENTE` coerente com o host de notas; emissão em homologação em `homologacao.focusnfe.com.br` costuma exigir `FOCUS_TOKEN_HOMOLOGACAO` (token de homologação do painel Focus — Painel API → Tokens); `FOCUS_TOKEN` com token principal segue para cadastro de empresa/certificado em `https://api.focusnfe.com.br` (não usar o host só de homologação de notas para fluxo de empresas). `401` em homologação muitas vezes indica token de tipo errado para o host, não falha no JSON da NF. **Webhook** `POST /api/v1/notas-fiscais/webhook/focus` existe no backend mas só atualiza o sistema se a URL estiver cadastrada no painel Focus (HTTPS público); cabeçalho típico `Authorization` com valor `Basic`+Base64(`token:`) alinhado ao token do ambiente no servidor, ou token puro no header; no `.env`/Railway fica só o token em texto (não colar o `Basic…` completo). Modal/listagem de emissão consultam estado no banco local — sem webhook ou com demora na SEFAZ pode parecer timeout com nota já “Autorizado” na Focus; usar `sincronizar-focus` ou atualizar a lista. `404` com `nao_encontrado` costuma ser host/path errado ou identificador de empresa incorreto; `422` com `Município inválido: -` costuma ser endereço fiscal incompleto; `codigo_municipio` IBGE (7–8 dígitos) ajuda.
- Pré-visualização DANFE ou outros PDFs de NF-e no `cotte-frontend`: tratar respostas `application/pdf` com opção `expectBinary` (ou equivalente) em `api.js` / `ApiService`, para não interpretar o corpo como JSON.
- Emissão assíncrona de NF-e: em `BackgroundTasks`, passar apenas IDs (nota/empresa) para o worker que abre sessão própria — evitar fechar a sessão HTTP e depois usar instâncias ORM desanexadas na task.
