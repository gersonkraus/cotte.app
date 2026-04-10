---
title: Knowledge Base
tags:
  - documentacao
prioridade: media
status: documentado
---
# Base de Conhecimento — COTTE
# Operador + Gestor (admin/superadmin fora do escopo)
# Estrutura: ## Módulo:NOME → ### Funcionalidade → Como: / Sinônimos: / Permissão:

## Template padrão por funcionalidade (usar sempre que aplicável)
- Como:
- Sinônimos:
- Permissão:
- Requisito:
- Validação:
- Erros comuns:
- Impacto financeiro:
- Estados/Transições:

## Módulo:ORCAMENTOS

### Criar orçamento manualmente
Como: Menu Orçamentos → + Novo Orçamento → aba Manual → preencha cliente, serviços, quantidade, valor unitário e validade → clique em Criar Orçamento. O número é gerado automaticamente (ex: ORC-12-26) e o status inicial é Rascunho.
Sinônimos: novo orçamento, fazer orçamento, adicionar orçamento, criar proposta, montar orçamento
Permissão: operador, gestor

### Criar orçamento por texto / IA
Como: Menu Orçamentos → + Novo Orçamento → aba "Por Texto (IA)" → descreva o pedido em linguagem natural (ex: "instalação de tomadas para João, R$ 350") → o sistema extrai os dados automaticamente.
Sinônimos: criar pelo texto, orçamento por IA, linguagem natural, criar via texto, orçamento automático
Permissão: operador, gestor

### Enviar orçamento por WhatsApp
Como: Na lista de orçamentos → clique no ícone de envio (WhatsApp) → o sistema gera um link público → envie direto pelo WhatsApp conectado ou copie o link. O cliente não precisa de login.
Sinônimos: mandar orçamento whatsapp, enviar proposta whatsapp, compartilhar orçamento, whatsapp cliente
Permissão: operador, gestor
Requisito: WhatsApp deve estar conectado para envio direto; sem conexão apenas copia o link.

### Enviar orçamento por e-mail
Como: Abra os detalhes do orçamento → clique em "Enviar por E-mail" → o sistema envia para o e-mail cadastrado do cliente.
Sinônimos: mandar email, enviar por email, e-mail cliente, email proposta
Permissão: operador, gestor
Requisito: cliente deve ter e-mail cadastrado.

### Aprovar orçamento (pelo operador)
Como: Abra os detalhes do orçamento → clique em "Aprovar". Ao aprovar, uma conta a receber é criada automaticamente no módulo Financeiro.
Sinônimos: aceitar orçamento, marcar aprovado, confirmar proposta, fechar orçamento
Permissão: operador, gestor
Validação: para aprovação pública do cliente, pode existir validação de segurança por OTP com limite de tentativas.
Estados/Transições: a mudança de status deve respeitar transições permitidas no backend.

### Recusar orçamento
Como: Abra os detalhes do orçamento → clique em "Recusar" → informe o motivo (opcional).
Sinônimos: rejeitar orçamento, marcar recusado, negar proposta, recusar proposta
Permissão: operador, gestor
Impacto financeiro: se o orçamento estava APROVADO e for recusado/desaprovado, o sistema remove automaticamente as contas a receber que ainda estavam pendentes e sem pagamento. Contas com pagamento já registrado permanecem para preservar histórico financeiro.

### Duplicar orçamento
Como: Na lista de orçamentos → clique no ícone ⋮ ao lado do orçamento → Duplicar. Um novo orçamento é criado em Rascunho com os mesmos itens, cliente e desconto, mas novo número e data.
Sinônimos: copiar orçamento, clonar orçamento, reusar orçamento, criar parecido, orçamento recorrente
Permissão: operador, gestor

### Ver histórico / linha do tempo do orçamento
Como: Na lista de orçamentos → clique no ícone 🕐 ao lado do orçamento. Mostra quando foi criado, enviado, visualizado pelo cliente, aprovado ou recusado.
Sinônimos: histórico orçamento, timeline, linha do tempo, quando foi enviado, visualizou, log orçamento
Permissão: operador, gestor

### Gerar / baixar PDF do orçamento
Como: Abra os detalhes do orçamento → clique em "Gerar PDF" ou "Baixar PDF". O PDF é gerado automaticamente com os dados da empresa e do orçamento.
Sinônimos: pdf orçamento, imprimir orçamento, baixar proposta, exportar pdf
Permissão: operador, gestor

