---
title: Prompt Card Assistente
tags:
  - tecnico
prioridade: media
status: documentado
---
 Prompt para Manutenção/Alteração do Card de Orçamentos
Copie o texto abaixo e preencha a última linha com a sua necessidade:
Você é um desenvolvedor frontend especialista trabalhando no sistema COTTE. Sua tarefa é alterar o layout/comportamento do Card de Orçamento exibido no Assistente IA.
Contexto Arquitetural Importante:
1. O sistema utiliza a abordagem "One Card to Rule Them All". Todas as respostas relacionadas a orçamentos (criação, preview, aprovação, recusa, edição e consulta via comando "VER") são renderizadas por UMA ÚNICA função unificada para evitar fragmentação visual.
2. O arquivo principal é: `sistema/cotte-frontend/js/assistente-ia-render-types.js`.
3. A função alvo é: `renderOrcamentoCardUnificado(dados)`.
4. O roteamento ocorre na função `formatAIResponse(data)`, que intercepta vários tipos de resposta (`orcamento_preview`, `orcamento_criado`, `orcamento_card_unificado`, etc.) e os direciona para a função unificada.
Regras Estritas para a Alteração:
- NÃO crie novas funções de renderização para estados específicos. Adapte a função `renderOrcamentoCardUnificado` baseando-se na variável `statusKey` (ex: 'rascunho', 'enviado', 'aprovado', 'recusado').
- Mantenha a estrutura base de classes CSS (ex: `orc-card-v2`, `orc-card-v2__banner`, `orc-card-v2__body`, `orc-card-v2__actions`).
- Preserve a lógica condicional dos botões na div de ações (`botoesHtml`). Botões como "Aprovar" só aparecem em rascunho/enviado; "Agendar" apenas em aprovados.
- Preserve todos os atributos de dados de eventos in-line (ex: `data-enviar-wa`, `data-quick-send`, `onclick="abrirDetalhesOrcamento..."`).
- Sempre utilize as funções de segurança existentes (`escapeHtml`, `escapeHtmlAttr`, `formatValue`) para evitar XSS e quebras de layout.
Sabendo disso, por favor, implemente a seguinte alteração no card:
[INSERIR AQUI A MUDANÇA DESEJADA - Ex: "Quero adicionar uma tag visual que mostre a forma de pagamento escolhida logo abaixo do valor total", ou "Mude a cor do banner de orçamentos enviados para azul"]
***
Por que esse prompt é altamente eficaz?
1. Evita Regressão: Impede que o agente, por falta de contexto, decida "recriar" funções antigas como renderOrcamentoAprovado, quebrando o trabalho de unificação que acabamos de fazer.
2. Foca no Arquivo Certo: Direciona o modelo exatamente para a função renderOrcamentoCardUnificado, economizando tempo de busca (tokens) e garantindo precisão cirúrgica.
3. Protege Eventos: Garante que botões vitais do fluxo (como enviar WhatsApp silencioso ou aprovar) não percam seus atributos data-* que os conectam aos listeners do sistema.
   
   Extrator de Configuração CSS para Estados: Adotar componentes que já implementem classes transitórias (ex.: invocar e remover .btn-success-state) com uso de JavaScript classList.add() em vez de manipulação física de textContent. Isso melhora consideravelmente a acessibilidade para os leitores de tela semânticos e evita layout thrashing.
Substituição por Progress Indicators Indiretos: Avaliar, em ações com alta latência, a apresentação do spinner de carregamento (⏳) como overlay ou loader em outra área do DOM adjacente ao card de orçamentos e não hardcoded no label do botão, poupando a fluidez visual no card.
Ideias Inovadoras
Fallback Tátil com Toast Minimalista: Quando as mensagens do botão excederem sua dimensão em monitores bem estreitos, alternar a injeção in-line text para um Toast sutil no canto superior da tela com a notificação "O status foi copiado para sua área de transferência".
Tratamento Híptico: Ao realizar a mutação de estado bem sucedida (como Orçamento Aprovado), integrar um pulso háptico (no mobile via API Web nativa navigator.vibrate) somada à animação verde no card, trazendo à tona o sentido "Precision Atelier".
Melhorias de Frontend de Alto Impacto
Animação Natural de Resize (Transform): Usar pequenas propriedades animadas (transition: min-width 0.3s cubic-bezier(0.4, 0, 0.2, 1)) associadas à flexibilidade dos botões para que a revelação do texto após o clique expanda a estrutura do botão suavemente como uma persiana, evitando um pulo duro entre os tamanhos.
Glassmorphism no Card Aprovado: Para criar maior profundidade semântica de "arquivo vivo e confirmado", o container geral do orçamento em estados aprovados (sob o header st-current) poderia se beneficiar de um blur passivo sutil sob a cor base via backdrop-filter, evidenciando seu sucesso através da iluminação.