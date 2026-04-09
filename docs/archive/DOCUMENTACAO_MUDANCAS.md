---
title: Documentacao Mudancas
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Documentacao Mudancas
tags:
  - documentacao
prioridade: media
status: documentado
---
# Documentação das mudanças — COTTE

Este arquivo descreve as alterações e funcionalidades implementadas no sistema COTTE (backend e frontend).

---

## 1. Logo e nome da empresa no menu lateral

- **Onde:** Menu lateral (sidebar) em todas as páginas do sistema (Dashboard, Orçamentos, Clientes, Catálogo, Configurações, Equipe).
- **O que foi feito:**
  - Exibição da **logo da empresa** no topo da sidebar quando cadastrada (em Configurações ou no Admin). Se não houver logo, continua aparecendo o texto “COTTE”.
  - Substituição do texto fixo “Sistema de Orçamentos” pelo **nome da empresa** (vindo do cadastro).
  - Bloco da logo centralizado (CSS: `text-align: center`, `align-items: center`, `justify-content: center`).
- **Arquivos:** `cotte-frontend/css/style.css`, `cotte-frontend/js/api.js` (`preencherLogoSidebar`), todos os HTMLs com sidebar (incluindo `id="sidebar-logo-default"`, `id="sidebar-logo-img"`, `id="sidebar-empresa-nome"`).

---

## 2. WhatsApp Bot apenas no painel Admin

- **Onde:** Navegação do sistema.
- **O que foi feito:**
  - Removido o link **“WhatsApp Bot”** da sidebar das páginas da **empresa** (Dashboard, Orçamentos, Clientes, etc.).
  - Link **“WhatsApp Bot”** mantido apenas no **painel Admin**, para configurar/conectar o número único (Z-API) usado por todas as empresas.
- **Arquivos:** `cotte-frontend/index.html`, `orcamentos.html`, `clientes.html`, `catalogo.html`, `configuracoes.html`, `usuarios.html`, `whatsapp.html`, `admin.html`.

---

## 3. PDF após criar/editar orçamento (sem recarregar)

- **Problema:** Ao criar ou editar orçamento no modal, o PDF só aparecia após atualizar a página (geração em background e sessão do banco fechada antes do commit).
- **O que foi feito:**
  - **Backend:** A tarefa em background que gera o PDF passou a usar **sessão própria** (`SessionLocal()`), em vez da sessão da requisição, para que o `pdf_url` seja commitado corretamente.
  - **Frontend:** Após salvar (criar/editar), o sistema **aguarda o PDF ficar pronto** (polling em `GET /orcamentos/{id}`) e só então atualiza o dashboard. Ao clicar em “Ver PDF”, se o orçamento ainda não tiver `pdf_url`, é exibido “Gerando PDF...” e feito polling até o PDF estar disponível.
- **Arquivos:** `app/routers/orcamentos.py` (`_gerar_e_salvar_pdf` com sessão própria), `cotte-frontend/index.html` (`aguardarPdfPronto`, `verPdf`, `salvarOrcamento`).

---

## 4. Bot do dashboard funcional (criar orçamento e comandos)

- **Onde:** Card “Bot COTTE — WhatsApp” no Dashboard (`index.html`).
- **O que foi feito:**
  - O chat deixou de ser simulação e passou a chamar a API.
  - **Criar orçamento:** o usuário digita em linguagem natural (ex.: “Pintura 800 reais para João”); a IA extrai cliente, serviço e valor e o sistema cria o orçamento.
  - **Comandos:** interpretação em linguagem natural para:
    - **Ajuda** — lista de comandos
    - **Ver** — exibir detalhes de um orçamento (ex.: “ver 5”)
    - **Aprovar** / **Recusar** — alterar status (ex.: “aprovar 5”)
    - **Desconto** — aplicar ou remover desconto
    - **Adicionar item** / **Remover item** — alterar itens do orçamento
    - **Enviar** — enviar PDF ao cliente via WhatsApp
  - Um único endpoint **`POST /orcamentos/comando-bot`** recebe a mensagem, identifica a ação (IA) e executa (criar orçamento, aprovar, ver, etc.).