### Filtrar e listar orçamentos
Como: Menu Orçamentos → use os filtros de status (Rascunho, Enviado, Aprovado, Recusado), cliente ou período.
Sinônimos: buscar orçamento, filtrar orçamentos, ver orçamentos, lista de orçamentos
Permissão: operador, gestor

### Exportar orçamentos em CSV
Como: Menu Orçamentos → clique em "Exportar CSV" → o arquivo é baixado com todos os orçamentos.
Sinônimos: exportar orçamentos, planilha orçamentos, csv orçamentos, download orçamentos
Permissão: operador, gestor

### Editar orçamento
Como: Na lista → clique no ícone de editar. Só é possível editar orçamentos em status Rascunho. É possível editar itens, desconto, validade e forma de pagamento.
Sinônimos: alterar orçamento, modificar proposta, editar itens, mudar valor
Permissão: operador, gestor
Observação: Orçamentos Enviados ou Aprovados não podem ser editados diretamente — duplique e recrie.
Erros comuns: tentar editar orçamento bloqueado por status.
Estados/Transições: status bloqueados devem retornar erro e orientar "duplicar e recriar".

### Aplicar desconto no orçamento
Como: Ao criar ou editar o orçamento, existe o campo "Desconto" onde você informa o valor ou percentual de desconto. O total é recalculado automaticamente.
Sinônimos: dar desconto, desconto orçamento, reduzir valor, percentual desconto
Permissão: operador, gestor

### Vincular documento ao orçamento
Como: Abra os detalhes do orçamento → clique em "Documentos" → selecione da biblioteca de documentos da empresa.
Sinônimos: anexar contrato, juntar documento, adicionar termo, vincular pdf, contrato orçamento
Permissão: operador, gestor

### Visualização pública pelo cliente (link público)
Como: Ao enviar o orçamento, o cliente recebe um link. Pelo link (sem login) o cliente vê todos os detalhes, pode aprovar, recusar ou solicitar ajuste. Também pode baixar o PDF.
Sinônimos: link cliente, proposta online, cliente ver orçamento, aprovar pelo link, link público
Permissão: qualquer pessoa com o link

### Status possíveis de orçamento
Rascunho → Enviado → Aprovado ou Recusado.
Observação: A aprovação pelo cliente pelo link público também move o status para Aprovado.

---

## Módulo:CLIENTES

### Cadastrar novo cliente
Como: Menu Clientes → + Novo Cliente → preencha nome, e-mail, telefone, CPF/CNPJ e CEP (endereço preenchido automaticamente pelo CEP) → Salvar.
Sinônimos: adicionar cliente, novo cliente, registrar cliente, cadastro cliente
Permissão: operador, gestor

### Buscar cliente
Como: Menu Clientes → use o campo de busca 🔍 para encontrar por nome, e-mail ou telefone.
Sinônimos: encontrar cliente, procurar cliente, pesquisar cliente
Permissão: operador, gestor

### Editar cliente
Como: Encontre o cliente na busca → clique em ✏️ → edite os dados → salve.
Sinônimos: alterar cliente, modificar cliente, atualizar dados cliente
Permissão: operador, gestor

### Exportar lista de clientes em CSV
Como: Menu Clientes → clique em "Exportar CSV" → o arquivo é baixado automaticamente com todos os clientes.
Sinônimos: exportar clientes, planilha clientes, csv clientes, backup clientes, lista clientes
Permissão: operador, gestor

---

## Módulo:FINANCEIRO

### Ver resumo financeiro / visão geral
Como: Menu Financeiro → aba "Visão Geral". Mostra cards: Recebido (total pago no período), A Receber (pendente), Vencido (atraso), Despesas (gastos), e gráfico de projeção de fluxo de caixa.
Sinônimos: dashboard financeiro, resumo financeiro, situação financeira, overview financeiro, quanto tenho
Permissão: operador, gestor

### Registrar pagamento de orçamento aprovado
Como: Menu Financeiro → aba A Receber → localize a conta → clique em "Registrar Pagamento" (ou "Receber") → informe valor, data e forma de pagamento → Confirmar.
Sinônimos: receber pagamento, marcar pago, registrar recebimento, quitar recebível, pago cliente
Permissão: operador, gestor

