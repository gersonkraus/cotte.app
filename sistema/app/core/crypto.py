import base64
import hashlib
from typing import Optional


def encrypt_secret(valor: Optional[str], crypto_secret: str = "") -> Optional[str]:
    if not valor:
        return valor
    secret = (crypto_secret or "").strip()
    if not secret:
        return valor
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    raw = str(valor).encode("utf-8")
    crypt = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
    return "encv1:" + base64.urlsafe_b64encode(crypt).decode("ascii")


def decrypt_secret(valor: Optional[str], crypto_secret: str = "") -> Optional[str]:
    if not valor:
        return valor
    if not str(valor).startswith("encv1:"):
        return valor
    secret = (crypto_secret or "").strip()
    if not secret:
        return valor
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    encoded = str(valor)[6:]
    try:
        raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except Exception:
        return valor
    plain = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
    return plain.decode("utf-8", errors="replace")
