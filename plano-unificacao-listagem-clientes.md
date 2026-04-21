# Plano de Unificação: Renderização da Listagem de Clientes

Este documento descreve o plano técnico para unificar a forma de exibição e o funcionamento da ferramenta de listar clientes com a ferramenta de listar orçamentos, evitando regressões em outros relatórios e no classificador de IA.

## 1. Por que os formatos atuais são diferentes?

O formato de exibição atual difere pelo histórico de evolução das ferramentas no sistema:
*   **Orçamentos (`listar_orcamentos`)**: Foi evoluído para suportar um "Card Rico" (`renderListaOrcamentos` no frontend), com botões de paginação (cursor), separação por status, *badges* visuais e ações rápidas. O backend foi adaptado para retornar chaves essenciais de controle como `has_more`, `next_cursor` e `filtros`.
*   **Clientes (`listar_clientes`)**: Permaneceu como uma tool simples (legada) que retorna um JSON bruto (apenas uma lista em array e um `total` baseado no limite). Como o frontend não encontrava um renderizador HTML específico para `clientes_lista`, ele recorria ao *fallback* padrão (`renderAnaliseTexto` ou `resposta-direta`), exibindo apenas o texto puro: *"Encontrei X cliente(s) encontrado(s)."*

## 2. Plano de Ação Estruturado (Sem Regressões)

Para que a listagem de clientes tenha a mesma qualidade visual e funcional (paginação e tabela rica) sem afetar outras partes do sistema, a execução deve seguir os passos abaixo:

### Fase 1: Backend - Paginação e Padronização do Contrato (Tool)
*   **Arquivo**: `sistema/app/services/ai_tools/cliente_tools.py`
*   **Ações**:
    1.  Adicionar `cursor: Optional[str] = Field(default=None)` no schema `ListarClientesInput`.
    2.  Modificar a query dentro de `_listar_clientes` para suportar cursor-based pagination (ex: filtrar por `id < cursor` ou um offset seguro codificado em base64).
    3.  Ajustar o retorno do dicionário JSON para incluir as chaves padrão consumidas pelo frontend:
        *   `has_more`: Booleano indicando se há mais resultados no banco.
        *   `next_cursor`: O cursor para a próxima página.
        *   `limit`: O limite utilizado.
        *   `filtros`: Dicionário com a busca aplicada (ex: `{"busca": inp.busca}`).

### Fase 2: Backend - Roteamento Fast-Path (Hub)
*   **Arquivo**: `sistema/app/services/cotte_ai_hub.py`
*   **Ações**:
    1.  Atualizar a função `_v2_build_listar_clientes_fastpath_response` (criada recentemente) para extrair o `cursor` da mensagem gerada pelo botão de paginação e repassá-lo para a função `listar_clientes()`.

### Fase 3: Frontend - Renderização do Card (JavaScript)
*   **Arquivo**: `sistema/cotte-frontend/js/assistente-ia-render-types.js`
*   **Ações**:
    1.  Criar a função `function renderListaClientes(dados)` espelhando o HTML/CSS de `renderListaOrcamentos`.
        *   Colunas sugeridas: **Nome**, **WhatsApp/Email**, **Data de Cadastro** e um botão de atalho visual.
    2.  Incluir o botão "Carregar mais resultados" gerando um HTML com os atributos de paginação (`data-clientes-load-more="1"`, `data-cursor`, `data-busca`).
    3.  Na função principal de roteamento de componentes (`resolveAssistenteRenderResult`), adicionar a condição:
        ```javascript
        if (dados && Array.isArray(dados.clientes) && typeof dados.total !== 'undefined') {
            return { html: renderListaClientes(dados), rendererId: 'renderListaClientes', tipoResposta, dados };
        }
        ```

### Fase 4: Frontend - Interatividade (Paginação)
*   **Arquivo**: `sistema/cotte-frontend/js/assistente-ia-shell.js`
*   **Ações**:
    1.  Adicionar o *event listener* para os cliques no novo botão de paginação:
        ```javascript
        const loadMoreClientesBtn = t.closest('[data-clientes-load-more]');
        if (loadMoreClientesBtn) {
            e.preventDefault();
            const cursor = loadMoreClientesBtn.getAttribute('data-cursor') || '';
            const busca = loadMoreClientesBtn.getAttribute('data-busca') || '';
            const lim = loadMoreClientesBtn.getAttribute('data-limit') || '10';
            // Disparar comando invisível: "Liste mais clientes com cursor 'X', limite Y. Busca 'Z'."
        }
        ```

### Fase 5: Regressão e Validação [OBRIGATÓRIO]
*   Após as modificações, executar obrigatoriamente:
    `cd sistema && pytest tests/test_ai_tool_routing.py`
    (Conforme conhecimento do projeto, não pode haver quebras nas prioridades de intenção criadas anteriormente).
*   Testar no chat do frontend o comando *"listar meus clientes"*, garantindo que o card HTML renderize e o botão "Carregar mais" injete corretamente as próximas páginas.

---

## 💡 Sugestões Técnicas Extras

### Melhorias Essenciais
1.  **Cursor Baseado em UUID/ID**: Utilizar paginação baseada no "maior ID" (ou menor, dependendo da ordenação) em vez de `offset`, para evitar pulo de registros caso novos clientes sejam criados durante a conversa da IA.
2.  **Tratamento de Busca Vazia**: Ao receber um `busca_val` vazio e sem `cursor`, o sistema deve focar nos clientes ordenados por `criado_em DESC` por padrão, dando mais relevância para cadastros recentes.

### Ideias Inovadoras
1.  **Ação de Orçamento Rápido via Lista**: Colocar um ícone flutuante `[+ Orçamento]` no card do cliente listado. Se clicado, ele preenche o chat da IA com "Criar orçamento para o cliente [NOME] de " e foca o input, cortando fricção.
2.  **Integração do Link do WhatsApp**: Nos cards da tabela, se houver um número de WhatsApp cadastrado, transformá-lo em um link nativo (`wa.me/...`) para que o usuário possa contatar o cliente com apenas 1 clique direto do chat.

### Melhorias de Frontend de Alto Impacto
1.  **Avatar com Iniciais**: No lugar de apenas o texto do nome, exibir um avatar circular gerado automaticamente (Ex: Cliente "João Silva" ganha um círculo colorido com "JS"). Melhora radicalmente o design e escaneabilidade da lista.
2.  **Badges de Contato (Status)**: Exibir tags pequenas na listagem informando se aquele cliente tem dados "Incompletos" (sem telefone/email) ou está "Completo", estimulando o usuário a enriquecer a base enquanto conversa com a IA.