### Criar conta a receber avulsa (sem orçamento)
Como: Menu Financeiro → aba A Receber → + Nova Conta → preencha descrição, valor, vencimento e categoria → Salvar.
Sinônimos: nova conta a receber, recebível manual, entrada manual, receita avulsa
Permissão: operador, gestor

### Registrar despesa / conta a pagar
Como: Menu Financeiro → aba Despesas → + Nova Despesa → preencha descrição, categoria, valor e vencimento → Salvar.
Sinônimos: nova despesa, adicionar despesa, conta a pagar, gasto, custo, boleto, fornecedor
Permissão: operador, gestor

### Marcar despesa como paga
Como: Menu Financeiro → aba Despesas → localize a despesa → clique em "Marcar como Paga".
Sinônimos: pagar despesa, quitar despesa, confirmar pagamento despesa
Permissão: operador, gestor

### Parcelar receita ou despesa
Como: Menu Financeiro → clique em "Novo Parcelamento" → preencha descrição, valor total, número de parcelas, data da primeira parcela e categoria → Confirmar. O sistema cria uma conta por parcela automaticamente.
Sinônimos: parcelar, criar parcelas, dividir em parcelas, parcelamento, 3x, 6x, 12x, parcela mensal
Permissão: operador, gestor

### Ver fluxo de caixa
Como: Menu Financeiro → aba "Fluxo de Caixa" (ou Visão Geral). Mostra gráfico com entradas e saídas por dia, saldo projetado e alertas de saldo negativo.
Sinônimos: fluxo de caixa, projeção financeira, gráfico financeiro, saldo futuro, previsão caixa
Permissão: operador, gestor

### Exportar dados financeiros
Como: Menu Financeiro → aba A Receber ou Despesas → clique em "Exportar CSV" → escolha o período.
Sinônimos: exportar financeiro, planilha financeira, csv financeiro, dados para contador, exportar despesas
Permissão: operador, gestor

### Configurar categorias de despesa
Como: Menu Configurações → seção "Configuração Financeira" → em Categorias de Despesa, digite o nome → + Adicionar.
Sinônimos: categorias despesa, categoria gasto, classificar despesa, tipo de despesa
Permissão: gestor

### Configurar formas de pagamento
Como: Menu Configurações → seção "Formas de Pagamento" → + Nova → preencha nome (ex: "30/70"), % de entrada e % de saldo → Salvar.
Sinônimos: forma de pagamento, condição de pagamento, entrada saldo, parcelamento orçamento, condições
Permissão: gestor

### Cobrar via WhatsApp
Como: No módulo Financeiro → conta a receber → clique em "Cobrar via WhatsApp". O sistema envia uma mensagem de cobrança automática para o cliente.
Sinônimos: cobrar cliente, lembrete pagamento, cobrança whatsapp, avisar vencimento
Permissão: operador, gestor
Requisito: WhatsApp conectado e cliente com telefone cadastrado.
Erros comuns: WhatsApp desconectado, cliente sem telefone, envio recusado pelo provider.

### Estornar pagamento
Como: No financeiro, localize o pagamento já registrado e execute a ação de estorno conforme regra da conta.
Sinônimos: estorno, desfazer pagamento, reverter recebimento, cancelar baixa
Permissão: operador, gestor
Requisito: conta com pagamento já registrado.
Validação: registrar motivo e preservar trilha de auditoria.
Impacto financeiro: reabre saldo devedor e, quando vinculado a orçamento, pode reverter status comercial para pendente.
Estados/Transições: pagamento confirmado -> estornado (com atualização consistente de conta e orçamento).

### Sweep de contas vencidas (rotina)
Como: rotina de background varre contas pendentes e atualiza para vencidas quando ultrapassam a data limite.
Sinônimos: sweep, rotina vencimento, atualizar inadimplência, varredura de vencidas
Permissão: gestor
Requisito: job/trigger ativo no ambiente.
Impacto financeiro: alimenta widgets de inadimplência e fluxo de cobrança.
Estados/Transições: pendente -> vencida quando regra de vencimento for atendida.

---

## Módulo:CATALOGO

### Adicionar serviço ao catálogo
Como: Menu Catálogo → + Novo Item → preencha nome, descrição, preço padrão, unidade (un, m², hora) e categoria (opcional) → Salvar. Ao criar orçamentos, o preço é preenchido automaticamente ao selecionar o serviço.
Sinônimos: novo serviço, adicionar serviço, cadastrar produto, novo item catálogo, preço serviço
Permissão: gestor (ou operador com permissão de catálogo)

