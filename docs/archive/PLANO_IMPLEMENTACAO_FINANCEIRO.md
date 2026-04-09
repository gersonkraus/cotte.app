---
title: Plano Implementacao Financeiro
tags:
  - roadmap
prioridade: alta
status: planejado
---
---
title: Plano de Implementação - Melhorias do Módulo Financeiro
tags:
  - implementacao
  - financeiro
  - planejamento
  - frontend
prioridade: alta
status: planejado
---

# Plano de Implementação - Melhorias do Módulo Financeiro

## Visão Geral
Este plano detalha as etapas para implementar as melhorias identificadas na análise do módulo financeiro, focando em usabilidade para usuários leigos e funcionalidades críticas.

## Fase 1: Melhorias Críticas (Sprint 1-2)

### Sprint 1.1: Interface Simplificada
**Objetivo**: Reduzir confusão para usuários leigos com terminologia clara e fluxos simplificados.

#### Tarefas Frontend:
1. **Redesign da Topbar** (`financeiro.html`):
   - Alterar botão "Registrar Pagamento" para "💰 Receber Pagamento"
   - Adicionar botão "📝 Nova Conta a Receber" 
   - Adicionar botão "💸 Nova Despesa" (já existe, apenas ajustar ícone)
   - Reorganizar ordem: Nova Conta → Nova Despesa → Receber Pagamento

2. **Simplificar Modal de Pagamento**:
   - Criar 3 modais separados:
     - `modal-receber-pagamento`: Para registrar pagamento recebido (simples)
     - `modal-nova-conta`: Para criar conta a receber (com wizard)
     - `modal-nova-despesa`: Já existe, apenas melhorar

3. **Wizard Nova Conta a Receber**:
   ```
   Passo 1: Tipo de Conta
     [ ] Vinculada a Orçamento (busca automática)
     [ ] Conta Avulsa (preencha manualmente)
   
   Passo 2: Dados Básicos
     - Cliente (select com busca)
     - Valor R$
     - Vencimento
     - Descrição
   
   Passo 3: Parcelamento (opcional)
     - Número de parcelas
     - Data primeira parcela
   
   Passo 4: Confirmação
     - Resumo
     - Botão Criar
   ```

#### Tarefas Backend:
1. **Endpoint Simplificado** (`/financeiro/contas/rapido`):
   ```python
   POST /financeiro/contas/rapido
   {
     "tipo": "receber",
     "cliente_id": 123,  # opcional
     "cliente_nome": "João Silva",  # se não tiver ID
     "valor": 1000.00,
     "vencimento": "2024-12-31",
     "descricao": "Serviço de pintura",
     "parcelas": 3  # opcional
   }
   ```

2. **Validação em Tempo Real**:
   - Endpoint `/financeiro/orcamentos/buscar?q=ORC-12` para buscar orçamentos
   - Validação de cliente existente

### Sprint 1.2: Funcionalidades de Gestão Básica
**Objetivo**: Implementar CRUD básico para contas.

#### Tarefas Backend:
1. **Endpoints de Edição/Exclusão**:
   ```python
   # Editar conta
   PUT /financeiro/contas/{id}
   {
     "descricao": "Nova descrição",
     "valor": 1500.00,
     "data_vencimento": "2024-12-31"
   }
   
   # Excluir conta (soft delete)
   DELETE /financeiro/contas/{id}
   {
     "motivo": "Criado por engano"
   }
   
   # Cancelar conta
   POST /financeiro/contas/{id}/cancelar
   {
     "motivo": "Cliente desistiu"
   }
   ```

2. **Atualizar Modelo `ContaFinanceira`**:
   - Adicionar campos: `excluido_em`, `excluido_por`, `motivo_exclusao`
   - Adicionar campo: `cancelado_em`, `cancelado_por`, `motivo_cancelamento`

#### Tarefas Frontend:
1. **Ações na Tabela**:
   - Adicionar dropdown "⋯" com opções:
     - Editar
     - Dar Baixa (já existe)
     - Cancelar
     - Excluir
   - Confirmação para ações destrutivas

