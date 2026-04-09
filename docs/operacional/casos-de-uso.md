---
title: Casos De Uso
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Casos De Uso
tags:
  - tecnico
prioridade: media
status: documentado
---
# Manual do Operador — COTTE

## Visão Geral

O COTTE é um sistema de gestão comercial para empresas de serviços. Ele centraliza orçamentos, clientes, financeiro, CRM e comunicação em um único lugar.

### O que o sistema faz

| Módulo | Para que serve |
|---|---|
| **Orçamentos** | Criar, enviar e acompanhar propostas comerciais |
| **Clientes** | Cadastrar e gerenciar a base de clientes |
| **Financeiro** | Controlar recebimentos, despesas e fluxo de caixa |
| **Catálogo** | Manter lista de serviços e preços-padrão |
| **Comercial** | CRM com pipeline de vendas e acompanhamento de leads |
| **Documentos** | Armazenar contratos e documentos reutilizáveis |
| **WhatsApp / IA** | Receber pedidos e criar orçamentos automaticamente |
| **Configurações** | Personalizar empresa, comunicação e integrações |

### Atores do sistema

- **Operador** — Cria orçamentos, registra pagamentos, gerencia clientes e leads
- **Gestor** — Tudo que o operador faz, mais acesso a configurações, catálogo e usuários
- **Cliente** — Acessa a proposta pelo link público, aceita ou recusa
- **Bot (WhatsApp)** — Recebe mensagens, interpreta com IA e cria orçamentos automaticamente

---

## Módulo 1 — Orçamentos

### UC-01 — Criar orçamento manualmente

**Ator:** Operador / Gestor
**Objetivo:** Criar uma proposta comercial preenchendo os dados manualmente.

**Pré-condições:**
- Estar logado no sistema
- Ter o cliente já cadastrado ou pronto para cadastrar

**Passos:**
1. No menu lateral, clique em **Orçamentos**
2. Clique no botão **＋ Novo Orçamento** (canto superior direito)
3. Na aba **Manual**, preencha:
   - **Cliente** — digite o nome para buscar ou clique em "＋ Novo" para cadastrar
   - **Serviço** — digite a descrição ou clique no ícone de catálogo para buscar um item cadastrado
   - **Valor** — deixe em branco para usar o preço-padrão do catálogo, ou informe um valor específico
   - **Validade** — número de dias que a proposta ficará aberta
   - **Forma de pagamento** — selecione entre as opções configuradas
   - **Observações** — informações adicionais para o cliente
4. Para adicionar mais serviços ao mesmo orçamento, clique em **＋ Adicionar item**
5. Clique em **✅ Criar Orçamento**

**Resultado:**
O orçamento é criado com status **Rascunho** e aparece na lista de orçamentos. O número é gerado automaticamente no formato `ORC-12-26`.

> **Dica:** É possível anexar documentos (contratos, termos) ao orçamento clicando em **📎 Documentos** antes de salvar.

---

### UC-02 — Criar orçamento via texto (IA)

**Ator:** Operador / Gestor
**Objetivo:** Descrever o serviço em linguagem natural e deixar a IA preencher o orçamento.

**Pré-condições:**
- Estar logado no sistema

**Passos:**
1. Clique em **Orçamentos** no menu lateral
2. Clique em **＋ Novo Orçamento**
3. Selecione a aba **Por Texto (IA)**
4. No campo de texto, descreva o pedido como recebeu do cliente — por exemplo:
   *"Instalação de 3 tomadas para João Silva, cobrar R$ 350"*
5. Clique em **Interpretar com IA**
6. Aguarde o preenchimento automático dos campos (cliente, serviço, valor)
7. Revise os dados preenchidos e ajuste se necessário
8. Clique em **✅ Criar Orçamento**

**Resultado:**
A IA interpreta o texto, busca o serviço no catálogo, preenche os campos e cria o orçamento. Se o cliente não existir, ele é criado automaticamente.

> **Dica:** Quanto mais detalhada for a descrição (nome do cliente, serviço, valor), melhor será a interpretação.

---

### UC-03 — Enviar orçamento ao cliente (WhatsApp / E-mail)