### Importar serviços em lote
Como: Menu Catálogo → clique em "Importar" → escolha colar texto (planilha Excel/Sheets) ou upload de arquivo (.csv, .xlsx, .pdf) → a IA identifica nome, preço e unidade automaticamente → revise o preview → Salvar Itens.
Sinônimos: importar serviços, upload serviços, csv catálogo, planilha serviços, bulk import
Permissão: gestor

### Criar categoria de catálogo
Como: Menu Catálogo → ao criar um item, há o campo "Categoria" onde você pode criar uma nova.
Sinônimos: categoria catálogo, grupo de serviços, tipo serviço
Permissão: gestor

### Editar serviço
Como: Menu Catálogo → encontre o serviço → clique em editar → altere os dados → Salvar.
Sinônimos: editar serviço, alterar preço, modificar item catálogo
Permissão: gestor

### Desativar serviço
Como: Menu Catálogo → encontre o serviço → clique em desativar. O serviço some do seletor ao criar orçamentos mas o histórico é preservado.
Sinônimos: desativar serviço, remover catálogo, ocultar serviço, arquivar item
Permissão: gestor

### Templates por segmento
Como: Ao importar serviços, há opção de carregar templates pré-definidos por segmento (eletricista, pintor, reformador, etc.). Menu Catálogo → Importar → ver templates disponíveis.
Sinônimos: templates catálogo, segmento, modelo de catálogo, serviços prontos
Permissão: gestor

---

## Módulo:COMERCIAL

### Criar lead
Como: Menu Comercial → aba Leads → + Novo Lead → preencha empresa/contato, telefone e origem → Salvar.
Sinônimos: novo lead, adicionar lead, cadastrar lead, prospect, oportunidade de venda
Permissão: operador, gestor

### Pipeline de vendas (CRM)
Como: Menu Comercial → aba Pipeline. Arraste o card do lead entre as colunas para avançar no funil: Novo → Contatado → Qualificado → Proposta → Negociação → Ganho / Perdido.
Sinônimos: pipeline, funil de vendas, crm, kanban leads, mover lead, avanço pipeline
Permissão: operador, gestor

### Registrar interação com lead
Como: Menu Comercial → clique no lead → aba Interações → + Nova → escolha o tipo (ligação, WhatsApp, e-mail, reunião, observação) → descreva o contato → Salvar.
Sinônimos: registrar interação, anotar contato, histórico lead, ligação lead, whatsapp lead, follow up
Permissão: operador, gestor

### Criar lembrete / follow-up
Como: Menu Comercial → clique no lead → clique em "Criar Lembrete" → defina data e descrição. O sistema avisa na data.
Sinônimos: lembrete, follow-up, agenda lead, agendar retorno, não esquecer lead
Permissão: operador, gestor

### Templates de mensagem (Comercial)
Como: Menu Comercial → aba Templates → + Novo Template → crie modelos com variáveis (ex: {{nome}}) para WhatsApp ou e-mail. Tipos: boas-vindas, proposta enviada, cobrança, follow-up.
Sinônimos: template mensagem, modelo whatsapp, mensagem padrão, texto padrão, usar variáveis
Permissão: gestor

### Enviar mensagem em lote / campanha
Como: Menu Comercial → aba Campanhas → + Nova Campanha → selecione os leads (por segmento, origem ou status) → escolha o template → defina se é WhatsApp ou e-mail → agende ou envie agora.
Sinônimos: campanha, mensagem em massa, envio em lote, broadcast leads, disparar mensagens, bulk
Permissão: gestor
Observação: Esta funcionalidade é para leads no módulo Comercial. Broadcast global para usuários do sistema (superadmin) é diferente.
Validação: segmentação e template devem ser revisados antes do envio.
Erros comuns: tentar usar campanha para base de clientes finais fora do CRM de leads.

### Campanha WhatsApp com pausas anti-bloqueio
Como: ao disparar mensagens em lote no WhatsApp, o sistema aplica pausas automáticas para reduzir risco de bloqueio.
Sinônimos: pausa campanha, anti-bloqueio whatsapp, throttle campanha, intervalo de envio
Permissão: gestor
Requisito: WhatsApp conectado e campanha de leads configurada.
Validação: respeitar limites operacionais da instância WhatsApp.

