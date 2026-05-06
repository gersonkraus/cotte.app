# Design: mover Campanhas para aba principal do Comercial

## Contexto

No tenant do Comercial, a funcionalidade de campanhas fica dentro do hub `Config`, enquanto o fluxo operacional principal do dia a dia ja usa abas de primeiro nivel como `Contatos`, `Funil` e `Lembretes`.

O usuario quer promover `Campanhas` para a barra principal ao lado de `Funil`, removendo esse acesso da subnavegacao de `Config`.

## Objetivo

Melhorar a navegacao do modulo Comercial com a menor alteracao possivel, sem refatorar o conteudo de campanhas nem mudar contratos de JavaScript desnecessariamente.

## Escopo

- Adicionar a aba principal `Campanhas` na barra `admin-tabs` em `tenant-comercial.html`
- Posicionar `Campanhas` ao lado de `Funil`
- Remover `Campanhas` da subnavegacao interna de `Config`
- Ajustar o `title` da aba `Config` para refletir a nova hierarquia
- Reaproveitar o painel e os containers de campanhas ja existentes

## Fora de escopo

- Criar pagina nova para campanhas
- Refatorar o modulo de campanhas
- Alterar o layout visual de outras abas sem necessidade funcional
- Mudar backend, APIs ou estrutura de dados

## Abordagem escolhida

Promover `Campanhas` para a navegacao principal e manter o restante da estrutura intacto.

Essa abordagem foi escolhida porque o codigo ja indica suporte para uma aba principal `campanhas` no fluxo JavaScript, reduzindo o risco e o tamanho do diff.

## Arquitetura da mudanca

### HTML

- Inserir um novo botao `.admin-tab` com `data-tab="campanhas"` imediatamente apos `Funil`
- Manter o painel `#tab-campanhas` como area de conteudo reutilizada
- Remover o botao `Campanhas` de `.config-subnav`
- Atualizar a descricao textual de `Config` para citar apenas configuracoes, modelos, propostas e cadastros

### JavaScript

- Preservar o carregamento atual de campanhas
- Validar se a navegacao principal ja chama `carregarCampanhas()` ao abrir `campanhas`
- Ajustar apenas se houver algum ponto assumindo que campanhas precisa estar dentro do subpainel de `Config`

### Mobile

- Preservar o seletor mobile baseado nas abas principais, garantindo que `Campanhas` apareca como item de primeiro nivel

## Fluxo esperado

1. Usuario abre `Comercial`
2. Enxerga `Campanhas` como aba principal ao lado de `Funil`
3. Ao clicar em `Campanhas`, o sistema mostra o mesmo conteudo atual de campanhas
4. Ao abrir `Config`, o usuario ve apenas `Configuracoes`, `Modelos`, `Propostas` e `Cadastros`

## Tratamento de risco

- Priorizar alteracao somente em `tenant-comercial.html` se o JS ja estiver compativel
- Fazer ajuste pequeno em JS apenas se a navegacao principal nao carregar campanhas corretamente
- Nao mover containers, ids ou handlers sem necessidade comprovada

## Validacao

- Abrir a tela `tenant-comercial.html`
- Confirmar que `Campanhas` aparece ao lado de `Funil`
- Confirmar que `Campanhas` nao aparece mais dentro de `Config`
- Confirmar que clicar em `Campanhas` carrega tabela/cards existentes
- Confirmar que `Config` continua funcionando com 4 sub-abas
- Confirmar que o seletor mobile reflete a nova ordem

## Testes

- Validacao manual da navegacao principal
- Validacao manual da subnavegacao de `Config`
- Validacao manual do carregamento de campanhas

## Limites e decisoes

- Sem refatoracao ampla
- Sem mudanca de nomenclatura de IDs existentes, exceto se estritamente necessario para funcionamento
- Sem alteracao de comportamento de backend