**Ator:** Operador / Gestor
**Objetivo:** Enviar a proposta ao cliente para que ele possa aceitar ou recusar.

**Pré-condições:**
- O orçamento deve existir e ter um cliente com telefone ou e-mail cadastrado
- O WhatsApp deve estar conectado (para envio por WhatsApp)

**Passos:**
1. Na lista de orçamentos, localize o orçamento desejado
2. Clique no ícone de **Detalhes** (📋) ao lado do orçamento
3. Dentro do modal de detalhes, clique em **Enviar por WhatsApp** ou **Enviar por E-mail**
4. Confirme o envio na caixa de diálogo

**Resultado:**
O cliente recebe a proposta com um link público. Pelo link, ele pode visualizar os detalhes, aceitar ou recusar. O status do orçamento muda para **Enviado**.

> **Dica:** O link público funciona sem login — o cliente acessa direto pelo celular.

---

### UC-04 — Aprovar orçamento pelo operador

**Ator:** Operador / Gestor
**Objetivo:** Marcar um orçamento como aprovado manualmente (sem passar pelo cliente).

**Pré-condições:**
- O orçamento deve estar no status **Enviado** ou **Rascunho**

**Passos:**
1. Na lista de orçamentos, clique no ícone de **Detalhes** do orçamento
2. Dentro do modal, clique em **Aprovar**
3. Confirme a ação

**Resultado:**
O status muda para **Aprovado**. Uma notificação é enviada via WhatsApp para o responsável pelo orçamento. A conta a receber é criada automaticamente no módulo **Financeiro**.

> **Dica:** O cliente também pode aprovar pelo link público respondendo "ACEITO" via WhatsApp.

---

### UC-05 — Duplicar orçamento existente

**Ator:** Operador / Gestor
**Objetivo:** Criar um novo orçamento a partir de um existente, reaproveitando os itens.

**Pré-condições:**
- Existir pelo menos um orçamento cadastrado

**Passos:**
1. Na lista de orçamentos, localize o orçamento a ser duplicado
2. Clique no ícone de ações (⋮) ao lado do orçamento
3. Selecione **Duplicar**

**Resultado:**
Um novo orçamento é criado com os mesmos itens, cliente e condições, no status **Rascunho**, pronto para edição e envio.

---

### UC-06 — Acompanhar status e linha do tempo

**Ator:** Operador / Gestor
**Objetivo:** Verificar o histórico de eventos de um orçamento (quando foi criado, enviado, visualizado, aprovado).

**Pré-condições:**
- O orçamento deve existir

**Passos:**
1. Na lista de orçamentos, clique no ícone de **Linha do Tempo** (🕐) ao lado do orçamento
2. O painel mostra cada evento com data e hora

**Resultado:**
Visão completa do histórico do orçamento, incluindo quando o cliente visualizou a proposta.

> **Dica:** Use a linha do tempo para saber se o cliente já abriu a proposta antes de fazer o follow-up.

---

## Módulo 2 — Clientes

### UC-07 — Cadastrar novo cliente

**Ator:** Operador / Gestor
**Objetivo:** Adicionar um novo cliente à base para vincular a orçamentos e contratos.

**Pré-condições:**
- Estar logado no sistema

**Passos:**
1. Clique em **Clientes** no menu lateral
2. Clique em **＋ Novo Cliente**
3. Preencha os campos:
   - **Nome** (obrigatório)
   - **E-mail**
   - **Telefone / WhatsApp**
   - **CPF / CNPJ**
   - **CEP** — clique na lupa para preencher o endereço automaticamente
   - **Observações** — notas internas sobre o cliente
4. Clique em **Salvar Cliente**

**Resultado:**
O cliente é cadastrado e fica disponível para uso em orçamentos e no CRM.

---

### UC-08 — Buscar e editar cliente existente

**Ator:** Operador / Gestor
**Objetivo:** Encontrar um cliente na base e atualizar seus dados.

**Pré-condições:**
- O cliente deve estar cadastrado

**Passos:**
1. Clique em **Clientes** no menu lateral
2. Digite o nome no campo de busca (🔍)
3. Clique no ícone de **Editar** (✏️) na linha do cliente
4. Altere os dados desejados
5. Clique em **Salvar Cliente**