### Dashboard comercial
Como: Menu Comercial → aba Dashboard. Mostra total de leads por estágio, taxa de conversão e últimas interações.
Sinônimos: dashboard comercial, resumo comercial, visão geral vendas, métricas comerciais
Permissão: operador, gestor

---

## Módulo:DOCUMENTOS

### Subir documento (contrato, termo)
Como: Menu Documentos → + Novo Documento → preencha nome, tipo, versão → faça o upload do arquivo PDF → defina se o cliente pode baixar e se aparece na proposta → Salvar.
Sinônimos: upload documento, subir contrato, adicionar termo, documento empresa, biblioteca documentos
Permissão: operador, gestor

### Vincular documento a orçamento
Como: Dentro do modal do orçamento → clique em "Documentos" → selecione da biblioteca da empresa.
Sinônimos: anexar documento, juntar contrato, vincular termo, contrato ao orçamento
Permissão: operador, gestor

---

## Módulo:WHATSAPP

### Conectar WhatsApp (QR Code)
Como: Menu WhatsApp → clique em "Gerar QR Code" → no celular, abra WhatsApp → Dispositivos Vinculados → Vincular Dispositivo → escaneie o QR Code. Após conectar, o bot começa a funcionar automaticamente.
Sinônimos: conectar whatsapp, configurar whatsapp, qr code, vincular whatsapp, ligar whatsapp
Permissão: gestor

### Como funciona o bot automático
O bot recebe mensagens dos clientes no WhatsApp conectado, interpreta com IA, cria orçamentos automaticamente e envia o PDF. O cliente pode responder ACEITO para aprovar ou RECUSO para recusar.
Sinônimos: bot whatsapp, automação whatsapp, resposta automática, whatsapp automático, orçamento automático
Permissão: (automático, sem ação do operador)
Observação: ações críticas devem passar por confirmação humana quando aplicável.

### Pausar bot quando humano assume atendimento
Como: quando um atendente humano assume a conversa, o bot pode ser pausado temporariamente para não interferir.
Sinônimos: pausar bot, handoff humano, assumir conversa, silenciar IA no whatsapp
Permissão: operador, gestor
Estados/Transições: bot ativo -> bot pausado ate timestamp configurado -> bot ativo novamente.

### Configurar respostas automáticas / boas-vindas
Como: Menu Configurações → seção Comunicação → campo "Boas-vindas" → edite a mensagem → Salvar.
Sinônimos: mensagem automática, resposta automática, boas-vindas whatsapp, texto inicial, primeiro contato
Permissão: gestor

### Desconectar WhatsApp
Como: Menu WhatsApp → clique em "Desconectar". O bot para de funcionar.
Sinônimos: desconectar whatsapp, remover whatsapp, desligar bot
Permissão: gestor

---

## Módulo:AGENDAMENTOS

### Criar agendamento
Como: Menu Agendamentos → + Novo Agendamento → preencha data/hora, cliente e responsável → pode vincular a um orçamento aprovado (opcional) → Salvar.
Sinônimos: novo agendamento, agendar serviço, marcar data, criar agenda, programar visita
Permissão: operador, gestor

### Criar agendamento a partir de orçamento aprovado
Como: Dentro do orçamento aprovado → clique em "Agendar Serviço". O agendamento é criado já vinculado ao orçamento.
Sinônimos: agendar do orçamento, vincular agendamento, serviço agendado, data do serviço
Permissão: operador, gestor

### Listar agendamentos do dia
Como: Menu Agendamentos → aba "Hoje" ou "Dashboard". Mostra todos os agendamentos de hoje.
Sinônimos: agenda do dia, agendamentos hoje, serviços hoje, compromissos hoje
Permissão: operador, gestor

### Ver slots disponíveis
Como: Menu Agendamentos → ao criar um agendamento, o sistema mostra os horários disponíveis para a data escolhida.
Sinônimos: horário disponível, slots, horário livre, disponibilidade
Permissão: operador, gestor

### Confirmar agendamento
Como: Menu Agendamentos → localize o agendamento → altere o status para "Confirmado".
Sinônimos: confirmar agendamento, confirmar data, aceitar agendamento
Permissão: operador, gestor

