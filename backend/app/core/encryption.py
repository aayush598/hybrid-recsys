"""Encryption and key-handling utilities.

- AES-256-GCM authenticated encryption for data at rest / in transit payloads.
- API key generation and hashing (keys are stored hashed, never plaintext).
- Sensitive-field masking for safe logging and API responses.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from collections.abc import Iterable, Mapping
from typing import Any

import structlog
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = structlog.get_logger(__name__)

# AES-256 requires a 32-byte key; GCM standard nonce is 12 bytes.
_KEY_BYTES = 32
_NONCE_BYTES = 12


def _resolve_key(key: str | bytes) -> bytes:
    """Accept a raw 32-byte key or derive one via SHA-256 from any secret."""
    if isinstance(key, str):
        key = key.encode("utf-8")
    if len(key) == _KEY_BYTES:
        return key
    return hashlib.sha256(key).digest()


def encrypt_data(data: str | bytes, key: str | bytes) -> str:
    """Encrypt ``data`` with AES-256-GCM.

    Returns a URL-safe base64 string of ``nonce || ciphertext+tag``.
    """
    aes = AESGCM(_resolve_key(key))
    nonce = secrets.token_bytes(_NONCE_BYTES)
    plaintext = data.encode("utf-8") if isinstance(data, str) else data
    ciphertext = aes.encrypt(nonce, plaintext, None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_data(encrypted: str | bytes, key: str | bytes) -> str:
    """Decrypt an ``encrypt_data`` payload. Raises ``InvalidTag`` on tampering."""
    try:
        raw = base64.urlsafe_b64decode(encrypted if isinstance(encrypted, bytes) else encrypted.encode("ascii"))
    except Exception as exc:
        raise ValueError("Malformed encrypted payload") from exc
    if len(raw) < _NONCE_BYTES + 16:
        raise ValueError("Encrypted payload too short")

    aes = AESGCM(_resolve_key(key))
    plaintext = aes.decrypt(raw[:_NONCE_BYTES], raw[_NONCE_BYTES:], None)
    return plaintext.decode("utf-8")


def generate_api_key(prefix: str = "orbo") -> str:
    """Generate a random 32-byte API key as hex (optionally prefixed)."""
    return f"{prefix}_{secrets.token_hex(_KEY_BYTES)}"


def hash_api_key(key: str | bytes) -> str:
    """SHA-256 hex digest of an API key — the only form persisted server-side."""
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hashlib.sha256(key).hexdigest()


def mask_sensitive(
    data: Mapping[str, Any],
    fields: Iterable[str],
    mask_char: str = "*",
    keep_last: int = 4,
) -> dict[str, Any]:
    """Return a copy of ``data`` with sensitive fields masked.

    String values keep their last ``keep_last`` characters visible;
    everything else is fully replaced by ``mask_char`` runs.
    """
    field_set = {f.lower() for f in fields}
    masked: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in field_set and v is not None:
            s = str(v)
            if keep_last > 0 and len(s) > keep_last:
                masked[k] = mask_char * (len(s) - keep_last) + s[-keep_last:]
            else:
                masked[k] = mask_char * max(len(s), 3)
        else:
            masked[k] = v
    return masked


__all__ = [
    "decrypt_data",
    "encrypt_data",
    "generate_api_key",
    "hash_api_key",
    "mask_sensitive",
]
