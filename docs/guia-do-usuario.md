---
title: Guia Do Usuario
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Guia do Usuário — Sistema COTTE
tags:
  - documentacao
  - usuario
  - frontend
prioridade: alta
status: documentado
---

# Guia do Usuário — Sistema COTTE

Bem-vindo ao COTTE! Este guia explica todas as funcionalidades do sistema de forma simples, como se você estivesse aprendendo com um amigo prestador de serviço.

O COTTE é um sistema completo para gestão de orçamentos, clientes e financeiro. Ele ajuda prestadores de serviço a criar orçamentos profissionais, enviar aos clientes pelo WhatsApp, acompanhar pagamentos e muito mais — tudo em um só lugar.

---

## 1. Autenticação e Acesso

### Primeiro Acesso — Criar Conta

**Onde acessar:** Página inicial do sistema (login.html)

**Para que serve:** Criar sua conta no COTTE para começar a usar o sistema.

**Passo a passo:**
1. Acesse a página de login do sistema
2. Clique em "Criar conta" ou "Cadastrar"
3. Preencha os dados da sua empresa:
   - Nome da empresa: como seu negócio vai aparecer para os clientes
   - Seu nome: seu nome completo
   - E-mail: seu e-mail para login
   - Telefone: seu WhatsApp para contato
   - Senha: crie uma senha segura
4. Clique em "Cadastrar"
5. Pronto! Você já pode usar o sistema

**Resultado esperado:** Você será direcionado para o dashboard do sistema e poderá começar a cadastrar seus serviços e clientes.

---

### Login — Entrar no Sistema

**Onde acessar:** Menu > Login

**Para que serve:** Acessar o sistema com sua conta cadastrada.

**Passo a passo:**
1. Acesse a página de login
2. Digite seu e-mail
3. Digite sua senha
4. Clique em "Entrar"

**Resultado esperado:** Você será direcionado para o dashboard principal.

---

### Esqueci Minha Senha

**Onde acessar:** Página de login > Link "Esqueci minha senha"

**Para que serve:** Recuperar acesso quando você esquecer sua senha.

**Passo a passo:**
1. Na página de login, clique em "Esqueci minha senha"
2. Digite o e-mail cadastrado
3. Clique em "Enviar"
4. Você receberá um e-mail com instruções para redefinir sua senha
5. Acesse o link enviado e crie uma nova senha

**Resultado esperado:** Você poderá acessar o sistema com a nova senha.

---

## 2. Dashboard — Página Inicial

### Visão Geral do Negócio

**Onde acessar:** Menu principal > Dashboard (index.html)

**Para que serve:** Ver um resumo rápido de como seu negócio está indo, com números importantes em um só lugar.

**O que você vê na tela:**

- **Orçamentos Aprovados:** Quantos orçamentos você aprovou este mês (clique para ver a lista)
- **Faturamento:** Total de dinheiro que entrou este mês
- **Ticket Médio:** Valor médio por orçamento aprovado
- **Taxa de Aprovação:** Percentual de orçamentos que viraram negócio
- **Orçamentos Pendentes:** Orçamentos esperando resposta do cliente
- **Orçamentos Prestes a Expirar:** Orçamentos que vencem em 3 dias

**Passo a passo para usar:**
1. Ao abrir o sistema, você já está no Dashboard
2. Os cards mostram informações em tempo real
3. Clique em qualquer card para ver mais detalhes
4. Use o botão "Novo Orçamento" no topo para criar rapidamente

**Resultado esperado:** Você tem uma visão clara do andamento do seu negócio sem precisar entrar em várias telas.

---

## 3. Clientes

### Cadastrar Novo Cliente

**Onde acessar:** Menu > Clientes > Botão "Novo Cliente"

**Para que serve:** Guardar informações dos seus clientes para usar nos orçamentos e facilitar o atendimento.

**Passo a passo:**
1. Acesse o menu Clientes
2. Clique no botão "+ Novo Cliente"
3. Escolha o tipo de pessoa:
   - **Pessoa Física (PF):** para clientes individuais
   - **Pessoa Jurídica (PJ):** para empresas
4. Preencha os campos:

**Campos disponíveis:**