### Remarcar agendamento
Como: Menu Agendamentos → localize o agendamento → clique em "Remarcar" → defina nova data/hora. O sistema cria um novo registro vinculado ao original.
Sinônimos: remarcar, adiar, mudar data, reagendar, nova data agendamento
Permissão: operador, gestor

### Cancelar agendamento
Como: Menu Agendamentos → localize o agendamento → clique em "Cancelar". Só funciona para agendamentos em status Pendente, Confirmado ou Em Andamento.
Sinônimos: cancelar agendamento, desmarcar, cancelar visita, remover agenda
Permissão: operador, gestor

### Dashboard de agendamentos
Como: Menu Agendamentos → aba Dashboard. Mostra agendamentos de hoje, pendentes de confirmação e próximos 7 dias.
Sinônimos: resumo agendamentos, visão geral agenda, calendar, calendário
Permissão: operador, gestor

### Configurar agendamentos da empresa
Como: Menu Agendamentos → Configurações → defina horário de funcionamento, duração padrão dos slots e outros parâmetros.
Sinônimos: configurar agenda, horário funcionamento, duração atendimento, configuração agendamento
Permissão: gestor

---

## Módulo:RELATORIOS

### Relatório geral
Como: Menu Relatórios → aba "Geral". Mostra indicadores consolidados: total de orçamentos, taxa de aprovação, ticket médio, receitas no período e comparativos.
Sinônimos: relatório, relatórios, indicadores, métricas, kpis, desempenho, resultados, ticket médio
Permissão: gestor (operadores precisam da permissão de relatórios habilitada)

### Relatório de aprovação
Como: Menu Relatórios → aba "Aprovação". Mostra taxa de conversão de orçamentos (enviados → aprovados).
Sinônimos: taxa aprovação, conversão orçamentos, percentual aprovação, aprovados recusados
Permissão: gestor

---

## Módulo:CONFIGURACOES

### Editar dados da empresa
Como: Menu Configurações → seção "Dados da Empresa" → edite nome, CNPJ, endereço, telefone → Salvar.
Sinônimos: dados empresa, editar empresa, informações empresa, razão social, cnpj empresa
Permissão: gestor

### Upload de logo
Como: Menu Configurações → seção "Dados da Empresa" → clique em "Upload do Logo" → selecione a imagem → Salvar. O logo aparece nos orçamentos e na proposta pública.
Sinônimos: logo, logotipo, imagem empresa, marca, logo orçamento
Permissão: gestor

### Configurações de orçamento
Como: Menu Configurações → seção "Configurações de Orçamento". Define validade padrão, template visual (moderno ou clássico) e agendamento automático.
Sinônimos: configurar orçamento, template orçamento, validade padrão, template pdf, visual orçamento
Permissão: gestor

### Personalizar textos de comunicação ao cliente
Como: Menu Configurações → seção "Comunicação" → edite: Apresentação da empresa, Assinatura de e-mail, Contato e WhatsApp, Aceite e Confiança, Boas-vindas (WhatsApp). Suporta variáveis como {{nome_empresa}}.
Sinônimos: texto cliente, comunicação, personalizar mensagem, mensagem proposta, texto email, assinatura email, rodapé
Permissão: gestor

### Gerenciar usuários da equipe
Como: Menu Usuários (no menu lateral) ou Configurações → Usuários → + Novo Usuário → preencha nome, e-mail, senha e perfil (Operador ou Gestor) → permissões específicas (catálogo, relatórios, etc.) → Salvar.
Sinônimos: adicionar usuário, novo usuário, equipe, funcionário, criar login, perfil usuário, operador gestor
Permissão: gestor
Observação: Operadores não acessam configurações globais nem gerenciam outros usuários. Gestores têm acesso completo.

### Configurações de notificações
Como: Menu Configurações → seção "Notificações". Define quais eventos geram alertas (orçamento aprovado, vencimento, etc.).
Sinônimos: notificações, alertas, avisos, configurar alertas
Permissão: gestor

---

## Módulo:NOTIFICACOES

### Ver notificações
Como: Ícone de sino (🔔) no topo do sistema → clique para ver as notificações recentes (orçamentos aprovados, vencimentos, leads, etc.).
Sinônimos: notificações, alertas, avisos, sino, ver avisos, novidades
Permissão: operador, gestor

---

## Módulo:ASSISTENTE_IA

