"""AES-256-GCM encryption for contributor API keys."""

import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes:
    """Load the 32-byte encryption key.

    Checks settings first (which reads .env), then falls back to os.environ.
    """
    hex_key = ""
    try:
        from hivemind.config import settings
        hex_key = settings.hivemind_encryption_key
    except Exception:
        pass
    if not hex_key:
        hex_key = os.environ.get("HIVEMIND_ENCRYPTION_KEY", "")
    if not hex_key:
        raise ValueError(
            "HIVEMIND_ENCRYPTION_KEY is required (set in .env or environment). "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    key = bytes.fromhex(hex_key)
    if len(key) != 32:
        raise ValueError(
            "HIVEMIND_ENCRYPTION_KEY must be exactly 32 bytes (64 hex chars)"
        )
    return key


def encrypt_api_key(plaintext: str) -> bytes:
    """Encrypt an API key using AES-256-GCM. Returns nonce + ciphertext."""
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext  # 12 bytes nonce + ciphertext


def decrypt_api_key(data: bytes) -> str:
    """Decrypt an API key. Input is nonce + ciphertext from encrypt_api_key."""
    key = _get_key()
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
