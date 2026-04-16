"""
text_preprocessor.py

Parser de linguagem natural leve (regex) que extrai hints estruturados
de mensagens antes de chamar o LLM.
Exemplos reconhecidos:
  "corte por 80"
  "2 pregos a R$3,50"
  "orçamento para Ana Maria de pintura por 150"
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedHints:
    cliente: Optional[str] = None
    servico: Optional[str] = None
    preco: Optional[float] = None
    quantidade: Optional[float] = None
    raw_matches: list = field(default_factory=list)


# ── Padrões em ordem de especificidade (mais específico primeiro) ──────────
_PATTERNS = [
    # "2 pregos a R$3,50" — quantidade + serviço + preço
    (
        r"(?P<quantidade>\d+(?:[.,]\d+)?)\s+"
        r"(?P<servico>[\wÀ-ÿ][\wÀ-ÿ\s]{1,50}?)\s+"
        r"(?:por|a)\s+R?\$?\s*"
        r"(?P<preco>\d+(?:[.,]\d{1,2})?)"
    ),
    # "corte por 80" / "cabelo a R$50" — serviço + preço
    (
        r"(?P<servico>[\wÀ-ÿ][\wÀ-ÿ\s]{1,50}?)\s+"
        r"(?:por|a)\s+R?\$?\s*"
        r"(?P<preco>\d+(?:[.,]\d{1,2})?)"
    ),
    # "para Ana Maria" — cliente (nome próprio com inicial maiúscula)
    r"para\s+(?P<cliente>[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
]


def parse_message_hints(mensagem: str) -> ParsedHints:
    """Extrai hints estruturados da mensagem via regex. Não modifica a mensagem."""
    hints = ParsedHints()
    for pattern in _PATTERNS:
        m = re.search(pattern, mensagem, re.IGNORECASE)
        if not m:
            continue
        d = m.groupdict()
        hints.raw_matches.append(d)

        if "preco" in d and d["preco"] and hints.preco is None:
            try:
                hints.preco = float(d["preco"].replace(",", "."))
            except ValueError:
                pass

        if "servico" in d and d["servico"] and hints.servico is None:
            hints.servico = d["servico"].strip()

        if "cliente" in d and d["cliente"] and hints.cliente is None:
            hints.cliente = d["cliente"].strip()

        if "quantidade" in d and d["quantidade"] and hints.quantidade is None:
            try:
                hints.quantidade = float(d["quantidade"].replace(",", "."))
            except ValueError:
                pass

    return hints


def build_hint_injection(hints: ParsedHints) -> str:
    """
    Retorna bloco de texto para injetar no contexto antes de [DADOS DO SISTEMA].
    Retorna string vazia se nenhum hint foi extraído.
    """
    fields = [hints.cliente, hints.servico, hints.preco]
    if not any(f is not None for f in fields):
        return ""

    parts = ["[HINTS EXTRAÍDOS AUTOMATICAMENTE]"]
    if hints.cliente:
        parts.append(f"- Cliente detectado: {hints.cliente}")
    if hints.servico:
        parts.append(f"- Serviço detectado: {hints.servico}")
    if hints.preco is not None:
        parts.append(f"- Preço detectado: R$ {hints.preco:.2f}")
    if hints.quantidade is not None:
        parts.append(f"- Quantidade detectada: {hints.quantidade:g}")

    return "\n".join(parts)
