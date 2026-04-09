"""
Sanitização de inputs não-confiáveis recebidos pelo webhook do WhatsApp.

SEC-05: telefones e mensagens vindos de fora nunca devem chegar às
chamadas de IA ou ao banco sem validação mínima.
"""
import re
import unicodedata

MAX_MSG_LEN = 2_000      # caracteres aceitos por mensagem
MIN_PHONE_DIGITS = 8
MAX_PHONE_DIGITS = 15


def sanitizar_telefone(raw: str | None) -> str | None:
    """
    Extrai apenas dígitos do telefone e valida o comprimento.
    Retorna a string de dígitos, ou None se inválido.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if not (MIN_PHONE_DIGITS <= len(digits) <= MAX_PHONE_DIGITS):
        return None
    return digits


def sanitizar_mensagem(raw: str | None) -> str | None:
    """
    Remove bytes nulos e caracteres de controle (exceto \\t, \\n, \\r),
    normaliza para Unicode NFC, trunca em MAX_MSG_LEN chars e elimina
    espaços extras nas bordas.
    Retorna None se o resultado for vazio.
    """
    if not raw:
        return None
    # Remove controles exceto TAB, LF, CR
    msg = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(raw))
    msg = unicodedata.normalize("NFC", msg)
    msg = msg[:MAX_MSG_LEN].strip()
    return msg or None