**Resultado:**
Os dados do cliente são atualizados em todos os orçamentos e registros vinculados.

> **Dica:** Use **Exportar CSV** para baixar a lista completa de clientes para uma planilha.

---

## Módulo 3 — Financeiro

### UC-09 — Registrar pagamento de orçamento aprovado

**Ator:** Operador / Gestor
**Objetivo:** Informar ao sistema que o cliente efetuou o pagamento de um orçamento.

**Pré-condições:**
- O orçamento deve estar com status **Aprovado**
- A conta a receber deve existir no módulo Financeiro

**Passos:**
1. Clique em **Financeiro** no menu lateral
2. Selecione a aba **A Receber**
3. Localize a conta referente ao orçamento (filtre por status **Pendente** se necessário)
4. Clique em **Registrar Pagamento** na linha correspondente
5. No modal, informe:
   - **Valor recebido**
   - **Data do pagamento**
   - **Forma de pagamento**
6. Clique em **Confirmar**

**Resultado:**
A conta é marcada como **Paga** e o valor entra no cálculo do fluxo de caixa.

---

### UC-10 — Criar conta a receber avulsa (sem orçamento)

**Ator:** Operador / Gestor
**Objetivo:** Registrar um recebimento que não está vinculado a um orçamento.

**Pré-condições:**
- Estar logado no sistema

**Passos:**
1. Clique em **Financeiro** no menu lateral
2. Selecione a aba **A Receber**
3. Clique em **＋ Nova Conta**
4. Preencha o assistente (wizard):
   - Descrição do recebimento
   - Cliente (opcional)
   - Valor
   - Data de vencimento
   - Categoria
5. Conclua o assistente

**Resultado:**
A conta é criada como pendente e aparece na lista de contas a receber.

---

### UC-11 — Criar despesa (conta a pagar)

**Ator:** Operador / Gestor
**Objetivo:** Registrar um gasto da empresa (material, serviço terceirizado, etc.).

**Pré-condições:**
- Categorias de despesa configuradas (Configurações → Financeiro)

**Passos:**
1. Clique em **Financeiro** no menu lateral
2. Selecione a aba **Despesas**
3. Clique em **＋ Nova Despesa**
4. Preencha:
   - **Descrição**
   - **Categoria** (Material, Mão de obra, Serviços terceirizados, etc.)
   - **Valor**
   - **Data de vencimento**
   - **Observações** (opcional)
5. Clique em **Salvar**

**Resultado:**
A despesa aparece na lista com status **Pendente** e entra no cálculo do fluxo de caixa.

---

### UC-12 — Parcelar receita ou despesa

**Ator:** Operador / Gestor
**Objetivo:** Dividir um valor em múltiplas parcelas com datas distintas.

**Pré-condições:**
- Estar na aba **A Receber** ou **Despesas** do módulo Financeiro

**Passos:**
1. Clique em **Financeiro** no menu lateral
2. Clique em **Novo Parcelamento**
3. No modal, preencha:
   - Descrição
   - Valor total
   - Número de parcelas
   - Data da primeira parcela
   - Categoria
   - Orçamento vinculado (opcional)
4. O sistema calcula automaticamente as datas e valores de cada parcela
5. Confirme o parcelamento

**Resultado:**
Múltiplas contas são criadas (uma por parcela) com as respectivas datas de vencimento.

---

### UC-13 — Marcar despesa como paga

**Ator:** Operador / Gestor
**Objetivo:** Registrar que uma despesa foi quitada.

**Pré-condições:**
- A despesa deve existir com status **Pendente**

**Passos:**
1. Na aba **Despesas**, localize a despesa
2. Clique em **Marcar como Paga** na linha correspondente
3. Confirme a data e o valor pago
4. Salve

**Resultado:**
A despesa é marcada como **Paga** e sai da lista de pendentes. O fluxo de caixa é atualizado.

---

### UC-14 — Ver fluxo de caixa e resumo financeiro

**Ator:** Operador / Gestor
**Objetivo:** Visualizar a saúde financeira do período: entradas, saídas e saldo projetado.

