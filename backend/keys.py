"""
Compact, dual-key handling for DRPE.

A key pair consists of two independent 32-byte secret seeds:
        - Both keys: <43 base64url chars>

Benefits:
    - Both keys have the same format, so their roles are not disclosed by the key text.
  - Phase masks are deterministically derived via SHAKE-256 (unit-magnitude complex exp(1j * phase)).
"""

import base64
import binascii
import hashlib
import re
import secrets
from typing import Tuple

import numpy as np

KEY_BYTES = 32


def generate_key_pair() -> Tuple[bytes, bytes]:
    """Generate two independent 32-byte seeds for mask1 and mask2."""
    return secrets.token_bytes(KEY_BYTES), secrets.token_bytes(KEY_BYTES)


def format_key(seed: bytes) -> str:
    """Format a seed into an anonymous key string."""
    encoded_seed = base64.urlsafe_b64encode(seed).decode("ascii").rstrip("=")
    return encoded_seed


def format_key_pair(seed1: bytes, seed2: bytes) -> Tuple[str, str]:
    return format_key(seed1), format_key(seed2)


def parse_key(text: str) -> bytes:
    """Parse a user-supplied anonymous key string."""
    text = (text or "").strip()

    if len(text) != 43:
        raise ValueError(
            f"Key has invalid length (expected 43 characters, got {len(text)})."
        )

    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", text):
        raise ValueError("Key contains invalid base64 characters.")

    try:
        seed = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError):
        raise ValueError("Key could not be decoded.")

    if len(seed) != KEY_BYTES:
        raise ValueError("Key seed length is invalid.")

    return seed


def derive_mask(seed: bytes, label: bytes, shape) -> np.ndarray:
    """Deterministic unit-magnitude complex phase mask of the given (H, W) shape."""
    height, width = shape
    header = b"drpe-v2|" + label + b"|" + height.to_bytes(4, "big") + width.to_bytes(4, "big")
    stream = hashlib.shake_256(header + seed).digest(4 * height * width)
    words = np.frombuffer(stream, dtype="<u4").reshape(height, width)
    phase = words.astype(np.float64) * (2.0 * np.pi / 4294967296.0)
    return np.exp(1j * phase)


def derive_masks(seed1: bytes, seed2: bytes, shape) -> Tuple[np.ndarray, np.ndarray]:
    """Derive mask1 from seed1 and mask2 from seed2."""
    return derive_mask(seed1, b"mask1", shape), derive_mask(seed2, b"mask2", shape)
