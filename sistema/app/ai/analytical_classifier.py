"""Classifier de intenção analítica — zero latência, sem chamada LLM.

Detecta se uma mensagem requer análise SQL/multi-tool antes de entrar
nos fast-paths do hub. Suporta contexto de histórico para detectar
follow-ups analíticos mesmo quando a mensagem isolada não contém keywords.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


_ANALYTICAL_KEYWORDS: frozenset[str] = frozenset({
    # Rankings e comparações
    "ranking", "top", "mais vendido", "mais comprou", "mais compraram",
    "melhores clientes", "piores clientes", "maiores clientes",
    "melhor cliente", "pior cliente", "maior cliente",
    "top clientes", "quem mais",
    # Agrupamentos temporais
    "por mês", "por semana", "por período", "por dia", "por cliente",
    "por vendedor", "por serviço", "por status", "por categoria",
    "mês passado", "ano passado", "mês anterior", "ano anterior",
    "últimos 30", "últimos 60", "últimos 90",
    "ultimos 30", "ultimos 60", "ultimos 90",
    "entre janeiro", "entre fevereiro", "de janeiro a",
    "nos últimos", "nos ultimos",
    # Métricas e análise
    "crescimento", "média", "ticket médio", "ticket medio",
    "inadimplente", "inadimplência", "inadimplencia",
    "histórico", "historico",
    "análise", "analise", "cruzar", "cruzamento", "combinar",
    # Perguntas analíticas
    "quais clientes", "quais orçamentos", "quais orcamentos",
    "quanto faturou", "quanto gastou", "quanto gerou",
    "total por", "soma por", "agrupado", "agrupa", "agrupar",
    "relatório detalhado", "relatorio detalhado",
    "faturamento por", "receita por", "despesa por",
    # Tabelas e relatórios explícitos
    "tabela", "criar tabela", "crie uma tabela", "gerar tabela", "montar tabela",
    "gerar relatório", "gerar relatorio", "relatório de", "relatorio de",
    # Contas e registros de cliente/entidade
    "todas as contas", "contas de", "contas da", "contas do",
    "todos os registros", "todos os pagamentos",
    "todas as movimentações", "todas as movimentacoes",
    "todas as despesas", "todos os orçamentos", "todos os orcamentos",
    "todas as transações", "todas as transacoes",
    # Detalhe e extrato
    "detalhar", "detalhe de", "detalhes de", "detalhado",
    "extrato de", "extrato da", "extrato do",
    "histórico de", "historico de",
    "resumo de", "resumo da", "resumo do",
    # Status financeiro
    "vencidas", "vencidos", "vencida", "vencido",
    "em aberto", "a receber de", "a pagar de",
    "pendentes de", "pendente de",
    "consolidado", "consolidada",
    # Listagem abrangente
    "ver tudo de", "mostrar tudo de", "listar tudo de",
})

_RANKING_PATTERN = re.compile(
    r"\b("
    r"top\s*\d+"
    r"|os?\s+\d+\s+(melhores?|piores?|maiores?|menores?|primeiros?)"
    r"|\d+\s+primeiros?"
    r"|primeiros?\s+\d+"
    r")\b",
    re.IGNORECASE,
)

_MULTI_FINANCIAL_PATTERN = re.compile(
    r"(?=.*\b(saldo|caixa|financeiro|receita|faturamento|despesa)\b)"
    r"(?=.*\b(cliente|orçamento|orcamento|serviço|servico|período|periodo|mês|mes)\b)",
    re.IGNORECASE,
)

# Padrões que indicam que o último turno do assistente retornou dados reais.
# Usados para detectar contexto analítico via histórico.
_DATA_RESPONSE_INDICATORS: tuple[str, ...] = (
    "foram encontrados",
    "encontrei",
    "encontradas",
    "exibindo",          # paginação "Exibindo N itens"
    "contas a receber",
    "aqui está o relatório",
    "aqui estão",
    "movimentações financeiras",
    "saldo atual",
    "total de r$",
    "r$ ",               # valor monetário com espaço (evita falso positivo em "r$0")
    "registros encontrados",
    "agendamentos encontrados",
    "orçamentos encontrados",
    "clientes encontrados",
    "despesas encontradas",
    "resultado da busca",
)

# Keywords de follow-up — só disparam quando há contexto de dados anterior.
# Palavras conservadoras: comuns em refinamentos mas raras em comandos novos.
_FOLLOWUP_KEYWORDS: frozenset[str] = frozenset({
    "tabela", "detalhes", "detalhar", "completo", "completa",
    "filtrar", "ordenar", "id",
    "esse", "essa", "este", "esta", "dele", "dela", "deste", "desta",
    "aquele", "aquela",
})

_FOLLOWUP_PHRASES: tuple[str, ...] = (
    "todos os", "todas as",
    "ver tudo", "mostrar tudo", "listar tudo",
    "ver mais", "mostrar mais", "mais detalhes",
    "todas as contas", "todos os registros",
)


@dataclass
class HistoryContext:
    """Contexto extraído do histórico de conversa para informar o classifier."""
    is_data_context: bool = False
    last_ai_asked_question: bool = False


@dataclass
class AnalyticalIntent:
    is_analytical: bool
    confidence: float
    triggers: List[str] = field(default_factory=list)


def build_history_context(messages: list) -> HistoryContext:
    """Extrai contexto analítico das últimas mensagens da sessão. Sem LLM."""
    if not messages:
        return HistoryContext()

    # Analisa últimas 4 turns (8 mensagens) para detectar contexto de dados
    recent = messages[-8:]
    is_data_context = False
    last_ai_asked_question = False

    for msg in reversed(recent):
        role = (
            msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        ) or ""
        content = (
            msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        ) or ""

        if role != "assistant":
            continue

        content_lower = content.lower()
        if any(p in content_lower for p in _DATA_RESPONSE_INDICATORS):
            is_data_context = True

        # Detecta pergunta do assistente (pode estar em qualquer posição)
        if "?" in content:
            last_ai_asked_question = True

        break  # Analisa apenas a última mensagem do assistente

    return HistoryContext(
        is_data_context=is_data_context,
        last_ai_asked_question=last_ai_asked_question,
    )


def classify_analytical_intent(
    mensagem: str,
    *,
    history_context: Optional[HistoryContext] = None,
) -> AnalyticalIntent:
    """Classifica se a mensagem requer análise SQL/multi-tool. Sem chamada LLM.

    Aceita history_context opcional para detectar follow-ups analíticos
    mesmo quando a mensagem isolada não contém keywords explícitas.
    """
    if not mensagem or not mensagem.strip():
        return AnalyticalIntent(is_analytical=False, confidence=0.0)

    normalized = mensagem.lower().strip()
    triggers: list[str] = []

    # 1. Keywords explícitas na mensagem atual
    for keyword in _ANALYTICAL_KEYWORDS:
        if keyword in normalized:
            triggers.append(keyword)

    # 2. Padrão de ranking numérico
    if _RANKING_PATTERN.search(normalized):
        triggers.append("ranking_pattern")

    # 3. Cruzamento de tópicos financeiros
    if _MULTI_FINANCIAL_PATTERN.search(normalized):
        triggers.append("multi_financial_topic")

    # 4. Contexto de dados: follow-up de turno analítico anterior
    if history_context and history_context.is_data_context:
        words = set(normalized.split())
        matched = _FOLLOWUP_KEYWORDS & words
        if matched:
            triggers.extend(f"data_followup:{t}" for t in matched)

        for phrase in _FOLLOWUP_PHRASES:
            if phrase in normalized:
                triggers.append(f"data_followup_phrase:{phrase}")

        # Reply curta a uma pergunta da IA em contexto de dados
        # Ex: "id 1", "o primeiro", "sim", "ana julia"
        if history_context.last_ai_asked_question and len(mensagem.split()) <= 8:
            triggers.append("short_reply_in_data_context")

    if not triggers:
        return AnalyticalIntent(is_analytical=False, confidence=0.0)

    confidence = min(0.5 + len(triggers) * 0.15, 1.0)
    return AnalyticalIntent(is_analytical=True, confidence=confidence, triggers=triggers)