- **Arquivos:** `app/routers/orcamentos.py` (endpoint `comando-bot` e lógica das ações), `app/services/ia_service.py` (ações APROVAR e RECUSAR no prompt do operador), `cotte-frontend/index.html` (`sendMsg` chamando `comando-bot`).

---

## 5. Funcionalidades (Relatórios, Duplicar, Notificações, Exportar)

### 5.1 Relatórios

- **Backend:** `GET /relatorios/resumo?data_inicio=&data_fim=` — retorna faturamento (aprovados), quantidades por status (aprovados, recusados, enviados, rascunho, expirados, total) e faturamento **por cliente** (top 20).
- **Frontend:** Página **Relatórios** (`relatorios.html`) com filtro por período (De/Até), cards de resumo e tabela “Faturamento por cliente”.
- **Navegação:** Link “Relatórios” no menu lateral em todas as páginas aponta para `relatorios.html`.
- **Arquivos:** `app/routers/relatorios.py`, `cotte-frontend/relatorios.html`, links nos demais HTMLs.

### 5.2 Duplicar orçamento

- **Backend:** `POST /orcamentos/{id}/duplicar` — cria novo orçamento com mesmo cliente, itens, desconto e forma de pagamento; novo número e data; PDF gerado em background.
- **Frontend:** Botão **“Duplicar”** (📋) na lista de orçamentos no Dashboard e na página Orçamentos.
- **Arquivos:** `app/routers/orcamentos.py`, `cotte-frontend/index.html`, `cotte-frontend/orcamentos.html`.

### 5.3 Notificações (aprovar/recusar via WhatsApp)

- **Modelo:** Tabela **`notificacoes`** (empresa_id, orcamento_id, tipo, titulo, mensagem, lida, criado_em).
- **Backend:**
  - Ao processar **“ACEITO”** no webhook do WhatsApp: orçamento marcado como aprovado e criada notificação “Orçamento aprovado”.
  - Ao processar **recusa** (“não”, “recuso”, “desisto”, “não quero”): orçamento marcado como recusado e criada notificação “Orçamento recusado”.
  - Endpoints: `GET /notificacoes/`, `GET /notificacoes/contagem-nao-lidas`, `PATCH /notificacoes/{id}/lida`, `PATCH /notificacoes/marcar-todas-lidas`.
- **Frontend:** Ícone de **sino** (🔔) no topo das páginas (Dashboard, Orçamentos, Clientes, Relatórios); badge com quantidade de não lidas; ao clicar, dropdown com lista de notificações e “Marcar todas como lidas”.
- **Arquivos:** `app/models/models.py` (modelo `Notificacao`), `app/routers/notificacoes.py`, `app/routers/whatsapp.py` (criação de notificação e fluxo de recusa), `cotte-frontend/js/api.js` (`preencherNotificacoes`, `abrirDropdownNotificacoes`), HTMLs com `id="topbar-notificacoes"`.

### 5.4 Exportar lista (CSV)

- **Backend:**
  - `GET /orcamentos/exportar/csv?data_inicio=&data_fim=` — CSV com Número, Cliente, Total, Status, Data criação, Forma pagamento.
  - `GET /clientes/exportar/csv` — CSV com Nome, Telefone, E-mail, Cidade, Estado, Criado em.
- **Frontend:** Botão **“Exportar CSV”** na página Orçamentos e na página Clientes; download com autenticação (token no header).
- **Arquivos:** `app/routers/orcamentos.py`, `app/routers/auth_clientes.py`, `cotte-frontend/js/api.js` (`baixarExportar`), `cotte-frontend/orcamentos.html`, `cotte-frontend/clientes.html`.

---

## 6. Melhorias de UX / Interface

