"""Validação e cálculo de desconto em orçamentos (NEG-05)."""

from decimal import Decimal


def aplicar_desconto(subtotal: Decimal, desconto: Decimal, tipo: str) -> Decimal:
    """Retorna o total após aplicar o desconto (usa Decimal para precisão monetária)."""
    if not desconto or desconto <= 0:
        return subtotal
    if tipo == "percentual":
        return max(Decimal("0.0"), subtotal - subtotal * (Decimal(str(desconto)) / 100))
    return max(Decimal("0.0"), subtotal - Decimal(str(desconto)))


def resolver_max_percent_desconto(usuario=None, empresa=None) -> int:
    """
    Limite de desconto efetivo: primeiro do usuário, depois da empresa, depois 100.
    Por usuário: cada um pode ter seu próprio limite; None = usa o da empresa.
    """
    pct = getattr(usuario, "desconto_max_percent", None) if usuario else None
    if pct is not None:
        return pct
    pct = getattr(empresa, "desconto_max_percent", None) if empresa else None
    return pct if pct is not None else 100


def erro_validacao_desconto(
    subtotal: float,
    desconto: float,
    desconto_tipo: str,
    max_percent: int = 100,
) -> str | None:
    """
    Retorna mensagem de erro se o desconto for inválido; None se válido.
    - Percentual: desconto <= 100 e desconto <= max_percent.
    - Fixo: desconto <= subtotal.
    """
    if not desconto or desconto <= 0:
        return None
    if desconto_tipo == "percentual":
        if desconto > 100:
            return "Desconto percentual não pode ser maior que 100%."
        if desconto > max_percent:
            return f"Desconto máximo permitido pela empresa é {max_percent}%."
    else:  # fixo
        if desconto > subtotal:
            return "Desconto em reais não pode ser maior que o subtotal do orçamento."
    return None
