"""Contexto de schema do banco para o LLM SQL Planner."""

from __future__ import annotations

from typing import Any

SCHEMA_CONTEXT = """
## SCHEMA DO BANCO DE DADOS

### REGRAS OBRIGATÓRIAS:
- TODA query DEVE incluir filtro: empresa_id = :empresa_id
- Use JOINs quando precisar relacionar tabelas
- Para somas: use SUM(coluna)
- Para contagens: use COUNT(*)
- Para agrupamentos: use GROUP BY
- Período: use colunas de data (criado_em, aprovado_em, data, vencimento)
- NÃO use UNION, subqueries EXISTS/IN, CTEs (WITH), nem aliases em FROM

### Tabelas Principais (com empresa_id):

1. **servicos** (catálogo de produtos/serviços)
   - id: Integer (PK)
   - nome: String (nome do produto/serviço)
   - descricao: Text
   - preco_padrao: Numeric (valor base/preço)
   - preco_custo: Numeric (custo)
   - unidade: String (un, m², hora)
   - categoria_id: Integer (FK para categorias_catalogo)
   - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
   - ativo: Boolean

2. **orcamentos** (orçamentos/propostas comerciais)
   - id: Integer (PK)
   - numero: String (ex: ORC-150-26)
   - cliente_id: Integer (FK para clientes)
   - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
   - criado_por_id: Integer (FK para usuarios)
   - total: Numeric (valor total com desconto)
   - desconto: Numeric, desconto_tipo: String (percentual/fixo)
    - status: Enum ('RASCUNHO','ENVIADO','APROVADO','RECUSADO','EXPIRADO','CANCELADO','EM_EXECUCAO','AGUARDANDO_PAGAMENTO','CONCLUIDO')
    - forma_pagamento: Enum
   - criado_em: DateTime, atualizado_em: DateTime
   - aprovado_em: DateTime (NULL se não aprovado)
   - enviado_em: DateTime, recusa_em: DateTime
   - validade_dias: Integer
   - visualizado_em: DateTime, visualizacoes: Integer
   - origem_whatsapp: Boolean

3. **itens_orcamento** (itens de um orçamento)
   - id: Integer (PK)
   - orcamento_id: Integer (FK para orcamentos)
   - servico_id: Integer (FK para servicos)
   - descricao: String
   - quantidade: Numeric
   - valor_unit: Numeric
   - total: Numeric (quantidade * valor_unit)

4. **clientes** (clientes/cadastro)
   - id: Integer (PK)
   - nome: String, email: String, telefone: String
   - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
   - tipo_pessoa: String (PF/PJ), cpf: String, cnpj: String
   - cidade: String, estado: String
   - criado_em: DateTime

5. **commercial_leads** (leads/oportunidades do CRM)
   - id: Integer (PK)
   - nome: String, email: String, telefone: String
   - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - status: Enum ('NOVO','CONTATO_INICIADO','PROPOSTA_ENVIADA','NEGOCIACAO','FECHADO_GANHO','FECHADO_PERDIDO')
   - valor_estimado: Numeric
   - origem: String, segment_id: Integer, source_id: Integer
   - criado_em: DateTime, atualizado_em: DateTime

6. **commercial_interactions** (interações com leads)
   - id: Integer (PK)
   - lead_id: Integer (FK para commercial_leads)
   - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
   - tipo: String (ligacao, email, whatsapp, reuniao)
   - descricao: Text
   - criado_em: DateTime

7. **agendamentos** (agendamentos de serviços)
   - id: Integer (PK)
   - numero: String, empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
   - cliente_id: Integer (FK), orcamento_id: Integer (FK, nullable)
   - criado_por_id: Integer, responsavel_id: Integer (nullable)
    - status: Enum ('PENDENTE','CONFIRMADO','CANCELADO','CONCLUIDO')
    - tipo: Enum, origem: Enum
   - data_agendada: DateTime, data_fim: DateTime
   - duracao_estimada_min: Integer
   - observacoes: Text
   - criado_em: DateTime, confirmado_em: DateTime, cancelado_em: DateTime, concluido_em: DateTime

8. **contas_financeiras** (contas a receber e a pagar)
   - id: Integer (PK)
   - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
   - orcamento_id: Integer (FK, nullable)
   - tipo: Enum ('receber','pagar')
   - descricao: String, valor: Numeric, valor_pago: Numeric
    - status: Enum ('PENDENTE','PAGO','VENCIDO','CANCELADO','PARCIAL')
   - data_vencimento: Date, data_criacao: DateTime
   - categoria: String, origem: Enum
   - tipo_lancamento: String ('entrada','saldo','integral')
   - numero_parcela: Integer, total_parcelas: Integer
   - favorecido: String

9. **pagamentos_financeiros** (registros de pagamento)
   - id: Integer (PK)
   - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
   - orcamento_id: Integer (FK, nullable)
   - conta_id: Integer (FK para contas_financeiras)
   - forma_pagamento_id: Integer (FK)
   - valor: Numeric
   - tipo: Enum ('quitacao','entrada','saldo','parcela')
   - data_pagamento: Date, confirmado_em: DateTime
    - status: Enum ('CONFIRMADO','ESTORNADO','PENDENTE')
   - observacao: String

10. **movimentacoes_caixa** (entradas e saídas de caixa)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - tipo: String ('entrada','saida')
    - valor: Numeric, descricao: String
    - categoria: String, data: Date
    - confirmado: Boolean, criado_em: DateTime

11. **categorias_financeiras** (categorias de receita/despesa)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - nome: String, tipo: String ('receita','despesa','ambos')
    - cor: String, icone: String, ativo: Boolean

12. **categorias_catalogo** (categorias do catálogo de serviços)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - nome: String

13. **notificacoes** (notificações in-app)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - tipo: String ('aprovado','recusado',etc.)
    - titulo: String, mensagem: Text
    - lida: Boolean, criado_em: DateTime

14. **commercial_templates** (templates de mensagens comerciais)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - nome: String, canal: String, conteudo: Text
    - ativo: Boolean

15. **campaigns** (campanhas de disparo em massa)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - nome: String, template_id: Integer, canal: String
    - status: String ('agendada','em_andamento','concluida','cancelada')
    - total_leads: Integer, enviados: Integer, entregues: Integer
    - criado_em: DateTime

16. **formas_pagamento_config** (formas de pagamento da empresa)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - nome: String, slug: String, ativo: Boolean
    - aceita_parcelamento: Boolean, max_parcelas: Integer

17. **feedback_assistente** (feedbacks do assistente IA)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - sessao_id: String, tipo: String ('positivo','negativo')
    - comentario: Text, criado_em: DateTime

18. **tool_call_logs** (auditoria de chamadas de tools IA)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - tool: String, status: String
    - latencia_ms: Integer, input_tokens: Integer, output_tokens: Integer
    - criado_em: DateTime

19. **tenant_commercial_leads** (leads do CRM tenant)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - nome: String, email: String, telefone: String
    - etapa_id: Integer, origem_id: Integer, segmento_id: Integer
    - valor_estimado: Numeric, status: String
    - criado_em: DateTime

20. **tenant_commercial_interactions** (interações CRM tenant)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - lead_id: Integer, tipo: String, descricao: Text
    - criado_em: DateTime

21. **tenant_propostas** (propostas comerciais tenant)
    - id: Integer (PK)
    - empresa_id: Integer (FK, OBRIGATÓRIO filtrar)
    - lead_id: Integer, status: String, valor: Numeric
    - criado_em: DateTime
"""