### 6.1 Histórico do chat do bot (localStorage)

- Mensagens do chat (usuário e bot) são salvas em **localStorage** (`cotte_chat_history`, até 50 mensagens).
- Ao abrir ou atualizar o Dashboard, o histórico é restaurado abaixo da mensagem de boas-vindas.
- **Arquivos:** `cotte-frontend/index.html` (`salvarHistoricoChat`, `carregarHistoricoChat`, `restaurarChatNaTela`, uso em `sendMsg`).

### 6.2 Paginação / “Carregar mais” na lista de orçamentos

- **Dashboard (Orçamentos Recentes):**
  - Exibição inicial de 8 orçamentos (respeitando o filtro: Todos, Pendentes, Aprovados, Enviados).
  - Botão **“Carregar mais”** abaixo da tabela quando houver mais itens; cada clique exibe mais 8.
  - Ao trocar o filtro, a contagem volta a 8.
- **Página Orçamentos:** Mantida a paginação por páginas numéricas já existente.
- **Arquivos:** `cotte-frontend/index.html` (`limiteOrcamentosVisiveis`, `_atualizarTabelaDashboard`, `carregarMaisOrcamentos`, `filtrarTabela`, bloco `#dashboard-carregar-mais`).

### 6.3 Filtro por data e busca (Orçamentos)

- Na página **Orçamentos**, foram adicionados filtros **De** e **Até** (date).
- A lista é filtrada pela data de criação do orçamento; o filtro funciona em conjunto com a busca por cliente/número e com os chips de status.
- **Arquivos:** `cotte-frontend/orcamentos.html` (inputs `filtro-data-inicio`, `filtro-data-fim`, lógica em `aplicarFiltros`).

### 6.4 Atalhos (chips) no chat do bot

- Acima do campo de digitação do chat, quatro botões:
  - **Ajuda** — envia “ajuda”.
  - **Ver último** — envia “ver {id}” do orçamento mais recente (se existir).
  - **Aprovar** — envia “aprovar 1” (usuário pode editar o número no campo).
  - **Criar orçamento** — preenche o campo com exemplo (“pintura 800 reais para João”) e foca o input.
- Estilo dos chips em `cotte-frontend/css/style.css` (classe `.chip-btn`).
- **Arquivos:** `cotte-frontend/index.html` (bloco `.wpp-chips`, `enviarChip`, `inserirChip`, `verUltimoOrcamento`), `cotte-frontend/css/style.css`.

---

## 7. Resumo de arquivos alterados

| Área              | Backend | Frontend |
|-------------------|---------|----------|
| Logo/nome sidebar | —       | `api.js`, `style.css`, todos os HTMLs com sidebar |
| WhatsApp só Admin | —       | Sidebars (index, orcamentos, clientes, catalogo, configuracoes, usuarios, whatsapp, admin) |
| PDF sem refresh   | `orcamentos.py` | `index.html` |
| Bot funcional     | `orcamentos.py`, `ia_service.py` | `index.html` |
| Relatórios        | `relatorios.py` (novo) | `relatorios.html` (novo), links |
| Duplicar          | `orcamentos.py` | `index.html`, `orcamentos.html` |
| Notificações      | `models.py`, `notificacoes.py` (novo), `whatsapp.py` | `api.js`, vários HTMLs |
| Exportar CSV      | `orcamentos.py`, `auth_clientes.py` | `api.js`, `orcamentos.html`, `clientes.html` |
| UX (histórico, carregar mais, filtro data, chips) | — | `index.html`, `orcamentos.html`, `style.css` |

---

## 8. Banco de dados

- Tabela **`notificacoes`** (criada automaticamente por `Base.metadata.create_all` na subida da API).
- Coluna **`orcamentos.approved_notification_sent_at`** (migration v19): marca o momento em que a notificação interna de aprovação foi enviada por WhatsApp, garantindo idempotência (não reenviar para a mesma aprovação).

---

