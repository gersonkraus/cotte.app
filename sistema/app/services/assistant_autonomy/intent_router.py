"""Roteamento de intenção em domínios semânticos."""

from __future__ import annotations

import re

from app.services.assistant_autonomy.contracts import IntentDomain


_ANALYTICS_RE = re.compile(
    r"\b("
    r"relatorio|resumo|desempenho|compare|comparar|vendas|financeiro|clientes|"
    r"ranking|comparativo|comissao|comissão|indicador|metricas|métricas|"
    r"contas a receber|inadimpl|trimestre|mes|mês|funil|pipeline|leads|"
    r"produtividade|agendamento|operacao|operação|ticket medio|ticket médio"
    r")\b",
    flags=re.IGNORECASE,
)
_QUOTE_RE = re.compile(r"\b(orcamento|orçamento|proposta)\b", flags=re.IGNORECASE)
_DELIVERY_RE = re.compile(r"\b(whatsapp|e-mail|email|enviar|disparar)\b", flags=re.IGNORECASE)
_DOCUMENT_RE = re.compile(r"\b(imprimir|imprimivel|imprimível|pdf|documento)\b", flags=re.IGNORECASE)
_COMMERCIAL_RE = re.compile(
    r"\b(comercial|linguagem comercial|copy|tom comercial|proposta)\b",
    flags=re.IGNORECASE,
)
_COMPOSITE_RE = re.compile(
    r"\b(crie|gerar|gere|montar|monte|consultar|consulte|envie|enviar)\b.*\b(e|tambem|também)\b",
    flags=re.IGNORECASE,
)


def route_intent(message: str) -> IntentDomain:
    text = (message or "").strip()
    lower = text.lower()
    if not text:
        return "unknown"
    if _COMPOSITE_RE.search(lower) and (_QUOTE_RE.search(lower) or _DELIVERY_RE.search(lower)):
        return "composite_ops"
    if _DOCUMENT_RE.search(lower) and _ANALYTICS_RE.search(lower):
        return "document_ops"
    if _ANALYTICS_RE.search(text):
        return "analytics"
    if _QUOTE_RE.search(text) and _DELIVERY_RE.search(text):
        return "communication"
    if _QUOTE_RE.search(text):
        return "quote_ops"
    if _COMMERCIAL_RE.search(lower):
        return "commercial"
    return "unknown"