- **Nome completo** (obrigatório): Nome do cliente
- **CPF** (obrigatório para PF): CPF com pontos e traço
- **CNPJ** (obrigatório para PJ): CNPJ da empresa
- **Razão Social** (para PJ): Nome oficial da empresa
- **Nome Fantasia** (opcional para PJ): Nome comercial da empresa
- **Telefone** (obrigatório): WhatsApp para contato
- **E-mail** (opcional): E-mail do cliente
- **Endereço** (opcional): Rua, número, complemento, bairro, cidade, estado, CEP
- **Observações** (opcional): Anotações sobre o cliente

5. Para CNPJ, você pode clicar no botão de busca para preencher automaticamente
6. Clique em "Salvar"

**Resultado esperado:** Cliente salvo na base de dados e disponível para criar orçamentos.

---

### Buscar Cliente

**Onde acessar:** Menu > Clientes > Campo de busca

**Para que serve:** Encontrar rapidamente um cliente específico na sua base.

**Passo a passo:**
1. Acesse o menu Clientes
2. Digite o nome do cliente no campo de busca
3. A lista filtra automaticamente conforme você digita

**Resultado esperado:** Apenas os clientes com nomes semelhantes aparecem.

---

### Editar Cliente

**Onde acessar:** Menu > Clientes > Lista > Botão editar

**Para que serve:** Atualizar informações de um cliente existente.

**Passo a passo:**
1. Na lista de clientes, clique no botão de editar (lápis)
2. O modal de edição abre com os dados atuais
3. Altere o que precisar
4. Clique em "Salvar"

**Resultado esperado:** Informações atualizadas.

---

### Exportar Lista de Clientes

**Onde acessar:** Menu > Clientes > Botão "Exportar CSV"

**Para que serve:** Baixar uma planilha com todos os seus clientes para usar em outros sistemas ou fazer envios em massa.

**Passo a passo:**
1. Acesse o menu Clientes
2. Clique no botão "Exportar CSV"
3. O arquivo será baixado automaticamente

**Resultado esperado:** Arquivo CSV com todos os clientes.

---

## 4. Orçamentos

### Criar Novo Orçamento

**Onde acessar:** Menu > Orçamentos > Botão "Novo Orçamento" (ou pelo Dashboard)

**Para que serve:** Criar uma proposta comercial detalhada para enviar ao cliente.

**Passo a passo:**
1. Clique em "Novo Orçamento"
2. Selecione ou cadastre o cliente:
   - Digite o nome para buscar clientes existentes
   - Ou clique em "Novo Cliente" para cadastrar na hora
3. Preencha os dados do orçamento:
   - **Validade:** até quando o orçamento é válido (padrão: 30 dias)
   - **Observações:** informações extras para o cliente
4. Adicione os serviços/itens:
   - Clique em "Adicionar Item"
   - Busque no catálogo ou digite o nome do serviço
   - Preencha quantidade, preço unitário e unidade
   - O total calcula automaticamente
5. Aplique desconto (se necessário):
   - Porcentagem ou valor fixo
6. Escolha a forma de pagamento:
   - Clique em "Adicionar forma de pagamento"
   - Selecione ou crie novas opções
7. Clique em "Salvar" ou "Salvar e Enviar"

**Campos disponíveis:**

- Cliente (obrigatório): Quem vai receber o orçamento
- Validade (obrigatório): Data limite para aceite
- Itens (obrigatório): Serviços incluidos
- Quantidade (obrigatório): Quanto de cada serviço
- Preço Unitário (obrigatório): Valor por unidade
- Unidade (obrigatório): hora, serviço, peça, metro, etc.
- Desconto (opcional): Percentual ou valor
- Forma de Pagamento (opcional): Como o cliente pode pagar
- Observações (opcional): Informações extras

**Resultado esperado:** Orçamento salvo e pronto para enviar ao cliente.

---

### Enviar Orçamento pelo WhatsApp

**Onde acessar:** Menu > Orçamentos > Lista > Botão enviar

**Para que serve:** Enviar o orçamento diretamente para o WhatsApp do cliente.

**Passo a passo:**
1. Na lista de orçamentos, encontre o orçamento desejado
2. Clique no botão de enviar (ícone do WhatsApp)
3. O sistema gera um link público do orçamento
4. Escolha como enviar:
   - Copiar o link para enviar manualmente
   - Enviar direto pelo WhatsApp (se conectado)
5. Confirme o envio

**Resultado esperado:** Cliente recebe o link e pode visualizar o orçamento online.

---

### Visualizar Orçamento Público (Cliente)

**Onde acessar:** Link enviado ao cliente (URL pública)

**Para que serve:** O cliente visualiza o orçamento de forma profissional sem precisar fazer login.

