# CONTRIBUTING.md

## Objetivo
Este documento define como contribuir com segurança, clareza e o menor impacto possível neste projeto.

O projeto usa:

- **Backend:** FastAPI
- **Frontend:** HTML, CSS e JavaScript

A prioridade é:

1. manter o sistema funcionando
2. corrigir problemas reais
3. evitar regressões
4. preservar contratos existentes
5. fazer mudanças pequenas, claras e fáceis de validar

### Relação com AGENTS.md

- **AGENTS.md** — resumo operacional para agentes e automação no repositório.
- **CONTRIBUTING.md** — guia estendido para pessoas (e revisão humana).
- **Índice unificado (gerado):** [docs/contribuicao.md](docs/contribuicao.md) — fonte: `docs/contribuicao.yaml`; após editar o YAML, rode `npm run generate:contribuicao` e faça commit de `docs/contribuicao.md`.
- Seções `##` críticas compartilhadas estão listadas em `docs/contribuicao.yaml` (`critical: true`) e são verificadas por `npm run validate:contributing`. Evite renomear esses títulos sem atualizar o YAML e o outro guia.
- Se no futuro houver **duplicação excessiva** entre os dois guias, prefira uma única fonte em `docs/` e manter em AGENTS/CONTRIBUTING apenas um parágrafo de contexto + link.

---

## Flags e telemetria (assistente IA)

No navegador, a chave de **localStorage** `cotte_assistente_metrics`:

- Valor **`1`**: ativa marcas e medidas da Performance API (`performance.mark` / `performance.measure`) no fluxo de confirmação de orçamento no assistente (mede tempo aproximado até paint após a ação).
- **Omissão ou outro valor**: telemetria desligada (comportamento padrão).

Uso recomendado apenas para **depuração de performance em ambiente local**, não para utilizadores finais em produção.

---

## Idioma e comunicação
- Escrever e responder em **português do Brasil**.
- Explicar mudanças de forma clara, direta e objetiva.
- Evitar descrições vagas.
- Sempre apontar riscos, impacto e forma de validação.

---

## Princípios de contribuição

### 1. Mudar o mínimo necessário
Toda contribuição deve buscar a menor alteração possível para resolver corretamente o problema.

Preferir nesta ordem:

1. corrigir o ponto exato do problema
2. ajustar lógica já existente
3. reutilizar função, utilitário ou padrão existente
4. criar pequeno helper local apenas se necessário
5. refatorar trechos maiores somente quando houver justificativa clara

### 2. Preservar comportamento atual
Antes de alterar qualquer fluxo, considerar:

- contratos de API existentes
- integração entre backend e frontend
- comportamento visual atual
- responsividade
- estados de carregamento, erro e sucesso
- impacto em fluxos já existentes

### 3. Não assumir sem evidência
Não assumir comportamento, causa ou impacto sem verificar no código, na configuração, nos logs, nos testes ou na execução real.

### 4. Evitar escopo desnecessário
Não misturar numa mesma alteração:

- correção funcional + mudança estética sem necessidade
- refatoração ampla + ajuste pontual
- mudanças de backend + frontend sem mapear impacto
- reorganização estrutural sem pedido explícito

---

## Ordem de precedência
Em caso de conflito, seguir esta ordem:

1. Segurança, integridade do sistema e prevenção de ações destrutivas
2. Regras específicas do projeto
3. Evidência observável no código, configuração, logs, testes e comportamento real
4. Menor alteração possível para resolver corretamente o problema
5. Preferências de estilo e organização

---

## Antes de contribuir
Antes de iniciar qualquer alteração, sempre que aplicável:

- localizar o arquivo exato envolvido
- identificar rota, função, classe, componente, seletor ou fluxo afetado
- mapear quem chama e quem depende do trecho
- verificar se o problema é de código, configuração, dados, integração ou ambiente
- avaliar impacto em backend, frontend e contrato de API
- definir a menor correção segura

---

## Regras para backend
Ao contribuir no backend:

- preservar contratos de API existentes sempre que possível
- manter coerência com FastAPI
- respeitar schemas, validações e tipagem
- evitar duplicação de lógica
- antes de alterar endpoint, verificar onde ele é chamado
- antes de alterar payload, verificar impacto no frontend
- não alterar formato de resposta sem necessidade comprovada
- se uma mudança de contrato for inevitável, documentar impacto, risco e validação necessária

### Boas práticas no backend
- preferir clareza a abstrações desnecessárias
- manter validações perto do fluxo real de uso
- evitar espalhar regra de negócio em vários pontos
- preservar nomes e estruturas já consistentes no projeto

---

## Regras para frontend
Ao contribuir no frontend:

- não quebrar layout existente sem necessidade
- não alterar estrutura visual só por preferência
- evitar mudanças amplas em CSS
- evitar mudanças globais em seletores
- antes de alterar JavaScript, verificar eventos, seletores, chamadas de API e comportamento do DOM
- preservar responsividade e fluxo atual
- preservar estados visuais, feedbacks de carregamento, erro e sucesso sempre que existirem
- se houver risco de quebrar interface, documentar claramente

### Boas práticas no frontend
- fazer mudanças localizadas
- evitar efeitos colaterais em telas não relacionadas
- validar comportamento em fluxos reais
- evitar acoplamento desnecessário entre JS, HTML e CSS
- preferir consistência visual a ajustes isolados de preferência pessoal

---

## Regras para debug
Toda correção de bug deve seguir este fluxo:

