# Design Spec: Preview Completo de Orçamento no Assistente

## 1. Objetivo
Permitir que o usuário, logo após confirmar a criação de um orçamento via IA, possa acessar um "Preview Completo" do orçamento gerado, utilizando 100% da interface rica, responsiva e interativa que já existe na tela de `orcamentos.html`.

## 2. Abordagem Escolhida
Inserir um botão de destaque "🔍 Ver Preview Completo" no card de resposta de "Orçamento criado com sucesso" e "Orçamento atualizado". Esse botão abrirá o mesmo modal reutilizável gerado por `orcamento-detalhes.js`.

## 3. Arquitetura e Componentes

### HTML (`assistente-ia.html`):
- Adicionar as tags `<script src="js/orcamento-detalhes.js"></script>` no final do `<body>`.
- Adicionar o HTML do `modal-detalhes` e do `modal-orc-docs` antes do fechamento do `<body>`.

### Integração de Ações (`assistente-ia-actions.js`):
- Criar aliases e stubs globais para que os botões dentro do `modal-detalhes` funcionem perfeitamente dentro do contexto do assistente de IA.
- Exemplo de mapeamentos:
  - `window.api` = `httpClient` (o `orcamento-detalhes.js` usa `api.get`, mas o assistente usa `httpClient.get`)
  - `enviarWhatsapp(id)` -> chama `enviarPorWhatsapp(id, null, null)`
  - `enviarEmail(id)` -> chama `enviarPorEmail(id, null, null)`
  - `aprovarOrcamento(id, num)` -> chama o atalho de mensagem `sendQuickMessage('aprovar ' + num)` e fecha o modal.
  - Ações como Duplicar, Timeline e Editar navegarão para `orcamentos.html` com querystrings apropriadas.

### UI do Assistente (`js/assistente-ia-render-types.js`):
- Na função `renderOrcamentoCriado()` e `renderOrcamentoAtualizado()`, injetar no rodapé do `orc-card-v2` o novo botão:
  `<button type="button" class="btn btn-primary" onclick="abrirDetalhesOrcamento(${orcId})" style="width: 100%; margin-top: 8px;">🔍 Ver Preview Completo</button>`

## 4. Tratamento de Erros e Dados
- Como o `orcamento-detalhes.js` espera a existência de um cache chamado `orcamentosCache`, vamos mockar ou ignorar esse comportamento, priorizando sempre a busca real do backend via `GET /orcamentos/{id}` que o próprio script já faz de forma primária.