**O que o cliente vê:**
- Logo e dados da sua empresa
- Descrição detalhada dos serviços
- Valores individuais e total
- Formas de pagamento disponíveis
- Data de validade
- Botões para: Aprovar, Recusar, Solicitar Ajuste
- Opção de baixar PDF

**Passo a passo do cliente:**
1. Cliente recebe o link pelo WhatsApp
2. Abre no navegador do celular ou computador
3. Vê todos os detalhes do orçamento
4. Pode escolher uma opção:
   - **Aprovar:** Aceita o orçamento (pode pedir código por SMS)
   - **Recusar:** Não aceitou
   - **Solicitar Ajuste:** Pede mudanças antes de decidir
5. Você recebe a notificação da decisão

**Resultado esperado:** Cliente toma conhecimento do orçamento e você sabe se aprovou ou não.

---

### Aprovar Orçamento

**Onde acessar:** Menu > Orçamentos > Detalhes > Botão "Aprovar"

**Para que serve:** Marcar formalmente que o cliente aprovou o orçamento e você iniciou o serviço.

**Passo a passo:**
1. Abra o orçamento
2. Clique no botão "Aprovar"
3. Confirme a aprovação
4. O orçamento muda de status

**Resultado esperado:** Status muda para "Aprovado" e você pode começar a acompanhar o pagamento.

---

### Recusar Orçamento

**Onde acessar:** Menu > Orçamentos > Detalhes > Botão "Recusar"

**Para que serve:** Registrar que o cliente não aprovou o orçamento.

**Passo a passo:**
1. Abra o orçamento
2. Clique no botão "Recusar"
3. Opcional: adicione um motivo
4. Confirme

**Resultado esperado:** Status muda para "Recusado" e você sabe que não houve negócio.

---

### Gerar PDF do Orçamento

**Onde acessar:** Menu > Orçamentos > Detalhes > Botão "PDF"

**Para que serve:** Baixar o orçamento em formato PDF para enviar por e-mail ou imprimir.

**Passo a passo:**
1. Abra o orçamento
2. Clique no botão "Baixar PDF"
3. O PDF é gerado e baixado automaticamente

**Resultado esperado:** Arquivo PDF profissional do orçamento.

---

### Duplicar Orçamento

**Onde acessar:** Menu > Orçamentos > Lista > Opção duplicar

**Para que serve:** Criar um novo orçamento baseado em um existente (útil para orçamentos recorrentes).

**Passo a passo:**
1. Na lista de orçamentos, encontre o que quer duplicar
2. Clique na opção "Duplicar"
3. Um novo orçamento é criado com os mesmos itens
4. Edite o que precisar
5. Salve

**Resultado esperado:** Novo orçamento com dados copiados.

---

### Listar e Filtrar Orçamentos

**Onde acessar:** Menu > Orçamentos

**Para que serve:** Ver todos os seus orçamentos e encontrar específicos com filtros.

**Filtros disponíveis:**

- **Por status:** Pendente, Aprovado, Recusado, Expirado
- **Por data:** Data de criação ou validade
- **Por cliente:** Nome do cliente
- **Busca:** Texto livre

**Passo a passo:**
1. Acesse o menu Orçamentos
2. Use os filtros no topo para refinar a busca
3. Clique em "Filtrar"
4. Resultados aparecem na tabela

**Resultado esperado:** Lista de orçamentos符合 os critérios selecionados.

---

### Exportar Orçamentos

**Onde acessar:** Menu > Orçamentos > Botão Exportar

**Para que serve:** Baixarplanilha com seus orçamentos para controle ou análise.

**Passo a passo:**
1. Acesse o menu Orçamentos
2. Clique em "Exportar CSV"
3. Configure os filtros se quiser
4. O arquivo é baixado

**Resultado esperado:** Planilha com dados dos orçamentos.

---

## 5. Catálogo de Serviços

### O que é o Catálogo?

O catálogo é onde você cadastra todos os serviços que oferece. Assim, na hora de criar orçamentos, é só buscar — não precisa digitar tudo de novo.

---

### Cadastrar Novo Serviço

**Onde acessar:** Menu > Catálogo > Botão "+ Novo Item"

**Para que serve:** Adicionar um serviço ao seu catálogo para usar depois nos orçamentos.

**Passo a passo:**
1. Acesse o menu Catálogo
2. Clique em "+ Novo Item"
3. Preencha os dados:

**Campos disponíveis:**

