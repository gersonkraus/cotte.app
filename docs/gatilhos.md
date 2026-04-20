# Gatilhos do Assistente COTTE

> Documentação completa de comandos e gatilhos para acionar relatórios, ações e visualizações no Assistente Inteligente.

---

## Índice

1. [Relatórios Dinâmicos](#1-relatórios-dinâmicos)
2. [Relatórios Financeiros Específicos](#2-relatórios-financeiros-específicos)
3. [Consultas Rápidas](#3-consultas-rápidas)
4. [Ações em Orçamentos](#4-ações-em-orçamentos)
5. [Ações Financeiras](#5-ações-financeiras)
6. [Ações em Clientes](#6-ações-em-clientes)
7. [Ações em Agendamentos](#7-ações-em-agendamentos)
8. [Ações em Catálogo](#8-ações-em-catálogo)
9. [Períodos e Filtros](#9-períodos-e-filtros)
10. [Dicas de Uso](#10-dicas-de-uso)

---

## 1. Relatórios Dinâmicos

O relatório dinâmico (`gerar_relatorio_dinamico`) é a ferramenta mais poderosa do assistente. Gera tabelas, métricas, gráficos e insights automaticamente.

### 1.1 Domínio: Orçamentos

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **Visão geral de orçamentos** | `"relatório de orçamentos"`, `"mostrar orçamentos"` |
| **Taxa de conversão** | `"taxa de conversão"`, `"conversão de orçamentos"`, `"qual a taxa de conversão"` |
| **Faturamento** | `"faturamento"`, `"total vendido"`, `"relatório de faturamento"` |
| **Ticket médio** | `"ticket médio"`, `"valor médio de venda"` |
| **Distribuição por status** | `"distribuição por status"`, `"orçamentos por status"`, `"quantos orçamentos em cada status"` |
| **Funil de conversão** | `"funil de orçamentos"`, `"funil de conversão"`, `"funil de vendas"` |
| **Evolução temporal** | `"evolução do faturamento"`, `"faturamento ao longo do tempo"`, `"gráfico de vendas"` |

#### Agrupamentos adicionais

| Agrupamento | Gatilhos |
|-------------|----------|
| **Por cliente** | `"ranking de clientes"`, `"top clientes por valor"`, `"clientes que mais compram"`, `"faturamento por cliente"` |
| **Por vendedor** | `"performance por vendedor"`, `"quem mais vende"`, `"ranking de vendedores"`, `"faturamento por vendedor"` |
| **Por serviço** | `"serviços mais vendidos"`, `"o que mais vende"`, `"ranking de serviços"`, `"faturamento por serviço"` |

---

### 1.2 Domínio: Clientes

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **Ranking por faturamento** | `"ranking de clientes"`, `"top clientes"`, `"clientes que mais compram"` |
| **Ranking por quantidade** | `"clientes por quantidade de orçamentos"`, `"quem tem mais pedidos"` |
| **Clientes inativos** | `"clientes inativos"`, `"quem não comprou"`, `"clientes parados"`, `"clientes sem movimento"` |

---

### 1.3 Domínio: Financeiro

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **Fluxo de caixa** | `"fluxo de caixa"`, `"relatório financeiro"`, `"entradas e saídas"`, `"posição financeira"` |
| **Despesas por categoria** | `"despesas por categoria"`, `"gastos por tipo"`, `"onde estou gastando"`, `"relatório de despesas"` |
| **Contas a pagar** | `"contas a pagar"`, `"despesas pendentes"`, `"a pagar"` |
| **Contas a receber** | `"contas a receber"`, `"valores a receber"`, `"a receber"` |

---

### 1.4 Domínio: Inadimplência

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **Clientes inadimplentes** | `"inadimplência"`, `"clientes inadimplentes"`, `"quem está devendo"`, `"contas em atraso"`, `"devedores"` |
| **Por faixa de atraso** | `"inadimplência por faixa"`, `"quem deve há mais tempo"`, `"inadimplência detalhada"` |
| **Total em aberto** | `"total em aberto"`, `"valor total a receber"` |

---

### 1.5 Domínio: Serviços

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **Mais vendidos por valor** | `"serviços mais vendidos"`, `"o que mais vende"`, `"ranking de serviços"` |
| **Mais vendidos por quantidade** | `"serviços por quantidade"`, `"o que mais sai"` |
| **Ticket médio por serviço** | `"ticket médio por serviço"`, `"valor médio por serviço"` |

---

### 1.6 Domínio: Agendamentos

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **Relatório geral** | `"relatório de agendamentos"`, `"status dos agendamentos"` |
| **Taxa de cancelamento** | `"taxa de cancelamento"`, `"agendamentos cancelados"`, `"índice de cancelamento"` |

---

### 1.7 Domínio: Operacional (Visão Geral)

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **KPIs da empresa** | `"resumo da empresa"`, `"KPIs"`, `"visão geral"`, `"painel operacional"`, `"dashboard"` |

---

## 2. Relatórios Financeiros Específicos

| Relatório | Gatilhos/Comandos |
|-----------|-------------------|
| **Relatório de vendas** | `"relatório de vendas"`, `"vendas do período"`, `"total vendido"` |
| **Vendas por cliente** | `"vendas por cliente"`, `"quem mais comprou"`, `"faturamento por cliente no período"` |
| **Vendas por serviço** | `"vendas por serviço"`, `"o que mais vendeu"`, `"faturamento por serviço"` |
| **Contas a receber pendentes** | `"contas a receber pendentes"`, `"valores a receber"`, `"quem me deve"` |
| **Contas vencidas** | `"contas vencidas"`, `"recebíveis atrasados"`, `"contas em atraso"` |
| **Ranking de clientes (mês vs mês)** | `"ranking de clientes do mês"`, `"melhores clientes este mês"`, `"comparativo de clientes"` |

---

## 3. Consultas Rápidas

### 3.1 Saldo e Caixa

| Consulta | Gatilhos/Comandos |
|----------|-------------------|
| **Saldo atual** | `"saldo em caixa"`, `"quanto tenho em caixa"`, `"saldo atual"`, `"ver saldo"`, `"saldo"` |
| **Movimentações** | `"movimentações de caixa"`, `"entradas e saídas"`, `"histórico financeiro"` |

### 3.2 Orçamentos

| Consulta | Gatilhos/Comandos |
|----------|-------------------|
| **Lista paginada** | `"listar orçamentos"`, `"ver orçamentos"`, `"últimos orçamentos"`, `"orçamentos recentes"` |
| **Relatório completo** | `"relatório completo de orçamentos"`, `"exportar orçamentos"`, `"todos os orçamentos"` |
| **Detalhes de um orçamento** | `"ver orçamento 104"`, `"detalhes do orçamento O-123"`, `"mostrar orçamento #50"` |
| **Por status** | `"orçamentos aprovados"`, `"orçamentos pendentes"`, `"orçamentos recusados"`, `"orçamentos rascunho"` |
| **Aprovados em data específica** | `"orçamentos aprovados ontem"`, `"orçamentos aprovados hoje"`, `"aprovações da semana"` |

### 3.3 Clientes

| Consulta | Gatilhos/Comandos |
|----------|-------------------|
| **Lista de clientes** | `"listar clientes"`, `"ver clientes"`, `"mostrar clientes"` |
| **Buscar cliente** | `"buscar cliente [nome]"`, `"procurar cliente [nome]"` |

### 3.4 Despesas

| Consulta | Gatilhos/Comandos |
|----------|-------------------|
| **Lista de despesas** | `"listar despesas"`, `"ver contas a pagar"`, `"despesas pendentes"` |
| **Despesas vencidas** | `"despesas vencidas"`, `"contas vencidas a pagar"` |

### 3.5 Agendamentos

| Consulta | Gatilhos/Comandos |
|----------|-------------------|
| **Lista de agendamentos** | `"listar agendamentos"`, `"ver agenda"`, `"agendamentos do dia"` |

### 3.6 Catálogo

| Consulta | Gatilhos/Comandos |
|----------|-------------------|
| **Lista de materiais/serviços** | `"listar catálogo"`, `"ver materiais"`, `"serviços cadastrados"`, `"catálogo"` |

---

## 4. Ações em Orçamentos

### 4.1 Criar Orçamento

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Criar com cliente e serviço** | `"criar orçamento para [cliente] de [serviço] por [valor]"` |
| **Criar com descrição livre** | `"fazer orçamento de [serviço] por [valor] para [cliente]"` |
| **Exemplos práticos** | `"orçamento de corte de cabelo a 50 reais para Maria"`, `"criar orçamento para João de pintura por 350"` |

### 4.2 Aprovar Orçamento

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Aprovar por número** | `"aprovar orçamento 104"`, `"aprovar O-123"`, `"aprovar o orçamento #50"` |

### 4.3 Recusar Orçamento

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Recusar por número** | `"recusar orçamento 104"`, `"recusar O-123"` |
| **Com motivo** | `"recusar orçamento 104 motivo cliente desistiu"` |

### 4.4 Enviar Orçamento

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Por WhatsApp** | `"enviar orçamento 104 por whatsapp"`, `"mandar pelo zap"`, `"enviar pelo whats"` |
| **Por e-mail** | `"enviar orçamento 104 por email"`, `"mandar por email"` |

### 4.5 Duplicar Orçamento

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Duplicar** | `"duplicar orçamento 104"`, `"copiar orçamento 104"` |

### 4.6 Editar Orçamento

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Alterar valor total** | `"alterar valor do orçamento 104 para 500"` |
| **Adicionar desconto** | `"dar 10% de desconto no orçamento 104"` |
| **Alterar observações** | `"adicionar observação no orçamento 104: entrega em 3 dias"` |

---

## 5. Ações Financeiras

### 5.1 Movimentações de Caixa

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Registrar entrada** | `"registrar entrada de 500 reais"`, `"entrada de 200"`, `"recebi 150 reais"` |
| **Registrar saída** | `"registrar saída de 100 reais"`, `"saída de 50"`, `"paguei 80 reais"` |

### 5.2 Despesas

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Criar despesa** | `"cadastrar despesa de 200 reais com aluguel"`, `"criar conta a pagar de 150"` |
| **Marcar como paga** | `"pagar despesa 50"`, `"marcar despesa 50 como paga"`, `"quitei a conta 50"` |

### 5.3 Recebimentos

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Registrar pagamento** | `"registrar pagamento de 300 reais na conta 45"`, `"recebi 300 do cliente"` |
| **Quitar conta** | `"quitar conta 45"`, `"pagamento total da conta 45"` |

### 5.4 Parcelamentos

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Criar parcelamento a receber** | `"criar parcelamento de 1200 em 3 vezes para cliente João"` |
| **Criar parcelamento a pagar** | `"criar parcelamento de 600 em 2 vezes com fornecedor X"` |

---

## 6. Ações em Clientes

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Cadastrar cliente** | `"cadastrar cliente Maria Silva"`, `"criar cliente João"`, `"novo cliente: Pedro"` |
| **Editar cliente** | `"editar cliente 10"`, `"alterar dados do cliente Maria"` |
| **Excluir cliente** | `"excluir cliente 10"`, `"remover cliente João"` |

---

## 7. Ações em Agendamentos

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Criar agendamento** | `"agendar para amanhã às 14h com Maria"`, `"criar agendamento para dia 15"` |
| **Cancelar agendamento** | `"cancelar agendamento 20"`, `"desmarcar agendamento 20"` |
| **Remarcar agendamento** | `"remarcar agendamento 20 para dia 18 às 10h"` |

---

## 8. Ações em Catálogo

| Ação | Gatilhos/Comandos |
|------|-------------------|
| **Cadastrar material/serviço** | `"cadastrar serviço Corte Feminino por 80"`, `"adicionar material Prego por 15"` |

---

## 9. Períodos e Filtros

### 9.1 Períodos Temporais

| Período | Exemplos de Uso |
|---------|-----------------|
| **Hoje** | `"orçamentos aprovados hoje"`, `"vendas de hoje"` |
| **Ontem** | `"orçamentos aprovados ontem"`, `"faturamento de ontem"` |
| **Últimos 7 dias** | `"últimos 7 dias"`, `"última semana"` |
| **Últimos 30 dias** | `"últimos 30 dias"`, `"último mês"`, `"no mês"` |
| **Últimos 60 dias** | `"últimos 60 dias"`, `"últimos 2 meses"` |
| **Últimos 90 dias** | `"últimos 90 dias"`, `"último trimestre"` |
| **Últimos 180 dias** | `"últimos 6 meses"`, `"semestre"` |
| **Últimos 365 dias** | `"último ano"`, `"no ano"` |

### 9.2 Filtros por Status

| Status | Gatilhos |
|--------|----------|
| **Rascunho** | `"orçamentos rascunho"`, `"em rascunho"` |
| **Enviado** | `"orçamentos enviados"`, `"pendentes"`, `"em aberto"` |
| **Aprovado** | `"orçamentos aprovados"`, `"fechados"` |
| **Recusado** | `"orçamentos recusados"`, `"rejeitados"` |

---

## 10. Dicas de Uso

### 10.1 Linguagem Natural

O assistente entende linguagem natural. Você pode:

- **Ser direto**: `"saldo"` → mostra o saldo atual
- **Ser descritivo**: `"quero ver quanto faturamos no último mês e quais clientes mais compraram"`
- **Fazer perguntas**: `"qual a taxa de conversão de orçamentos este mês?"`
- **Usar variações**: `"me mostre"`, `"quero ver"`, `"exiba"`, `"liste"`, `"mostre"`

### 10.2 Combinações

Você pode combinar filtros e agrupamentos:

```
"relatório de orçamentos aprovados do último trimestre por cliente"
"despesas por categoria dos últimos 60 dias"
"ranking de vendedores do mês"
```

### 10.3 Ações em Sequência

```
"ver orçamento 104" → "aprovar" → "enviar por whatsapp"
```

### 10.4 Correções

Se o assistente não entender corretamente:

```
"não, quero dizer o orçamento 105"
"na verdade, o cliente é Maria, não João"
```

---

## Referência Rápida

### Financeiro
| Comando | Resultado |
|---------|-----------|
| `"saldo"` | Saldo atual do caixa |
| `"fluxo de caixa"` | Relatório de entradas/saídas |
| `"inadimplência"` | Clientes devendo |
| `"despesas por categoria"` | Gastos agrupados |
| `"contas a receber"` | Valores pendentes |

### Orçamentos
| Comando | Resultado |
|---------|-----------|
| `"listar orçamentos"` | Últimos orçamentos |
| `"aprovar O-123"` | Aprova orçamento |
| `"enviar por whatsapp"` | Envia pelo WhatsApp |
| `"taxa de conversão"` | Métrica de conversão |
| `"faturamento"` | Total vendido |

### Clientes
| Comando | Resultado |
|---------|-----------|
| `"ranking de clientes"` | Top clientes |
| `"clientes inativos"` | Sem compras recentes |
| `"cadastrar cliente"` | Novo cadastro |

### Geral
| Comando | Resultado |
|---------|-----------|
| `"resumo da empresa"` | KPIs gerais |
| `"KPIs"` | Visão operacional |
| `"help"` | Ajuda |

---

## Changelog

| Data | Alteração |
|------|-----------|
| 2026-04-20 | Criação inicial do documento |

---

> **Nota**: Os gatilhos são interpretados pelo assistente via IA. Pequenas variações na forma de falar são aceitas e compreendidas naturalmente.