def get_schema_context_for_llm() -> str:
    """Retorna contexto de schema para injeção no prompt do LLM."""
    return SCHEMA_CONTEXT


def get_table_hints() -> dict[str, str]:
    """Mapeamento de termos de negócio para tabelas."""
    return {
        "catalogo": "servicos",
        "catálogo": "servicos",
        "produto": "servicos",
        "produtos": "servicos",
        "serviço": "servicos",
        "servico": "servicos",
        "serviços": "servicos",
        "servicos": "servicos",
        "orcamento": "orcamentos",
        "orçamento": "orcamentos",
        "orcamentos": "orcamentos",
        "orçamentos": "orcamentos",
        "proposta": "orcamentos",
        "propostas": "orcamentos",
        "item_orcamento": "itens_orcamento",
        "itens_orcamento": "itens_orcamento",
        "cliente": "clientes",
        "clientes": "clientes",
        "lead": "commercial_leads",
        "leads": "commercial_leads",
        "oportunidade": "commercial_leads",
        "oportunidades": "commercial_leads",
        "interacao": "commercial_interactions",
        "interação": "commercial_interactions",
        "interacoes": "commercial_interactions",
        "interações": "commercial_interactions",
        "agendamento": "agendamentos",
        "agendamentos": "agendamentos",
        "agenda": "agendamentos",
        "conta a pagar": "contas_financeiras",
        "contas a pagar": "contas_financeiras",
        "conta a receber": "contas_financeiras",
        "contas a receber": "contas_financeiras",
        "conta financeira": "contas_financeiras",
        "contas financeiras": "contas_financeiras",
        "pagamento": "pagamentos_financeiros",
        "pagamentos": "pagamentos_financeiros",
        "despesa": "movimentacoes_caixa",
        "despesas": "movimentacoes_caixa",
        "receita": "movimentacoes_caixa",
        "receitas": "movimentacoes_caixa",
        "caixa": "movimentacoes_caixa",
        "movimentacao": "movimentacoes_caixa",
        "movimentações": "movimentacoes_caixa",
        "faturamento": "orcamentos",
        "venda": "orcamentos",
        "vendas": "orcamentos",
        "categoria": "categorias_catalogo",
        "categorias": "categorias_catalogo",
        "categoria financeira": "categorias_financeiras",
        "categorias financeiras": "categorias_financeiras",
        "notificacao": "notificacoes",
        "notificações": "notificacoes",
        "notificacoes": "notificacoes",
        "template": "commercial_templates",
        "templates": "commercial_templates",
        "campanha": "campaigns",
        "campanhas": "campaigns",
        "forma pagamento": "formas_pagamento_config",
        "formas pagamento": "formas_pagamento_config",
        "feedback": "feedback_assistente",
        "feedbacks": "feedback_assistente",
        "tool": "tool_call_logs",
        "tools": "tool_call_logs",
        "tenant lead": "tenant_commercial_leads",
        "tenant leads": "tenant_commercial_leads",
    }


def resolve_table_name(term: str) -> str | None:
    """Resolve um termo de negócio para o nome da tabela."""
    hints = get_table_hints()
    return hints.get(term.lower().strip())


_ALLOWED_TABLES_CACHE: dict[str, dict[str, str]] | None = None


def get_allowed_tables_for_guard() -> dict[str, dict[str, str]]:
    """Retorna mapping de tabelas permitidas para o SQL guard.
    Todas as tabelas com empresa_id são incluídas automaticamente.
    """
    global _ALLOWED_TABLES_CACHE
    if _ALLOWED_TABLES_CACHE is not None:
        return _ALLOWED_TABLES_CACHE
    tables: dict[str, dict[str, str]] = {}
    for name, hint in get_table_hints().items():
        table_name = hint
        if table_name not in tables:
            tables[table_name] = {"empresa_column": "empresa_id"}
    _ALLOWED_TABLES_CACHE = tables
    return tables