- **Nome** (obrigatório): Nome do serviço
- **Descrição** (opcional): Detalhes sobre o serviço
- **Categoria** (obrigatório): Grupo que o serviço pertence (ex: "Instalação", "Manutenção")
- **Preço** (obrigatório): Valor unitário
- **Unidade** (obrigatório): Como mede (hora, serviço, peça, metro, kg, etc.)
- **Ativo** (opcional): Se aparece nos orçamentos
4. Clique em "Salvar"

**Resultado esperado:** Serviço disponível no catálogo.

---

### Criar Categoria

**Onde acessar:** Menu > Catálogo > Campo categoria > "Nova categoria"

**Para que serve:** Agrupar seus serviços por tipo para facilitar a organização e busca.

**Passo a passo:**
1. Ao cadastrar um serviço, clique em "Nova Categoria"
2. Digite o nome da categoria
3. Salve

**Resultado esperado:** Categoria criada e associada ao serviço.

---

### Importar Serviços em Lote

**Onde acessar:** Menu > Catálogo > Botão "Importar"

**Para que serve:** Cadastrar vários serviços de uma vez, copiando de uma planilha.

**Passo a passo:**
1. Clique em "Importar"
2. Escolha como quer importar:
   - **Colar texto:** Copie uma tabela do Excel/Sheets e cole
   - **Upload arquivo:** Envie um arquivo .csv, .xlsx ou .pdf
3. A IA identifica automaticamente:
   - Nome do serviço
   - Preço
   - Unidade
4. Revise os itens na tela de preview
5. Clique em "Salvar Items"

**Dica:** A IA é esperta! Ela entende vários formatos de tabela.

**Resultado esperado:** Todos os serviços importados de uma vez.

---

### Templates por Segmento

**Onde acessar:** Menu > Catálogo > Importar > Aba "Templates"

**Para que serve:** Usar modelos prontos de serviços para seu tipo de negócio.

**Passo a passo:**
1. Clique em "Importar"
2. Escolha um segmento:
   - Construção Civil
   - Mecânica
   - Informática
   - Beauty/Estética
   - E outros...
3. O sistema importa serviços prontos para esse segmento

**Resultado esperado:** Catálogo preenchido com serviços típicos do ramo.

---

### Buscar e Filtrar Serviços

**Onde acessar:** Menu > Catálogo > Campo de busca

**Para que serve:** Encontrar rapidamente um serviço específico.

**Passo a passo:**
1. Digite o nome no campo de busca
2. Use o filtro por categoria
3. Escolha ver: Ativos, Inativos ou Todos

**Resultado esperado:** Lista filtrada de serviços.

---

### Editar Serviço

**Onde acessar:** Menu > Catálogo > Card do serviço > Editar

**Para que serve:** Alterar dados de um serviço existente.

**Passo a passo:**
1. Clique no serviço no catálogo
2. Edite as informações
3. Salve

**Resultado esperado:** Serviço atualizado.

---

### Desativar Serviço

**Onde acessar:** Menu > Catálogo > Card do serviço > Desativar

**Para que serve:** Remover um serviço da lista sem apagar definitivamente (pode reativar depois).

**Passo a passo:**
1. Clique no serviço
2. Desmarque a opção "Ativo"
3. Salve

**Resultado esperado:** Serviço não aparece mais na criação de orçamentos.

---

## 6. WhatsApp

### Conectar seu WhatsApp

**Onde acessar:** Menu > WhatsApp Bot

**Para que serve:** Conectar seu WhatsApp ao sistema para receber e enviar mensagens automaticamente.

**Passo a passo:**
1. Acesse o menu WhatsApp Bot
2. Você verá um QR Code na tela
3. Abra o WhatsApp no seu celular
4. Vá em Configurações > Aparelhos conectados
5. Escaneie o QR Code da tela do computador
6. Aguarde a conexão
7. Pronto! Seu WhatsApp está conectado

**O que acontece quando conectado:**

- Clientes podem te mandar mensagens descrevendo serviços
- A IA interpreta a mensagem e cria um orçamento automaticamente
- Você recebe notificações de novas mensagens
- Pode enviar orçamentos direto pelo WhatsApp

**Resultado esperado:** Status mostra "WhatsApp Conectado" com o número do telefone.

---

### Desconectar WhatsApp

**Onde acessar:** Menu > WhatsApp Bot > Botão "Desconectar"

**Para que serve:** Desvincular seu WhatsApp do sistema.