**Pré-condições:**
- Existir lançamentos no módulo Financeiro

**Passos:**
1. Clique em **Financeiro** no menu lateral
2. Selecione a aba **Visão Geral**
3. Os cards mostram:
   - **Recebido** — total pago no período
   - **A Receber** — total pendente
   - **Vencido** — contas em atraso
   - **Despesas** — total de gastos
4. O gráfico de **Fluxo de Caixa** exibe a projeção do saldo ao longo do tempo
5. Alertas de saldo negativo são exibidos com as datas críticas

**Resultado:**
Visão completa da situação financeira para tomada de decisão.

> **Dica:** Use os filtros de data para comparar períodos diferentes.

---

## Módulo 4 — Catálogo de Serviços

### UC-15 — Adicionar serviço ao catálogo

**Ator:** Gestor
**Objetivo:** Cadastrar um serviço ou produto com preço-padrão para agilizar a criação de orçamentos.

**Pré-condições:**
- Ter permissão de gestor ou permissão de catálogo

**Passos:**
1. Clique em **Catálogo** no menu lateral
2. Clique em **＋ Novo Item**
3. Preencha:
   - **Nome** do serviço/produto
   - **Descrição** (aparece no orçamento)
   - **Preço padrão**
   - **Unidade** (un, m², hora, etc.)
   - **Categoria** (opcional)
4. Clique em **Salvar**

**Resultado:**
O serviço aparece no catálogo e fica disponível para busca ao criar orçamentos. Quando selecionado, o preço-padrão é preenchido automaticamente.

---

### UC-16 — Importar serviços em lote por CSV

**Ator:** Gestor
**Objetivo:** Adicionar múltiplos serviços ao catálogo de uma vez usando uma planilha.

**Pré-condições:**
- Ter permissão de gestor ou permissão de catálogo
- Ter o arquivo CSV no formato correto

**Passos:**
1. Clique em **Catálogo** no menu lateral
2. Clique em **📋 Importar**
3. Selecione o arquivo CSV com as colunas: `nome`, `descricao`, `preco_padrao`, `unidade`
4. Revise a pré-visualização dos dados
5. Confirme a importação

**Resultado:**
Todos os itens do CSV são adicionados ao catálogo. Itens com nome duplicado são ignorados.

> **Dica:** Baixe o modelo de CSV na tela de importação para garantir o formato correto.

---

## Módulo 5 — Comercial (CRM)

### UC-17 — Criar lead

**Ator:** Operador / Gestor
**Objetivo:** Registrar uma oportunidade de venda para acompanhamento.

**Pré-condições:**
- Estar logado no sistema

**Passos:**
1. Clique em **Comercial** no menu lateral
2. Selecione a aba **Leads**
3. Clique em **＋ Novo Lead**
4. Preencha:
   - **Empresa / Nome do contato**
   - **Telefone / E-mail**
   - **Origem** (indicação, site, WhatsApp, etc.)
   - **Valor estimado** (opcional)
   - **Observações**
5. Clique em **Salvar**

**Resultado:**
O lead é criado na coluna **Novo** do pipeline e aparece na lista de leads.

---

### UC-18 — Avançar lead no pipeline de vendas

**Ator:** Operador / Gestor
**Objetivo:** Mover o lead para a próxima etapa do processo de vendas.

**Pré-condições:**
- O lead deve existir no pipeline

**Passos:**
1. Clique em **Comercial** no menu lateral
2. Selecione a aba **Pipeline**
3. Localize o card do lead na coluna atual
4. Arraste o card para a próxima coluna, ou clique no card e altere o status manualmente
5. As colunas disponíveis são: **Novo → Contato Iniciado → Proposta Enviada → Negociação → Fechado Ganho / Fechado Perdido**

**Resultado:**
O lead avança no pipeline. O histórico de movimentação é registrado automaticamente.

---

### UC-19 — Registrar interação ou observação com lead

**Ator:** Operador / Gestor
**Objetivo:** Documentar contatos, ligações ou anotações sobre um lead para não perder o histórico.

**Pré-condições:**
- O lead deve existir