2. **Modal de Edição**:
   - Reutilizar modal de criação com dados pré-preenchidos
   - Bloquear edição de campos relacionados a pagamentos já realizados

### Sprint 1.3: Dashboard com Saldo em Caixa
**Objetivo**: Adicionar visibilidade do caixa atual.

#### Tarefas Backend:
1. **Endpoint de Saldo**:
   ```python
   GET /financeiro/saldo
   {
     "saldo_caixa": 15230.50,
     "saldo_banco": 0,  # futuro
     "total_disponivel": 15230.50,
     "a_receber_30_dias": 8500.00,
     "a_pagar_30_dias": 3200.00,
     "projecao_30_dias": 20530.50
   }
   ```

2. **Lógica de Cálculo**:
   ```python
   saldo_caixa = (
       soma_pagamentos_recebidos - 
       soma_despesas_pagas +
       saldo_inicial_configurado
   )
   ```

#### Tarefas Frontend:
1. **Atualizar KPI Grid**:
   - Adicionar card "Saldo em Caixa" (verde/vermelho)
   - Adicionar card "Disponível 30 dias" (projeção)
   - Reorganizar ordem:
     1. Saldo em Caixa
     2. Recebido no Mês
     3. A Receber
     4. A Pagar
     5. Vencidos
     6. Disponível 30 dias

2. **Configuração de Saldo Inicial**:
   - Modal simples para definir saldo inicial
   - Apenas na primeira vez ou quando necessário

## Fase 2: Funcionalidades Avançadas (Sprint 3-4)

### Sprint 2.1: Módulo Caixa & Bancos
**Objetivo**: Sistema completo de gestão de caixa.

#### Tarefas Backend:
1. **Modelo `MovimentacaoCaixa`**:
   ```python
   class MovimentacaoCaixa(Base):
       id: int
       empresa_id: int
       tipo: Enum(ENTRADA, SAIDA)
       valor: Decimal
       descricao: str
       categoria: str  # "venda", "despesa", "transferencia", etc.
       data: date
       confirmado: bool
       comprovante_url: Optional[str]
       criado_por_id: int
       criado_em: datetime
   ```

2. **Endpoints**:
   - `GET /financeiro/caixa/movimentacoes`
   - `POST /financeiro/caixa/entrada`
   - `POST /financeiro/caixa/saida`
   - `POST /financeiro/caixa/saldo-inicial`

#### Tarefas Frontend:
1. **Nova Aba "Caixa"**:
   - Lista de movimentações
   - Filtros por data, tipo, categoria
   - Formulários simples para entrada/saída
   - Gráfico de evolução diária

2. **Conciliação Básica**:
   - Marcar movimentações como conciliadas
   - Upload de extrato CSV (futuro)

### Sprint 2.2: Categorização Flexível
**Objetivo**: Permitir categorias customizáveis.

#### Tarefas Backend:
1. **Modelo `CategoriaFinanceira`**:
   ```python
   class CategoriaFinanceira(Base):
       id: int
       empresa_id: int
       nome: str
       tipo: Enum(RECEITA, DESPESA, AMBOS)
       cor: str  # hex
       icone: str
       ativo: bool
       ordem: int
   ```

2. **Endpoints CRUD**:
   - `GET /financeiro/categorias`
   - `POST /financeiro/categorias`
   - `PUT /financeiro/categorias/{id}`
   - `DELETE /financeiro/categorias/{id}`

#### Tarefas Frontend:
1. **Gestão de Categorias**:
   - Modal de administração
   - Drag & drop para ordenação
   - Seleção por cor/ícone

2. **Integração com Formulários**:
   - Select com categorias no lugar de opções fixas
   - Criação rápida de nova categoria

### Sprint 2.3: Melhorias de UX
**Objetivo**: Polir experiência do usuário.

#### Tarefas:
1. **Validações em Tempo Real**:
   - Busca de cliente/orçamento com autocomplete
   - Validação de datas (não permitir passado para vencimento)
   - Cálculo automático de parcelas

2. **Feedback Melhorado**:
   - Toast notifications consistentes
   - Loading states em todos os botões
   - Mensagens de erro específicas

