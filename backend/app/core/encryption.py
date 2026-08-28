import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _fernet_key() -> bytes:
    if settings.CREDENTIALS_ENCRYPTION_KEY:
        return settings.CREDENTIALS_ENCRYPTION_KEY.encode()
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _aes256_key() -> bytes:
    material = settings.CREDENTIALS_ENCRYPTION_KEY or settings.SECRET_KEY
    return hashlib.sha256(material.encode()).digest()


def encrypt_secret(value: str) -> str:
    return Fernet(_fernet_key()).encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return Fernet(_fernet_key()).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt stored credential") from exc


def encrypt_secret_aes(value: str) -> tuple[bytes, bytes, bytes]:
    """AES-256-GCM: returns (ciphertext, iv, tag)."""
    iv = os.urandom(12)
    aesgcm = AESGCM(_aes256_key())
    ciphertext_with_tag = aesgcm.encrypt(iv, value.encode(), None)
    tag = ciphertext_with_tag[-16:]
    ciphertext = ciphertext_with_tag[:-16]
    return ciphertext, iv, tag


def decrypt_secret_aes(
    *, ciphertext: bytes, iv: bytes, tag: bytes
) -> str:
    aesgcm = AESGCM(_aes256_key())
    try:
        plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)
    except Exception as exc:
        raise ValueError("Failed to decrypt stored credential") from exc
    return plaintext.decode()
