"""
Compact key handling for DRPE.

A key is 32 random bytes, shown to users as  drpe1-<43 base64url chars>.
Both phase masks are derived deterministically from the key with SHAKE-256
(a cryptographic extendable-output function from the standard library), so
nothing but the short key string ever needs to be stored or uploaded.

ASSUMPTION: masks are unit-magnitude complex arrays exp(1j * phase) with shape
(H, W), which is what encrypt()/decrypt() in drpe.py are assumed to expect.
If generate_random_phase_mask() returns something else (e.g. raw phase angles),
adjust the last line of derive_mask().
"""

import base64
import binascii
import hashlib
import re
import secrets

import numpy as np

KEY_PREFIX = "drpe1-"
KEY_BYTES = 32


def generate_key() -> bytes:
    return secrets.token_bytes(KEY_BYTES)


def format_key(key: bytes) -> str:
    return KEY_PREFIX + base64.urlsafe_b64encode(key).decode("ascii").rstrip("=")


def parse_key(text: str) -> bytes:
    """Parse a user-supplied key string. Raises ValueError if it is malformed."""
    text = (text or "").strip()
    if not text.startswith(KEY_PREFIX):
        raise ValueError("Key must start with 'drpe1-'.")
    body = text[len(KEY_PREFIX):]
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", body):
        raise ValueError("Key is malformed (expected 43 characters after 'drpe1-').")
    try:
        key = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
    except (binascii.Error, ValueError):
        raise ValueError("Key contains invalid characters.")
    if len(key) != KEY_BYTES:
        raise ValueError("Key has the wrong length.")
    return key


def derive_mask(key: bytes, label: bytes, shape) -> np.ndarray:
    """Deterministic unit-magnitude complex phase mask of the given (H, W) shape."""
    height, width = shape
    header = b"drpe-v1|" + label + b"|" + height.to_bytes(4, "big") + width.to_bytes(4, "big")
    stream = hashlib.shake_256(header + key).digest(4 * height * width)
    words = np.frombuffer(stream, dtype="<u4").reshape(height, width)
    phase = words.astype(np.float64) * (2.0 * np.pi / 4294967296.0)
    return np.exp(1j * phase)


def derive_masks(key: bytes, shape):
    return derive_mask(key, b"mask1", shape), derive_mask(key, b"mask2", shape)
