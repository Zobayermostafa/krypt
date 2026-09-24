"""
Compact, dual-key handling for DRPE.

A key pair consists of two independent 32-byte secret seeds:
  - Key 1 (Spatial Phase Mask): drpe1-m1-<43 base64url chars><4 hex checksum chars>
  - Key 2 (Fourier Phase Mask): drpe1-m2-<43 base64url chars><4 hex checksum chars>

Benefits:
  - Role-tagged prefixes prevent accidental key swapping (drpe1-m1- vs drpe1-m2-).
  - 4-character checksum detects copy-paste truncation or typo before running heavy FFTs.
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
PREFIX_M1 = "drpe1-m1-"
PREFIX_M2 = "drpe1-m2-"
CHECKSUM_HEX_LEN = 4


def _compute_checksum(prefix: str, seed: bytes) -> str:
    """Compute a 4-hex-character checksum over (prefix + seed)."""
    digest = hashlib.sha256(prefix.encode("ascii") + seed).hexdigest()
    return digest[:CHECKSUM_HEX_LEN]


def generate_key_pair() -> Tuple[bytes, bytes]:
    """Generate two independent 32-byte seeds for mask1 and mask2."""
    return secrets.token_bytes(KEY_BYTES), secrets.token_bytes(KEY_BYTES)


def format_key(seed: bytes, mask_index: int) -> str:
    """Format a seed into a tagged, checksummed key string (mask_index: 1 or 2)."""
    if mask_index not in (1, 2):
        raise ValueError("mask_index must be 1 or 2")
    prefix = PREFIX_M1 if mask_index == 1 else PREFIX_M2
    encoded_seed = base64.urlsafe_b64encode(seed).decode("ascii").rstrip("=")
    checksum = _compute_checksum(prefix, seed)
    return f"{prefix}{encoded_seed}{checksum}"


def format_key_pair(seed1: bytes, seed2: bytes) -> Tuple[str, str]:
    return format_key(seed1, 1), format_key(seed2, 2)


def parse_key(text: str, expected_mask_index: int = None) -> bytes:
    """
    Parse a user-supplied key string and verify its role prefix, length, and checksum.
    If expected_mask_index is provided (1 or 2), validates that the key belongs to that mask.
    """
    text = (text or "").strip()
    
    if text.startswith(PREFIX_M1):
        actual_index = 1
        prefix = PREFIX_M1
    elif text.startswith(PREFIX_M2):
        actual_index = 2
        prefix = PREFIX_M2
    else:
        raise ValueError("Key must start with 'drpe1-m1-' or 'drpe1-m2-'.")

    if expected_mask_index is not None and actual_index != expected_mask_index:
        raise ValueError(
            f"Expected Key {expected_mask_index} ('drpe1-m{expected_mask_index}-...'), "
            f"but got Key {actual_index} ('{prefix}...'). Did you swap them?"
        )

    body = text[len(prefix):]
    expected_body_len = 43 + CHECKSUM_HEX_LEN  # 43 chars base64url + 4 chars checksum = 47
    if len(body) != expected_body_len:
        raise ValueError(
            f"Key has invalid length (expected {expected_body_len} chars after prefix, got {len(body)})."
        )

    encoded_seed = body[:43]
    provided_checksum = body[43:].lower()

    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", encoded_seed):
        raise ValueError("Key contains invalid base64 characters.")

    try:
        seed = base64.urlsafe_b64decode(encoded_seed + "=" * (-len(encoded_seed) % 4))
    except (binascii.Error, ValueError):
        raise ValueError("Key could not be decoded.")

    if len(seed) != KEY_BYTES:
        raise ValueError("Key seed length is invalid.")

    expected_checksum = _compute_checksum(prefix, seed)
    if not secrets.compare_digest(provided_checksum, expected_checksum):
        raise ValueError("Key checksum mismatch. Please check for typos or missing characters.")

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