### Criar orçamento via texto pelo assistente
Como: No assistente (chat) → descreva o pedido (ex: "Orçamento de pintura para João Silva, R$ 800") → o assistente extrai os dados e apresenta um card de confirmação. Confirme para criar.
Sinônimos: criar orçamento pelo chat, orçamento via IA, assistente criar, pedir orçamento
Permissão: operador, gestor

### Consultar dados via assistente
O assistente pode mostrar: saldo do caixa, orçamentos recentes, contas a receber, leads, agendamentos do dia e análises financeiras.
Sinônimos: perguntar ao assistente, consultar saldo, ver orçamentos assistente, dados pelo chat
Permissão: operador, gestor

### Comandos disponíveis no assistente
Exemplos: "Quanto tenho em caixa?", "Quais orçamentos estão pendentes?", "Cria orçamento de elétrica para Pedro, R$ 500", "Quais agendamentos tenho hoje?", "Como vai o faturamento?"
Sinônimos: comandos assistente, o que o assistente faz, perguntas para IA
Permissão: operador, gestor

### Regras de desambiguação e exceção do assistente
Como: quando houver dados faltantes, conflito de estado, falta de permissão ou ação sensível, o assistente deve pedir confirmação/perguntas antes de executar.
Sinônimos: confirmar ação, validar antes de executar, pedir dados faltantes, ação sensível
Permissão: operador, gestor
Validação: exigir identificadores mínimos (ex.: id/número do orçamento, cliente, valor, data) para executar ações operacionais.
Erros comuns: pedido vago ("aprova ai"), orçamento em status incompatível, usuário sem permissão, integração indisponível.
Estados/Transições: nunca forçar transição inválida; em caso de dúvida, responder com próximo passo seguro.

### Matriz de ações sensíveis (confirmação obrigatória)
- Aprovar/recusar orçamento quando houver impacto financeiro imediato.
- Registrar pagamento, estornar pagamento, cancelar conta, baixar despesa.
- Alterar status de orçamento/agendamento fora do fluxo padrão.
- Enviar cobrança ou campanha em lote via WhatsApp/e-mail.
- Qualquer operação destrutiva ou reversível com impacto de caixa.

### Checklist de execução segura (assistente)
- Confirmar permissão do usuário para a ação.
- Confirmar pré-condições (integração conectada, dados obrigatórios e status atual).
- Exibir resumo operacional antes de confirmar (cliente, entidade, valores e alterações).
- Executar e retornar resultado estruturado (sucesso/erro com causa objetiva).
- Em falha, sugerir correção acionável (ex.: conectar WhatsApp, informar dado faltante, ajustar status).

---

## Módulo:FUNCIONALIDADES_INEXISTENTES

### Funcionalidades que NÃO existem no sistema atual
- Emissão de Nota Fiscal (NFS-e): não disponível. Dados fiscais/certificado digital ainda não integrados.
- Integração com contabilidade ou ERP externo: não disponível.
- Múltiplas empresas em uma conta: não disponível. Cada conta pertence a uma empresa.
- Assinatura digital: não disponível. Aprovação é feita via link público, não assinatura eletrônica.
- Pagamento online / PIX integrado: não disponível nativamente como cobrança automática.
- App mobile dedicado: não existe. O sistema é web responsivo.
- Broadcast global para clientes finais: não disponível. Campanhas são para leads no CRM, não para clientes com orçamentos.
- Importação de leads via CSV: não disponível (importação existe apenas no catálogo).
Sinônimos: nota fiscal, nfs-e, erp, múltiplas empresas, assinatura digital, pix, app mobile, importar leads csv

---

## Governança de atualização desta base
- Fonte primária para cobertura funcional: `docs/funcionalidades.md`.
- Frequência mínima de revisão: a cada release relevante de backend/frontend.
- Processo recomendado:
  1) identificar funcionalidades novas/alteradas em `docs/funcionalidades.md`;
  2) atualizar módulos e sinônimos correspondentes nesta base;
  3) revisar ações sensíveis e checklist de execução segura;
  4) validar exemplos de prompts/comandos no Assistente IA.
- Critério de qualidade: toda funcionalidade crítica deve ter pelo menos `Como`, `Sinônimos`, `Permissão` e, quando aplicável, `Requisito`, `Validação`, `Erros comuns`, `Impacto financeiro`, `Estados/Transições`.
