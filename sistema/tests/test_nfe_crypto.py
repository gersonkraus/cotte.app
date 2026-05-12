import pytest
from app.core.crypto import encrypt_secret, decrypt_secret


def test_encrypt_decrypt_roundtrip():
    original = "ntaas_sk_abc123secret"
    encrypted = encrypt_secret(original, crypto_secret="my-test-secret-key")
    assert encrypted.startswith("encv1:")
    assert encrypted != original
    decrypted = decrypt_secret(encrypted, crypto_secret="my-test-secret-key")
    assert decrypted == original


def test_decrypt_plain_text_returns_as_is():
    plain = "ntaas_sk_plain_value"
    result = decrypt_secret(plain, crypto_secret="my-test-secret-key")
    assert result == plain


def test_encrypt_returns_none_for_none():
    assert encrypt_secret(None, crypto_secret="key") is None


def test_encrypt_returns_empty_for_empty():
    assert encrypt_secret("", crypto_secret="key") == ""


def test_decrypt_returns_none_for_none():
    assert decrypt_secret(None, crypto_secret="key") is None


def test_decrypt_without_crypto_secret_returns_plain():
    plain = "ntaas_sk_plain_value"
    result = decrypt_secret(plain, crypto_secret="")
    assert result == plain


def test_different_secrets_fail_to_decrypt_correctly():
    encrypted = encrypt_secret("secret_value", crypto_secret="key-a")
    result = decrypt_secret(encrypted, crypto_secret="key-b")
    assert result != "secret_value"


def test_decrypt_invalid_base64_returns_as_is():
    invalid_encrypted = "encv1:not-base-64!"
    result = decrypt_secret(invalid_encrypted, crypto_secret="my-test-secret-key")
    assert result == invalid_encrypted


def test_encrypt_non_string_casts_to_string():
    integer_value = 12345
    encrypted = encrypt_secret(integer_value, crypto_secret="my-test-secret-key")
    assert encrypted.startswith("encv1:")
    decrypted = decrypt_secret(encrypted, crypto_secret="my-test-secret-key")
    assert decrypted == "12345"
