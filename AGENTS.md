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