**Passo a passo:**
1. Clique em "Desconectar WhatsApp"
2. Confirme a ação
3. O sistema desconecta

**Resultado esperado:** WhatsApp desconectado, QR Code disponível para nova conexão.

---

### Como funciona o Bot de Orçamento

O sistema funciona assim:

1. **Cliente manda mensagem:** Cliente envia no WhatsApp: "Quero instalar 3 ventiladores de teto"
2. **IA interpreta:** O sistema entende o serviço, quantidade e cria o orçamento
3. **Você recebe:** Notificação de novo orçamento pendente
4. **Você envia:** Review o orçamento e envia para o cliente aprobar

---

### Configurar Respostas Automáticas

**Onde acessar:** Menu > Configurações > WhatsApp

**Para que serve:** Definir mensagens que o sistema envia automaticamente.

**Passo a passo:**
1. Vá em Configurações
2. Encontre a seção WhatsApp
3. Configure:
   - Mensagem de boas-vindas
   - Resposta quando você está offline
   - Mensagem de confirmação de orçamento

**Resultado esperado:** Clientes recebem respostas automáticas.

---

## 7. Financeiro

### Dashboard Financeiro

**Onde acessar:** Menu > Financeiro

**Para que serve:** Ver uma visão geral das finanças da sua empresa.

**O que você vê:**

- **Contas a Receber:** Total esperado receber
- **Recebido:** Valor que já entrou
- **Contas a Pagar:** Total de despesas
- **Saldo:** Diferença entre receber e pagar
- **Inadimplentes:** Clientes devendo
- **Gráficos:** Evolução de receitas e despesas

---

### Criar Conta a Receber

**Onde acessar:** Menu > Financeiro > Aba "Contas" > "Nova Conta"

**Para que serve:** Registrar uma cobrança que você vai enviar para o cliente.

**Passo a passo:**
1. Vá em Financeiro
2. Clique em "Nova Conta"
3. Preencha:

**Campos disponíveis:**

- **Cliente** (obrigatório): Quem vai pagar
- **Orçamento** (opcional): Vincula a um orçamento
- **Valor** (obrigatório): Valor a receber
- **Data de vencimento** (obrigatório): Quando deve ser pago
- **Categoria** (opcional): Tipo de receita
- **Descrição** (opcional): Detalhes
- **Forma de pagamento** (opcional): Como vai receber

4. Clique em "Salvar"

**Resultado esperado:** Conta criada e aparece na lista de a receber.

---

### Registrar Pagamento

**Onde acessar:** Menu > Financeiro > Conta > Botão "Receber"

**Para que serve:** Registrar quando o cliente paga.

**Passo a passo:**
1. Encontre a conta na lista
2. Clique em "Receber"
3. Confirme o valor
4. Adicione data do pagamento
5. Clique em "Confirmar"

**Resultado esperado:** Conta marcada como paga, valor entra no saldo.

---

### Criar Despesa

**Onde acessar:** Menu > Financeiro > Aba "Despesas" > "Nova Despesa"

**Para que serve:** Registrar seus gastos para controlar o lucro.

**Passo a passo:**
1. Vá em Financeiro
2. Mude para aba Despesas
3. Clique em "Nova Despesa"
4. Preencha:

**Campos disponíveis:**

- **Descrição** (obrigatório): O que você comprou/gastou
- **Valor** (obrigatório): Quanto gastou
- **Data** (obrigatório): Quando pagou
- **Categoria** (opcional): Tipo de despesa (material, mão de obra, etc.)
- **Forma de pagamento** (opcional): Como pagou

5. Salve

**Resultado esperado:** Despesa registrada, valor sai do saldo.

---

### Fluxo de Caixa

**Onde acessar:** Menu > Financeiro > Aba "Fluxo de Caixa"

**Para que serve:** Ver a previsão de dinheiro nos próximos dias/semanas.

**O que mostra:**

- Gráfico com entradas e saídas por dia
- Saldo projetado
- Alertas de quando o saldo fica negativo
- Separado por: hoje, esta semana, este mês

---

### Cobrar via WhatsApp

**Onde acessar:** Menu > Financeiro > Conta > Botão "Cobrar"

**Para que serve:** Enviar lembrete de pagamento para o cliente pelo WhatsApp.

**Passo a passo:**
1. Encontre a conta vencida ou próxima do vencimento
2. Clique em "Cobrar"
3. Escolha o modelo de mensagem
4. O sistema envia no WhatsApp do cliente

