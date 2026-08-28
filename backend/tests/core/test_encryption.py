import pytest

from app.core.encryption import (
    decrypt_secret,
    decrypt_secret_aes,
    encrypt_secret,
    encrypt_secret_aes,
)


def test_encrypt_decrypt_roundtrip():
    plaintext = "sk-test-openai-key-12345"
    encrypted = encrypt_secret(plaintext)
    assert encrypted != plaintext
    assert decrypt_secret(encrypted) == plaintext


def test_decrypt_invalid_token_raises():
    with pytest.raises(ValueError, match="Failed to decrypt"):
        decrypt_secret("not-a-valid-fernet-token")


def test_aes_encrypt_decrypt_roundtrip():
    plaintext = "sk-test-aes-key"
    ciphertext, iv, tag = encrypt_secret_aes(plaintext)
    assert decrypt_secret_aes(ciphertext=ciphertext, iv=iv, tag=tag) == plaintext