## 9. Notificações internas de orçamento (refatoração)

- **Onde:** Mudança de status para aprovado ou expirado (dashboard, webhook WhatsApp, link público, PATCH status).
- **O que foi feito:**
  - **Removido:** envio de e-mail interno ao gestor quando orçamento é aprovado ou expira.
  - **Adicionado:** serviço central `quote_notification_service` que, ao detectar mudança para **aprovado**, envia uma mensagem por **WhatsApp** ao responsável pelo orçamento (criador do orçamento ou gestor da empresa). O envio é **idempotente** (campo `approved_notification_sent_at` no orçamento).
  - **Expirado:** apenas atualização de status; nenhuma notificação interna (e-mail ou WhatsApp) é enviada.
  - Resolução do destinatário: `resolve_quote_responsible_user()` (criado_por → gestor → primeiro usuário ativo). Telefone obtido do usuário ou fallback para `empresa.telefone_operador`.
  - Função `send_whatsapp_message()` no `whatsapp_service` com retorno estruturado (`SendResult`), normalização de telefone e tratamento defensivo de erros (falha do WhatsApp não quebra o fluxo principal).
- **Arquivos:** `app/services/quote_notification_service.py` (novo), `app/services/whatsapp_service.py`, `app/utils/phone.py` (novo), `app/schemas/notifications.py` (novo), `app/models/models.py`, `app/routers/orcamentos.py`, `app/routers/whatsapp.py`, `app/routers/publico.py`, `app/services/email_service.py` (removida `enviar_email_notificacao_gestor`), `main.py` (migration v19), `cotte-frontend/configuracoes.html` (removida UI de notificações por e-mail Aprovado/Expirado).
- **Timeline:** o evento "Notificação interna de aprovação enviada por WhatsApp" aparece na linha do tempo do orçamento quando aplicável.

---

## 19. Correção: Pagamento de contas a receber avulsas

- **Problema:** Ao registrar uma conta a receber avulsa (sem vínculo com orçamento) e marcá-la como "Paga" selecionando uma forma de pagamento, o sistema retornava o erro "Orçamento não identificado". Contas avulsas não devem exigir associação a orçamento para serem baixadas como pagas.

- **O que foi feito:**
  1. **Backend:** Criado novo endpoint `POST /financeiro/contas/{conta_id}/receber` para marcar contas a receber avulsas como pagas, sem exigir `orcamento_id`.
  2. **Serviço:** Implementada função `registrar_pagamento_conta_receber` no `financeiro_service.py` que:
     - Valida se a conta existe e não está paga
     - Cria registro de pagamento com `conta_id` (e `orcamento_id` como `None` quando aplicável)
     - Atualiza status da conta para `PAGO`
     - Aceita parâmetros opcionais: `valor`, `forma_pagamento_id`, `observacao`, `data_pagamento`
  3. **Frontend:** Modificada lógica no `financeiro.html`:
     - Função `abrirModalBaixa` atualizada para receber `contaId` além de `orcamentoId`
     - Variável `_baixaContaId` adicionada para armazenar ID da conta avulsa
     - Função `salvarBaixa` atualizada para usar novo endpoint quando `_baixaOrcId` é `null`
  4. **API JavaScript:** Adicionada função `receberConta` no `api-financeiro.js` para chamar o novo endpoint.

- **Arquivos modificados:**
  - `app/routers/financeiro.py` (novo endpoint `receber_conta`)
  - `app/services/financeiro_service.py` (nova função `registrar_pagamento_conta_receber`)
  - `cotte-frontend/financeiro.html` (lógica de frontend atualizada)
  - `cotte-frontend/js/api-financeiro.js` (nova função `receberConta`)

- **Impacto:** Contas a receber avulsas agora podem ser baixadas como pagas sem erro, mantendo compatibilidade com contas vinculadas a orçamentos (que continuam usando o endpoint original).

---

*Documento gerado para referência das mudanças no projeto COTTE.*