**Resultado esperado:** Cliente recebe a cobrança.

---

### Formas de Pagamento

**Onde acessar:** Menu > Financeiro > Configurações > Formas de Pagamento

**Para que serve:** Definir quais opções de pagamento você aceita.

**Passo a passo:**
1. Vá em Configurações do Financeiro
2. Clique em "Formas de Pagamento"
3. Adicione novas formas:
   - Dinheiro
   - PIX
   - Cartão de crédito
   - Cartão de débito
   - Transferência bancária
   - Boleto
4. Defina qual é a padrão
5. Adicione dados bancários se necessário (para PIX/transfers)

**Resultado esperado:** Formas disponíveis nos orçamentos.

---

### Categorias Financeiras

**Onde acessar:** Menu > Financeiro > Configurações > Categorias

**Para que serve:** Organizar receitas e despesas por tipo.

**Categorias padrão de receita:**

- Orçamento
- Serviço avulso
- Outro

**Categorias padrão de despesa:**

- Material
- Mão de obra
- Equipamento
- Transporte
- Impostos
- Outro

Você pode criar novas categorias personalizadas.

---

### Exportar Dados Financeiros

**Onde acessar:** Menu > Financeiro > Botão "Exportar"

**Para que serve:** Baixarplanilhas para controle ou para o contador.

**Passo a passo:**
1. Na aba de contas ou despesas
2. Clique em "Exportar CSV"
3. Escolha o período
4. Arquivo baixado

**Resultado esperado:** Planilha com todas as movimentações.

---

## 8. Comercial (CRM)

### O que é o Módulo Comercial?

É um sistema para gerenciar seus leads (potenciais clientes) e acompanhar todo o processo de venda, do primeiro contato até o fechamento.

---

### Dashboard Comercial

**Onde acessar:** Menu > Comercial

**Para que serve:** Ver métricas e terças do funil de vendas.

**O que mostra:**

- **Novos leads:** Contatos recentes
- **Em prospecção:** Leads sendo trabalhados
- **Proposta enviada:** Orçamentos enviados
- **Negócio ganho:** Clientes fechados
- **Negócio perdido:** Leads que não fecharam
- **Follow-ups hoje:** Tarefas de hoje
- **Lembretes:** Compromissos pendentes

---

### Criar Novo Lead

**Onde acessar:** Menu > Comercial > Botão "+ Novo Lead"

**Para que serve:** Registrar um potencial cliente que ainda não virou orçamento.

**Passo a passo:**
1. Vá em Comercial
2. Clique em "+ Novo Lead"
3. Preencha:

**Campos disponíveis:**

- **Nome** (obrigatório): Nome do lead
- **Telefone** (obrigatório): WhatsApp para contato
- **E-mail** (opcional): E-mail
- **Origem** (opcional): De onde veio (Google, indicações, Instagram, etc.)
- **Segmento** (opcional): Tipo de negócio
- **Valor estimado** (opcional): Quanto pode gastar
- **Observações** (opcional): Anotações do primeiro contato

4. Salve

**Resultado esperado:** Lead criado e aparecendo na lista.

---

### Pipeline de Leads

**Onde acessar:** Menu > Comercial > Aba "Pipeline"

**Para que serve:** Acompanhar em qual etapa cada lead está.

**Etapas do pipeline:**

1. **Novo:** Acabou de entrar
2. **Contatado:** Você falou com o cliente
3. **Qualificado:** Entendeu a necessidade
4. **Proposta:** Enviou orçamento
5. **Negociação:** Cliente está decidindo
6. **Ganho:** Fechou!
7. **Perdido:** Não fechou

**Passo a passo:**
1. Arraste o lead de uma coluna para outra
2. Ou clique no lead e mude o status
3. O sistema registra a mudança

---

### Registrar Interação

**Onde acessar:** Menu > Comercial > Lead > Aba "Interações" > "+ Nova"

**Para que serve:** Anotar tudo que acontece com o lead (ligações, mensagens, reuniões).

**Passo a passo:**
1. Clique no lead
2. Vá na aba Interações
3. Clique em "+ Nova"
4. Escolha o tipo:
   - Ligação
   - WhatsApp
   - E-mail
   - Reunião
   - Observação
5. Descreva o que aconteceu
6. Salve

**Resultado esperado:** Histórico completo de interações.

---

### Criar Lembrete

**Onde acessar:** Menu > Comercial > Aba "Lembretes" > "+ Novo Lembrete"