1. reproduzir o problema
2. localizar a causa raiz
3. corrigir com a menor mudança possível
4. validar a correção
5. explicar o que mudou
6. informar riscos restantes

### Durante o debug
- não parar na primeira hipótese plausível
- confirmar a causa com evidência
- diferenciar sintoma, causa raiz e efeito colateral
- verificar se o problema é isolado ou se afeta outros fluxos

---

## Regras para configuração
Ao lidar com configuração:

- verificar arquivos de ambiente e configuração com cuidado
- não alterar variáveis de ambiente sem necessidade
- não assumir valores de produção
- identificar claramente quando o problema é de configuração e não de código
- nunca expor segredos, chaves, tokens ou credenciais

---

## Regras para cleanup, refactor e simplificação
Quando a contribuição envolver limpeza, refatoração ou simplificação:

- escrever primeiro um plano curto e seguro
- proteger comportamento existente com validação adequada antes de mexer
- preferir remoção a adição
- preferir simplificar fluxo existente a criar nova abstração
- não adicionar dependências sem pedido explícito
- não misturar cleanup amplo com correção funcional sem necessidade clara

---

## Regras para testes e validação
Sempre que fizer sentido, validar:

- testes existentes
- rotas afetadas
- chamadas frontend/backend
- logs
- build ou execução local
- fluxo alterado manualmente

### Ao validar
- verificar o resultado esperado e ausência de regressão óbvia
- ler o resultado real antes de concluir
- não declarar sucesso sem evidência suficiente
- declarar explicitamente o que não foi validado quando houver limitação

---

## Padrão esperado para contribuições
Toda contribuição deve deixar claro:

- o que foi entendido
- onde está o problema
- quais arquivos importam
- qual é o plano
- o que foi alterado
- como validar
- quais riscos existem

Além disso, ao realizar uma verificação, análise, correção ou alteração relevante, incluir também:

### 1. Sugestão de Melhorias essenciais
Apontar pelo menos **2 melhorias relevantes e essenciais** relacionadas diretamente ao contexto analisado.

### 2. Sugestão de ideias inovadoras
Apontar pelo menos **2 ideias inovadoras** que facilitem o processo relacionado ao contexto analisado.

### 3. Sugestão de Melhorias de frontend de alto impacto
Apontar pelo menos **2 melhorias específicas de frontend** que fariam diferença real naquele contexto.

Esses pontos devem ser:

- contextuais
- práticos
- relacionados ao caso
- não genéricos

---

## Tarefas grandes
Quando a contribuição for grande, antes de implementar:

- quebrar em etapas pequenas
- identificar riscos
- propor ordem segura de execução
- apontar o que deve ser validado em cada etapa
- evitar mudar múltiplos fluxos críticos ao mesmo tempo
- priorizar entregas incrementais e verificáveis

---

## O que evitar
Evitar:

- refatoração ampla sem pedido
- mudança estética desnecessária
- alteração de múltiplos fluxos ao mesmo tempo
- correções criativas sem confirmar causa raiz
- mudanças grandes em CSS global
- alterar API e frontend ao mesmo tempo sem mapear impacto
- alterar contratos sem verificar consumidores
- declarar conclusão sem validar
- adicionar complexidade para resolver problema simples

---

## Commits
Os commits devem ser claros, objetivos e coerentes com o que foi realmente alterado.

### Regras para commits
- fazer commits pequenos e revisáveis
- evitar commits com múltiplos objetivos não relacionados
- alinhar mensagem de commit com a real intenção da mudança
- não esconder refatorações dentro de commits de correção simples

### Estrutura recomendada
Preferir mensagens que indiquem intenção, por exemplo:

- `corrige falha de validação no endpoint de login`
- `ajusta tratamento de erro no fluxo de upload`
- `reduz impacto de CSS no formulário de cadastro`

---

## Deploy e push
O processo de deploy e espelhamento é **100% automatizado** via hook `post-commit`.

Quando for solicitado:

- **"commit e push"**
- **"faça o deploy"**

deve ser feito apenas:

- `git commit`
- `git push`

no repositório local principal:

`/home/gk/Projeto-izi`

### Não fazer
- não fazer deploy manual
- não rodar scripts de deploy arbitrários
- não copiar arquivos manualmente para outras pastas do sistema
- não tentar sincronizações paralelas fora do fluxo padrão

### O hook automático executa em background
1. sincronização do changelog com o Notion
2. limpeza da pasta de destino e extração de arquivos rastreados com `git archive`
3. verificação bloqueadora de segurança para impedir cópia acidental de `.env`, `.key` e `.pem`
4. commit na pasta de destino e deploy final para a Railway
5. script de rebuild do `graphify`

---

## Checklist rápido antes de concluir uma contribuição
Antes de encerrar, confirmar:

- o problema foi realmente entendido
- a causa foi verificada
- a mudança foi a menor possível
- os arquivos impactados foram mapeados
- backend e frontend tiveram impacto avaliado
- o contrato existente foi preservado, quando possível
- a validação foi executada
- os riscos restantes foram documentados
- foram sugeridas 2 melhorias essenciais
- foram sugeridas 2 ideias inovadoras
- foram apontadas 2 melhorias de frontend de alto impacto

---

## Modelo recomendado de resposta técnica
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

---

## Princípio final
Contribuir com segurança, evidência e o menor impacto possível.

Quando houver dúvida entre uma solução maior e uma solução menor que resolve corretamente, preferir a menor.

Quando houver dúvida entre suposição e verificação, verificar.