**Passos:**
1. Na aba **Leads**, clique no nome do lead para abrir os detalhes
2. Na seção de histórico, clique em **Registrar Interação**
3. Escolha o tipo (ligação, WhatsApp, reunião, e-mail)
4. Digite o resumo do contato
5. Salve

**Resultado:**
A interação é registrada com data/hora e aparece no histórico do lead, visível para toda a equipe.

> **Dica:** Use **Lembretes** para agendar o próximo follow-up e nunca esquecer de retornar ao lead.

---

## Módulo 6 — Documentos

### UC-20 — Subir documento da empresa

**Ator:** Gestor
**Objetivo:** Carregar um documento (contrato, termo de garantia, etc.) para reutilizar em orçamentos.

**Pré-condições:**
- Arquivo em formato PDF
- Ter permissão de gestor

**Passos:**
1. Clique em **Documentos** no menu lateral
2. Clique em **＋ Novo documento**
3. Preencha:
   - **Nome** do documento
   - **Tipo** (Contrato, Certificado de garantia, Termo, Documento técnico, Anexo complementar, Outro)
   - **Versão** (ex: 1.0)
   - **Status** (Ativo, Inativo, Arquivado)
   - **Descrição** — notas internas
   - **Permite download** — se o cliente pode baixar
   - **Visível no portal** — se aparece para o cliente na proposta
4. Faça o upload do arquivo PDF
5. Clique em **Salvar**

**Resultado:**
O documento fica disponível na biblioteca para ser anexado a orçamentos.

---

### UC-21 — Anexar documento a um orçamento

**Ator:** Operador / Gestor
**Objetivo:** Vincular um documento da biblioteca a um orçamento específico.

**Pré-condições:**
- O orçamento deve existir
- O documento deve estar cadastrado e ativo

**Passos:**
1. Na tela de **Orçamentos**, abra o modal de criação ou edição do orçamento
2. Clique em **📎 Documentos**
3. Selecione os documentos desejados da lista
4. Salve o orçamento

**Resultado:**
Os documentos vinculados aparecem na proposta pública para o cliente visualizar e/ou baixar, conforme as permissões configuradas.

---

## Módulo 7 — WhatsApp e IA

### UC-22 — Conectar WhatsApp (QR Code)

**Ator:** Gestor
**Objetivo:** Vincular o número de WhatsApp da empresa para receber e enviar orçamentos automaticamente.

**Pré-condições:**
- Ter plano que suporte WhatsApp próprio
- Ter o celular com o WhatsApp em mãos

**Passos:**
1. Clique em **WhatsApp** no menu lateral (ou acesse via **Configurações → Integrações**)
2. Clique em **Gerar novo QR Code**
3. No celular, abra o WhatsApp → **Dispositivos vinculados → Vincular dispositivo**
4. Aponte a câmera para o QR Code exibido na tela
5. Aguarde a confirmação de conexão

**Resultado:**
O status muda para **Conectado** e exibe o número de telefone vinculado. O bot começa a responder mensagens automaticamente.

> **Dica:** Mantenha o celular com o WhatsApp original conectado à internet para o bot funcionar continuamente.

---

### UC-23 — Criar orçamento pelo bot via WhatsApp

**Ator:** Bot / Cliente
**Objetivo:** Receber um pedido de serviço por WhatsApp e gerar o orçamento automaticamente.

**Pré-condições:**
- WhatsApp conectado (UC-22)
- Serviços cadastrados no catálogo

**Passos (do lado do cliente):**
1. O cliente envia uma mensagem para o número da empresa descrevendo o serviço
2. O bot interpreta a mensagem com IA
3. O bot responde confirmando o serviço e o valor
4. O orçamento é criado automaticamente no sistema
5. O PDF é gerado e enviado ao cliente pelo próprio WhatsApp
6. O cliente responde **"ACEITO"** para aprovar ou **"RECUSO"** para recusar

**Passos (verificação pelo operador):**
1. O novo orçamento aparece automaticamente na lista de **Orçamentos**
2. Uma notificação é enviada ao responsável quando o cliente aceitar