**Para que serve:** Agendar uma tarefa ou follow-up com um lead.

**Passo a passo:**
1. Vá em Comercial > Lembretes
2. Clique em "+ Novo"
3. Preencha:
   - **Título:** O que precisa fazer
   - **Lead:** Com qual lead
   - **Data/Hora:** Quando fazer
   - **Descrição:** Detalhes
4. Salve

**Resultado esperado:** Lembrete aparece na lista e no dashboard.

---

### Templates de Mensagem

**Onde acessar:** Menu > Comercial > Templates

**Para que serve:** Criar modelos de mensagem para usar no WhatsApp e e-mail.

**Passo a passo:**
1. Vá em Comercial > Templates
2. Clique em "+ Novo Template"
3. Crie modelos para:
   - Boas-vindas
   - Proposta enviada
   - Cobrança
   - Follow-up
4. Use variáveis como {{nome}} para personalizar
5. Salve

**Resultado esperado:** Templates disponíveis ao enviar mensagens.

---

### Enviar Mensagem em Lote

**Onde acessar:** Menu > Comercial > Aba "Campanhas"

**Para que serve:** Enviar a mesma mensagem para vários leads de uma vez.

**Passo a passo:**
1. Vá em Campanhas
2. Clique em "+ Nova Campanha"
3. Selecione os leads (por segmento, origem, status)
4. Escolha o template
5. Defina se é WhatsApp ou E-mail
6. Agende ou envie agora

**Resultado esperado:** Mensagem enviada para todos os leads selecionados.

---

## 9. Relatórios

### Relatório Geral

**Onde acessar:** Menu > Relatórios

**Para que serve:** Ver análise completa do seu negócio com gráficos e números.

**O que inclui:**

- **Faturamento:** Total recebido no período
- **Orçamentos criados:** Quantos você fez
- **Taxa de aprovação:** % que virou negócio
- **Ticket médio:** Valor médio por orçamento
- **Tempo médio de aprovação:** Dias até o cliente aceitar
- **Top clientes:** Quem gastou mais
- **Serviços mais vendidos:** Quais serviços mais aparecem

**Passo a passo:**
1. Selecione o período (este mês, último mês, este ano, personalizado)
2. Os dados atualizam automaticamente
3. Clique nos cards para ver detalhes

**Resultado esperado:** Análise visual do desempenho.

---

### Relatório de Aprovação

**Onde acessar:** Menu > Relatórios > Filtro "Aprovados"

**Para que serve:** Ver apenas os orçamentos que viraram negócio.

**Passo a passo:**
1. Clique em "Aprovados" no card do dashboard
2. See lista completa
3. Pode filtrar por período

---

## 10. Configurações da Empresa

### Dados da Empresa

**Onde acessar:** Menu > Configurações > Dados da Empresa

**Para que serve:** Preencher informações que aparecem nos orçamentos e no portal público.

**Campos disponíveis:**

- **Nome Fantasia:** Nome comercial
- **Razão Social:** Nome oficial
- **CNPJ:** Número do CNPJ
- **Telefone:** Contato principal
- **E-mail:** E-mail de contato
- **Endereço:** Endereço completo
- **Logo:** Imagem que aparece nos orçamentos
- **Cor principal:** Cor do tema do sistema

**Passo a passo:**
1. Vá em Configurações
2. Edite os dados
3. Salve

**Resultado esperado:** Dados atualizados nos orçamentos.

---

### Upload do Logo

**Onde acessar:** Menu > Configurações > Dados da Empresa > Upload de Logo

**Para que serve:** Colocar o logo da sua empresa nos orçamentos e no sistema.

**Passo a passo:**
1. Vá em Configurações > Dados da Empresa
2. Clique em "Alterar Logo"
3. Selecione uma imagem (PNG ou JPG)
4. O logo aparece na pré-visualização
5. Salve

**Resultado esperado:** Logo aparece nos orçamentos gerados.

---

### Configurações de Orçamento

**Onde acessar:** Menu > Configurações > Orçamentos

**Para que serve:** Definir padrões e regras para seus orçamentos.

**Opções disponíveis:**

- **Validade padrão:** Dias que o orçamento fica válido
- **Mostrar logo:** Se aparece ou não
- **Observações padrões:** Texto que sempre inclui
- **E-mail padrão:** Remetente dos envios

---

### Configurações de Notificações

**Onde acessar:** Menu > Configurações > Notificações

**Para que serve:** Escolher quais avisos você quer receber.