3. **Responsividade**:
   - Melhorar mobile (colapsar colunas)
   - Touch-friendly buttons

## Fase 3: Funcionalidades Empresariais (Sprint 5-6)

### Sprint 3.1: Relatórios Avançados
**Objetivo**: Sistema completo de relatórios.

#### Tarefas Backend:
1. **Endpoints de Relatórios**:
   ```python
   GET /financeiro/relatorios/fluxo-caixa?inicio=2024-01-01&fim=2024-12-31
   GET /financeiro/relatorios/despesas-por-categoria?mes=2024-12
   GET /financeiro/relatorios/inadimplencia?dias_atraso=30
   ```

2. **Exportação**:
   - PDF com gráficos
   - Excel com formatação
   - CSV melhorado

#### Tarefas Frontend:
1. **Nova Aba "Relatórios"**:
   - Filtros avançados
   - Preview do relatório
   - Opções de exportação
   - Agendamento (futuro)

### Sprint 3.2: Integração e Automação
**Objetivo**: Conectar com sistemas externos.

#### Tarefas:
1. **API Bancária** (futuro):
   - Conexão com bancos via Open Banking
   - Importação automática de transações
   - Conciliação automática

2. **Webhooks**:
   - Notificações para Slack/Teams
   - Alertas de vencimento
   - Relatórios automáticos por e-mail

## Cronograma Estimado

| Sprint | Duração | Foco | Entregáveis |
|--------|---------|------|-------------|
| 1.1 | 1 semana | Interface Simplificada | Wizard nova conta, botões claros |
| 1.2 | 1 semana | CRUD Básico | Editar/excluir/cancelar contas |
| 1.3 | 1 semana | Dashboard Caixa | KPI saldo, configuração inicial |
| 2.1 | 2 semanas | Módulo Caixa | Aba caixa, movimentações |
| 2.2 | 1 semana | Categorização | Categorias customizáveis |
| 2.3 | 1 semana | UX Polishing | Validações, feedback, mobile |
| 3.1 | 2 semanas | Relatórios | Aba relatórios, exportação |
| 3.2 | 2 semanas | Integração | APIs externas (futuro) |

**Total**: 10 semanas (2.5 meses)

## Recursos Necessários

### Equipe:
- **1 Desenvolvedor Frontend**: HTML/CSS/JavaScript
- **1 Desenvolvedor Backend**: Python/FastAPI
- **0.5 Designer UX/UI**: Protótipos, validação

### Infraestrutura:
- **Banco de Dados**: Migrações para novos modelos
- **Storage**: Para comprovantes (já existe R2)
- **Cache**: Redis para relatórios pesados

## Riscos e Mitigações

### Riscos Técnicos:
1. **Performance de Relatórios**: 
   - Mitigação: Cache agressivo, agendamento noturno
2. **Complexidade de Conciliação**:
   - Mitigação: Implementar versão simplificada primeiro
3. **Compatibilidade com Dados Existentes**:
   - Mitigação: Migrações cuidadosas, backup prévio

### Riscos de Negócio:
1. **Resistência à Mudança**:
   - Mitigação: Treinamento, documentação, suporte
2. **Curva de Aprendizado**:
   - Mitigação: Interface intuitiva, tutoriais
3. **Tempo de Desenvolvimento**:
   - Mitigação: Priorizar funcionalidades críticas

## Métricas de Sucesso

### Quantitativas:
- **Tempo para criar conta**: Reduzir de 2min para 30s
- **Erros de preenchimento**: Reduzir em 50%
- **Uso do módulo**: Aumentar em 30%
- **Inadimplência**: Reduzir em 20% com alertas

### Qualitativas:
- **Satisfação do usuário**: Pesquisa NPS > 8
- **Feedback positivo**: Redução de tickets de suporte
- **Adoção completa**: Todos os usuários usando o módulo

## Próximos Passos Imediatos

1. **Revisar análise** com stakeholders
2. **Priorizar Sprint 1.1** (mais impacto)
3. **Criar branch de desenvolvimento**
4. **Iniciar implementação do wizard**

---

*Documento criado em: 2024-03-17*
*Última atualização: 2024-03-17*
*Versão: 1.0*