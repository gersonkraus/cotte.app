import re


def normalize_phone_number(phone: str | None) -> str | None:
    """Normaliza para dígitos com DDI 55 (ex: 5548999887766)."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if not digits.startswith("55"):
        digits = "55" + digits
    # Número brasileiro com DDI costuma ter entre 12 e 13 dígitos.
    if len(digits) < 12 or len(digits) > 13:
        return None
    return digits