**Tipos de notificação:**

- Novo lead
- Orçamento aprovado
- Orçamento recusado
- Pagamento recebido
- Conta vencida
- Lembrete de follow-up

---

### Gerenciar Usuários

**Onde acessar:** Menu > Configurações > Usuários (ou Menu > Usuários)

**Para que serve:** Adicionar pessoas da equipe para usar o sistema.

**Passo a passo:**
1. Vá em Usuários
2. Clique em "+ Novo Usuário"
3. Preencha:
   - Nome
   - E-mail
   - Telefone
   - Permissão (Admin, Editor, Visualizador)
4. O usuário recebe convite por e-mail

**Níveis de acesso:**

- **Admin:** Acesso total
- **Editor:** Pode criar e editar tudo
- **Visualizador:** Só ver, sem editar

---

### Configurações Financeiras

**Onde acessar:** Menu > Configurações > Financeiro

**Para que serve:** Definir regras do módulo financeiro.

**Opções:**

- Cuenta bancária padrão
- Categorias personalizadas
- Modelos de cobrança
- Informações para notas fiscais

---

## 11. Assistente de IA

### Criar Orçamento via Texto

**Onde acessar:** Menu > Assistente de IA (ou pelo botão na página de orçamento)

**Para que serve:** Criar um orçamento automaticamente apenas descrevendo o serviço em linguagem natural.

**Passo a passo:**
1. Clique em "Assistente de IA"
2. Digite o que o cliente quer: "Quero instalar 5 split 12000 BTU com material incluso"
3. O sistema:
   - Identifica os serviços
   - Separa materiais de mão de obra
   - Estima valores
4. Revise e ajuste o que precisar
5. Salve como orçamento

**Resultado esperado:** Orçamento praticamente pronto em segundos.

---

## 12. Documentos

### O que são Documentos?

Sistema para armazenar arquivos como contratos, termos, apresentações que você quer enviar junto com orçamentos.

---

### Upload de Documento

**Onde acessar:** Menu > Documentos > "+ Novo"

**Para que serve:** Guardar arquivos para usar depois nos orçamentos.

**Passo a passo:**
1. Vá em Documentos
2. Clique em "+ Novo"
3. Escolha o arquivo (PDF, imagem)
4. Dê um nome
5. Defina se é público ou privado
6. Salve

**Resultado esperado:** Documento salvo e disponível.

---

### Vincular Documento ao Orçamento

**Onde acessar:** Menu > Orçamentos > Detalhes > Documentos

**Para que serve:** Anexar contratos ou outros arquivos ao enviar orçamento.

**Passo a passo:**
1. Abra o orçamento
2. Vá na seção Documentos
3. Clique em "Vincular Documento"
4. Selecione dos já enviados ou faça upload novo
5. O documento aparece no orçamento

**Resultado esperado:** Cliente baixa junto com o orçamento.

---

## 13. Notificações

### Ver Notificações

**Onde acessar:** Ícone de sino no topo da tela

**Para que serve:** Ver todos os avisos importantes do sistema.

**Tipos de notificação:**

- Novo lead criado
- Orçamento aprovado
- Orçamento recusado
- Pagamento recebido
- Lembrete de follow-up
- Orçamento expirando

**Passo a passo:**
1. Clique no ícone de sino
2. See lista de notificações
3. Clique em uma para ver detalhes
4. Marque como lida

---

## Dicas e Boas Práticas

### Para usar o sistema de forma eficiente:

1. **Mantenha o catálogo atualizado:** Cadastre todos os seus serviços com preços

2. **Use o WhatsApp conectado:** Receba mensagens de clientes automaticamente

3. **Acompanhe o pipeline:** Mude o status dos leads para saber onde cada um está

4. **Configure o financeiro desde o início:** Cadastre suas despesas para ter controle de lucro

5. **Revise relatórios semanalmente:** Veja o que está funcionando

6. **Use templates:** Crie modelos de mensagem para ganhar tempo

7. **Conecte o sistema ao contador:** Exporte dados financeiros regularmente

---

## Precisa de Ajuda?

Se tiver dúvidas sobre alguma funcionalidade:

1. **Verifique este guia** — pode ter a resposta
2. **Fale com o suporte** — equipe está disponível para ajudar
3. **Veja os tutoriais** — videos explicativos no canal do COTTE

---

*Este guia foi criado para a versão atual do sistema COTTE. Algumas funcionalidades podem variar conforme seu plano de assinatura.*