**Resultado:**
O orçamento é criado, enviado e pode ser aprovado sem intervenção manual do operador.

> **Dica:** Use a ferramenta **Testar Interpretação por IA** na tela de WhatsApp para simular como o bot interpretaria uma mensagem.

---

## Módulo 8 — Configurações (Gestor)

### UC-24 — Configurar forma de pagamento (entrada + parcelamento)

**Ator:** Gestor
**Objetivo:** Definir as condições de pagamento disponíveis para incluir nos orçamentos.

**Pré-condições:**
- Ter permissão de gestor

**Passos:**
1. Clique em **Configurações** no menu lateral
2. Na seção **Formas de Pagamento**, clique em **＋ Nova forma de pagamento**
3. Preencha:
   - **Nome** (ex: "30/70 — Entrada + Saldo")
   - **Ícone** (emoji representativo)
   - **Descrição** explicativa
   - **% de entrada**
   - **% de saldo** (complemento)
4. Salve

**Resultado:**
A forma de pagamento fica disponível no seletor ao criar orçamentos.

---

### UC-25 — Gerenciar categorias de despesas

**Ator:** Gestor
**Objetivo:** Criar e organizar as categorias usadas para classificar despesas financeiras.

**Pré-condições:**
- Ter permissão de gestor

**Passos:**
1. Clique em **Configurações** no menu lateral
2. Localize a seção **Configuração Financeira**
3. Em **Categorias de Despesa**, digite o nome da nova categoria
4. Clique em **＋ Adicionar**

**Resultado:**
A categoria aparece no seletor ao criar despesas no módulo Financeiro.

---

### UC-26 — Configurar textos de comunicação ao cliente

**Ator:** Gestor
**Objetivo:** Personalizar os textos que o cliente vê na proposta e no e-mail.

**Pré-condições:**
- Ter permissão de gestor

**Passos:**
1. Clique em **Configurações** no menu lateral
2. Acesse a seção **Comunicação**
3. Edite os campos conforme necessário:
   - **Apresentação** — Descrição pública da empresa e texto de assinatura da proposta
   - **Assinatura de e-mail** — Texto de rodapé dos e-mails enviados (suporta variáveis como `{{nome_empresa}}`)
   - **Contato e WhatsApp** — Telefone exibido na proposta e botão de WhatsApp
   - **Aceite e Confiança** — Texto de aviso antes do aceite e mensagem de confiança
   - **Boas-vindas** — Mensagem automática enviada ao cliente quando ele entra em contato pelo WhatsApp
4. Clique em **Salvar** no card correspondente

**Resultado:**
As alterações são refletidas imediatamente nas próximas propostas enviadas.

---

### UC-27 — Criar e configurar usuários da equipe

**Ator:** Gestor
**Objetivo:** Adicionar novos membros à equipe com as permissões adequadas.

**Pré-condições:**
- Ter permissão de gestor

**Passos:**
1. Clique em **Usuários** no menu lateral (ou acesse via **Configurações → Usuários**)
2. Clique em **＋ Novo Usuário**
3. Preencha:
   - **Nome**
   - **E-mail** (será usado para login)
   - **Senha provisória**
   - **Perfil**: Operador ou Gestor
   - **Permissões específicas** (catálogo, relatórios, etc.)
4. Salve

**Resultado:**
O usuário recebe acesso ao sistema com o perfil configurado. Operadores não acessam configurações globais; gestores têm acesso completo.

> **Dica:** Defina bem o perfil antes de salvar — operadores não podem alterar configurações da empresa nem gerenciar outros usuários.

---

## Fluxo completo — Do pedido ao recebimento

Para referência rápida, este é o caminho completo de uma venda:

```
Cliente contata (WhatsApp ou telefone)
        ↓
Operador cria orçamento (UC-01, UC-02 ou UC-23)
        ↓
Orçamento enviado ao cliente (UC-03)
        ↓
Cliente aceita (pela proposta pública ou WhatsApp)
        ↓
Status → Aprovado | Conta a receber criada no Financeiro
        ↓
Operador registra pagamento quando recebido (UC-09)
        ↓
Conta marcada como Paga | Fluxo de caixa atualizado (UC-14)
```
